import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from routers.scan import router as scan_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="CodeQL AI Security Scanner",
    description="Automated security analysis with AI-enhanced vulnerability reports",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router)


@app.get("/health")
async def health_check() -> dict[str, object]:
    import shutil
    from utils.config import settings

    codeql_path = shutil.which("codeql") or settings.CODEQL_PATH
    codeql_exists = os.path.isfile(codeql_path)

    return {
        "status": "healthy",
        "codeql_path": codeql_path,
        "codeql_installed": codeql_exists,
        "codeql_env": settings.CODEQL_PATH,
    }
