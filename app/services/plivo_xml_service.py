from plivo import plivoxml
from typing import Optional, List
from app.config import settings

class PlivoXMLService:
    @staticmethod
    def generate_answer_xml(message: str = "Hello from PipeCat!", 
                          record: bool = True,
                          callback_url: Optional[str] = None) -> str:
        """Generate XML for answering a call with WebSocket connection"""
        response = plivoxml.ResponseElement()
        response.add(plivoxml.SpeakElement(message))
        
        # Add WebSocket connection
        base_url = settings.BASE_URL.replace("https://", "")
        response.add(plivoxml.WebSocketElement(
            url=f"wss://{base_url}/ws/voice",
            action=f"{settings.BASE_URL}/api/v1/calls/websocket/status",
            method="POST"
        ))
        
        if record:
            record_params = {
                'action': callback_url,
                'method': 'POST',
                'maxLength': 3600,  # 1 hour max
                'transcriptionType': 'auto',
                'fileFormat': 'mp3'
            }
            response.add(plivoxml.RecordElement(**record_params))
        
        return response.to_string()
    
    @staticmethod
    def generate_hangup_xml(message: Optional[str] = None) -> str:
        """Generate XML for hanging up a call"""
        response = plivoxml.ResponseElement()
        if message:
            response.add(plivoxml.SpeakElement(message))
        response.add(plivoxml.HangupElement())
        return response.to_string()
    
    @staticmethod
    def generate_conference_xml(room_name: str, 
                              participants: List[str],
                              message: str = "Joining conference") -> str:
        """Generate XML for conference calls"""
        response = plivoxml.ResponseElement()
        response.add(plivoxml.SpeakElement(message))
        
        conference_params = {
            'enterSound': 'beep:1',
            'exitSound': 'beep:2',
            'startConferenceOnEnter': True,
            'endConferenceOnExit': False,
            'record': True
        }
        
        response.add(plivoxml.ConferenceElement(
            room_name,
            **conference_params
        ))
        
        return response.to_string()