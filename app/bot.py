import os
from typing import List
import asyncio

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
import plivo
from plivo.resources.calls import Call

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, EndTaskFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from loguru import logger
import sys

from app.models.call_models import CallState
from app.services.plivo_xml_service import PlivoXMLService

logger.remove(0)
logger.add(sys.stderr, format="{time} {level} {message}", level="DEBUG")

class VoiceBot:
    def __init__(self, websocket_client, stream_sid, call_sid):
        self.websocket_client = websocket_client
        self.stream_sid = stream_sid
        self.call_sid = call_sid
        self.plivo_client = plivo.RestClient(
            os.getenv("PLIVO_AUTH_ID"), os.getenv("PLIVO_AUTH_TOKEN"))
        self.xml_service = PlivoXMLService()
        self.task = None
        self.transport = None

    async def end_call(self, function_name, tool_call_id, args, llm, context, result_callback):
        logger.info(f"Ending call {self.call_sid}")
        xml_response = self.xml_service.generate_hangup_xml(
            message="Thank you for using our service. Goodbye!")
        self.plivo_client.calls.update(self.call_sid, xml=xml_response)
        await llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)

    async def on_client_connected(self, transport, client):
        assert self.task is not None
        logger.info(f"Client connected for call {self.call_sid}")

    async def on_client_disconnected(self, transport, client):
        assert self.task is not None
        logger.info(f"Client disconnected for call {self.call_sid}")
        await self.task.queue_frames([EndFrame()])

    async def run(self, system_prompt: str, voice_id: str):
        self.transport = FastAPIWebsocketTransport(
            websocket=self.websocket_client,
            params=FastAPIWebsocketParams(
                audio_out_enabled=True,
                add_wav_header=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
                serializer=None,  # We'll handle serialization in the transport layer
            ),
        )

        llm = OpenAILLMService(api_key=os.getenv(
            "OPENAI_API_KEY") or "", model="gpt-4")
        llm.register_function("end_call", self.end_call)

        tools = [
            ChatCompletionToolParam(
                type="function",
                function={
                    "name": "end_call",
                    "description": "ends the call",
                },
            )
        ]

        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY") or "")
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY") or "",
            voice_id=voice_id,
        )

        self.messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "system",
                "content": "end the call if the user says goodbye or indicates they want to end the conversation",
            },
        ]

        context = OpenAILLMContext(self.messages, tools)
        self.context_aggregator = llm.create_context_aggregator(context)

        pipeline = Pipeline(
            [
                self.transport.input(),
                stt,
                self.context_aggregator.user(),
                llm,
                tts,
                self.transport.output(),
                self.context_aggregator.assistant(),
            ]
        )

        self.task = PipelineTask(
            pipeline, params=PipelineParams(allow_interruptions=True))

        self.transport.event_handler(
            "on_client_connected")(self.on_client_connected)
        self.transport.event_handler("on_client_disconnected")(
            self.on_client_disconnected)

        runner = PipelineRunner(handle_sigint=False)
        await runner.run(self.task)

        return self.messages

async def run_voice_bot(system_prompt: str, voice_id: str, websocket_client, stream_sid, call_sid):
    bot = VoiceBot(websocket_client, stream_sid, call_sid)
    try:
        transcript = await bot.run(system_prompt, voice_id)
        return transcript
    except asyncio.CancelledError:
        logger.warning(f"Bot run cancelled for call {call_sid}")
        return None
    except Exception as e:
        logger.error(f"Error running bot for call {call_sid}: {str(e)}")
        raise