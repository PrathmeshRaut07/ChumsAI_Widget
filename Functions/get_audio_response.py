import os
import io
import wave
import tempfile
import traceback

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

import google.generativeai as genai
from google.cloud import texttospeech
from dotenv import load_dotenv

# For WebM -> WAV conversion:
# pip install pydub
# Also ensure you have ffmpeg installed and on your PATH
from pydub import AudioSegment

load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "Google_API.json"

model = genai.GenerativeModel('gemini-2.0-flash')

TARGET_SAMPLE_RATE = 16000


def webm_to_wav_bytes(webm_data: bytes, target_sample_rate: int = 16000) -> bytes:
    """
    Convert a WebM (Opus) chunk to WAV (PCM) at the specified sample rate.
    Returns the WAV data as bytes.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_in:
            temp_in.write(webm_data)
            temp_in.flush()
            in_path = temp_in.name

        out_path = in_path + ".wav"

        # Use pydub to read the input (webm) and export to WAV
        audio = AudioSegment.from_file(in_path, format="webm")
        audio = audio.set_frame_rate(target_sample_rate).set_channels(1).set_sample_width(2)
        audio.export(out_path, format="wav")

        with open(out_path, "rb") as f_out:
            wav_bytes = f_out.read()
        
        # Clean up
        try:
            os.remove(in_path)
            os.remove(out_path)
        except:
            pass

        return wav_bytes

    except Exception as e:
        print("Error converting WebM to WAV:", e)
        # Return empty or pass through the original
        return b""


def response_to_audio(audio_data: bytes):
    """
    - Use Google's Generative AI to interpret audio (the new speech input interface).
    - If that fails, fall back to a default response.
    - Convert the text response to TTS (LINEAR16, 16kHz).
    """
    try:
        if not audio_data:
            raise ValueError("No audio data provided.")

        default_prompt = "You are a helpful AI assistant. Respond concisely."

        try:
            # Attempt to generate content from audio
            response = model.generate_content([
                default_prompt,
                {
                    "mime_type": "audio/webm",   # We label it as webm for the model
                    "data": audio_data
                }
            ])
            text_response = response.text
            print("AI recognized text:", text_response)
        except Exception as audio_process_error:
            print(f"Audio processing error: {audio_process_error}")
            text_response = "I'm sorry, I couldn't understand the audio. Please try again."

        # Text-to-speech conversion
        tts_client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text_response)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=TARGET_SAMPLE_RATE,
        )

        tts_response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        return tts_response.audio_content, text_response

    except Exception as e:
        print("Critical error in response_to_audio:", traceback.format_exc())
        return None, f"An error occurred: {str(e)}"

