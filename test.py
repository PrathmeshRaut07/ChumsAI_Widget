from fastapi import FastAPI, WebSocket
from google.cloud import speech_v1 as speech
from google.cloud import texttospeech as tts
import google.generativeai as genai
import asyncio
import os
import uvicorn

app = FastAPI()
from dotenv import load_dotenv
load_dotenv()
# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# Configure Google Cloud clients
speech_client = speech.SpeechClient()
tts_client = tts.TextToSpeechClient()

async def handle_audio(websocket: WebSocket):
    await websocket.accept()
    try:
        # Configure streaming speech recognition
        config = speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=16000,
                language_code="en-US",
                enable_automatic_punctuation=True,
            ),
            interim_results=True
        )

        # Start bidirectional streaming
        stream = await asyncio.to_thread(
            lambda: speech_client.streaming_recognize(config)
        )

        async def receive_audio():
            while True:
                data = await websocket.receive_bytes()
                request = speech.StreamingRecognizeRequest(audio_content=data)
                await asyncio.to_thread(stream.send, request)

        async def process_transcript():
            async for response in stream:
                for result in response.results:
                    if result.is_final:
                        text = result.alternatives[0].transcript
                        ai_response = await generate_ai_response(text)
                        audio_data = await text_to_speech(ai_response)
                        await websocket.send_bytes(audio_data)

        await asyncio.gather(receive_audio(), process_transcript())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()

async def generate_ai_response(text: str):
    response = await model.generate_content_async(text)
    return response.text

async def text_to_speech(text: str):
    synthesis_input = tts.SynthesisInput(text=text)
    voice = tts.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-J"
    )
    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding.OGG_OPUS
    )
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    return response.audio_content

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_audio(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "test:app",
        host="0.0.0.0",
        port=8000,
        reload=True  
    )    