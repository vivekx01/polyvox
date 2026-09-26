import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from polyvox.auth.dependencies import RedirectToLogin
from polyvox.db.bootstrap import init_db
from polyvox.routers import api_tts, audio, health, pages_admin, pages_auth, pages_generate
from polyvox.storage.cleanup import cleanup_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cleanup_task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()


app = FastAPI(title="Polyvox", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.include_router(health.router)
app.include_router(pages_auth.router)
app.include_router(pages_generate.router)
app.include_router(pages_admin.router)
app.include_router(api_tts.router)
app.include_router(audio.router)


@app.exception_handler(RedirectToLogin)
def redirect_to_login(request: Request, exc: RedirectToLogin):
    return RedirectResponse(url="/login", status_code=303)
