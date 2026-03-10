from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.core.logger import logger

class BaseExtractor(ABC):
    """
    모든 스트리밍 플랫폼(치지직, 소프, 유튜브, 트위치 등) 추출을 위한 기본 추상 클래스
    SRP 원칙: 각 플랫폼의 메타데이터 조회, 생방송 상태 판별 기능만 담당함 (실제 녹화는 Recorder 서비스가 담당)
    """
    
    def __init__(self, channel_id: str, cookies: Optional[Dict[str, str]] = None):
        self.channel_id = channel_id
        self.cookies = cookies or {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

    @abstractmethod
    async def is_live(self) -> bool:
        """현재 생방송 진행 여부를 반환 (빠른 폴링용 API 호출 권장)"""
        pass

    @abstractmethod
    async def get_metadata(self) -> Dict[str, Any]:
        """
        방송 메타데이터 반환
        Expected keys: 'title', 'channel_name', 'start_time', 'thumbnail_url', 'stream_url'
        """
        pass

    @abstractmethod
    async def get_channel_info(self) -> Dict[str, Any]:
        """
        방송/생방송 여부와 무관하게 해당 채널(스트리머)의 고유 정보(예: 닉네임) 반환
        Expected keys: 'channel_name'
        """
        pass

    @abstractmethod
    def get_streamlink_args(self) -> list:
        """
        각 Extract 클래스 특성에 따른 Streamlink 혹은 yt-dlp, wget 등의 프로세스를 위한 인수를 정의 
        """
        pass

    def get_cookie_string(self) -> str:
        """딕셔너리 형태의 쿠키를 Cookie 문자열 헤더용으로 반환"""
        if not self.cookies:
            return ""
        return "; ".join([f"{k}={v}" for k, v in self.cookies.items()])

    async def _fetch_json(self, url: str, method: str = "GET", headers: dict = None, data=None, json_body=None, timeout: int = 10) -> dict:
        """
        공통 HTTP JSON 요청 유틸리티. 자식 클래스에서 aiohttp 세션 생성/에러 처리 중복을 줄여줍니다.
        """
        import aiohttp
        req_headers = headers or self.headers.copy()
        try:
            async with aiohttp.ClientSession(headers=req_headers) as session:
                if method.upper() == "POST":
                    async with session.post(url, data=data, json=json_body, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        logger.warning(f"HTTP {response.status} from {url}")
                else:
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        logger.warning(f"HTTP {response.status} from {url}")
        except Exception as e:
            logger.error(f"HTTP 통신 실패 ({url}): {e}")
        return {}
