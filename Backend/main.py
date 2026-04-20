import os

# Reduce verbose TensorFlow/MediaPipe native warnings during startup.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("ABSL_MIN_LOG_LEVEL", "2")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from routes.analyze import router as analyze_router
from routes.auth import router as auth_router
from routes.catalog import router as catalog_router
from routes.performance import router as performance_router
from routes.privacy import router as privacy_router
from routes.profiles import router as profiles_router
from routes.quality import router as quality_router
from utils.config import get_settings
from utils.exceptions import SmartFitError
from utils.logger import configure_logging, get_logger


def _normalize_origin(origin: str) -> str:
	return origin.strip().rstrip("/")

settings = get_settings()
configure_logging(debug=settings.debug)
logger = get_logger(__name__)

default_fallback_origins = {
	"https://smart-fit-ai-two.vercel.app",
	"http://localhost:5173",
	"http://127.0.0.1:5173",
}

configured_origins = {
	_normalize_origin(origin)
	for origin in settings.allowed_origins
	if origin and origin.strip()
}

effective_allowed_origins = sorted(configured_origins | default_fallback_origins)
effective_cors_regex = settings.cors_allow_origin_regex or (
	r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|"
	r"^https://.*\.vercel\.app$|"
	r"^https://.*\.onrender\.com$"
)

logger.info("CORS allow_origins: %s", effective_allowed_origins)
logger.info("CORS allow_origin_regex: %s", effective_cors_regex)

app = FastAPI(
	title=settings.app_name,
	version=settings.app_version,
	description="SmartFit AI backend for body measurement extraction and apparel size prediction.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=effective_allowed_origins,
	allow_origin_regex=effective_cors_regex,
	allow_credentials="*" not in effective_allowed_origins,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(auth_router)
app.include_router(quality_router)
app.include_router(performance_router)
app.include_router(catalog_router)
app.include_router(profiles_router)
app.include_router(privacy_router)

app.mount(
	"/static",
	StaticFiles(directory=str(settings.tryon_assets_dir.parent)),
	name="static",
)


@app.get("/", tags=["Health"])
def root() -> dict:
	return {
		"status": "ok",
		"service": settings.app_name,
		"version": settings.app_version,
		"docs": "/docs",
		"health": "/health",
	}


@app.get("/health", tags=["Health"])
def health_check() -> dict:
	return {
		"status": "ok",
		"service": settings.app_name,
		"version": settings.app_version,
	}


@app.exception_handler(SmartFitError)
async def smartfit_exception_handler(request: Request, exc: SmartFitError) -> JSONResponse:
	logger.warning("SmartFit error on %s: %s", request.url.path, exc.message)
	return JSONResponse(
		status_code=exc.status_code,
		content={
			"error_code": exc.error_code,
			"message": exc.message,
		},
	)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
	logger.exception("Unhandled server error on %s: %s", request.url.path, exc)
	return JSONResponse(
		status_code=500,
		content={
			"error_code": "INTERNAL_SERVER_ERROR",
			"message": "An unexpected error occurred.",
		},
	)


if __name__ == "__main__":
	import uvicorn

	port = int(os.environ.get("PORT", "8000"))

	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=port,
		reload=settings.debug,
	)
