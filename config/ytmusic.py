import logging
import os
from functools import lru_cache
from pathlib import Path

from ytmusicapi import OAuthCredentials, YTMusic

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_auth_path(env_key: str, default_name: str) -> Path | None:
    raw = os.getenv(env_key, default_name).strip()
    if not raw:
        return None

    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path if path.is_file() else None


@lru_cache
def get_ytmusic_client() -> YTMusic:
    """
    Build a YTMusic client.

    Auth priority:
    1. OAuth file (YTMUSIC_OAUTH_FILE + client id/secret env vars)
    2. Browser headers file (YTMUSIC_BROWSER_FILE)
    3. Unauthenticated client (public browse/search only)
    """
    brand_account_id = os.getenv("YTMUSIC_BRAND_ACCOUNT_ID", "").strip() or None

    oauth_path = _resolve_auth_path("YTMUSIC_OAUTH_FILE", "oauth.json")
    client_id = os.getenv("YTMUSIC_CLIENT_ID", "").strip()
    client_secret = os.getenv("YTMUSIC_CLIENT_SECRET", "").strip()

    if oauth_path:
        if not client_id or not client_secret:
            raise RuntimeError(
                "YTMUSIC_OAUTH_FILE is set but YTMUSIC_CLIENT_ID and "
                "YTMUSIC_CLIENT_SECRET are required for OAuth auth."
            )

        logger.info("Initializing YTMusic with OAuth: file=%s", oauth_path)
        credentials = OAuthCredentials(client_id=client_id, client_secret=client_secret)
        return YTMusic(str(oauth_path), brand_account_id, oauth_credentials=credentials)

    browser_path = _resolve_auth_path("YTMUSIC_BROWSER_FILE", "browser.json")
    if browser_path:
        logger.info("Initializing YTMusic with browser auth: file=%s", browser_path)
        return YTMusic(str(browser_path), brand_account_id)

    logger.info("Initializing unauthenticated YTMusic client")
    return YTMusic()
