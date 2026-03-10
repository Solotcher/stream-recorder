import os
import json
import psutil
from app.core.logger import logger
from app.core.config import settings

PID_FILE = os.path.join(settings.DATA_DIR, "active_pids.json")

def _load_pids() -> dict:
    if not os.path.exists(PID_FILE):
        return {}
    try:
        with open(PID_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"PID 파일 로드 실패: {e}")
        return {}

def _save_pids(data: dict):
    try:
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"PID 파일 저장 실패: {e}")

def register_process(channel_id: str, pid: int, metadata: dict):
    """ 실행된 녹화 프로세스 PID와 복구용 메타데이터 기록 """
    data = _load_pids()
    data[channel_id] = {
        "pid": pid,
        "metadata": metadata
    }
    _save_pids(data)
    logger.info(f"💾 프로세스 상태 저장됨: [{channel_id}] PID={pid}")

def unregister_process(channel_id: str):
    """ 녹화 정상 종료 시 PID 기록 원격 삭제 """
    data = _load_pids()
    if channel_id in data:
        del data[channel_id]
        _save_pids(data)

def cleanup_and_get_active_processes() -> dict:
    """ 
    서버 부팅 시 호출: 기록된 PID 중 여전히 OS에서 살아있는 것들만 반환하고,
    죽은 것들은 기록에서 청소함 
    """
    data = _load_pids()
    active_processes = {}
    dead_channels = []
    
    for ch_id, info in data.items():
        pid = info.get("pid")
        if pid and psutil.pid_exists(pid):
            # 좀비나 재할당 PID일 가능성을 완벽히 배제하려면 cmdline까지 체크하는게 좋으나
            # streamlink 나 ffmpeg 키워드가 있는지 가볍게 검사
            try:
                proc = psutil.Process(pid)
                cmdline = proc.cmdline()
                if "streamlink" in str(cmdline) or "ffmpeg" in str(cmdline):
                    active_processes[ch_id] = info
                else:
                    dead_channels.append(ch_id)
            except psutil.NoSuchProcess:
                dead_channels.append(ch_id)
        else:
            dead_channels.append(ch_id)
            
    # 죽은 프로세스 DB 정리
    if dead_channels:
        for ch in dead_channels:
            del data[ch]
        _save_pids(data)
        logger.info(f"🧹 시스템에 없는 과거 프로세스 청소 완료: {dead_channels}")
        
    return active_processes
