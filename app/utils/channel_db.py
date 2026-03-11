import json
import os
import threading
from typing import List, Dict, Optional
from app.core.config import settings
from app.core.logger import logger

DB_FILE = os.path.join(settings.DATA_DIR, "channels.json")
_db_lock = threading.RLock()

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        logger.info("채널 데이터베이스(channels.json)를 초기화했습니다.")

def get_all_channels() -> List[Dict]:
    init_db()
    with _db_lock:
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"채널 DB 조회 중 에러 발생: {e}")
            return []

def get_channel(channel_id: str) -> Optional[Dict]:
    channels = get_all_channels()
    for ch in channels:
        if ch.get("id") == channel_id:
            return ch
    return None

def add_channel(channel_data: Dict) -> bool:
    with _db_lock:
        channels = get_all_channels()
        # 중복 체크
        for ch in channels:
            if ch.get("id") == channel_data.get("id"):
                logger.warning(f"이미 존재하는 채널입니다: {channel_data.get('id')}")
                return False
                
        channels.append(channel_data)
        _save_all(channels)
        logger.info(f"채널 추가 완료: {channel_data.get('name', channel_data.get('id'))}")
        return True

def update_channel(channel_id: str, updated_data: Dict) -> bool:
    with _db_lock:
        channels = get_all_channels()
        for i, ch in enumerate(channels):
            if ch.get("id") == channel_id:
                channels[i].update(updated_data)
                _save_all(channels)
                return True
        return False

def delete_channel(channel_id: str) -> bool:
    with _db_lock:
        channels = get_all_channels()
        new_channels = [ch for ch in channels if ch.get("id") != channel_id]
        if len(channels) != len(new_channels):
            _save_all(new_channels)
            logger.info(f"채널 삭제 완료: {channel_id}")
            return True
        return False

def _save_all(channels: List[Dict]):
    with _db_lock:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(channels, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"채널 DB 저장 중 에러 발생: {e}")
