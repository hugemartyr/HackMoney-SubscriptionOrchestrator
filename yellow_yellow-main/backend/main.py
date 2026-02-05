
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.dotenv import load_dotenv

# Load environment variables BEFORE importing config
load_dotenv()

from config import settings
from routes import router as api_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
