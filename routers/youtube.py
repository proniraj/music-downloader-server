import asyncio
import logging

from fastapi import APIRouter, HTTPException

from schemas.youtube import (
    ParseYouTubeRequest,
    ParseYouTubeResponse,
    StreamYouTubeResponse,
)
from services.youtube_parser import (
    YouTubeParseError,
    get_youtube_audio_stream,
    is_youtube_url,
    parse_youtube_url,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


def _validate_youtube_url(url: str) -> str:
    normalized_url = url.strip()
    if not normalized_url:
        logger.warning("YouTube request rejected: empty URL")
        raise HTTPException(status_code=400, detail="URL is required")

    if not is_youtube_url(normalized_url):
        logger.warning("YouTube request rejected: invalid YouTube URL: %s", normalized_url)
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Only YouTube video, music, or shorts URLs are supported.",
        )

    return normalized_url


def _handle_youtube_error(url: str, exc: YouTubeParseError, action: str) -> None:
    message = str(exc)
    status_code = 400 if "not supported" in message.lower() else 502
    log = logger.warning if status_code == 400 else logger.error
    log("%s failed: url=%s status=%d error=%s", action, url, status_code, message)
    raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/parse", response_model=ParseYouTubeResponse)
async def parse_youtube(request: ParseYouTubeRequest) -> ParseYouTubeResponse:
    url = _validate_youtube_url(request.url)
    logger.info("Parse request received: url=%s", url)

    try:
        result = await asyncio.to_thread(parse_youtube_url, url)
        logger.info(
            "Parse request succeeded: id=%s title=%r formats=%d",
            result.id,
            result.title,
            len(result.audio_formats),
        )
        return result
    except YouTubeParseError as exc:
        _handle_youtube_error(url, exc, "Parse request")


@router.post("/stream", response_model=StreamYouTubeResponse)
async def stream_youtube(request: ParseYouTubeRequest) -> StreamYouTubeResponse:
    url = _validate_youtube_url(request.url)
    logger.info("Stream request received: url=%s", url)

    try:
        stream = await asyncio.to_thread(get_youtube_audio_stream, url)
        logger.info("Stream request succeeded: url=%s format_id=%s", url, stream.format_id)
        return StreamYouTubeResponse(url=stream.url, http_headers=stream.http_headers)
    except YouTubeParseError as exc:
        _handle_youtube_error(url, exc, "Stream request")
