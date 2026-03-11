from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.core.logger import logger
from app.utils.channel_db import get_all_channels, add_channel, delete_channel, get_channel, update_channel
from app.utils.cookie_manager import parse_raw_cookie, update_platform_cookies, get_platform_cookies
from app.services.recorder import RecorderManager
from app.utils.event_bus import broadcast_event

router = APIRouter()

class ChannelCreateRequest(BaseModel):
    """채널 등록 전용 모델"""
    platform: str
    id: str
    name: str
    resolution: Optional[str] = "best"

class ManualRecordRequest(BaseModel):
    """수동 즉시 녹화 전용 모델"""
    platform: str
    id: str
    name: str
    resolution: Optional[str] = "best"
    stream_password: Optional[str] = None

class CookieRequest(BaseModel):
    raw_cookie: str

class ConfigRequest(BaseModel):
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    OUTPUT_DIR: Optional[str] = None
    RCLONE_PATH: Optional[str] = None
    RCLONE_REMOTE: Optional[str] = None
    FILENAME_PATTERN: Optional[str] = None

@router.get("/channels")
async def get_channels_list():
    """ 현재 등록된 채널 목록 및 레코더 상태 반환 """
    channels = get_all_channels()
    res_list = []
    for ch in channels:
        ch_id = ch.get("id")
        recorder = RecorderManager.get_instance(ch_id)
        # TODO: 실시간 API를 한 번 더 쏠 수도 있으나, 여기서는 캐싱된 상태만 내려줌
        ch["is_recording"] = recorder.is_recording
        res_list.append(ch)
    return {"status": "success", "data": res_list}

@router.post("/channels")
async def register_channel(request: ChannelCreateRequest):
    """ 새 채널 추가 """
    from app.services.scheduler import EXTRACTOR_MAP
    
    # URL 경로 찌꺼기가 ID에 섞여 들어왔을 경우 방어
    real_id = request.id
    if '/' in real_id:
        real_id = real_id.split('/')[0]
        request.id = real_id
        
    # Extractor를 통해 채널 공식 닉네임(스트리머명) 자동 파싱
    platform = request.platform
    ExtClass = EXTRACTOR_MAP.get(platform)
    if ExtClass:
        cookies = get_platform_cookies(platform)
        extractor = ExtClass(channel_id=request.id, cookies=cookies)
        try:
            info = await extractor.get_channel_info()
            parsed_name = info.get("channel_name")
            if parsed_name:
                request.name = parsed_name
        except Exception as e:
            logger.error(f"채널명 자동 파싱 실패: {e}")
            
    logger.info(f"신규 채널 추가: [{request.platform}] {request.name} ({request.id})")
    success = add_channel(request.dict())
    if not success:
        raise HTTPException(status_code=400, detail="Channel already exists or error occurs")
    await broadcast_event("channel_added", {"id": request.id, "platform": request.platform, "name": request.name})
    return {"status": "success"}

@router.delete("/channels/{channel_id}")
async def remove_channel(channel_id: str):
    logger.info(f"채널 삭제 요청: {channel_id}")
    delete_channel(channel_id)
    await broadcast_event("channel_deleted", {"id": channel_id})
    return {"status": "success"}

@router.post("/cookies/{platform}")
async def update_cookie(platform: str, req: CookieRequest):
    try:
        parsed = parse_raw_cookie(req.raw_cookie)
        update_platform_cookies(platform, parsed)
        return {"status": "success", "message": f"{platform} 쿠키 적용 완료", "parsed_keys": list(parsed.keys()), "key_count": len(parsed)}
    except Exception as e:
        logger.error(f"쿠키 파싱 실패: {e}")
        raise HTTPException(status_code=400, detail="Invalid cookie format")

@router.get("/cookies/status")
async def get_cookies_status():
    """각 플랫폼별 쿠키 적용 상태를 조회합니다."""
    platforms = ["chzzk", "twitch", "soop", "youtube"]
    status = {}
    for p in platforms:
        cookies = get_platform_cookies(p)
        status[p] = {
            "applied": bool(cookies and len(cookies) > 0),
            "key_count": len(cookies) if cookies else 0
        }
    return {"status": "success", "data": status}

@router.get("/config")
async def get_system_config():
    from app.core.config import settings
    
    raw_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    masked_token = raw_token[:10] + "***" if len(raw_token) > 10 else raw_token
    
    return {
        "status": "success",
        "data": {
            "TELEGRAM_BOT_TOKEN": masked_token,
            "TELEGRAM_CHAT_ID": getattr(settings, "TELEGRAM_CHAT_ID", ""),
            "OUTPUT_DIR": getattr(settings, "OUTPUT_DIR", ""),
            "RCLONE_PATH": getattr(settings, "RCLONE_PATH", "rclone"),
            "RCLONE_REMOTE": getattr(settings, "RCLONE_REMOTE", ""),
            "FILENAME_PATTERN": getattr(settings, "FILENAME_PATTERN", "{date}_{streamer}_{title}_{quality}")
        }
    }

