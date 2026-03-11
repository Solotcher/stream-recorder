# Stream Recorder 리팩토링 종합 계획서

> **생성 일시**: 2026-03-11
> 이 문서는 `project_review.md`의 평가 결과를 바탕으로 수립된 구체적인 실행 계획입니다.
> 다음 작업 세션 시작 시 이 문서의 Phase 1부터 순차적으로 진행하면 됩니다.

---

## 📋 진행 상태 체크리스트

### Phase 1: 긴급 핫픽스 (안정성 확보)
- [ ] `channel_db.py`: `add_channel` 등 데이터를 변경하는 함수 전체를 Lock(`with _db_lock:`)으로 감싸 레이스 컨디션 방지
- [ ] `config.py`: 프로덕션 안전을 위해 `DEBUG: bool` 기본값을 `False`로 변경

### Phase 2: DRY (코드 중복 제거)
- [ ] `endpoints.py`: `start_manual_record`와 `start_recording_scheduled_manual`의 중복 로직(Extractor 생성~메타데이터조회~녹화시작)을 `services/recording_service.py` 등에 공통 함수로 추출
- [ ] `services/merger.py`: `process_remuxing`과 `process_soop_concat` 내의 FFmpeg 프로세스 실행 및 통신 비동기 대기 로직을 `_run_ffmpeg_async` 공통 함수로 통합

### Phase 3: 성능 및 예외 처리 고도화
- [ ] `main.py` (또는 별도 예외 모듈): 범용 `Exception`을 잡아내는 커스텀 `Exception Handler` 작성, 표준화된 JSON 에러 응답(`code`, `message`, `traceId`) 반환
- [ ] `extractors/base_extractor.py`: `is_live` 연쇄 호출 시 `aiohttp.ClientSession`이 불필요하게 재생성되지 않도록 클래스 레벨 보존 또는 싱글턴 세션 풀 도입

### Phase 4: 프론트엔드 개선 및 테스트
- [ ] `frontend/script.js`: `10000`, `60000` 등의 매직넘버를 파일 최상단 상수로 분리
- [ ] 코어 테스트 작성: `RecorderManager`, `scheduler`, `merger`에 대한 기본 비즈니스 로직 단위 테스트(pytest) 작성 (TestSprite 연동 오류는 추후 파악 시 수정)

---

## 🛠️ 상세 구현 계획 (Implementation Details)

### Phase 1: 긴급 핫픽스 및 설정 안전성
*   **[MODIFY] `app/utils/channel_db.py`**: `add_channel`, `update_channel`, `delete_channel` 함수 실행 시, DB 읽어오기(`get_all_channels`)부터 쓰기(`_save_all`)까지 모든 과정을 `with _db_lock:` 블록 안에 넣어 원자성(Atomicity) 보장.
*   **[MODIFY] `app/core/config.py`**: `Settings` 클래스의 `DEBUG` 필드 기본값을 `True`에서 `False`로 변경하여 향후 배포 시 혹시 모를 로깅 유출 방지.

### Phase 2: DRY (코드 중복 제거) 및 서비스 레이어 분리
*   **[MODIFY] `app/api/endpoints.py`**: `start_manual_record`와 `start_recording_scheduled_manual`의 코어 로직을 공통 서비스 함수(`start_recording_common` 등)로 빼내어 코드량을 절반으로 단축.
*   **[MODIFY] `app/services/merger.py`**: `process_remuxing`과 `process_soop_concat`에서 동일하게 사용 중인 `subprocess.Popen` 및 비동기 대기 부분, 에러 체크 부분을 내부 헬퍼 함수 `_run_ffmpeg_async(cmd, context_name)`로 통합.

### Phase 3: 예외 처리와 성능 최적화
*   **[MODIFY] `app/main.py`**: FastAPI의 글로벌 예외 핸들러(`@app.exception_handler(Exception)`)를 등록하여 알 수 없는 오류 발생 시 일관된 JSON 스키마로 응답.
*   **[MODIFY] `app/extractors/base_extractor.py`**: 현재 HTTP 요청마다 `aiohttp.ClientSession`을 새로 생성하는 비효율을 제거하기 위해 라이프사이클 안에서 세션을 재사용하는 구조로 변경.

### Phase 4: 프론트엔드 정리 및 테스트 보강
*   **[MODIFY] `frontend/script.js`**: 폴링 타이머나 재시도 딜레이 같은 매직 넘버(`10000` 등)를 스크립트 최상단에 상수로 정의.
*   **[NEW] `tests/test_recorder.py`, `tests/test_scheduler.py`**: `pytest`를 활용하여 `RecorderManager` 등의 핵심 모듈에 대한 기초 유닛 테스트 작성.

---
> **다음 세션 시작 시 지시어 예시:**
> "REFACTORING_PLAN.md 파일의 Phase 1부터 작업을 시작해줘."
