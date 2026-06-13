import logging
import re
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from schemas.youtube import AudioFormat, ParseYouTubeResponse

logger = logging.getLogger(__name__)

MAX_AUDIO_FORMATS = 5

# iOS + Android both play AAC (m4a/mp4a) and MP3. WebM/Opus is common on YouTube but
# not reliably supported on iOS (AVPlayer / expo-av).
MOBILE_AUDIO_EXTENSIONS = frozenset({"m4a", "mp3"})
MOBILE_AUDIO_CODEC_PREFIXES = ("mp4a", "aac", "mp3")
EXCLUDED_AUDIO_EXTENSIONS = frozenset({"webm", "ogg", "opus"})
EXCLUDED_AUDIO_CODECS = frozenset({"opus", "vorbis"})

YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "format": "ba[ext=m4a]/ba[acodec^=mp4a]/ba[ext=mp3]/ba[acodec=mp3]",
}


class YouTubeParseError(Exception):
    pass


def is_youtube_url(url: str) -> bool:
    """
    Basic validation to ensure the URL is a YouTube URL.
    Supports: youtube.com, youtu.be, music.youtube.com
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube\.com|youtu\.be|music\.youtube\.com)'
        r'/(watch\?v=|embed/|v/|shorts/)?[\w-]{11}'
    )
    return bool(re.match(youtube_regex, url))


def _is_audio_format(fmt: dict[str, Any]) -> bool:
    if not fmt.get("url"):
        return False

    vcodec = fmt.get("vcodec")
    acodec = fmt.get("acodec")

    if vcodec == "none":
        return acodec not in (None, "none")

    return acodec not in (None, "none") and vcodec in (None, "none")


def _is_mobile_compatible_audio_format(fmt: dict[str, Any]) -> bool:
    if not _is_audio_format(fmt):
        return False

    ext = str(fmt.get("ext", "")).lower()
    acodec = str(fmt.get("acodec", "")).lower()

    if ext in EXCLUDED_AUDIO_EXTENSIONS:
        return False
    if acodec in EXCLUDED_AUDIO_CODECS or acodec.startswith("opus"):
        return False

    if ext in MOBILE_AUDIO_EXTENSIONS:
        return True

    return any(acodec.startswith(prefix) for prefix in MOBILE_AUDIO_CODEC_PREFIXES)


def _select_mobile_audio_formats(formats: list[dict[str, Any]]) -> list[AudioFormat]:
    compatible_formats = [
        fmt for fmt in formats if _is_mobile_compatible_audio_format(fmt)
    ]

    return sorted(
        (_to_audio_format(fmt) for fmt in compatible_formats),
        key=lambda fmt: _bitrate({"abr": fmt.abr, "tbr": None}),
        reverse=True,
    )[:MAX_AUDIO_FORMATS]


def _bitrate(fmt: dict[str, Any]) -> float:
    for key in ("abr", "tbr"):
        value = fmt.get(key)
        if value is not None:
            return float(value)
    return 0.0


def _to_audio_format(fmt: dict[str, Any]) -> AudioFormat:
    headers = fmt.get("http_headers") or {}
    return AudioFormat(
        format_id=str(fmt.get("format_id", "")),
        ext=str(fmt.get("ext", "")),
        url=str(fmt["url"]),
        abr=fmt.get("abr"),
        filesize=fmt.get("filesize"),
        filesize_approx=fmt.get("filesize_approx"),
        acodec=fmt.get("acodec"),
        protocol=fmt.get("protocol"),
        http_headers={str(k): str(v) for k, v in headers.items()},
    )


def _pick_thumbnail(info: dict[str, Any]) -> str | None:
    thumbnail = info.get("thumbnail")
    if thumbnail:
        return str(thumbnail)

    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        return str(thumbnails[-1].get("url"))

    return None


def _str_list(value: Any) -> list[str]:
    if not value:
        return []
    return [str(item) for item in value]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def get_youtube_audio_stream(url: str) -> AudioFormat:
    result = parse_youtube_url(url)
    stream = next(
        (
            fmt
            for fmt in result.audio_formats
            if fmt.format_id == result.recommended_format_id
        ),
        None,
    )
    if not stream:
        raise YouTubeParseError("No audio stream returned for this URL")
    return stream


def parse_youtube_url(url: str) -> ParseYouTubeResponse:
    logger.info("Starting YouTube extraction: url=%s", url)

    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                logger.error("yt-dlp returned no metadata: url=%s", url)
                raise YouTubeParseError("No metadata returned for this URL")

            safe = ydl.sanitize_info(info)
    except (DownloadError, ExtractorError) as exc:
        logger.error("yt-dlp extraction failed: url=%s error=%s", url, exc)
        raise YouTubeParseError(str(exc)) from exc

    if not safe:
        logger.error("Failed to sanitize yt-dlp metadata: url=%s", url)
        raise YouTubeParseError("Failed to sanitize metadata for this URL")

    if safe.get("_type") == "playlist":
        logger.warning("Playlist URL rejected: url=%s", url)
        raise YouTubeParseError("Playlist URLs are not supported. Provide a single video URL.")

    formats = safe.get("formats") or []
    audio_formats = _select_mobile_audio_formats(formats)

    if not audio_formats:
        total_audio_formats = sum(1 for fmt in formats if _is_audio_format(fmt))
        logger.error(
            "No mobile-compatible audio formats found: url=%s total_formats=%d audio_only=%d",
            url,
            len(formats),
            total_audio_formats,
        )
        raise YouTubeParseError(
            "No mobile-compatible audio formats found for this URL. "
            "Only AAC (m4a) and MP3 streams are supported."
        )

    video_id = str(safe.get("id", ""))
    title = str(safe.get("title") or safe.get("fulltitle") or "Unknown title")
    webpage_url = str(safe.get("webpage_url") or url)

    logger.info(
        "YouTube extraction completed: id=%s title=%r audio_formats=%d recommended=%s",
        video_id,
        title,
        len(audio_formats),
        audio_formats[0].format_id,
    )

    return ParseYouTubeResponse(
        id=video_id,
        title=title,
        uploader=safe.get("uploader"),
        channel=safe.get("channel"),
        duration=safe.get("duration"),
        thumbnail=_pick_thumbnail(safe),
        webpage_url=webpage_url,
        recommended_format_id=audio_formats[0].format_id,
        audio_formats=audio_formats,
        artist=safe.get("artist"),
        artists=_str_list(safe.get("artists")),
        album=safe.get("album"),
        track=safe.get("track"),
        categories=_str_list(safe.get("categories")),
        tags=_str_list(safe.get("tags")),
        genres=_str_list(safe.get("genres")),
        description=safe.get("description"),
        upload_date=safe.get("upload_date"),
        release_date=safe.get("release_date"),
        release_year=safe.get("release_year"),
        view_count=safe.get("view_count"),
        like_count=safe.get("like_count"),
        comment_count=safe.get("comment_count"),
        channel_id=_optional_str(safe.get("channel_id")),
        channel_url=_optional_str(safe.get("channel_url")),
        channel_follower_count=safe.get("channel_follower_count"),
        channel_is_verified=safe.get("channel_is_verified"),
        uploader_id=_optional_str(safe.get("uploader_id")),
        uploader_url=_optional_str(safe.get("uploader_url")),
        creator=safe.get("creator"),
        creators=_str_list(safe.get("creators")),
        availability=safe.get("availability"),
        is_live=safe.get("is_live"),
        live_status=safe.get("live_status"),
        language=safe.get("language"),
        age_limit=safe.get("age_limit"),
    )