@router.post("/config")
async def update_system_config(req: ConfigRequest):
    from app.utils.env_manager import update_env_file
    import os
    
    updates = {k: v for k, v in req.dict().items() if v is not None}
    
    # 마스킹된 토큰("***" 포함)이나 빈 문자열이 들어오면 업데이트 대상에서 제외
    # → 사용자가 토큰을 변경하지 않았을 때 기존 값 보존
    if "TELEGRAM_BOT_TOKEN" in updates:
        token_val = updates["TELEGRAM_BOT_TOKEN"]
        if not token_val or "***" in token_val:
            del updates["TELEGRAM_BOT_TOKEN"]
    
    # OUTPUT_DIR이 수정 요청에 포함되어 있다면 디렉토리 생성(존재확인) 로직 수행
    if "OUTPUT_DIR" in updates and updates["OUTPUT_DIR"]:
        os.makedirs(updates["OUTPUT_DIR"], exist_ok=True)
        
    update_env_file(updates)
    return {"status": "success", "message": "시스템 설정이 업데이트되었습니다."}

from app.services.scheduler import EXTRACTOR_MAP, trigger_recording

@router.get("/records/active")
async def get_active_records():
    """ 현재 녹화 중인 세션 목록 반환 (DB 쿼리 없이 메모리 인스턴스 전용) """
    active_jobs = []
    for ch_id, recorder in RecorderManager._instances.items():
        if recorder.is_recording:
            started_at = None
            if recorder.session_started_at:
                started_at = recorder.session_started_at.isoformat()
            active_jobs.append({
                "id": ch_id,
                "platform": getattr(recorder, "session_platform", "unknown"),
                "name": getattr(recorder, "session_channel_name", ch_id),
                "title": getattr(recorder, "session_title", ""),
                "category": getattr(recorder, "session_category", ""),
                "record_type": getattr(recorder, "session_record_type", "scheduled"),
                "started_at": started_at,
                "is_recording": True
            })
    return {"status": "success", "data": active_jobs}

@router.post("/records/manual/start")
async def start_manual_record(request: ManualRecordRequest):
    """ 수동 전용 녹화 시작 (DB 등록 거치지 않음) """
    platform = request.platform
    channel_id = request.id
    
    # URL 찌꺼기 방어
    if '/' in channel_id:
        channel_id = channel_id.split('/')[0]

    recorder = RecorderManager.get_instance(channel_id)
    if recorder.is_recording:
        return {"status": "success", "message": "이미 녹화 중입니다."}
        
    ExtClass = EXTRACTOR_MAP.get(platform)
    if not ExtClass:
        raise HTTPException(status_code=400, detail="Unsupported platform")
        
    cookies = get_platform_cookies(platform)
    extractor = ExtClass(channel_id=channel_id, cookies=cookies)
    
    if getattr(request, "stream_password", None):
        extractor.stream_password = request.stream_password
        
    try:
        is_live = await extractor.is_live()
        if is_live:
            meta = await extractor.get_metadata()
            ch_name = meta.get("channel_name", channel_id)
                
            await trigger_recording(channel_id, platform, ch_name, extractor, recorder, meta, record_type="manual", resolution=request.resolution)
            await broadcast_event("recording_started", {"id": channel_id, "platform": platform, "name": ch_name, "record_type": "manual"})
            return {"status": "success", "message": "수동 녹화 시작됨"}
        else:
            raise HTTPException(status_code=400, detail="방송이 오프라인 상태이거나 정보를 가져올 수 없습니다.")
    except Exception as e:
        logger.error(f"수동 녹화 처리 중 에러: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/channel/{channel_id}/start")
async def start_recording_scheduled_manual(channel_id: str):
    logger.info(f"예약 채널의 강제 녹화 요청: {channel_id}")
    
    ch = get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    recorder = RecorderManager.get_instance(channel_id)
    if recorder.is_recording:
        return {"status": "success", "message": "이미 녹화 중입니다."}
        
    platform = ch.get("platform")
    ExtClass = EXTRACTOR_MAP.get(platform)
    if not ExtClass:
        raise HTTPException(status_code=400, detail="Unsupported platform")
        
    cookies = get_platform_cookies(platform)
    extractor = ExtClass(channel_id=channel_id, cookies=cookies)
    
    try:
        is_live = await extractor.is_live()
        if is_live:
            meta = await extractor.get_metadata()
            ch_name = ch.get("name", channel_id)
            resolution = ch.get("resolution", "best")
            await trigger_recording(channel_id, platform, ch_name, extractor, recorder, meta, record_type="scheduled", resolution=resolution)
            return {"status": "success", "message": "강제 녹화 시작됨"}
        else:
            raise HTTPException(status_code=400, detail="방송이 오프라인 상태이거나 정보를 가져올 수 없습니다.")
    except Exception as e:
        logger.error(f"녹화 처리 중 에러: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/channel/{channel_id}/stop")
async def stop_recording_manual(channel_id: str):
    # 매뉴얼 강제 중지 로직
    recorder = RecorderManager.get_instance(channel_id)
    if recorder.is_recording:
        await recorder.stop_record("사용자 강제 종료")
        await broadcast_event("recording_stopped", {"id": channel_id})
    return {"status": "success"}
