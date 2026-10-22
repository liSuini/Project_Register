from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings, make_settings
from app.core.database import init_engine
from app.errors import AppError


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = make_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_engine(settings.db_url)

    app = FastAPI(title="Project Ledger API")
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code,
                            content={"code": exc.code, "message": exc.message})

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
