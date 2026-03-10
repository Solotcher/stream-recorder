#!/bin/bash
# Stream Recorder 서버 시작 스크립트 (Linux)
cd "$(dirname "$0")"

# 가상환경이 없으면 생성
if [ ! -d ".venv" ]; then
    echo "[Stream Recorder] 가상환경을 생성합니다..."
    python3 -m venv .venv
fi

# 가상환경 활성화
source .venv/bin/activate

# 의존성 설치
echo "[Stream Recorder] 의존성을 설치합니다..."
pip install -r requirements.txt --quiet

# .env 파일이 없으면 example에서 복사
if [ ! -f ".env" ]; then
    echo "[Stream Recorder] .env.example → .env 복사..."
    cp .env.example .env
fi

# data, output 디렉토리 생성
mkdir -p data output

echo "[Stream Recorder] 서버를 시작합니다..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
