"""
Streamlink/yt-dlp를 통해 실제 가용 스트림 해상도를 조회하는 유틸리티.
'best' 키워드가 실제로 어떤 해상도에 매핑되는지 파악합니다.
"""

import asyncio
import json
import re
from typing import Optional

from app.core.config import settings
from app.core.logger import logger


async def resolve_best_quality(stream_url: str, extractor_args: list, platform: str = "chzzk") -> str:
    """
    'best' 키워드가 실제로 매핑되는 스트림 해상도를 조회합니다.

    Args:
        stream_url: 스트림 URL
        extractor_args: extractor에서 제공하는 Streamlink/yt-dlp 추가 인자
        platform: 플랫폼 식별자

    Returns:
        실제 해상도 문자열 (예: "1080p60", "720p30"), 실패 시 "best"
    """
    if platform == "youtube":
        return await _resolve_ytdlp_quality(stream_url, extractor_args)
    return await _resolve_streamlink_quality(stream_url, extractor_args)


async def _resolve_streamlink_quality(stream_url: str, extractor_args: list) -> str:
    """
    Streamlink --json 옵션으로 가용 스트림 목록을 조회하고,
    best에 매핑되는 실제 해상도를 반환합니다.
    """
    cmd = [
        settings.STREAMLINK_PATH,
        *extractor_args,
        stream_url,
        "--json"
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
        output = stdout.decode("utf-8", errors="replace")

        data = json.loads(output)
        streams = data.get("streams", {})

        if not streams:
            logger.debug(f"[stream_quality] 스트림 목록이 비어있음: {stream_url}")
            return "best"

        # best 키가 직접 있는 경우, 해당 스트림의 실제 이름을 찾음
        best_stream = streams.get("best")
        if best_stream:
            # best와 동일한 URL을 가진 실제 해상도 키를 탐색
            best_url = best_stream.get("url", "")
            for name, info in streams.items():
                if name in ("best", "worst"):
                    continue
                if info.get("url", "") == best_url:
                    logger.debug(f"[stream_quality] best → {name} 매핑 확인")
                    return name

        # best 키가 없으면, 해상도 키 중 가장 높은 것을 반환
        resolution_keys = [k for k in streams.keys() if k not in ("best", "worst")]
        if resolution_keys:
            # 해상도 정렬을 위한 파서 (1080p60 → (1080, 60))
            selected = _select_highest_resolution(resolution_keys)
            logger.debug(f"[stream_quality] 최고 해상도 선택: {selected}")
            return selected

    except asyncio.TimeoutError:
        logger.warning(f"[stream_quality] Streamlink --json 조회 타임아웃: {stream_url}")
    except json.JSONDecodeError:
        logger.warning(f"[stream_quality] Streamlink JSON 파싱 실패: {stream_url}")
    except FileNotFoundError:
        logger.error("[stream_quality] Streamlink 실행 파일을 찾을 수 없습니다.")
    except Exception as e:
        logger.warning(f"[stream_quality] 해상도 조회 실패 (폴백 적용): {e}")

    return "best"


async def _resolve_ytdlp_quality(stream_url: str, extractor_args: list) -> str:
    """
    yt-dlp --dump-json 옵션으로 최적 포맷의 해상도를 조회합니다.
    """
    cmd = [
        settings.YTDLP_PATH,
        *extractor_args,
        "--dump-json",
        stream_url
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
        output = stdout.decode("utf-8", errors="replace")

        data = json.loads(output)
        height = data.get("height")
        fps = data.get("fps")

        if height:
            fps_suffix = f"{int(fps)}" if fps and fps > 30 else ""
            quality = f"{height}p{fps_suffix}"
            logger.debug(f"[stream_quality] yt-dlp 해상도 조회: {quality}")
            return quality

    except asyncio.TimeoutError:
        logger.warning(f"[stream_quality] yt-dlp --dump-json 타임아웃: {stream_url}")
    except json.JSONDecodeError:
        logger.warning(f"[stream_quality] yt-dlp JSON 파싱 실패")
    except FileNotFoundError:
        logger.error("[stream_quality] yt-dlp 실행 파일을 찾을 수 없습니다.")
    except Exception as e:
        logger.warning(f"[stream_quality] yt-dlp 해상도 조회 실패: {e}")

    return "best"


def _select_highest_resolution(keys: list) -> str:
    """
    해상도 키 목록에서 가장 높은 해상도를 선택합니다.
    예: ["480p", "720p", "720p60", "1080p", "1080p60"] → "1080p60"
    """
    def _parse_resolution(key: str):
        match = re.match(r"(\d+)p(\d*)", key)
        if match:
            height = int(match.group(1))
            fps = int(match.group(2)) if match.group(2) else 30
            return (height, fps)
        return (0, 0)

    sorted_keys = sorted(keys, key=_parse_resolution, reverse=True)
    return sorted_keys[0] if sorted_keys else "best"


def format_quality_display(resolution: str) -> str:
    """
    해상도 문자열을 UI 표시용으로 포맷합니다.
    예: "1080p60" → "1080P60", "best" → "최고 화질"
    """
    if resolution == "best":
        return "최고 화질"
    if resolution == "worst":
        return "최저 화질"
    return resolution.upper()
