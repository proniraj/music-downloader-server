import logging

from fastapi import FastAPI

from logging_config import setup_logging
from routers.youtube import router as youtube_router
from routers.youtube_music import router as youtube_music_router

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Music Player Backend")

app.include_router(youtube_router)
app.include_router(youtube_music_router)

logger.info("Music Player Backend initialized")


@app.get("/")
def health_check():
    return {"status": "ok"}
