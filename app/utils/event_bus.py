"""
WebSocket 연결 관리 및 이벤트 브로드캐스트 모듈

녹화 시작/종료, 채널 추가/삭제 등의 서버 이벤트를
연결된 모든 웹 클라이언트에 실시간으로 전파한다.
"""

import json
import asyncio
from typing import List
from fastapi import WebSocket
from app.core.logger import logger


class ConnectionManager:
    """WebSocket 연결 풀을 관리하는 싱글턴 매니저"""

    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """새 WebSocket 연결 수립"""
        await websocket.accept()
        self._connections.append(websocket)
        logger.debug(f"WebSocket 클라이언트 연결됨 (총 {len(self._connections)}개)")

    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.debug(f"WebSocket 클라이언트 해제됨 (총 {len(self._connections)}개)")

    async def broadcast(self, event_type: str, data: dict = None):
        """
        모든 연결된 클라이언트에 이벤트를 브로드캐스트한다.

        Args:
            event_type: 이벤트 식별자 (예: recording_started, channel_added)
            data: 이벤트와 함께 전달할 추가 데이터 (선택)
        """
        if not self._connections:
            return

        message = json.dumps({
            "event": event_type,
            "data": data or {}
        })

        stale_connections = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale_connections.append(ws)

        # 끊어진 연결 정리
        for ws in stale_connections:
            self.disconnect(ws)


# 전역 싱글턴 인스턴스
ws_manager = ConnectionManager()


async def broadcast_event(event_type: str, data: dict = None):
    """모듈 외부에서 간편하게 호출할 수 있는 브로드캐스트 헬퍼 함수"""
    await ws_manager.broadcast(event_type, data)
