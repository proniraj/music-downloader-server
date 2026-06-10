from pydantic import BaseModel


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
    http_headers: dict[str, str] = {}


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
