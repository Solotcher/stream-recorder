# 프로젝트 종합 평가 보고서 (Project Review)

> **프로젝트**: Stream Recorder v2.0
> **평가 일시**: 2026-03-11
> **평가 모델**: Gemini 3.1 Pro + Claude 4 Sonnet (독립 교차 검증)

---

## 1. 아키텍처 및 폴더 구조

**두 모델 모두 동의: ✅ 우수 (8/10)**

- FastAPI 기반 백엔드를 `extractors`, `core`, `services`, `utils`로 역할별 분리 — 명확한 계층 구조
- `BaseExtractor` ABC 추상 클래스로 4개 플랫폼(치지직, 트위치, 숲, 유튜브)을 일관된 인터페이스로 통합
- `lifespan` 비동기 컨텍스트 매니저 채택 (FastAPI 최신 권장 패턴)
- WebSocket 이벤트 버스(`event_bus.py`)가 깔끔한 싱글턴 + 헬퍼 함수 패턴

**개선 필요:**

| 지적 사항 | Gemini | Claude | 비고 |
|-----------|--------|--------|------|
| `script.js` 500줄+ 모놀리식 → 기능별 분리 권장 | ⚠️ | ⚠️ | 동의, 단 현 규모에서는 치명적이진 않음 |
| `RecorderManager` 상태를 Redis로 분리 | ⚠️ | 🤔 반론 | 단일 인스턴스 앱에서 **과잉 설계** — 현재 `active_pids.json` 영속화로 충분 |
| `trigger_recording()`이 `scheduler.py`에 위치 | — | ⚠️ | 별도 `recording_service.py`로 분리하는 게 적절 (Claude만 지적) |

---

## 2. DRY 원칙 (중복 제거)

**두 모델 모두 동의: ⚠️ 가장 시급한 개선 (5/10)**

### 2-1. endpoints.py 녹화 시작 로직 중복 (공통 지적)

`start_manual_record` (L176~L215)과 `start_recording_scheduled_manual` (L217~L251)의 핵심 흐름이 80% 이상 동일:

```
ExtClass 로드 → Extractor 생성 → is_live() → get_metadata() → trigger_recording()
```

→ **해결**: 공통 서비스 함수 `_initiate_recording(channel_id, platform, ...)` 추출

### 2-2. merger.py FFmpeg 실행 패턴 중복 (Claude만 추가 발견)

`process_remuxing`과 `process_soop_concat` 내부의 FFmpeg 실행 패턴이 동일:

```python
proc = subprocess.Popen(cmd, stdout=DEVNULL, stderr=PIPE)
def _wait_proc(): _, stderr = proc.communicate(); return proc.returncode, stderr
returncode, stderr_bytes = await asyncio.to_thread(_wait_proc)
# → 무결성 검증 → 성공/실패 분기 → 업로드 트리거
```

→ **해결**: `_run_ffmpeg_async(cmd, channel_name)` 공통 함수로 추출

---

## 3. 동시성 / 데이터 무결성

**Claude만 추가 지적: ⚠️ (6/10)**

### channel_db.py 레이스 컨디션

```python
def add_channel(channel_data):
    channels = get_all_channels()  # ← Lock 획득 후 "해제됨"
    # ... 중복 체크 (Lock 없이 진행) ...
    channels.append(channel_data)
    _save_all(channels)             # ← 다시 Lock 획득
```

`get_all_channels()`와 `_save_all()` 사이에 **Lock이 풀려** 있어 동시 요청 시 데이터 유실 가능.

→ **해결**: 전체 read-modify-write를 하나의 Lock 범위(`with _db_lock:`)로 감싸기

---

## 4. 예외 처리 및 로깅

**두 모델 모두 동의: ⚠️ (6/10)**

**잘된 점:**
- `app.core.logger`를 통한 일관된 로깅
- 텔레그램(`send_error_alert`)으로 장애 알림
- 리먹싱 실패 시 원본 `.ts` 파일 보존 전략

**개선 필요:**
- `except Exception as e:` 범용 처리 후 `str(e)`를 직접 500 응답으로 반환하는 패턴
- **표준 에러 응답 포맷**(`code`, `message`, `traceId`)과 **Global Exception Handler** 도입 필요

---

## 5. 리소스 관리

**Claude만 추가 지적: ⚠️ (6/10)**

### aiohttp 세션 낭비

`BaseExtractor._fetch_json()`이 호출마다 새 `ClientSession`을 생성/소멸:

```python
async with aiohttp.ClientSession(headers=req_headers) as session:
    # 매번 TCP 핸드셰이크 발생
```

