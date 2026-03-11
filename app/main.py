from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.core.config import settings
from app.core.logger import logger
from app.api.endpoints import router as api_router
from app.services.scheduler import init_scheduler, shutdown_scheduler
import os
import sys
import asyncio

# Windows 환경에서 subprocess (streamlink, ffmpeg) 비동기 실행 시 
# NotImplementedError 가 발생하는 것을 막기 위해 ProactorEventLoop 강제 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    logger.info(f"{settings.APP_NAME} {settings.VERSION} 가 시작되었습니다.")
    
    # 외부 의존성(FFmpeg, Streamlink) 자동 감지 및 다운로드
    from app.utils.dependency_manager import check_all_dependencies
    check_all_dependencies()
    
    # 서버 재부팅(Live Reload) 시 분실된 FFmpeg 프로세스(PID) 추적 및 메모리 부착
    from app.services.recorder import RecorderManager
    try:
        RecorderManager.restore_active_processes()
    except Exception as e:
        logger.error(f"프로세스 복구 실패: {e}")
        
    init_scheduler()
    
    yield
    
    # Shutdown Events
    logger.info(f"{settings.APP_NAME} 종료 중...")
    shutdown_scheduler()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="통합 스트림 레코더 시스템 API (치지직, 숲, 유튜브, 트위치 지원)",
        lifespan=lifespan
    )

    # CORS: 로컬호스트만 허용 (운영 시 실제 도메인 추가)
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Key 인증 미들웨어 (설정에 API_KEY가 있을 때만 적용)
    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        api_key = getattr(settings, "API_KEY", "")
        # API Key가 미설정이면 인증 생략 (개발 모드)
        if api_key and request.url.path.startswith("/api"):
            req_key = request.headers.get("X-API-Key", "")
            if req_key != api_key:
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing API Key"})
        return await call_next(request)

    # API 라우터 등록
    app.include_router(api_router, prefix="/api", tags=["API"])

    # WebSocket 실시간 이벤트 엔드포인트
    from app.utils.event_bus import ws_manager

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                # 클라이언트로부터의 메시지 대기 (keep-alive)
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception:
            ws_manager.disconnect(websocket)

    # 프론트엔드 정적 디렉토리 마운트
    frontend_dir = os.path.join(settings.BASE_DIR, "frontend")
    if os.path.exists(frontend_dir):
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

        @app.get("/")
        async def root_html():
            return FileResponse(os.path.join(frontend_dir, "index.html"))
    else:
        logger.warning("Frontend directory not found. Static GUI serving disabled.")
        @app.get("/")
        async def root():
            return {"message": f"Welcome to {settings.APP_NAME} API. (Frontend missing)"}

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

