"""
Fonctions d'interaction avec les modèles de langage (LLM).
"""

import base64
import openai

from utils.config import TECH_CONFIG,  LLM_CONFIG
from utils.auth import _get_keys

from utils.helpers import logger_tech



def _translate_with_chatgpt(text: str, source_lang: str, target_lang: str, use_secondary:bool = False) -> str:
    """
    Helper function to translate a given text from source_lang to target_lang using ChatGPT.
    """
    logger_tech.debug(f"Translating transcript from {source_lang} to {target_lang} ")
    config = LLM_CONFIG["translate"]["main"]
    if use_secondary:
        config = LLM_CONFIG["translate"]["secondary"]
    if (config["api"] == "openrouter"):
        client = openai.OpenAI(
            base_url=TECH_CONFIG["openrouter_url"],
            api_key=_get_keys()["OPENROUTER_API_KEY"],
        )
    elif (config["api"] == "openai"):
        client = openai.OpenAI(api_key=_get_keys()["OPENAI_API_KEY"])
    else:
        raise ValueError("Invalid LLM API specified in configuration.")

    try:
        context={
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        prompt = config["prompt"].format(**context)
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger_tech.error(f"Error translating text via ChatGPT: {e}")
        raise




def generate_design_transcript(img: bytes, lang: str, use_secondary:bool = False) -> str:
    """
    Sends the image to ChatGPT-4 with a predefined prompt stored in an environment variable (PROMPT).
    The ChatGPT API key is stored in AWS Secret Manager.
    """
    logger_tech.debug("Generating design transcript via ChatGPT.")
    
    config = LLM_CONFIG["transcript"]["main"]
    if use_secondary:
        config = LLM_CONFIG["transcript"]["secondary"]
    
    if (config["api"] == "openrouter"):
        client = openai.OpenAI(
            base_url=TECH_CONFIG["openrouter_url"],
            api_key=_get_keys()["OPENROUTER_API_KEY"],
        )
    else :
        if (config["api"] == "openai"):
            client = openai.OpenAI(api_key=_get_keys()["OPENAI_API_KEY"])
        else:
            raise ValueError("Invalid LLM API specified in configuration.")


    # Convert bytes to base64 string
    if isinstance(img, bytes):
        base64_image = base64.b64encode(img).decode('utf-8')
    else:
        logger_tech.error("Expected bytes for image data")
        raise ValueError("Image data must be bytes")


    context = {
        "target_lang": lang,
    }
    prompt = config["prompt"].format(**context)
    try:
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=1000
        )
        transcript = response.choices[0].message.content.strip()
        return transcript
    except Exception as e:
        logger_tech.error(f"Error generating transcript from ChatGPT: {e}")
        raise
