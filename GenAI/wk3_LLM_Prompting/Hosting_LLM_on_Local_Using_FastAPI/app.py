from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI(title="Self-Hosted LLM API")

# This is a sentence-completion model, not a Q&A model
generator = pipeline("text-generation", model="distilgpt2")

class Query(BaseModel):
    prompt: str
    max_length: int = 100

@app.post("/generate")
def generate_text(data: Query):
    output = generator(data.prompt, max_length=data.max_length, num_return_sequences=1)
    return {"response": output[0]['generated_text']}