`is_live()` → `get_metadata()` 순서 호출 시 **불필요한 세션 2회 재생성**.

→ **해결**: Extractor 인스턴스 수명에 맞춘 세션 재사용 또는 루프 내 공유

---

## 6. 매직 넘버

**두 모델 모두 동의: ⚠️ (7/10)**

`script.js`에 `10000`(폴링 간격), `60000`(활성 작업 갱신), `30000`(WS 최대 딜레이) 등이 로직 중간에 하드코딩.

> 참고: `WS_MAX_RECONNECT_DELAY`는 이미 상수화되어 있음 (L465). 나머지도 동일하게 처리 필요.

→ **해결**: 파일 최상단에 `const CHANNEL_POLL_MS = 10000;` 등으로 통일

---

## 7. 보안

**공통 평가: ✅ 기본 조치 양호 (7/10)**

- ✅ API Key 미들웨어, 토큰 마스킹, XSS(`escapeHtml`) 적용
- ⚠️ `config.py`에 `DEBUG: bool = True`가 **기본값** — 프로덕션 배포 시 위험 (Claude만 지적)
- ⚠️ CORS가 `localhost:8000`만 허용하지만, 같은 포트에서 프론트엔드도 서빙되어 CORS 자체가 불필요한 구조

---

## 8. 테스트

**Claude만 심층 지적: ❌ 가장 취약 (2/10)**

- 테스트 파일이 `test_cookie_manager.py` **단 1개** (1,466바이트)
- 핵심 비즈니스 로직(`RecorderManager`, `scheduler`, `merger`)에 테스트 **전무**
- 사용자 자체 기준(핵심 로직 90% 커버리지) 대비 **현저히 부족**

---

## 9. 비동기 안정성

**두 모델 모두 동의: ✅ 우수 (8/10)**

- `subprocess.Popen` + `asyncio.to_thread` 조합으로 Windows `SelectorEventLoop` 호환 문제 해결
- PID 파일 영속화 + 서버 재시작 시 Re-attach 패턴
- 리먹싱 실패 시 원본 보존 정책 (장애 격리 우수)

---

## 10. 프론트엔드

**공통 평가: ✅ 미적 완성도 높음 (7/10)**

- ✅ Glassmorphism 다크 테마, CSS 변수 시스템, `fadeIn` 애니메이션
- ✅ WebSocket 지수 백오프 재연결
- ⚠️ `switchMainTab()`에서 `event` 암시적 전역 참조 (Claude만 지적)
- ⚠️ `onclick` 핸들러에 채널 ID 직접 삽입 — 특수문자 포함 시 깨질 위험

---

## 📊 종합 점수 비교

| 카테고리 | Gemini 3.1 Pro | Claude 4 Sonnet | 합산 평균 |
|----------|:-:|:-:|:-:|
| 아키텍처 | 8 | 8 | **8.0** |
| DRY / 코드 품질 | 5 | 5 | **5.0** |
| 동시성 안정성 | — | 6 | **6.0** |
| 예외 처리 | 6 | 6 | **6.0** |
| 리소스 관리 | — | 6 | **6.0** |
| 보안 | 7 | 7 | **7.0** |
| 테스트 | — | 2 | **2.0** |
| 비동기 안정성 | 8 | 8 | **8.0** |
| 프론트엔드 | 7 | 7 | **7.0** |
| **종합** | | | **6.1 / 10** |

---

## 🎯 우선순위 리팩토링 로드맵

| 순위 | 작업 | 긴급도 | 난이도 |
|:----:|------|:------:|:------:|
| 1 | `endpoints.py` 중복 녹화 로직 → 공통 서비스 함수 추출 | 🔴 긴급 | ⭐⭐ |
| 2 | `channel_db.py` Lock 범위 확대 (원자성 보장) | 🔴 긴급 | ⭐ |
| 3 | `merger.py` FFmpeg 실행 공통 함수 추출 | 🟡 중요 | ⭐⭐ |
| 4 | 핵심 로직 단위 테스트 추가 | 🟡 중요 | ⭐⭐⭐ |
| 5 | Global Exception Handler 도입 | 🟡 중요 | ⭐⭐ |
| 6 | `config.py` DEBUG 기본값 False로 변경 | 🟢 권장 | ⭐ |
| 7 | aiohttp 세션 재사용 패턴 적용 | 🟢 권장 | ⭐⭐ |
| 8 | `script.js` 매직 넘버 상수화 | 🟢 권장 | ⭐ |
