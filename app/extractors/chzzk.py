import aiohttp
from typing import Dict, Any, Optional
from app.extractors.base_extractor import BaseExtractor
from app.core.logger import logger

class ChzzkExtractor(BaseExtractor):
    """
    치지직 1.1.5b ~ 2508d의 안정적 라이브 채널 검사 API (LiveStatus)를 활용
    """
    
    BASE_API_URL = "https://api.chzzk.naver.com/polling/v3/channels/{}/live-status"

    def __init__(self, channel_id: str, cookies: Optional[Dict[str, str]] = None):
        super().__init__(channel_id, cookies)
    
    async def get_metadata(self) -> Dict[str, Any]:
        url = self.BASE_API_URL.format(self.channel_id)
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("content", {})
                        if not content:
                            return {"status": "CLOSE"}
                            
                        status = content.get("status", "CLOSE")
                        title = content.get("liveTitle", "제목 없음")
                        thumbnail = content.get("liveImageUrl", "")
                        
                        # live-status API에는 채널명이 없으므로 별도 Channel API로 실제 닉네임 조회
                        channel_name = self.channel_id
                        try:
                            info = await self.get_channel_info()
                            channel_name = info.get("channel_name", self.channel_id)
                        except Exception:
                            pass
                        
                        return {
                            "title": title,
                            "channel_name": channel_name,
                            "status": status, 
                            "thumbnail": thumbnail,
                            "stream_url": f"https://chzzk.naver.com/live/{self.channel_id}"
                        }
                    else:
                        logger.warning(f"Chzzk API 응답 에러 (Status {response.status}): {self.channel_id}")
        except Exception as e:
            logger.error(f"Chzzk API 통신 실패: {str(e)}")
            
        return {"status": "CLOSE", "channel_name": self.channel_id}

    async def get_channel_info(self) -> Dict[str, Any]:
        """ 치지직 채널 고유 정보(닉네임 등) 조회 """
        url = f"https://api.chzzk.naver.com/service/v1/channels/{self.channel_id}"
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("content", {})
                        if content:
                            return {
                                "channel_name": content.get("channelName", self.channel_id),
                                "thumbnail": content.get("channelImageUrl", "")
                            }
        except Exception as e:
            logger.error(f"Chzzk Channel API 통신 실패: {str(e)}")
            
        return {"channel_name": self.channel_id}

    async def is_live(self) -> bool:
        meta = await self.get_metadata()
        return meta.get("status") == "OPEN"

    def get_streamlink_args(self) -> list:
        """기존 2508d와 동일하게 FFmpeg Copy를 유도하는 커맨드 라인 인자 반환"""
        # streamlink --ffmpeg-copyts --ffmpeg-ffmpeg [경로] https://chzzk.naver.com/live/xxx best -o [경로]
        args = [
            "--ffmpeg-copyts",
            "--stream-segment-timeout", "15",
            "--stream-segment-attempts", "12",
            "--hls-live-restart"
        ]
        cookie_str = self.get_cookie_string()
        if cookie_str:
            args.extend(["--http-header", f"Cookie={cookie_str}"])
        return args
