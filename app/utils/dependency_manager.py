"""
외부 의존성(FFmpeg, Streamlink) 자동 감지 및 다운로드 관리자.
서버 시작 시 필요한 바이너리가 없으면 자동으로 다운로드하여
프로젝트 내 bin/ 디렉토리에 저장합니다.
"""
import os
import sys
import shutil
import platform
import zipfile
import tarfile
import urllib.request
from app.core.logger import logger
from app.core.config import settings

# 프로젝트 내부 bin 디렉토리 (다운로드된 바이너리 저장 위치)
BIN_DIR = os.path.join(settings.BASE_DIR, "bin")

# FFmpeg 다운로드 URL (플랫폼별)
FFMPEG_URLS = {
    "Windows": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "Linux": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
}


def _get_bin_path(binary_name: str) -> str:
    """bin 디렉토리 내 바이너리의 전체 경로를 반환합니다."""
    ext = ".exe" if platform.system() == "Windows" else ""
    return os.path.join(BIN_DIR, f"{binary_name}{ext}")


def find_binary(binary_name: str, config_path: str = "") -> str:
    """
    바이너리를 다음 순서로 탐색합니다:
    1) config에 설정된 절대 경로
    2) 프로젝트 bin/ 디렉토리
    3) 시스템 PATH (shutil.which)
    
    찾으면 전체 경로를 반환, 못 찾으면 빈 문자열 반환.
    시스템에 설치된 다른 프로그램(Jellyfin 등)의 ffmpeg에 의존하지 않습니다.
    """
    # 1) config에 절대 경로가 설정되어 있으면 우선
    if config_path and os.path.isabs(config_path) and os.path.isfile(config_path):
        return config_path
    
    # 2) 프로젝트 bin/ 디렉토리
    bin_path = _get_bin_path(binary_name)
    if os.path.isfile(bin_path):
        return bin_path
    
    # 3) 시스템 PATH
    found = shutil.which(config_path or binary_name)
    if found:
        return found
    
    return ""


def _download_with_progress(url: str, dest: str):
    """URL에서 파일을 다운로드합니다 (진행률 로깅 포함)."""
    logger.info(f"📥 다운로드 시작: {url}")
    
    req = urllib.request.Request(url, headers={"User-Agent": "StreamRecorder/2.0"})
    
    with urllib.request.urlopen(req, timeout=120) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 256  # 256KB
        
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = int(downloaded / total * 100)
                    if pct % 20 == 0:
                        logger.info(f"  ⏳ 다운로드 진행: {pct}% ({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)")
    
    logger.info(f"✅ 다운로드 완료: {dest}")


def _extract_ffmpeg(archive_path: str):
    """다운로드된 FFmpeg 아키이브에서 ffmpeg 바이너리만 추출합니다."""
    os.makedirs(BIN_DIR, exist_ok=True)
    system = platform.system()
    
    if system == "Windows":
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                basename = os.path.basename(name)
                if basename in ("ffmpeg.exe", "ffprobe.exe"):
                    target = os.path.join(BIN_DIR, basename)
                    with zf.open(name) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                    logger.info(f"  📦 추출: {basename} → {BIN_DIR}")
    elif system == "Linux":
        with tarfile.open(archive_path, "r:xz") as tf:
            for member in tf.getmembers():
                basename = os.path.basename(member.name)
                if basename in ("ffmpeg", "ffprobe"):
                    member.name = basename
                    tf.extract(member, BIN_DIR)
                    # 실행 권한 부여
                    target = os.path.join(BIN_DIR, basename)
                    os.chmod(target, 0o755)
                    logger.info(f"  📦 추출: {basename} → {BIN_DIR}")


def ensure_ffmpeg() -> str:
    """
    FFmpeg가 사용 가능한지 확인하고, 없으면 자동 다운로드합니다.
    반환: ffmpeg 전체 경로
    """
    path = find_binary("ffmpeg", settings.FFMPEG_PATH)
    if path:
        logger.info(f"✅ FFmpeg 확인됨: {path}")
        return path
    
    # 다운로드 시도
    system = platform.system()
    url = FFMPEG_URLS.get(system)
    if not url:
        logger.error(f"❌ FFmpeg 자동 다운로드는 {system}을(를) 지원하지 않습니다. 수동으로 설치해주세요.")
        return "ffmpeg"
    
    logger.info(f"🔍 FFmpeg를 찾을 수 없습니다. 자동 다운로드를 시작합니다... ({system})")
    
    os.makedirs(BIN_DIR, exist_ok=True)
    ext = ".zip" if system == "Windows" else ".tar.xz"
    archive_path = os.path.join(BIN_DIR, f"ffmpeg_download{ext}")
    
    try:
        _download_with_progress(url, archive_path)
        _extract_ffmpeg(archive_path)
        
        # 아카이브 정리
        os.remove(archive_path)
        
        result = _get_bin_path("ffmpeg")
        if os.path.isfile(result):
            logger.info(f"🎉 FFmpeg 자동 설치 완료: {result}")
            return result
        else:
            logger.error("❌ FFmpeg 추출 후 바이너리를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"❌ FFmpeg 다운로드 실패: {e}")
        # 불완전 파일 정리
        if os.path.exists(archive_path):
            os.remove(archive_path)
    
    return "ffmpeg"


def ensure_streamlink() -> str:
    """Streamlink이 사용 가능한지 확인합니다."""
    path = find_binary("streamlink", settings.STREAMLINK_PATH)
    if path:
        logger.info(f"✅ Streamlink 확인됨: {path}")
        return path
    
    logger.warning("⚠️ Streamlink를 찾을 수 없습니다. 'pip install streamlink'으로 설치해주세요.")
    return "streamlink"


def check_all_dependencies():
    """
    서버 시작 시 호출되는 전체 의존성 검사 함수.
    FFmpeg가 없으면 자동 다운로드하고, 찾은 경로를 settings에 반영합니다.
    """
    logger.info("🔧 외부 의존성 검사를 시작합니다...")
    
    # FFmpeg
    ffmpeg_path = ensure_ffmpeg()
    settings.FFMPEG_PATH = ffmpeg_path
    
    # Streamlink
    streamlink_path = ensure_streamlink()
    settings.STREAMLINK_PATH = streamlink_path
    
    logger.info("🔧 의존성 검사 완료.")
