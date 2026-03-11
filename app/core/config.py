import os
import json
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Stream Recorder Server"
    VERSION: str = "v2.0"
    DEBUG: bool = False
    
    # 디렉토리 설정
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", os.path.join(BASE_DIR, "output"))
    
    # 텔레그램봇 설정
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # FFmpeg / Streamlink / yt-dlp Path (시스템 환경 변수에 없으면 커스텀 경로 사용)
    FFMPEG_PATH: str = "ffmpeg"
    STREAMLINK_PATH: str = "streamlink"
    YTDLP_PATH: str = "yt-dlp"
    
    # 클라우드 동기화를 위한 Rclone 속성
    RCLONE_PATH: str = os.getenv("RCLONE_PATH", "rclone")
    RCLONE_REMOTE: str = os.getenv("RCLONE_REMOTE", "")
    
    # 파일명 패턴 설정 (사용 가능 변수: {date}, {streamer}, {title}, {quality}, {platform})
    # 기본값: yyyymmdd_스트리머명_방송제목_화질
    FILENAME_PATTERN: str = os.getenv("FILENAME_PATTERN", "{date}_{streamer}_{title}_{quality}")
    
    # API 인증 키 (빈 문자열이면 인증 비활성화 = 개발 모드)
    API_KEY: str = os.getenv("API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()

# 필요한 디렉토리가 없으면 자동 생성
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
