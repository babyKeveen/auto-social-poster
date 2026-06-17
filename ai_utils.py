import os
import base64
from openai import OpenAI
import google.generativeai as genai
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from PIL import Image
import io

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_alt_text_openai(image_path, api_key):
    client = OpenAI(api_key=api_key)
    base64_image = encode_image(image_path)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Generate a concise and descriptive alt-text for this image, suitable for visually impaired users. Do not include 'Image of' or similar introductory phrases."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content

def generate_alt_text_gemini(image_path, api_key):
    genai.configure(api_key=api_key)
    
    # Load image using PIL
    img = Image.open(image_path)
    
    model = genai.GenerativeModel('gemini-2.5-pro')
    response = model.generate_content(
        ["Generate a concise and descriptive alt-text for this image, suitable for visually impaired users. Do not include 'Image of' or similar introductory phrases.", img]
    )
    return response.text

def generate_alt_text_moondream(image_path):
    model_id = "vikhyatk/moondream2"
    revision = "2024-08-26"
    
    print(f"Loading local model {model_id}...")
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            trust_remote_code=True, 
            revision=revision
        )
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    except Exception as e:
        return f"Error loading Moondream model: {e}"

    # Load image using PIL
    img = Image.open(image_path)
    
    try:
        enc_image = model.encode_image(img)
        answer = model.answer_question(enc_image, "Describe this image concisely for alt-text.", tokenizer)
        return answer
    except Exception as e:
        return f"Error running Moondream: {e}"

def generate_alt_text(image_path, provider="openai"):
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        return generate_alt_text_openai(image_path, api_key)
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        return generate_alt_text_gemini(image_path, api_key)
    elif provider == "moondream":
        return generate_alt_text_moondream(image_path)
    else:
        raise ValueError(f"Unknown provider: {provider}")
