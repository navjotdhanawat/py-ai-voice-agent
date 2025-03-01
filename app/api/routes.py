from fastapi import APIRouter, HTTPException, Response, Request
from app.services.call_service import CallService
from app.services.plivo_xml_service import PlivoXMLService
from app.models.call_models import CallState, CallRecord
from app.api.websocket import voice_manager
from app.config import settings
import plivo
import os
from loguru import logger

router = APIRouter()
call_service = CallService()
xml_service = PlivoXMLService()
plivo_client = plivo.RestClient(
    os.getenv("PLIVO_AUTH_ID"), os.getenv("PLIVO_AUTH_TOKEN")
)

RINGBACK_TONE_URL = (
    "https://ontune.s3.ap-south-1.amazonaws.com/ringbacktone-original.mp3"
)


def get_stream_xml(call_id):
    """
    Returns the XML for the websocket stream with recording enabled.
    """

    base_url = settings.BASE_URL.replace("https://", "")
    recordCallback = f"https://{base_url}/api/v1/calls/recording/{call_id}"
    ws_url = f"wss://{base_url}/ws/voice/{call_id}"

    response = plivo.plivoxml.ResponseElement()
    response.add(
        plivo.plivoxml.RecordElement(
            record_session=True,
            callback_url=recordCallback,
            redirect=False,
            max_length=3600,  # Maximum recording duration in seconds
            callback_method="POST",  # Explicitly set POST method
        )
    )

    response.add(
        plivo.plivoxml.StreamElement(
            content=ws_url,
            streamTimeout=True,
            keepCallAlive=True,
            bidirectional=True,
            contentType="audio/x-mulaw;rate=8000",
        )
    )
    return response.to_string()


@router.post("/calls/outbound/{to_number}", response_model=CallRecord)
async def make_outbound_call(to_number: str):
    try:
        return await call_service.make_outbound_call(to_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calls/answer/{call_id}")
async def handle_answer_webhook(call_id: str, request: Request):
    """Handle Plivo's answer callback and return XML with WebSocket instructions."""
    try:
        data = await request.form()
        logger.info(f"Call status for {call_id}: {data.get('CallStatus')}")
        # TODO: update call webhook
        xml_content = get_stream_xml(call_id)
        return Response(content=xml_content, media_type="text/xml", status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calls/status/{call_id}")
async def handle_call_status(call_id: str, request: Request):
    """Handle Plivo's status callback."""
    try:
        data = await request.form()
        logger.info(f"Call status update for {call_id}: {data.get('CallStatus')}")
        return Response(content="", media_type="text/xml", status_code=200)
    except Exception as e:
        logger.error(f"Error handling call status for {call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calls/hangup/{call_id}")
async def handle_hangup_webhook(call_id: str, request: Request):
    try:
        data = await request.form()
        logger.info(f"Call status for {call_id}: {data.get('CallStatus')}")
        # TODO: FAILED, COMPLETED, REJECTED, USERBUSY status

        return Response(content="", media_type="application/xml")
    except Exception as e:
        logger.error(f"Error handling call hangup for {call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calls/recording/{call_uuid}")
async def store_call_recording(call_uuid: str, request: Request):
    try:
        data = await request.form()
        recording_url = data.get("RecordUrl")
        voice_manager.update_recording_url(call_uuid, recording_url)
        logger.info(f"Recording...... {data}")
        if recording_url:
            logger.info("recording_url::::", recording_url)
            await call_service.store_recording(call_uuid, recording_url)
        return Response(content="")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
