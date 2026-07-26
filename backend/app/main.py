from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import router
from app.services.scheduler import iniciar_scheduler, parar_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
def _startup_scheduler() -> None:
    import os
    import threading
    # Gate de emergência: DISABLE_SCHEDULER=1 sobe a API SEM o scheduler.
    if os.getenv("DISABLE_SCHEDULER", "0").strip().lower() in ("1", "true", "yes", "on"):
        return
    # DEFERE o início do scheduler: a API precisa fazer BIND imediatamente. O
    # scheduler, ao subir, pode disparar um job "atrasado" (misfire) que roda a
    # montagem (download + LLM + gate) — se isso rodar dentro do startup, o worker
    # demora minutos para ficar "ready" (502 na janela). Deferindo em thread, a
    # API atende na hora e o scheduler/montagem roda depois, sem bloquear.
    _atraso = float(os.getenv("SCHEDULER_START_DELAY", "20"))
    threading.Timer(_atraso, iniciar_scheduler).start()


@app.on_event("shutdown")
def _shutdown_scheduler() -> None:
    parar_scheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

web_dist = Path(__file__).parent.parent.parent / "web" / "dist"
if web_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index = web_dist / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION}", "docs": "/docs"}
else:
    @app.get("/")
    def root():
        return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION}", "docs": "/docs"}
