from fastapi import FastAPI, WebSocket
from loguru import logger
from dotenv import load_dotenv
import os
import json  # Add this import

# Load environment variables at startup
load_dotenv()

from app.config import settings
from app.api.routes import router as api_router
from app.api.websocket import handle_voice_websocket
from app.pbot import run_bot

app = FastAPI(
    title="PipeCat AI Voice Agent",
    description="AI Voice Agent for handling calls using Plivo and S3",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up PipeCat AI Voice Agent")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down PipeCat AI Voice Agent")

@app.websocket("/ws/voice/{call_uuid}")
async def voice_websocket_endpoint(websocket: WebSocket, call_uuid: str):
    try:
        logger.info(f"New WebSocket connection for call UUID:............. {call_uuid}")
        await websocket.accept()
        start_data = websocket.iter_text()
        await start_data.__anext__()
        call_data = json.loads(await start_data.__anext__())
        print(call_data, flush=True)
        stream_sid = call_data["streamId"]
        print("WebSocket connection accepted")
        await run_bot(websocket, stream_sid)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Ensure proper cleanup
        try:
            await websocket.close()
        except:
            pass

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("⚡️ Debugger is listening on port 5678")
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)