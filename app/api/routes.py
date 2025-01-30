from fastapi import APIRouter, HTTPException, Response
from app.services.call_service import CallService
from app.services.plivo_xml_service import PlivoXMLService
from app.models.call_models import CallState, CallRecord
from app.api.websocket import voice_manager
from typing import List
from app.config import settings
import plivo
import os

router = APIRouter()
call_service = CallService()
xml_service = PlivoXMLService()
plivo_client = plivo.RestClient(os.getenv("PLIVO_AUTH_ID"), os.getenv("PLIVO_AUTH_TOKEN"))


def get_stream_xml():
    """
    Returns the XML for the websocket stream with recording enabled.
    """
    ws_url = settings.BASE_URL.replace('https://', '')
    return f"<Response><Record recordSession=\"true\" maxLength=\"3600\" callbackUrl=\"https://{ws_url}/api/v1/calls/recording\" callbackMethod=\"POST\" /><Stream streamTimeout=\"3600\" keepCallAlive=\"true\" bidirectional=\"true\" contentType=\"audio/x-mulaw;rate=8000\">wss://{ws_url}/ws/voice/call_uuid</Stream></Response>"


@router.post("/calls/outbound/{to_number}", response_model=CallRecord)
async def make_outbound_call(to_number: str):
    try:
        
        response = plivo_client.calls.create(
            to_=to_number,
            from_=settings.PLIVO_FROM_NUMBER,
            answer_url=f"{settings.BASE_URL}/api/v1/calls/answer",
            answer_method="POST",
            callback_url=f"{settings.BASE_URL}/api/v1/calls/recording",
            callback_method="POST"
        )
        return await call_service.make_outbound_call(to_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calls/answer")
async def handle_answer_webhook():
    """Handle Plivo's answer callback and return XML with WebSocket instructions."""
    try:
        xml_content = get_stream_xml()
        return Response(content=xml_content, media_type="text/xml", status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calls/hangup")
async def handle_hangup_webhook():
    try:
        xml_response = xml_service.generate_hangup_xml(
            message="Thank you for using PipeCat. Goodbye!"
        )
        return Response(content=xml_response, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calls/{call_uuid}/recording", response_model=CallRecord)
async def store_call_recording(call_uuid: str, recording_url: str):
    try:
        # Format the recording URL with authentication credentials
        auth_id = os.getenv("PLIVO_AUTH_ID")
        auth_token = os.getenv("PLIVO_AUTH_TOKEN")
        base_url = recording_url.replace("https://", "")
        authenticated_url = f"https://{auth_id}:{auth_token}@{base_url}"
        
        # Update the recording URL in voice manager
        voice_manager.update_recording_url(call_uuid, authenticated_url)
        
        s3_path = await call_service.store_recording(call_uuid, authenticated_url)
        call_record = CallRecord(
            call_uuid=call_uuid,
            from_number=settings.PLIVO_FROM_NUMBER,
            to_number="mock_number",
            direction="outbound",
            state=CallState.COMPLETED,
            recording_url=authenticated_url,
            s3_recording_path=s3_path
        )
        return call_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calls/{call_uuid}/status")
async def get_call_status(call_uuid: str):
    try:
        status = voice_manager.get_call_status(call_uuid)
        if not status:
            raise HTTPException(status_code=404, detail="Call not found")
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/calls/{call_uuid}/state", response_model=CallRecord)
async def update_call_state(call_uuid: str, new_state: CallState):
    try:
        # In real implementation, fetch call_record from database
        call_record = CallRecord(
            call_uuid=call_uuid,
            from_number="mock_number",
            to_number="mock_number",
            direction="outbound",
            state=CallState.INITIATED
        )
        return await call_service.update_call_state(call_record, new_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))