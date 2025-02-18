from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")


client = genai.Client(api_key=api_key)

model_name = "gemini-2.0-flash"

def response_to_text(prompt):
  
    generation_config = {
        "max_output_tokens": 500,
    }
    
    response = client.models.generate_content(
        model=model_name,
        contents=[prompt],
        config=generation_config
    )

    return response.text
