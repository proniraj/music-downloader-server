import logging
from typing import Any

from config.ytmusic import get_ytmusic_client
from ytmusicapi.exceptions import YTMusicError

logger = logging.getLogger(__name__)


class YouTubeMusicError(Exception):
    pass


def get_home(limit: int = 3) -> list[dict[str, Any]]:
    logger.info("Fetching YouTube Music home: limit=%d", limit)

    try:
        result = get_ytmusic_client().get_home(limit=limit)
    except YTMusicError as exc:
        logger.error("YouTube Music get_home failed: %s", exc)
        raise YouTubeMusicError(str(exc)) from exc

    logger.info("YouTube Music home fetched: rows=%d", len(result))
    return result


def get_mood_categories() -> dict[str, Any]:
    logger.info("Fetching YouTube Music mood categories")

    try:
        result = get_ytmusic_client().get_mood_categories()
    except YTMusicError as exc:
        logger.error("YouTube Music get_mood_categories failed: %s", exc)
        raise YouTubeMusicError(str(exc)) from exc

    logger.info(
        "YouTube Music mood categories fetched: sections=%d",
        len(result),
    )
    return result
