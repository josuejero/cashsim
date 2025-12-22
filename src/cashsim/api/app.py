from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cashsim.api.middleware import RequestIdMiddleware, TimingMiddleware
from cashsim.api.settings import ApiSettings
from cashsim.api.v1.routes import router as v1_router


def create_app() -> FastAPI:
    settings = ApiSettings()

    app = FastAPI(
        title="CashSim API",
        version="1.0.0",
        default_response_class=JSONResponse,
    )

    # Versioned API surface
    app.include_router(v1_router, prefix="/v1", tags=["v1"])

    # Middleware
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(TimingMiddleware)

    if settings.allow_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
