import logging
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from ytmusicapi import OAuthCredentials, YTMusic

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_auth_path(env_key: str) -> Path | None:
    raw = os.getenv(env_key, "").strip()
    if not raw:
        return None

    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path if path.is_file() else None


def get_auth_mode() -> str:
    """Returns: browser, oauth, or none."""
    client = get_ytmusic_client()
    auth_type = str(client.auth_type)
    if "BROWSER" in auth_type:
        return "browser"
    if "OAUTH" in auth_type:
        return "oauth"
    return "none"


@lru_cache
def get_ytmusic_client() -> YTMusic:
    """
    Build a YTMusic client.

    Auth priority (YTMUSIC_AUTH=auto by default):
    1. Browser headers (browser.json) — currently the reliable option for personalization
    2. OAuth (oauth.json) — often rejected by YouTube Music with HTTP 400 as of 2025/2026
    3. Unauthenticated client (public browse/search only)
    """
    auth_mode = os.getenv("YTMUSIC_AUTH", "auto").strip().lower()
    brand_account_id = os.getenv("YTMUSIC_BRAND_ACCOUNT_ID", "").strip() or None

    browser_path = _resolve_auth_path("YTMUSIC_BROWSER_FILE")
    oauth_path = _resolve_auth_path("YTMUSIC_OAUTH_FILE")
    client_id = os.getenv("YTMUSIC_CLIENT_ID", "").strip()
    client_secret = os.getenv("YTMUSIC_CLIENT_SECRET", "").strip()

    def browser_client() -> YTMusic | None:
        if browser_path:
            logger.info("Initializing YTMusic with browser auth: file=%s", browser_path)
            return YTMusic(str(browser_path), brand_account_id)
        return None

    def oauth_client() -> YTMusic | None:
        if oauth_path and client_id and client_secret:
            logger.info("Initializing YTMusic with OAuth: file=%s", oauth_path)
            credentials = OAuthCredentials(client_id=client_id, client_secret=client_secret)
            return YTMusic(str(oauth_path), brand_account_id, oauth_credentials=credentials)
        if oauth_path:
            logger.warning(
                "OAuth file %s exists but YTMUSIC_CLIENT_ID / YTMUSIC_CLIENT_SECRET are missing",
                oauth_path,
            )
        return None

    if auth_mode == "browser":
        if client := browser_client():
            return client
        raise RuntimeError("YTMUSIC_AUTH=browser but YTMUSIC_BROWSER_FILE is missing or invalid")

    if auth_mode == "oauth":
        if client := oauth_client():
            return client
        raise RuntimeError(
            "YTMUSIC_AUTH=oauth but oauth.json or client credentials are missing or invalid"
        )

    if auth_mode == "none":
        logger.info("Initializing unauthenticated YTMusic client")
        return YTMusic()

    # auto: browser first (OAuth is frequently broken server-side)
    if client := browser_client():
        return client
    if client := oauth_client():
        return client

    logger.info("Initializing unauthenticated YTMusic client")
    return YTMusic()
