from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from typing import Any
from Functions.get_audio_response import response_to_audio,webm_to_wav_bytes
from Functions.get_text_response import response_to_text
from Functions.get_video_response import generate_video,transcribe_audio
from Functions.try_it_on import apply_cloth_on_person
from Functions.get_response_to_audio_as_text import response_to_audio_as_text
import tempfile
import os
import wave
import audioop
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from io import BytesIO

router = APIRouter()
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

manager = ConnectionManager()



TARGET_SAMPLE_RATE = 16000

class TextRequest(BaseModel):
    prompt: str
def convert_wav_sample_rate(audio_data: bytes, target_sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:

    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_in:
        temp_in.write(audio_data)
        temp_in_path = temp_in.name

    try:
        with wave.open(temp_in_path, 'rb') as wav_in:
            n_channels = wav_in.getnchannels()
            sampwidth = wav_in.getsampwidth()
            orig_sample_rate = wav_in.getframerate()
            
            if orig_sample_rate != target_sample_rate:
                frames = wav_in.readframes(wav_in.getnframes())
                
            
                converted, _ = audioop.ratecv(frames, sampwidth, n_channels, 
                                            orig_sample_rate, target_sample_rate, None)
                
            
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_out:
                    with wave.open(temp_out.name, 'wb') as wav_out:
                        wav_out.setnchannels(n_channels)
                        wav_out.setsampwidth(sampwidth)
                        wav_out.setframerate(target_sample_rate)
                        wav_out.writeframes(converted)
                    
                    with open(temp_out.name, 'rb') as f:
                        converted_audio = f.read()
                    os.unlink(temp_out.name)
                    
                return converted_audio
            else:
                return audio_data
                
    finally:
        os.unlink(temp_in_path)


@router.post("/text", response_model=dict)
async def process_text(request: TextRequest):
    """
    Process text input and return text response
    """
    try:
        response = response_to_text(request.prompt)
        if response is None:
            raise HTTPException(status_code=500, detail="Failed to generate text response")
        
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/audio")
async def process_audio(audio_file: UploadFile = File(...)):
    """
    Process audio input and return audio response as a WAV file
    """
    try:
        if not audio_file.filename.endswith('.wav'):
            raise HTTPException(status_code=400, detail="Only WAV files are supported")

        audio_data = await audio_file.read()
        
        try:
            with wave.open(tempfile.SpooledTemporaryFile(), 'wb') as wav_check:
                wav_check.setnchannels(1)
                wav_check.setsampwidth(2)
                wav_check.setframerate(TARGET_SAMPLE_RATE)
                wav_check.writeframes(audio_data)
        except:

            audio_data = convert_wav_sample_rate(audio_data)
        
        audio_response,text_response = response_to_audio(audio_data)
        if audio_response is None:
            raise HTTPException(status_code=500, detail="Failed to generate audio response")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file.write(audio_response)
            temp_path = temp_file.name
    
        bg_tasks = BackgroundTasks()
        bg_tasks.add_task(os.unlink, temp_path)
        #encode dtext
        encoded_text = base64.b64encode(text_response.encode('utf-8')).decode('ascii')

        headers = {
            'X-Text-Response': encoded_text,  
            'Content-Disposition': 'attachment; filename=response.wav'
        }
        
        return FileResponse(
            path=temp_path,
            media_type='audio/wav',
            filename='response.wav',
            background=bg_tasks,
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# @router.websocket("/ws/audio")
# async def audio_ws_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     print("WebSocket connection established")

#     try:
#         while True:
#             try:
#                 # Receive the binary audio data
#                 audio_chunk = await websocket.receive_bytes()
#                 print(f"Received audio chunk of size: {len(audio_chunk)} bytes")

#                 if not audio_chunk:
#                     print("Empty chunk received, continuing...")
#                     continue

#                 # Convert WebM to WAV
#                 try:
#                     wav_bytes = webm_to_wav_bytes(audio_chunk)
#                     print(f"Converted to WAV, size: {len(wav_bytes)} bytes")
#                 except Exception as e:
#                     print(f"Error converting audio: {e}")
#                     continue

#                 if not wav_bytes:
#                     print("No WAV data after conversion")
#                     continue

#                 # Process audio and get response
#                 try:
#                     audio_response, text_response = response_to_audio(wav_bytes)
#                     print(f"Generated response: {text_response}")
                    
#                     if audio_response:
#                         await websocket.send_bytes(audio_response)
#                         print(f"Sent response audio of size: {len(audio_response)} bytes")
#                     else:
#                         print("No audio response generated")
#                 except Exception as e:
#                     print(f"Error processing audio: {e}")
#                     continue

#             except Exception as e:
#                 print(f"Error in websocket loop: {e}")
#                 continue

#     except WebSocketDisconnect:
#         print("Client disconnected")
#     except Exception as e:
#         print(f"Unhandled WebSocket error: {e}")
#     finally:
#         print("WebSocket connection closed")


@router.websocket("/ws/audio")
async def audio_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established")

    try:
        while True:
            try:
                # Receive the binary audio data
                audio_chunk = await websocket.receive_bytes()
                print(f"Received audio chunk of size: {len(audio_chunk)} bytes")
            except WebSocketDisconnect:
                print("Client disconnected during receive")
                break  # Break out of the loop on disconnect
            except Exception as e:
                print(f"Error receiving audio chunk: {e}")
                continue

            if not audio_chunk:
                print("Empty chunk received, continuing...")
                continue

            # Convert WebM to WAV
            try:
                wav_bytes = webm_to_wav_bytes(audio_chunk)
                print(f"Converted to WAV, size: {len(wav_bytes)} bytes")
            except Exception as e:
                print(f"Error converting audio: {e}")
                continue

            if not wav_bytes:
                print("No WAV data after conversion")
                continue

            # Process audio and get response
            try:
                audio_response, text_response = response_to_audio(wav_bytes)
                print(f"Generated response: {text_response}")

                if audio_response:
                    await websocket.send_bytes(audio_response)
                    print(f"Sent response audio of size: {len(audio_response)} bytes")
                else:
                    print("No audio response generated")
            except Exception as e:
                print(f"Error processing audio: {e}")
                continue

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unhandled WebSocket error: {e}")
    finally:
        print("WebSocket connection closed")




@router.post("/video")
async def process_audio(audio_file: UploadFile = File(...)):
    """
    Process audio input and return audio response as a WAV file
    """
    try:
        if not audio_file.filename.endswith('.wav'):
            raise HTTPException(status_code=400, detail="Only WAV files are supported")

        audio_data = await audio_file.read()
        try:
            with wave.open(tempfile.SpooledTemporaryFile(), 'wb') as wav_check:
                wav_check.setnchannels(1)
                wav_check.setsampwidth(2)
                wav_check.setframerate(TARGET_SAMPLE_RATE)
                wav_check.writeframes(audio_data)
        except:

            audio_data = convert_wav_sample_rate(audio_data)
        
        text_response =response_to_audio_as_text(audio_data)
    
        video_url=generate_video(text_response)
        
        return  {"video_url":video_url,"text_response":text_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/video")
# async def process_audio(audio_file: UploadFile = File(...)):
#     """
#     FastAPI route that accepts a WAV file, transcribes the audio, and generates a video.
#     """
#     # Check that the file is a WAV file
#     if not audio_file.filename.endswith(".wav"):
#         raise HTTPException(status_code=400, detail="Only WAV files are supported.")

#     # Save the uploaded file to a temporary file
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
#         tmp.write(await audio_file.read())
#         temp_file_path = tmp.name

#     # Transcribe the audio
#     transcription = transcribe_audio(temp_file_path)
#     if transcription is None:
#         os.remove(temp_file_path)
#         raise HTTPException(status_code=500, detail="Audio transcription failed.")

#     # Generate the video using the transcribed text
#     transcription=response_to_text(transcription+"respond max to max in words not more than that")
#     video_url = generate_video(transcription)
#     os.remove(temp_file_path)  

#     if video_url is None:
#         raise HTTPException(status_code=500, detail="Video generation failed.")

#     return {"video_url": video_url,"text":transcription}

@router.post("/image_generate", response_model=dict)
async def generate_image(
    person_image: UploadFile = File(...),
    cloth_image: UploadFile = File(...)
):
    """
    FastAPI endpoint that:
      - Accepts two uploaded files.
      - Saves them temporarily.
      - Calls apply_cloth_on_person to generate a new image.
      - Returns a JSON object containing the generated image as a base64 string.
    """
    try:
        # Read the uploaded files into bytes.
        person_bytes = await person_image.read()
        cloth_bytes = await cloth_image.read()

        # Write the bytes to temporary files (so we can pass file paths).
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as person_tmp:
            person_tmp.write(person_bytes)
            person_tmp_path = person_tmp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as cloth_tmp:
            cloth_tmp.write(cloth_bytes)
            cloth_tmp_path = cloth_tmp.name

        # Generate the new image using the provided function.
        generated_img = apply_cloth_on_person(
            person_image_path=person_tmp_path, 
            cloth_image_path=cloth_tmp_path
        )

        # Convert the PIL Image to bytes.
        buffer = BytesIO()
        generated_img.save(buffer, format="PNG")
        buffer.seek(0)

        # Encode the image bytes to a base64 string.
        img_str = base64.b64encode(buffer.read()).decode("utf-8")

        return {"image": img_str}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))