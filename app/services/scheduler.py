import os
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import json
import logging
from app.core.logger import logger
from app.core.config import settings
from app.utils.channel_db import get_all_channels
from app.utils.cookie_manager import get_platform_cookies
from app.utils.telegram_bot import send_error_alert
from app.services.recorder import RecorderManager

# Extractors
from app.extractors.chzzk import ChzzkExtractor
from app.extractors.twitch import TwitchExtractor
from app.extractors.soop import SoopExtractor
from app.extractors.youtube import YouTubeExtractor

EXTRACTOR_MAP = {
    "chzzk": ChzzkExtractor,
    "twitch": TwitchExtractor,
    "soop": SoopExtractor,
    "youtube": YouTubeExtractor
}

# 글로벌 스케줄러 인스턴스
scheduler = AsyncIOScheduler()

def init_scheduler():
    """ FastAPI 시작 시 스케줄러 구동 """
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler 백그라운드 모니터링 모듈이 시작되었습니다.")
        
        # 30초마다 모니터링 (실서비스 시 30~60초 권장)
        scheduler.add_job(
            check_all_channels,
            trigger=IntervalTrigger(seconds=30),
            id="main_channel_monitor",
            name="Periodic Channel Live Status Check",
            replace_existing=True
        )

def shutdown_scheduler():
    """ FastAPI 종료 시 스케줄러 정리 """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler가 안전하게 종료되었습니다.")

async def trigger_recording(ch_id: str, platform: str, ch_name: str, extractor, recorder, meta, record_type: str = "scheduled", resolution: str = "best"):
    """ 실제로 Streamlink 커맨드를 조립하고 녹화 프로세스를 실행하는 분리 로직 """
    import shlex
    
    # 세션 시작/유지 처리 (분할 녹화 방지/병합 용도)
    if not recorder.session_started_at:
        recorder.session_started_at = datetime.now()
        recorder.session_part = 1
        recorder.session_platform = platform
        recorder.session_channel_name = ch_name
        recorder.session_title = meta.get("title", "")
    else:
        recorder.session_part += 1

    # 파일명에 사용할 안전 문자 변환 함수
    def _safe(text: str) -> str:
        return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()

    safe_name = _safe(ch_name)
    safe_title = _safe(meta.get("title", "제목없음"))
    date_str = recorder.session_started_at.strftime("%Y%m%d")
    
    # FILENAME_PATTERN을 사용하여 파일명 생성
    pattern = settings.FILENAME_PATTERN
    # 화질 표기: 1080p60 → 1080P60, best → Best
    display_quality = resolution.upper() if resolution != "best" else "Best"
    filename_base = pattern.format(
        date=date_str,
        streamer=safe_name,
        title=safe_title,
        quality=display_quality,
        platform=platform
    )
    
    # 파일명 길이 제한 (255바이트 - 확장자 여유분)
    if len(filename_base) > 200:
        filename_base = filename_base[:200]
    
    if platform == "soop":
        filename = f"{filename_base}_part{recorder.session_part}.webm"
    elif platform == "youtube":
        # 유튜브는 yt-dlp로 직접 MP4 녹화 (리멕싱 불필요)
        filename = f"{filename_base}.mp4"
    else:
        # 단일 파일 (트위치, 치지직) — .ts로 녹화 후 리멕싱으로 .mp4 변환
        filename = f"{filename_base}.ts"
        
    # 스트리머별 폴더 생성
    streamer_dir = os.path.join(settings.OUTPUT_DIR, safe_name)
    os.makedirs(streamer_dir, exist_ok=True)
    
    output_path = os.path.join(streamer_dir, filename)
    
    if platform == "youtube":
        # 유튜브: yt-dlp 커맨드 조립
        cmd = [settings.YTDLP_PATH]
        cmd.extend(extractor.get_streamlink_args())
        cmd.extend(["-o", output_path, meta.get("stream_url", "")])
    else:
        # 기타 플랫폼: Streamlink 커맨드 조립
        cmd = [settings.STREAMLINK_PATH]
        cmd.extend(extractor.get_streamlink_args())
        cmd.extend([meta.get("stream_url", ""), resolution, "-o", output_path])
    
    # 백그라운드 태스크로 시작
    asyncio.create_task(recorder.start_record(cmd, output_path, safe_name, record_type))
    return True

async def check_all_channels():
    """ 주기적으로 호출되어 채널 상태를 모니터링하는 코어 태스크 (병렬 실행) """
    logger.debug("[Scheduler] 등록된 채널들의 라이브 상태를 확인합니다...")
    channels = get_all_channels()
    
    active_channels = [ch for ch in channels if ch.get("is_active", True)]
    if not active_channels:
        return
    
    async def _check_single(ch):
        platform = ch.get("platform")
        ch_id = ch.get("id")
        ch_name = ch.get("name", ch_id)
        
        ExtClass = EXTRACTOR_MAP.get(platform)
        if not ExtClass:
            return
            
        cookies = get_platform_cookies(platform)
        extractor = ExtClass(channel_id=ch_id, cookies=cookies)
        
        try:
            is_live = await extractor.is_live()
            recorder = RecorderManager.get_instance(ch_id)
            
            if is_live and not recorder.is_recording:
                meta = await extractor.get_metadata()
                resolution = ch.get("resolution", "best")
                
                # meta에서 가져온 실제 채널명이 있으면 우선 사용 (DB에 ID만 저장된 경우 대응)
                real_name = meta.get("channel_name", ch_name)
                if real_name and real_name != ch_id:
                    ch_name = real_name
                    # DB에도 실제 채널명을 영속화
                    from app.utils.channel_db import update_channel
                    update_channel(ch_id, {"name": ch_name})
                
                await trigger_recording(ch_id, platform, ch_name, extractor, recorder, meta, resolution=resolution)
                
            elif not is_live:
                if recorder.is_recording:
                    logger.info(f"[{ch_name}] 방종 감지. 레코더 자체 안전 중지(EOF)를 대기합니다.")
                elif recorder.session_started_at:
                    logger.info(f"[{ch_name}] 채널 오프라인 확정. 세션을 종료하고 후처리를 진행합니다.")
                    if recorder.session_platform == "soop" and recorder.session_part > 0:
                        from app.services.merger import process_soop_concat
                        safe_name = "".join(c for c in recorder.session_channel_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        base_filename = f"[{recorder.session_started_at.strftime('%y%m%d_%H%M')}] {safe_name}_{recorder.session_platform}"
                        streamer_dir = os.path.join(settings.OUTPUT_DIR, safe_name)
                        asyncio.create_task(process_soop_concat(streamer_dir, base_filename, recorder.session_channel_name))
                    
                    recorder.session_started_at = None
                    recorder.session_part = 0
                
        except Exception as e:
            logger.error(f"[{ch_name}] 모니터링 중 오류 발생: {e}")

    await asyncio.gather(*[_check_single(ch) for ch in active_channels], return_exceptions=True)
