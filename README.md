# PipeCat Voice Agent

PipeCat Voice Agent is an AI-powered voice communication system that enables intelligent, real-time phone conversations. The system integrates various technologies to provide a seamless voice interaction experience:

## Core Features

- **Real-time Voice Processing**: Utilizes WebSocket connections for bidirectional audio streaming
- **Speech Recognition**: Integrates with Deepgram for accurate speech-to-text conversion
- **Natural Language Processing**: Leverages OpenAI's GPT-4 for intelligent conversation handling
- **Text-to-Speech**: Uses Cartesia for high-quality voice synthesis
- **Telephony Integration**: Built on Plivo's platform for reliable call handling
- **Call Recording**: Supports automatic call recording and storage
- **Voice Activity Detection**: Implements Silero VAD for precise speech detection

## Technical Stack

- **Backend**: FastAPI (Python)
- **Voice Processing**: PipeCat Pipeline System
- **External Services**:
  - Plivo (Telephony)
  - OpenAI GPT-4 (LLM)
  - Deepgram (STT)
  - Cartesia (TTS)
  - S3 (Recording Storage)

## Local Development with Plivo and ngrok

To enable Plivo to reach your local development server, follow these steps:

1. Install ngrok:

   ```zsh
   npm install -g ngrok
   # or
   brew install ngrok
   ```

2. Start your FastAPI server:

   ```zsh
   uvicorn app.main:app --reload
   ```

3. Start ngrok tunnel (in a new terminal):

   ```zsh
   ngrok http 8000
   ```

4. Copy the HTTPS URL provided by ngrok (e.g., https://your-tunnel.ngrok.io)

5. Update your environment variables:

   ```zsh
   export BASE_URL=your-ngrok-url
   ```

6. Configure Plivo:
   - Log into your Plivo dashboard
   - Update your application's Answer URL to: `{ngrok-url}/api/v1/calls/answer`
   - Update your application's Hangup URL to: `{ngrok-url}/api/v1/calls/hangup`

Now Plivo will be able to reach your local server through the secure ngrok tunnel for both HTTP callbacks and WebSocket connections.

## Important Notes

- The ngrok URL changes each time you restart ngrok (unless you have a paid plan)
- Make sure to update your BASE_URL environment variable with the new ngrok URL each time
- For production, replace the ngrok URL with your actual domain name

## Testing

To test the integration:

1. Make sure your server is running and ngrok is active
2. Try making an outbound call using the API endpoint:
   ```zsh
   curl -X POST "http://localhost:8000/api/v1/calls/outbound/{phone-number}"
   ```
3. The call should connect and establish a WebSocket connection for real-time voice processing
