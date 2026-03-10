# Stream Recorder (다충 플랫폼 자동 녹화기)

치지직(Chzzk), 아프리카TV(SOOP), 트위치(Twitch) 방송을 모니터링하고 자동으로 녹화하는 웹 애플리케이션입니다.

> [!WARNING]
> **SOOP(아프리카TV) 플랫폼 안내**: 현재 SOOP의 녹화 로직에 문제가 있어 원활한 녹화가 이루어지지 않을 수 있습니다. 녹화 로직 및 세그먼트 처리 방식이 아직 원활하지 않으니 사용 시 참고 부탁드립니다.

## 주요 특징

- **다중 플랫폼 지원**: Chzzk, SOOP, Twitch 완벽 대응.
- **자동 녹화**: 스트리머가 방송을 시작하면 자동으로 감지하여 녹화를 시작합니다.
- **의존성 자동 관리**: FFmpeg 및 Streamlink가 없어도 실행 시 자동으로 환경에 맞춰 다운로드 및 설정됩니다.
- **MP4 자동 리먹싱**: 녹화 완료(또는 강제 종료) 후 고화질 유지 및 스트리밍에 최적화된 MP4 형식으로 자동 변환합니다.
- **파일명 커스터마이징**: `{date}`, `{streamer}`, `{title}`, `{quality}` 등 다양한 변수를 조합한 파일명 규칙 설정 가능.
- **웹 UI 제공**: 브라우저에서 간편하게 스트리머 추가, 쿠키 관리, 설정 변경이 가능합니다.
- **안정적인 프로세스 관리**: 서버 재시작 시에도 기존 녹화 중인 프로세스를 자동으로 감지하여 연결을 유지합니다.

---

## 설치 및 실행 방법 (Requirement: Python 3.10+)

### 1. Windows (윈도우)

1. 저장소 클론: `git clone https://github.com/Solotcher/stream-recorder.git`
2. 해당 폴더로 이동.
3. **방법 A (배치 파일)**: `start.bat` 실행 (자동으로 가상환경 구축 후 서버 실행)
4. **방법 B (파워쉘)**: `PowerShell -ExecutionPolicy Bypass -File start.ps1` 실행

### 2. Linux (리눅스 / Ubuntu, OCI 등)

1. 저장소 클론: `git clone https://github.com/Solotcher/stream-recorder.git`
2. 폴더 진입 후 스크립트 실행 권한 부여: `chmod +x start.sh`
3. 실행: `./start.sh`
   - 이 스크립트는 내부적으로 가상환경(`.venv`) 생성, 필수 패키지 설치, `.env` 기본값 설정을 모두 자동으로 수행합니다.

---

## 환경 설정 (.env)

최초 실행 시 `.env` 파일이 생성됩니다. 다음 항목을 필요에 따라 수정하세요:

- `OUTPUT_DIR`: 녹화 파일 저장 경로 (기본: `output`)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: 알림 설정
- `FILENAME_PATTERN`: 파일명 생성 규칙 
  - (예: `{date}_{streamer}_{title}_{quality}`)
- `USER_AGENT`: 브라우저 식별 정보

---

## 사용 방법

1. 서버 실행 후 웹 브라우저에서 `http://localhost:8000` (또는 서버IP:8000) 접속.
2. **채널 관리** 탭에서 플랫폼 선택 후 스트리머 ID를 입력하여 추가하세요.
3. **쿠키 관리** 탭에서 유료/성인용 방송 녹화를 위한 쿠키 데이터를 파싱하여 저장할 수 있습니다.
4. 방송이 시작되면 자동으로 `output` 폴더에 파일이 저장됩니다.

---

## 기술 스택

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JS, CSS (Glassmorphism UI)
- **Tools**: Streamlink, FFmpeg
- **Dependency**: `psutil`, `aiohttp`, `apscheduler` 등

---

## 기여 및 문의

문제가 있거나 추가 기능이 필요한 경우 이슈를 남겨주세요.
