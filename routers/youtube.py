import asyncio
import logging

from fastapi import APIRouter, HTTPException

from schemas.youtube import ParseYouTubeRequest, ParseYouTubeResponse
from services.youtube_parser import YouTubeParseError, is_youtube_url, parse_youtube_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


@router.post("/parse", response_model=ParseYouTubeResponse)
async def parse_youtube(request: ParseYouTubeRequest) -> ParseYouTubeResponse:
    url = request.url.strip()
    if not url:
        logger.warning("Parse request rejected: empty URL")
        raise HTTPException(status_code=400, detail="URL is required")

    if not is_youtube_url(url):
        logger.warning("Parse request rejected: invalid YouTube URL: %s", url)
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Only YouTube video, music, or shorts URLs are supported."
        )

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
        message = str(exc)
        status_code = 400 if "not supported" in message.lower() else 502
        log = logger.warning if status_code == 400 else logger.error
        log("Parse request failed: url=%s status=%d error=%s", url, status_code, message)
        raise HTTPException(status_code=status_code, detail=message) from exc
