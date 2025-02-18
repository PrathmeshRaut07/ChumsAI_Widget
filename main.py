from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routes.functions import router as Function
import uvicorn

app = FastAPI(
    title="Text and Audio Processing API",
    description="API for processing text and audio inputs",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(Function, prefix="/Response")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  
    )