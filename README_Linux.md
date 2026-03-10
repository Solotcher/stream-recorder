# Stream Recorder: 크로스플랫폼 설치 및 실행 가이드

이 애플리케이션은 **Python FastAPI**를 기반으로 작성되어 Windows와 Linux 어디서든 동일하게 작동하도록 설계되었습니다.
특히 상시 구동이 필요한 특성상 **AWS EC2, 라즈베리파이, 일반 NAS 등 Linux 환경 배포**를 적극 권장합니다.

## 시스템 요구사항
- Python 3.10 이상
- FFmpeg (시스템 전역 설치 필수)
- Streamlink (pip 설치 혹은 시스템 전역 패키지)

## 1. 리눅스(Ubuntu/Debian) 기본 패키지 설치
FFmpeg는 영상 후처리와 병합, Streamlink는 라이브 다운로드에 사용됩니다. 터미널에서 아래 명령어로 설치하세요.

```bash
sudo apt update
sudo apt install -y ffmpeg
```

## 2. 파이썬 환경 설정 및 의존성 다운로드

터미널에서 명령를 실행할 때는 반드시 깃허브에서 클론하거나 다운로드 받은 **`Stream Recorder` 프로젝트의 메인 폴더(예: `main.py` 파일이 있는 위치)** 안으로 이동한 후에 진행해야 합니다.

```bash
# 먼저 프로젝트 폴더로 이동합니다. (경로는 실제 다운로드 받은 위치에 맞게 변경하세요)
# 예시: cd /home/ubuntu/stream-recorder
cd /경로/to/Stream_Recorder_폴더

# 해당 폴더 안에서 파이썬 가상환경(.venv) 활성화
# (가상환경이 없다면 python3 -m venv .venv 명령어로 먼저 생성)
source .venv/bin/activate

# 요구 패키지 목록
pip install fastapi uvicorn aiohttp apscheduler pydantic pydantic-settings streamlink
```

## 3. 백그라운드 무중단 실행 (systemd / nohup / pm2)

서버 데몬을 켤 때도 **항상 `Stream Recorder` 프로젝트 메인 폴더 위치**에서 실행해야 합니다. 프로젝트 메인 폴더가 아니면 `app.main` 모듈을 찾을 수 없다는 에러가 발생합니다.

현재 구현체는 웹 브라우저(`http://서버IP:8000`)를 통해 UI와 레코더가 조작됩니다.
원격 SSH 터미널이 꺼져도 서버가 계속 돌아가게 하려면 `nohup` 이나 `pm2`를 사용하세요.

### 방법 A: nohup을 이용한 심플 실행
```bash
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```
서버가 8000번 포트로 구동됩니다. 외부에서 접속하기 위한 설정은 아래 **[네트워크 및 보안 설정 가이드]**를 참고하세요.

### 방법 B: PM2 (Node.js 생태계의 데몬 매니저 활용)
PM2를 사용하면 크래시 났을 때 자동으로 재시작하는 장점이 있습니다.

```bash
# pm2 설치 (npm 사전 설치 필요)
sudo apt install npm
sudo npm install -g pm2

# pm2를 이용한 프로세스 실행 유틸
cat << 'EOF' > start.sh
#!/bin/bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF

chmod +x start.sh
pm2 start start.sh --name "stream-recorder"
pm2 save
```

## 4. 네트워크 및 보안 설정 가이드 (OCI 등 클라우드 배포 시)

FastAPI 서버는 기본적으로 8000번 포트를 사용합니다. OCI(Oracle Cloud) 인스턴스에서 구동 후 접속하려면 다음 두 가지 방식 중 하나를 선택해 구성하세요.

### [방식 1] 직접 외부 공개 (Public Access)
가장 쉽지만 누구나 UI에 접근할 수 있어 보안에 다소 취약할 수 있습니다.
1. **OCI 콘솔**: [가상 클라우드 네트워크(VCN)] -> [보안 목록(Security List)]에서 **수신(Ingress) 규칙에 TCP 8000 포트**를 추가합니다.
2. **Ubuntu OS 방화벽 (iptables)**: OCI 기본 우분투 이미지는 iptables가 막혀있으므로 아래 명령어로 8000번 포트를 열어야 합니다.
   ```bash
   sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
   sudo netfilter-persistent save
   ```
3. 브라우저에서 `http://[인스턴스공인IP]:8000` 으로 접속합니다.

### [방식 2] WireGuard VPN을 통한 안전한 내부 접속 (강력 추천)
서버를 외부에 노출하지 않고, VPN으로 묶인 기기(나의 PC, 스마트폰)에서만 안전하게 접속하는 방법입니다.
이 방식을 사용하면 OCI 콘솔이나 방화벽에서 8000 포트를 외부에 열어둘 필요가 없습니다! (대신 WireGuard 포트인 51820 UDP만 엽니다)

1. 서버에 WireGuard(또는 쉽게 구축 가능한 [PiVPN](https://pivpn.io/), [wg-easy](https://github.com/wg-easy/wg-easy) 등)를 설치하여 VPN 서버를 구축합니다.
2. 내 PC(또는 스마트폰)에 WireGuard 클라이언트를 설치하고 서버와 연결합니다.
3. VPN이 연결된 상태에서, 브라우저를 열고 **VPN 내부 사설 IP** (예: `http://10.8.0.1:8000` 또는 `http://10.0.0.xx:8000`)로 접속합니다.
4. 외부에서는 절대 뚫고 들어올 수 없는 강력한 나만의 비밀 녹화 데몬 환경이 완성됩니다.

## 5. 전역 설정 (Config / 텔레그램 연동)
초기 구동 후, http://[서버IP]:8000 로 접속하여 프론트엔드의 **⚙️ 설정(쿠키/시스템)** 모달을 클릭합니다.
그 곳에서 **텔레그램 알림 토큰과 채팅 ID**를 기입하고 저장하면, 프로젝트 루트 디렉토리에 `.env` 파일이 동적으로 편집되며 즉각 알림 시스템이 동작합니다.

## 개발 정보 노트 (Cross-Platform)
- Windows 환경: `app.core.config.py`의 `STREAMLINK_PATH`는 기본값으로 `streamlink` 문자열을 던져 OS가 경로를 자동 탐색하게 되어 있습니다.
- Mac 환경에서도 Homebrew로 `brew install ffmpeg streamlink` 를 통해 손쉽게 연동 가능합니다.
- `app/services/recorder.py`는 `asyncio.create_subprocess_exec`로 서브프로세스를 호출하므로 OS 독립적입니다.
