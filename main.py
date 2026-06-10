from fastapi import FastAPI

from routers.youtube import router as youtube_router

app = FastAPI(title="Music Player Backend")

app.include_router(youtube_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
