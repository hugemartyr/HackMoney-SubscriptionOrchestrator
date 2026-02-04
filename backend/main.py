from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from services.agent_service import handle_api_call, stream_api_call
from utils.schema import AgentRequest, AgentResponse
from utils.config import load_config

load_config()

app = FastAPI(title="HackMoney LLM Backend", version="0.1.0")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.post("/agent", response_model=AgentResponse)
async def agent_endpoint(payload: AgentRequest):
    try:
        if payload.stream:
            generator = stream_api_call(payload)
            return StreamingResponse(generator, media_type="text/plain")
        return await handle_api_call(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=500, content={"error": str(exc)})


# Run with:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
