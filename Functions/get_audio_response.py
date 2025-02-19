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
def response_to_audio(audio_data):
    """
    Process audio data through speech-to-text, get a response, and convert back to audio
    
    Parameters:
    audio_data (bytes): Raw audio data in WAV format
    
    Returns:
    bytes: Generated audio response in WAV format
    """
    # speech_client = speech_v1.SpeechClient()
    
    # config = speech_v1.RecognitionConfig(
    #     encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
    #     sample_rate_hertz=44100,
    #     language_code="en-US",
    # )

    # audio = speech_v1.RecognitionAudio(content=audio_data)

    # response = speech_client.recognize(config=config, audio=audio)
    
    # if not response.results:
    #     return None
    
    # transcribed_text = response.results[0].alternatives[0].transcript
    prompt="you are a helful assitant"
    response = model.generate_content([
                prompt,
                {
                    "mime_type": "audio/mp3",
                    "data": audio_data
                }
            ])
    

    tts_client = texttospeech.TextToSpeechClient()
    
    print(response.text)
    synthesis_input = texttospeech.SynthesisInput(text=response.text)
    
 
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
    )
    

    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    return response.audio_content
