from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Plivo credentials
    PLIVO_AUTH_ID: str
    PLIVO_AUTH_TOKEN: str
    PLIVO_FROM_NUMBER: str

    # AWS S3 credentials
    AWS_ACCESS_KEY_ID: str = "your_aws_access_key"
    AWS_SECRET_ACCESS_KEY: str = "your_aws_secret_key"
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "your-bucket-name"

    # Application settings
    APP_NAME: str = "PipeCat AI Voice Agent"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    BASE_URL: str 

    # API Keys
    OPENAI_API_KEY: str = "your_openai_api_key"
    DEEPGRAM_API_KEY: str = "your_deepgram_api_key"
    CARTESIA_API_KEY: str = "your_cartesia_api_key"
    
    # Twilio Settings
    TWILIO_ACCOUNT_SID: str = "your_twilio_account_sid"
    TWILIO_AUTH_TOKEN: str = "your_twilio_auth_token"
    
    # Other Settings
    NGROK_AUTH_TOKEN: str = "your_ngrok_auth_token"
    FIXA_KEY: str = "your_fixa_key"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()