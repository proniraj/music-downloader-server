from pydantic import BaseModel, Field


class ParseYouTubeRequest(BaseModel):
    url: str


class AudioFormat(BaseModel):
    format_id: str
    ext: str
    url: str
    abr: float | None = None
    filesize: int | None = None
    filesize_approx: int | None = None
    acodec: str | None = None
    protocol: str | None = None
    http_headers: dict[str, str] = Field(default_factory=dict)


class StreamYouTubeResponse(BaseModel):
    url: str
    http_headers: dict[str, str] = Field(default_factory=dict)


class DownloadYouTubeResponse(BaseModel):
    url: str
    ext: str = "mp3"
    title: str
    filename: str
    filesize: int | None = None
    expires_in_seconds: int | None = None


class ParseYouTubeResponse(BaseModel):
    id: str
    title: str
    uploader: str | None = None
    channel: str | None = None
    duration: float | None = None
    thumbnail: str | None = None
    webpage_url: str
    recommended_format_id: str
    audio_formats: list[AudioFormat]

    # Music / track metadata (present on many music uploads; may be null)
    artist: str | None = None
    artists: list[str] = Field(default_factory=list)
    album: str | None = None
    track: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)

    # Description and dates
    description: str | None = None
    upload_date: str | None = None
    release_date: str | None = None
    release_year: int | None = None

    # Engagement
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None

    # Channel details
    channel_id: str | None = None
    channel_url: str | None = None
    channel_follower_count: int | None = None
    channel_is_verified: bool | None = None
    uploader_id: str | None = None
    uploader_url: str | None = None

    # Creator and availability
    creator: str | None = None
    creators: list[str] = Field(default_factory=list)
    availability: str | None = None
    is_live: bool | None = None
    live_status: str | None = None
    language: str | None = None
    age_limit: int | None = None
