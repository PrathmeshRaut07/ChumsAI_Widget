from google.cloud import speech_v1
from google.cloud import texttospeech
import os
import wave
from Functions.get_text_response import response_to_text
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "GOOGLE_API.json"
model = genai.GenerativeModel('models/gemini-2.0-flash')
def response_to_audio_as_text(audio_data):
    """
    Process audio data through speech-to-text, get a response, and convert back to audio
    
    Parameters:
    audio_data (bytes): Raw audio data in WAV format
    
    Returns:
    bytes: Generated audio response in WAV format
    """
    
    prompt="you are helpful assistant and reply in maximum 20 words not more that"
    response = model.generate_content([
                prompt,
                {
                    "mime_type": "audio/mp3",
                    "data": audio_data
                }
            ])
    text_response=response.text
    
    
    return text_response
