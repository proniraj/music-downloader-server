import logging
from dataclasses import dataclass
from typing import Any

from config.ytmusic import get_auth_mode, get_ytmusic_client
from ytmusicapi import YTMusic
from ytmusicapi.exceptions import YTMusicError

logger = logging.getLogger(__name__)


class YouTubeMusicError(Exception):
    pass


@dataclass
class HomeResult:
    rows: list[dict[str, Any]]
    personalized: bool
    auth_mode: str


def _is_oauth_rejection(exc: YTMusicError) -> bool:
    message = str(exc).lower()
    return "400" in message and "invalid argument" in message


def _fetch_with_client(client: YTMusic, limit: int) -> list[dict[str, Any]]:
    return client.get_home(limit=limit)


def get_home(limit: int = 3) -> HomeResult:
    logger.info("Fetching YouTube Music home: limit=%d", limit)
    auth_mode = get_auth_mode()
    client = get_ytmusic_client()

    try:
        rows = _fetch_with_client(client, limit)
    except YTMusicError as exc:
        if auth_mode == "oauth" and _is_oauth_rejection(exc):
            logger.warning(
                "OAuth rejected by YouTube Music (known upstream issue); "
                "falling back to unauthenticated home feed"
            )
            rows = _fetch_with_client(YTMusic(), limit)
            logger.info("YouTube Music generic home fetched: rows=%d", len(rows))
            return HomeResult(rows=rows, personalized=False, auth_mode="none")

        logger.error("YouTube Music get_home failed: %s", exc)
        raise YouTubeMusicError(str(exc)) from exc

    personalized = auth_mode in {"browser", "oauth"}
    logger.info("YouTube Music home fetched: rows=%d personalized=%s", len(rows), personalized)
    return HomeResult(rows=rows, personalized=personalized, auth_mode=auth_mode)


def get_mood_categories() -> dict[str, Any]:
    logger.info("Fetching YouTube Music mood categories")
    client = get_ytmusic_client()

    try:
        result = client.get_mood_categories()
    except YTMusicError as exc:
        if get_auth_mode() == "oauth" and _is_oauth_rejection(exc):
            logger.warning("OAuth rejected; fetching mood categories without auth")
            result = YTMusic().get_mood_categories()
        else:
            logger.error("YouTube Music get_mood_categories failed: %s", exc)
            raise YouTubeMusicError(str(exc)) from exc

    logger.info(
        "YouTube Music mood categories fetched: sections=%d",
        len(result),
    )
    return result
