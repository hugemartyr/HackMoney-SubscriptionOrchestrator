
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.dotenv import load_dotenv
from utils.logger import get_logger

# Load environment variables BEFORE importing config
load_dotenv()

from config import settings
from routes import router as api_router


logger = get_logger(__name__)

logger.info("Initializing FastAPI application with CORS and API routes")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(
    "CORS configured",
    extra={
        "allow_origins": settings.CORS_ALLOW_ORIGINS,
    },
)

app.include_router(api_router)
logger.info("API router included and application startup completed")


if __name__ == "__main__":
    import uvicorn

    logger.info("Running app with uvicorn", extra={"host": "0.0.0.0", "port": 8000})
    uvicorn.run(app, host="0.0.0.0", port=8000)
