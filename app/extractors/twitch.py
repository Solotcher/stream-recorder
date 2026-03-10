import aiohttp
from typing import Dict, Any, Optional
from app.extractors.base_extractor import BaseExtractor
from app.core.logger import logger

class TwitchExtractor(BaseExtractor):
    """
    무거운 Streamlink를 계속 폴링하지 않도록 Twitch의 자체 GQL 또는 HTTP API를 가볍게 체크하는 클래스.
    """
    
    # Twitch GQL endpoint for fast status check
    GQL_URL = "https://gql.twitch.tv/gql"
    CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # Twitch Web Common Client ID

    def __init__(self, channel_id: str, cookies: Optional[Dict[str, str]] = None):
        super().__init__(channel_id, cookies)
        self.headers.update({"Client-ID": self.CLIENT_ID})
    
    async def get_metadata(self) -> Dict[str, Any]:
        query = {
            "query": """
            query($login: String!) {
                user(login: $login) {
                    stream {
                        id
                        title
                        type
                        viewersCount
                        createdAt
                    }
                }
            }
            """,
            "variables": {"login": self.channel_id}
        }
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(self.GQL_URL, json=query, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        user_data = data.get("data", {}).get("user")
                        
                        if not user_data or not user_data.get("stream"):
                            return {"status": "CLOSE"}
                            
                        stream_info = user_data["stream"]
                        return {
                            "title": stream_info.get("title", "제목 없음"),
                            "channel_name": self.channel_id,
                            "status": "OPEN",
                            "start_time": stream_info.get("createdAt"),
                            "stream_url": f"https://twitch.tv/{self.channel_id}"
                        }
                    else:
                        logger.warning(f"Twitch GQL 에러 (Status {response.status}): {self.channel_id}")
        except Exception as e:
            logger.error(f"Twitch 통신 실패: {str(e)}")

        return {"status": "CLOSE", "channel_name": self.channel_id}

    async def get_channel_info(self) -> Dict[str, Any]:
        """ 트위치 GQL을 통해 라이브여부와 상관없이 스트리머 공식 명칭(displayName) 조회 """
        query = {
            "query": """
            query($login: String!) {
                user(login: $login) {
                    displayName
                }
            }
            """,
            "variables": {"login": self.channel_id}
        }
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(self.GQL_URL, json=query, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        user_data = data.get("data", {}).get("user")
                        if user_data:
                            return {"channel_name": user_data.get("displayName", self.channel_id)}
        except Exception as e:
            logger.error(f"Twitch GQL 통신 실패 (채널조회): {str(e)}")
            
        return {"channel_name": self.channel_id}
    async def is_live(self) -> bool:
        meta = await self.get_metadata()
        return meta.get("status") == "OPEN"

    def get_streamlink_args(self) -> list:
        """Twitch 특화 Streamlink 인자 (광고 우회 등 추가 가능)"""
        args = [
            "--twitch-disable-ads",
            "--twitch-disable-hosting",
            "--twitch-disable-reruns"
        ]
        cookie_str = self.get_cookie_string()
        # 트위치 OAuth 토큰이나 auth가 들어있다면 주입
        if "auth-token" in self.cookies:
            args.extend(["--twitch-api-header", f"Authorization=OAuth {self.cookies['auth-token']}"])
        return args
