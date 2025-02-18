import requests
import base64
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
load_dotenv()


api_key = os.getenv("SEGMIND")

def image_file_to_base64(image_path):
    with open(image_path, 'rb') as f:
        image_data = f.read()
    return base64.b64encode(image_data).decode('utf-8')

def image_url_to_base64(image_url):
    response = requests.get(image_url)
    image_data = response.content
    return base64.b64encode(image_data).decode('utf-8')

# Function to apply cloth on person
def apply_cloth_on_person(person_image_path, cloth_image_path):
    # Convert images to base64
    model_image_base64 = image_file_to_base64(person_image_path)  # Person image
    cloth_image_base64 = image_file_to_base64(cloth_image_path)  # Cloth image

    # API request payload
    url = "https://api.segmind.com/v1/try-on-diffusion"
    data = {
        "model_image": model_image_base64,
        "cloth_image": cloth_image_base64,
        "category": "Upper body",  # Assuming the category is upper body, you can change as needed
        "num_inference_steps": 35,
        "guidance_scale": 2,
        "seed": 12467,
        "base64": False
    }

    # API headers
    headers = {'x-api-key': api_key}

    # Make the API request
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        # Save and return the generated image
        image_data = response.content
        img = Image.open(BytesIO(image_data))
        
        # Return the image
        return img
    else:
        raise Exception(f"Error in API response: {response.status_code}, {response.text}")

