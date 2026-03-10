import os
import asyncio
import subprocess
from app.core.logger import logger
from app.core.config import settings

async def upload_file(file_path: str, channel_name: str):
    """
    Rclone을 활용하여 로컬 후처리가 끝난 영상을 지정한 클라우드 Remote
    또는 NAS 내부 경로로 동기화(복사)하는 함수입니다.
    RCLONE_REMOTE가 설정되어 있을 때만 작동합니다.
    subprocess.Popen + asyncio.to_thread 패턴으로 Windows 호환 보장.
    """
    if not settings.RCLONE_REMOTE:
        return

    remote_dest = f"{settings.RCLONE_REMOTE}/{channel_name}"

    logger.info(f"[{channel_name}] 클라우드 업로드 시작 ({settings.RCLONE_REMOTE}): {file_path}")

    cmd = [
        settings.RCLONE_PATH,
        "copy",
        file_path,
        remote_dest,
        "--ignore-existing"
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        def _wait_proc():
            return proc.communicate()

        stdout, stderr = await asyncio.to_thread(_wait_proc)

        if proc.returncode == 0:
            logger.info(f"[{channel_name}] 업로드 성공: {file_path}")
            from app.utils.telegram_bot import send_telegram_message
            await send_telegram_message(f"☁️ <b>{channel_name}</b> 영상이 클라우드({settings.RCLONE_REMOTE})에 무사히 백업되었습니다.")
        else:
            error_msg = stderr.decode("utf-8", errors="replace") if stderr else "Unknown error"
            logger.error(f"[{channel_name}] 업로드 실패: {error_msg}")
            from app.utils.telegram_bot import send_error_alert
            await send_error_alert(channel_name, f"Rclone 업로드 실패 ({settings.RCLONE_REMOTE})", error_msg)
    except Exception as e:
        logger.error(f"[{channel_name}] Rclone 실행 중 예외 발생: {e}")
