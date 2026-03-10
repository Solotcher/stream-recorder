import aiohttp
from typing import Dict, Any, Optional
from app.extractors.base_extractor import BaseExtractor
from app.core.logger import logger

class SoopExtractor(BaseExtractor):
    """
    숲(SOOP) FHD 자동 녹화를 위한 모듈. 
    일반적인 m3u8 방식 외에, soop-streamer-alert처럼 웹소켓 및 chunk 다운로드 병합 방식을 
    옵셔널하게 선택할 수 있도록 구현.
    """
    
    BASE_API_URL = "https://live.sooplive.co.kr/afreeca/player_live_api.php"

    def __init__(self, channel_id: str, cookies: Optional[Dict[str, str]] = None):
        super().__init__(channel_id, cookies)
    
    async def get_metadata(self) -> Dict[str, Any]:
        """ SOOP 방송국 정보 API를 통한 메타데이터 조회 """
        url = self.BASE_API_URL
        
        try:
            req_headers = self.headers.copy()
            req_headers["Origin"] = "https://play.sooplive.co.kr"
            req_headers["Referer"] = "https://play.sooplive.co.kr/"
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            payload = f"bid={self.channel_id}"
            
            async with aiohttp.ClientSession(headers=req_headers) as session:
                async with session.post(url, data=payload, timeout=10) as response:
                    if response.status == 200:
                        # SOOP API는 text/html mimetype으로 JSON을 반환하므로 content_type=None 필수
                        data = await response.json(content_type=None)
                        channel = data.get("CHANNEL")
                        
                        # 응답 파싱 실패 (API 구조 변경 등)
                        if not channel:
                            logger.warning(f"SOOP API CHANNEL 응답 누락: {self.channel_id}")
                            return {"status": "ERROR"}
                            
                        is_live = (channel.get("RESULT") == 1)
                        
                        if not is_live:
                            return {"status": "CLOSE"}
                            
                        return {
                            "title": channel.get("TITLE", "제목 없음"),
                            "channel_name": channel.get("BJNICK", self.channel_id),
                            "status": "OPEN", 
                            "stream_url": f"https://play.sooplive.co.kr/{self.channel_id}"
                        }
                    else:
                        logger.warning(f"SOOP API 응답 에러 (Status {response.status}): {self.channel_id}")
                        return {"status": "ERROR"}
        except Exception as e:
            logger.error(f"SOOP API 통신 실패: {str(e)}")
            return {"status": "ERROR"}

        return {"status": "ERROR", "channel_name": self.channel_id}

    async def get_channel_info(self) -> Dict[str, Any]:
        """ SOOP 플레이어 API를 재활용하여 라이브 관계없이 닉네임 파싱 시도 """
        url = self.BASE_API_URL
        try:
            req_headers = self.headers.copy()
            req_headers["Origin"] = "https://play.sooplive.co.kr"
            req_headers["Referer"] = "https://play.sooplive.co.kr/"
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            payload = f"bid={self.channel_id}"
            
            async with aiohttp.ClientSession(headers=req_headers) as session:
                async with session.post(url, data=payload, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        channel = data.get("CHANNEL")
                        if channel:
                            return {"channel_name": channel.get("BJNICK", self.channel_id)}
        except Exception as e:
            logger.error(f"SOOP API 통신 실패 (채널조회): {str(e)}")
            
        return {"channel_name": self.channel_id}

    async def is_live(self) -> bool:
        meta = await self.get_metadata()
        if meta.get("status") == "ERROR":
            # API 일시 오류 시: 이미 녹화가 진행 중이면 True(세션 보존), 아니면 False(새 녹화 시도 안 함)
            from app.services.recorder import RecorderManager
            recorder = RecorderManager.get_instance(self.channel_id)
            if recorder.is_recording:
                logger.warning(f"[{self.channel_id}] API 오류이나 녹화 중이므로 라이브 상태를 보존합니다.")
                return True
            logger.warning(f"[{self.channel_id}] API 오류. 녹화 중이 아니므로 라이브 판단을 보류합니다.")
            return False
        return meta.get("status") == "OPEN"

    def get_streamlink_args(self) -> list:
        """
        SOOP 녹화용 Streamlink 인자.
        Streamlink soop 플러그인의 title-change 이슈(GitHub #6703) 대응으로
        --hls-live-reload, --retry-open 플래그를 포함하여 즉시 종료를 방지합니다.
        """
        args = [
            "--ffmpeg-copyts",
            "--stream-segment-timeout", "15",
            "--stream-timeout", "60",
            "--retry-streams", "5",
            "--retry-open", "3",
            "--hls-live-restart",
            "--http-header", "Origin=https://play.sooplive.co.kr",
            "--http-header", "Referer=https://play.sooplive.co.kr/"
        ]
        cookie_str = self.get_cookie_string()
        if cookie_str:
            args.extend(["--http-header", f"Cookie={cookie_str}"])
            
        # 수동 녹화 등으로 주입된 일회성 비밀번호 처리
        stream_pw = getattr(self, "stream_password", None)
        if stream_pw:
            args.extend(["--soop-stream-password", stream_pw])
            
        return args
