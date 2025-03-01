import plivo
import boto3
import uuid
from loguru import logger
from datetime import datetime
from app.config import settings
from app.models.call_models import CallRecord, CallState
import requests


class CallService:
    def __init__(self):
        self.plivo_client = plivo.RestClient(
            settings.PLIVO_AUTH_ID, settings.PLIVO_AUTH_TOKEN
        )
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

    async def make_outbound_call(self, to_number: str) -> CallRecord:
        try:
            call_uuid = str(uuid.uuid4())
            # Make actual Plivo outbound call
            response = self.plivo_client.calls.create(
                ring_url="https://ontune.s3.ap-south-1.amazonaws.com/ringbacktone-original.mp3",
                from_=settings.PLIVO_FROM_NUMBER,
                to_=to_number,
                answer_url=f"{settings.BASE_URL}/api/v1/calls/answer/{call_uuid}",
                answer_method="POST",
                hangup_url=f"{settings.BASE_URL}/api/v1/calls/hangup/{call_uuid}",
                hangup_method="POST",
            )

            # Create and return proper CallRecord object instead of dict
            call_record = CallRecord(
                call_uuid=call_uuid,
                from_number=settings.PLIVO_FROM_NUMBER,
                to_number=to_number,
                direction="outbound",
                state=CallState.INITIATED,
                start_time=datetime.now(),
            )

            logger.info(f"Initiated outbound call to {to_number}")
            return call_record
        except Exception as e:
            # TODO: update call failed status
            logger.error(f"Failed to make outbound call: {str(e)}")
            raise

    async def handle_inbound_call(self, from_number: str) -> CallRecord:
        try:
            # Handle real inbound call
            call_uuid = self.plivo_client.calls.get_live()[0].call_uuid
            call_record = CallRecord(
                call_uuid=call_uuid,
                from_number=from_number,
                to_number=settings.PLIVO_FROM_NUMBER,
                direction="inbound",
                state=CallState.IN_PROGRESS,
                start_time=datetime.now(),
            )
            logger.info(f"Handling inbound call from {from_number}")
            return call_record
        except Exception as e:
            logger.error(f"Failed to handle inbound call: {str(e)}")
            raise

    async def store_recording(self, call_uuid: str, recording_url: str) -> str:
        try:
            # Download recording from Plivo URL
            response = requests.get(recording_url)
            response.raise_for_status()

            # Store in S3
            s3_path = f"recordings/{call_uuid}.mp3"
            self.s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_path,
                Body=response.content,
                ContentType="audio/mpeg",
            )
            logger.info(f"Stored recording for call {call_uuid} at {s3_path}")
            return s3_path
        except Exception as e:
            logger.error(f"Failed to store recording: {str(e)}")
            raise

    async def update_call_state(
        self, call_record: CallRecord, new_state: CallState
    ) -> CallRecord:
        try:
            call_record.state = new_state
            if new_state == CallState.COMPLETED:
                call_record.end_time = datetime.now()
                if call_record.start_time:
                    call_record.duration = int(
                        (call_record.end_time - call_record.start_time).total_seconds()
                    )
            logger.info(f"Updated call {call_record.call_uuid} state to {new_state}")
            return call_record
        except Exception as e:
            logger.error(f"Failed to update call state: {str(e)}")
            raise
