from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.repositories.permission_repository import PermissionRepository
from app.routers import bugs, projects, users
from config.database import session


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


@app.exception_handler(AppError)
async def app_error_handler(_, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(users.router)
app.include_router(projects.router)
app.include_router(bugs.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}