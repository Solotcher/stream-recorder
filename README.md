# Stream Recorder (다중 플랫폼 자동 녹화기)

치지직(Chzzk), 아프리카TV(SOOP), 트위치(Twitch), **유튜브(YouTube)** 방송을 모니터링하고 자동으로 녹화하는 웹 애플리케이션입니다.

> [!WARNING]
> **SOOP(아프리카TV) 플랫폼 안내**: 현재 SOOP의 녹화 로직에 문제가 있어 원활한 녹화가 이루어지지 않을 수 있습니다. 녹화 로직 및 세그먼트 처리 방식이 아직 원활하지 않으니 사용 시 참고 부탁드립니다.

## 주요 특징

- **다중 플랫폼 지원**: Chzzk, SOOP, Twitch, **YouTube** 완벽 대응.
- **자동 녹화**: 스트리머가 방송을 시작하면 자동으로 감지하여 녹화를 시작합니다.
- **의존성 자동 관리**: FFmpeg, Streamlink, yt-dlp가 없어도 실행 시 자동으로 환경에 맞춰 다운로드 및 설정됩니다.
- **MP4 자동 리먹싱**: 녹화 완료(또는 강제 종료) 후 고화질 유지 및 스트리밍에 최적화된 MP4 형식으로 자동 변환합니다.
- **후처리 안전 보호**: 리먹싱/병합 실패 시에도 원본 파일이 안전하게 보존되며, FFmpeg 에러 로그가 기록됩니다.
- **파일명 커스터마이징**: `{date}`, `{streamer}`, `{title}`, `{quality}` 등 다양한 변수를 조합한 파일명 규칙 설정 가능.
- **웹 UI 제공**: 브라우저에서 간편하게 스트리머 추가, 쿠키 관리, 설정 변경이 가능합니다.
- **안정적인 프로세스 관리**: 서버 재시작 시에도 기존 녹화 중인 프로세스를 자동으로 감지하여 연결을 유지합니다.
- **클라우드 자동 업로드**: rclone 연동으로 녹화 완료 후 구글 드라이브 등 클라우드에 자동 백업.

---

## 설치 및 실행 방법 (Requirement: Python 3.10+)

### 1. Windows (윈도우)

1. 저장소 클론: `git clone https://github.com/Solotcher/stream-recorder.git`
2. 해당 폴더로 이동: `cd stream-recorder`
3. **방법 A (배치 파일)**: `start.bat` 실행 (자동으로 가상환경 구축 후 서버 실행)
4. **방법 B (파워쉘)**: `PowerShell -ExecutionPolicy Bypass -File start.ps1` 실행

### 2. Linux (리눅스 / Ubuntu, OCI 등)

```bash
# 저장소 클론
git clone https://github.com/Solotcher/stream-recorder.git
cd stream-recorder

# 실행 권한 부여 및 실행
chmod +x start.sh
./start.sh
```

이 스크립트는 내부적으로 가상환경(`.venv`) 생성, 필수 패키지 설치, `.env` 기본값 설정을 모두 자동으로 수행합니다.

> [!TIP]
> OCI(Oracle Cloud) 등 클라우드 환경에서는 8000번 포트 방화벽을 열어야 외부 접속이 가능합니다.
> ```bash
> sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
> ```

---

## 환경 설정 (.env)

최초 실행 시 `.env` 파일이 생성됩니다. 다음 항목을 필요에 따라 수정하세요:

- `OUTPUT_DIR`: 녹화 파일 저장 경로 (기본: `output`)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: 알림 설정
- `FILENAME_PATTERN`: 파일명 생성 규칙 (예: `{date}_{streamer}_{title}_{quality}`)
- `RCLONE_REMOTE`: rclone 원격 저장소 이름 (클라우드 백업용)
- `USER_AGENT`: 브라우저 식별 정보

---

## 사용 방법

1. 서버 실행 후 웹 브라우저에서 `http://localhost:8000` (또는 서버IP:8000) 접속.
2. **채널 관리** 탭에서 플랫폼 선택 후 스트리머 ID 또는 URL을 입력하여 추가하세요.
   - 치지직: `chzzk.naver.com/채널ID`
   - 트위치: `twitch.tv/아이디`
   - 숲: `play.sooplive.co.kr/아이디`
   - 유튜브: `youtube.com/@핸들` 또는 `youtube.com/channel/UC채널ID`
3. **쿠키 관리** 탭에서 유료/성인용/멤버십 방송 녹화를 위한 쿠키 데이터를 저장할 수 있습니다.
4. 방송이 시작되면 자동으로 지정된 폴더에 파일이 저장됩니다.

---

## 기술 스택

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JS, CSS (Glassmorphism UI)
- **녹화 엔진**: Streamlink (치지직/트위치/숲), yt-dlp (유튜브)
- **후처리**: FFmpeg (Remuxing / Concat)
- **Dependency**: `psutil`, `aiohttp`, `apscheduler` 등

---

## 🤖 AI 개발 안내

이 프로젝트의 모든 코드는 **100% AI에 의해 작성**되었습니다.

**사용된 AI 모델:**
- **Claude 4 Sonnet** (Anthropic) — 핵심 아키텍처 설계, 백엔드/프론트엔드 전체 구현, 버그 수정, 리팩토링

> [!NOTE]
> 코드 작성, 디버깅, 기능 추가, 테스트, 문서화까지 모든 개발 과정이 AI를 통해 수행되었습니다.

---

## 기여 및 문의

문제가 있거나 추가 기능이 필요한 경우 이슈를 남겨주세요.
