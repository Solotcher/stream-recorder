import aiohttp
from app.core.config import settings
from app.core.logger import logger

def escape_html(text: str) -> str:
    """ 텔레그램 HTML 파싱 오류 방지를 위한 이스케이프 """
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def send_error_alert(channel_name: str, context: str, error_msg: str):
    """ 시스템 주요 에러 발생 시 지정 포맷으로 알림 전송 """
    safe_err = escape_html(str(error_msg))
    msg = f"🚨 <b>시스템 에러 알림</b> 🚨\n\n채널명: <b>{channel_name}</b>\n발생위치: {context}\n오류내용:\n<code>{safe_err}</code>"
    await send_telegram_message(msg)

async def send_telegram_message(message: str) -> bool:
    """
    비동기로 Telegram 봇에 메시지를 발송합니다.
    (BotFather에서 획득한 토큰 및 Chat ID 사용)
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning("Telegram Bot Token 혹은 Chat ID가 설정되지 않아 알림을 보낼 수 없습니다.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    logger.debug(f"텔레그램 발송 성공: {message[:20]}...")
                    return True
                else:
                    error_data = await response.text()
                    logger.error(f"텔레그램 발송 실패 (Status: {response.status}): {error_data}")
                    return False
    except Exception as e:
        logger.error(f"텔레그램 메시지 발송 중 오류 발생: {str(e)}")
        return False
