from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .config import get_settings
from .routers import auth, profile, matches, university

settings = get_settings()


@asynccontextmanager
async def lifespan(_):
    if settings.auto_seed_demo:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from backend.scripts.seed_demo import seed
        seed()
    yield


app = FastAPI(lifespan=lifespan, title="RoomSync API", version="1.0.0",
              description="Roommate compatibility estimates (hybrid rule-based + unsupervised ML).")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, profile.router, matches.router, university.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health():
    from .db import get_db
    from .services.matching import get_engine
    eng = get_engine()
    return {"status": "ok", "users": get_db().users.count_documents({}), "latent_model": eng.embedder is not None,
            "supervised_residual": eng.residual is not None}


@app.exception_handler(Exception)
async def unhandled(_, exc):
    return JSONResponse({"detail": "Internal server error"}, status_code=500)
