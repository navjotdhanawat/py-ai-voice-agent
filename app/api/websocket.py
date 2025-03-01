from fastapi import WebSocket
from loguru import logger
from typing import Dict, List, Optional, TypedDict
from typing_extensions import Literal
from openai.types.chat import ChatCompletionMessageParam
from app.bot import run_bot


class CallStatus(TypedDict):
    status: Literal["in_progress", "completed", "error"]
    transcript: Optional[List[ChatCompletionMessageParam]]
    stereo_recording_url: Optional[str]
    error: Optional[str]


class VoiceWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.call_status: Dict[str, CallStatus] = {}
        self.voice_bots: Dict[str, bool] = {}

    async def connect(self, websocket: WebSocket, call_uuid: str):
        await websocket.accept()
        self.active_connections[call_uuid] = websocket
        self.call_status[call_uuid] = {
            "status": "INPROGRESS",
            "transcript": None,
            "stereo_recording_url": None,
            "error": None,
        }
        self.voice_bots[call_uuid] = False
        logger.info(f"WebSocket connection established for call {call_uuid}")

    def disconnect(self, call_uuid: str):
        if call_uuid in self.active_connections:
            del self.active_connections[call_uuid]
            if call_uuid in self.call_status:
                del self.call_status[call_uuid]
            if call_uuid in self.voice_bots:
                del self.voice_bots[call_uuid]
            logger.info(f"WebSocket connection closed for call {call_uuid}")

    async def receive_audio(self, call_uuid: str, audio_data: bytes):
        """Handle incoming audio data from Plivo"""
        if call_uuid in self.active_connections:
            try:
                if not self.voice_bots.get(call_uuid):
                    # Initialize the voice bot for this call
                    self.voice_bots[call_uuid] = True
                    system_prompt = "You are an AI assistant helping with a phone call. Be concise and helpful."
                    voice_id = (
                        "79a125e8-cd45-4c13-8a67-188112f4dd22"  # Default voice ID
                    )

                    # Start the voice bot in the background
                    transcript = await run_bot(
                        system_prompt,
                        voice_id,
                        self.active_connections[call_uuid],
                        "stream_sid",  # This is a placeholder, you might want to store the actual stream_sid
                        call_uuid,
                    )
                    logger.info(f"transcript........{transcript}")
                    if transcript:
                        self.call_status[call_uuid]["transcript"] = transcript
                        self.call_status[call_uuid]["status"] = "completed"

            except Exception as e:
                logger.error(f"Error processing audio for call {call_uuid}: {str(e)}")
                self.call_status[call_uuid] = {
                    "status": "error",
                    "transcript": None,
                    "stereo_recording_url": None,
                    "error": str(e),
                }

    def update_recording_url(self, call_uuid: str, recording_url: str):
        """Update the recording URL for a call"""
        if call_uuid in self.call_status:
            self.call_status[call_uuid]["stereo_recording_url"] = recording_url

    def get_call_status(self, call_uuid: str) -> Optional[CallStatus]:
        """Get the status of a call"""
        return self.call_status.get(call_uuid)


voice_manager = VoiceWebSocketManager()


async def handle_voice_websocket(websocket: WebSocket, call_uuid: str):
    await voice_manager.connect(websocket, call_uuid)
    try:
        while True:
            data = await websocket.receive_bytes()
            await voice_manager.receive_audio(call_uuid, data)
    except Exception as e:
        logger.error(f"WebSocket error for call {call_uuid}: {str(e)}")
    finally:
        voice_manager.disconnect(call_uuid)
