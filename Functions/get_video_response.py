import time
import requests
import os
from dotenv import load_dotenv
import speech_recognition as sr

# Load environment variables (e.g., DID_API_KEY)
load_dotenv()
api_key = os.getenv("DID_API_KEY")

def transcribe_audio(audio_file_path):
    """
    Transcribes a WAV audio file to text using the SpeechRecognition library.
    
    Parameters:
        audio_file_path (str): Path to the WAV file.
        
    Returns:
        str or None: The transcribed text if successful, otherwise None.
    """
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio = recognizer.record(source)
    try:
        # Using Google's free API for demonstration
        text = recognizer.recognize_google(audio)
        return text
    except Exception as e:
        print("Error during transcription:", str(e))
        return None

def generate_video(text, voice_id="Sara"):
    """
    Generates a talking head video from text using the D-ID API and returns the video URL.
    
    Parameters:
        text (str): The text to be spoken in the video.
        voice_id (str): The voice to be used (default: "Sara").
    
    Returns:
        str or None: The URL of the generated video if successful, otherwise None.
    """
    # Step 1: Create the video request
    url = "https://api.d-id.com/talks"
    payload = {
        "source_url": "https://d-id-public-bucket.s3.us-west-2.amazonaws.com/alice.jpg",  # Default avatar
        "script": {
            "type": "text",
            "subtitles": "false",
            "provider": {
                "type": "microsoft",
                "voice_id": voice_id
            },
            "input": text
        },
        "config": {
            "fluent": "false",
            "pad_audio": "0.0"
        }
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Basic " + api_key
    }
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    if "id" not in data:
        print("Error creating video:", data)
        return None

    talk_id = data["id"]
    print("Video generation started. ID:", talk_id)

    # Step 2: Poll for the video status using the talk_id in the status URL
    video_url = None
    status_url = f"https://api.d-id.com/talks/{talk_id}"

    while True:
        response = requests.get(status_url, headers=headers)
        status_data = response.json()

        if status_data.get("status") == "done":
            video_url = status_data["result_url"]
            break
        elif status_data.get("status") == "failed":
            print("Video generation failed.")
            return None
        else:
            print("Processing... Waiting for the video to be ready.")
            time.sleep(2)

    print("Video Ready:", video_url)
    return video_url

def main():
    # Path to your audio file (WAV format)
    audio_file = "path/to/your/audio.wav"
    
    print("Transcribing audio...")
    transcription = transcribe_audio(audio_file)
    
    if transcription:
        print("Transcription:", transcription)
        video_url = generate_video(transcription)
        if video_url:
            print("Generated Video URL:", video_url)
        else:
            print("Video generation failed.")
    else:
        print("Failed to transcribe audio.")

if __name__ == "__main__":
    main()
