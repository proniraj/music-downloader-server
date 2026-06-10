import asyncio

from fastapi import APIRouter, HTTPException

from schemas.youtube import ParseYouTubeRequest, ParseYouTubeResponse
from services.youtube_parser import YouTubeParseError, parse_youtube_url

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


@router.post("/parse", response_model=ParseYouTubeResponse)
async def parse_youtube(request: ParseYouTubeRequest) -> ParseYouTubeResponse:
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        return await asyncio.to_thread(parse_youtube_url, url)
    except YouTubeParseError as exc:
        message = str(exc)
        status_code = 400 if "not supported" in message.lower() else 502
        raise HTTPException(status_code=status_code, detail=message) from exc
