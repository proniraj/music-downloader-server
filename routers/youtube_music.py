import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from schemas.youtube_music import HomeResponse, HomeRow, MoodCategoriesResponse
from services.youtube_music import YouTubeMusicError, get_home, get_mood_categories

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube-music", tags=["youtube-music"])


def _to_home_response(rows: list[dict[str, Any]]) -> HomeResponse:
    return HomeResponse(
        rows=[
            HomeRow(
                title=row.get("title"),
                contents=row.get("contents") or [],
            )
            for row in rows
        ]
    )


def _to_mood_categories_response(data: dict[str, Any]) -> MoodCategoriesResponse:
    sections: dict[str, list[dict[str, str]]] = {}
    for section_name, categories in data.items():
        sections[section_name] = [
            {"title": item["title"], "params": item["params"]}
            for item in categories
            if item.get("title") and item.get("params")
        ]
    return MoodCategoriesResponse(sections=sections)


@router.get("/home", response_model=HomeResponse)
async def fetch_home(
    limit: int = Query(default=3, ge=1, le=20, description="Number of home rows to return"),
) -> HomeResponse:
    logger.info("Home request received: limit=%d", limit)

    try:
        rows = await asyncio.to_thread(get_home, limit)
        logger.info("Home request succeeded: rows=%d", len(rows))
        return _to_home_response(rows)
    except YouTubeMusicError as exc:
        message = str(exc)
        logger.error("Home request failed: error=%s", message)
        raise HTTPException(status_code=502, detail=message) from exc
    except RuntimeError as exc:
        message = str(exc)
        logger.error("Home request failed during client init: error=%s", message)
        raise HTTPException(status_code=500, detail=message) from exc


@router.get("/mood-categories", response_model=MoodCategoriesResponse)
async def fetch_mood_categories() -> MoodCategoriesResponse:
    logger.info("Mood categories request received")

    try:
        data = await asyncio.to_thread(get_mood_categories)
        response = _to_mood_categories_response(data)
        logger.info("Mood categories request succeeded: sections=%d", len(response.sections))
        return response
    except YouTubeMusicError as exc:
        message = str(exc)
        logger.error("Mood categories request failed: error=%s", message)
        raise HTTPException(status_code=502, detail=message) from exc
    except RuntimeError as exc:
        message = str(exc)
        logger.error("Mood categories request failed during client init: error=%s", message)
        raise HTTPException(status_code=500, detail=message) from exc
