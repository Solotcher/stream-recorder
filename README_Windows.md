# Stream Recorder: Windows 환경 설치 및 실행 가이드

이 애플리케이션은 **Python FastAPI**를 기반으로 작성되어 있어 Windows와 Linux 어디서든 동일하게 작동하도록 설계되었습니다.
이 문서는 **Windows 환경**에서 Stream Recorder를 원활하게 설정하고 실행하기 위한 가이드입니다.

## 시스템 요구사항
- Python 3.10 이상 (반드시 환경 변수 PATH에 추가되어 있어야 합니다)
- FFmpeg (Windows용 빌드 전역 설치 및 PATH 등록 필수)
- Streamlink (pip를 통해 설치)

## 1. 기본 프로그램 및 의존성 다운로드

### Python 설치
1. [Python 공식 웹사이트](https://www.python.org/downloads/windows/)에서 Python 3.10 이상의 버전을 다운로드하여 설치합니다.
2. 설치 시 하단의 **"Add Python to PATH"** 옵션을 반드시 체크해야 합니다.

### FFmpeg 설치
FFmpeg는 영상 후처리와 병합 기능에 필수적입니다.
1. [Gyan.dev FFmpeg 빌드](https://www.gyan.dev/ffmpeg/builds/) 또는 [BtbN 빌드](https://github.com/BtbN/FFmpeg-Builds/releases)에서 Windows용 최신 릴리즈 압축 파일을 다운로드합니다. (예: `ffmpeg-release-essentials.zip`)
2. 원하는 위치(예: `C:\ffmpeg`)에 압축을 풂니다.
3. Windows 키를 누르고 **"환경 변수"**를 검색하여 `시스템 환경 변수 편집`을 엽니다.
4. `환경 변수(N)...` 버튼을 클릭합니다.
5. 시스템 변수 또는 사용자 변수의 `Path`를 선택하고 `편집(E)...`을 클릭합니다.
6. `새로 만들기(N)`를 클릭하고 압축을 푼 FFmpeg의 `bin` 폴더 경로(예: `C:\ffmpeg\bin`)를 추가합니다.
7. 명령 프롬프트(cmd)나 PowerShell을 열고 `ffmpeg -version`을 입력하여 정상적으로 작동하는지 확인합니다.

## 2. 파이썬 가상환경 설정 및 패키지 설치

터미널이나 명령 프롬프트에서 명령어를 실행할 때는 반드시 **코드 파일들(예: `app` 폴더, `main.py` 등)이 있는 최상위 프로젝트 폴더**에서 진행해야 합니다. 

**초보자를 위한 터미널 열기 팁:**
1. 윈도우 파일 탐색기에서 `Stream Recorder` 폴더를 엽니다.
2. 상단의 **폴더 주소창** 여백을 클릭합니다.
3. 주소창에 `cmd`라고 입력하고 엔터(Enter)를 누르면, 해당 폴더 위치에서 명령 프롬프트가 열립니다.

열린 명령 프롬프트(또는 PowerShell)에서 아래 명령어를 차례대로 한 줄씩 복사 및 붙여넣기(우클릭)하여 실행합니다.

```powershell
cd "C:\Users\User\Documents\Study_n_Work\Stream Recorder"

# 가상환경 활성화 (Powershell 전용)
.\.venv\Scripts\Activate.ps1

# ※ 만약 위 명령어가 실행 정책 오류(빨간 글씨)로 실패할 경우, 아래 명령어를 먼저 한 번 실행해주세요.
# Set-ExecutionPolicy Unrestricted -Scope CurrentUser
# 그 후 다시 .\.venv\Scripts\Activate.ps1 를 입력합니다.

# 가상환경 활성화 (일반 cmd 명령 프롬프트 사용자)
# .venv\Scripts\activate.bat

# 요구 패키지 목록 설치
pip install fastapi uvicorn aiohttp apscheduler pydantic pydantic-settings streamlink
```

## 3. 서버 실행 (로컬 환경)

서버를 켤 때도 마찬가지로 **항상 `Stream Recorder` 메인 폴더 위치**에서 터미널을 열고 실행해야 합니다.
가상환경이 활성화되어 있지 않다면, 위에서 배운 `.\.venv\Scripts\Activate.ps1` 명령어를 먼저 쳐서 `(.venv)` 마크를 띄운 후에 다음 명령어를 실행합니다.

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- 서버가 실행되면 웹 브라우저를 열고 `http://127.0.0.1:8000`으로 접속하여 웹 UI를 확인할 수 있습니다.
- 백그라운드 환경에서 터미널 없이 구동하려면 Windows의 '작업 스케줄러'나 별도의 데몬 관리 툴(ex. nssm)을 활용할 수 있습니다.

## 4. 전역 설정 (Config / 텔레그램 연동)
1. 서버 실행 후, `http://127.0.0.1:8000` 로 접속하여 프론트엔드의 **⚙️ 설정(쿠키/시스템)** 모달을 클릭합니다.
2. 그 곳에서 **텔레그램 알림 토큰과 채팅 ID**를 기입하고 저장합니다.
3. 프로젝트 루트 디렉토리에 `.env` 파일이 동적으로 생성/편집되며, 즉각 알림 시스템이 동작합니다.

## 개발 정보 노트 (Cross-Platform)
- `app.core.config.py`의 `STREAMLINK_PATH` 설정은 기본값으로 `streamlink` 문자열을 던져 OS가 경로를 자동 탐색하게 되어 있습니다.
- `app/services/recorder.py`는 `asyncio.create_subprocess_exec`로 서브프로세스를 호출하므로 OS 독립적입니다. 단, Windows 환경에서 파일 경로나 명령어 처리 시 호환성 문제가 생길 수 있는 부분을 대비하여 관리하고 있습니다.
