import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.repositories.permission_repository import PermissionRepository
from app.routers import bugs, projects, users
from config.database import session

load_dotenv()


def _allowed_origins() -> list[str]:
    # Comma-separated list in CORS_ORIGINS. Defaults to "*" (any origin).
    raw = os.getenv("CORS_ORIGINS", "*")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["*"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema is managed by Alembic (`alembic upgrade head`).
    # Seed the built-in permission catalog on startup (idempotent).
    db = session()
    try:
        PermissionRepository(db).seed_defaults()
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title="BugDrop API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(users.router)
app.include_router(projects.router)
app.include_router(bugs.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}