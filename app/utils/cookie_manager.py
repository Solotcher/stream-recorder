import json
import os
from typing import Dict, Optional
from app.core.config import settings
from app.core.logger import logger

COOKIE_FILE = os.path.join(settings.DATA_DIR, "cookies.json")

def load_all_cookies() -> Dict[str, Dict[str, str]]:
    """모든 플랫폼의 쿠키 딕셔너리 리드"""
    if not os.path.exists(COOKIE_FILE):
        return {}
    try:
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"쿠키 파일 로드 실패: {e}")
        return {}

def save_all_cookies(cookie_data: Dict[str, Dict[str, str]]) -> bool:
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookie_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"쿠키 파일 저장 실패: {e}")
        return False

def get_platform_cookies(platform: str) -> Dict[str, str]:
    """특정 플랫폼(chzzk, soop 등)의 쿠키 조회"""
    data = load_all_cookies()
    return data.get(platform, {})

def update_platform_cookies(platform: str, new_cookies: Dict[str, str]):
    data = load_all_cookies()
    data[platform] = new_cookies
    save_all_cookies(data)
    logger.info(f"{platform} 플랫폼 쿠키가 업데이트 되었습니다.")

def parse_raw_cookie(raw_text: str) -> Dict[str, str]:
    """Netscape, JSON(EditThisCookie), 일반 헤더 문자열 형태 클립보드 쿠키 자동 파싱 유틸리티"""
    cookies = {}
    raw_text = raw_text.strip()
    
    if not raw_text:
        return cookies

    # 1. JSON Array (EditThisCookie format)
    if raw_text.startswith("[") and raw_text.endswith("]"):
        try:
            json_cookies = json.loads(raw_text)
            for c in json_cookies:
                if "name" in c and "value" in c:
                    cookies[c["name"]] = c["value"]
            return cookies
        except json.JSONDecodeError:
            pass # JSON 포맷이 아니면 아래 로직 진행

    # 2. Netscape / Semicolon Format
    import re
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 탭이나 두 번 이상의 연속된 공백으로 구분된 Netscape 포맷 매칭
        parts = re.split(r'\t+|\s{2,}', line)
        if len(parts) >= 7:
            # Netscape format: domain, flag, path, secure, expiration, name, value
            cookies[parts[5]] = parts[6]
        elif "=" in line and not line.startswith("."):
            # 헤더에 들어가는 "name=value; name2=value2" 형태
            for pair in line.split(";"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    cookies[k.strip()] = v.strip()
    return cookies
