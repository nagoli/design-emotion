import os
import json
import logging
from datetime import datetime, timedelta, timezone

import boto3
import redis
import openai

# If you are using an AWS-compatible version of Playwright, import it accordingly.
# For example, if you have a layer that includes playwright_aws_lambda, you might do:
# from playwright_aws_lambda import PlaywrightAwsLambda
# Or if you package playwright in your Lambda, you might use:
from playwright.sync_api import sync_playwright

# -----------------------------------------------------------------------------
# Global Configuration & Initialization
# -----------------------------------------------------------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables expected (example):
#   REDIS_HOST: Host of the Redis cluster (ElastiCache).
#   REDIS_PORT: Port of the Redis cluster.
#   OPENAI_SECRET_NAME: Name of the secret in AWS Secrets Manager that holds the OpenAI API key.
#   AWS_REGION: AWS region where the secret is stored.
#   PROMPT: Predefined prompt for ChatGPT to analyze the design.

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
OPENAI_SECRET_NAME = os.environ.get("OPENAI_SECRET_NAME", "my-openai-secret")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
PROMPT = os.environ.get("PROMPT", "Please provide a design transcript based on this screenshot.")

# We will hold a global reference to Playwright's browser to avoid re-initialization
_browser = None

# Initialize Redis client (ElastiCache)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def _get_openai_api_key():
    """
    Retrieves the OpenAI API key from AWS Secrets Manager.
    Assumes the secret is a JSON with a field named 'API_KEY'.
    """
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=OPENAI_SECRET_NAME)
    secret_str = response['SecretString']
    secret_dict = json.loads(secret_str)
    return secret_dict['API_KEY']

def _init_browser():
    """
    Initializes and returns a singleton Playwright browser instance.
    """
    global _browser
    if _browser is None:
        # If using a special AWS-compatible version, replace with that approach:
        playwright = sync_playwright().start()
        _browser = playwright.chromium.launch(headless=True)
    return _browser

# JavaScript code to hide modal elements
HIDE_MODAL_ELEMENTS_JS = """
() => {
    const shift = 30; // Margin to define corners
    const allElements = document.querySelectorAll('*');
    Array.from(allElements).forEach(element => {
        const style = window.getComputedStyle(element);
        if (style.position === 'fixed') {
            const rect = element.getBoundingClientRect();
            const inCorner = (
                (rect.top < shift && rect.left < shift && rect.height < window.innerHeight - (2 * shift)) ||  // Top-left corner
                (rect.top < shift && rect.right > window.innerWidth - shift && rect.height < window.innerHeight - (2 * shift)) ||  // Top-right corner
                (rect.bottom > window.innerHeight - shift && rect.right > window.innerWidth - shift && rect.width < window.innerWidth - (2 * shift))  // Bottom-right corner
            );
            if (!inCorner) {
                element.style.opacity = 0;
            }
        }
    });
}
"""

# -----------------------------------------------------------------------------
# Lambda Functions
# -----------------------------------------------------------------------------

def hideModalElements():
    """
    This is a placeholder Python function referencing the JS snippet above.
    In practice, we inject the JavaScript into the page using Playwright's evaluate method.
    """
    pass  # The actual script is in HIDE_MODAL_ELEMENTS_JS above.


def get_screen_shot(url: str) -> bytes:
    """
    For a given URL, captures a screenshot of the page (up to 1024px height),
    after executing the 'hideModalElements' JS script in the browser.
    """
    logger.info(f"Capturing screenshot for URL: {url}")
    browser = _init_browser()
    context = browser.new_context(viewport={"width": 1280, "height": 1024})
    page = context.new_page()

    try:
        page.goto(url, wait_until="networkidle")
        page.evaluate(HIDE_MODAL_ELEMENTS_JS)
        screenshot = page.screenshot(full_page=False)
    except Exception as e:
        logger.error(f"Failed to capture screenshot for {url}: {e}")
        raise
    finally:
        context.close()
    return screenshot


def get_cached_design_transcript(url: str, lang: str, etag: str, lastmodifieddate: str) -> str:
    """
    Fetches the transcript in the specified language from ElastiCache (Redis).
    If the page's etag has not changed or if the provided lastmodifieddate is within two weeks,
    uses the cache and translates to the specified language if needed.
    The translations are then added to the cache.
    """
    logger.info("Checking cached transcript...")
    cache_key = f"transcript_cache:{url}"
    cached_value = redis_client.get(cache_key)

    if not cached_value:
        logger.info("No cache entry found.")
        return None

    try:
        cache_data = json.loads(cached_value)
    except json.JSONDecodeError:
        logger.warning("Cache data is not valid JSON. Ignoring.")
        return None

    # Check ETag match and lastmodifieddate within 2 weeks
    cached_etag = cache_data.get("etag")
    cached_last_modified = cache_data.get("lastmodifieddate")
    transcripts = cache_data.get("transcripts", [])  # List of tuples (lang, transcript)

    def _within_two_weeks(date_str: str) -> bool:
        try:
            date_val = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (datetime.now(timezone.utc) - date_val) < timedelta(weeks=2)
        except Exception:
            return False

    # If ETag matches or lastmodifieddate is within two weeks, we can reuse from cache
    if (etag and etag == cached_etag) or (lastmodifieddate and _within_two_weeks(lastmodifieddate)):
        logger.info("Cache is potentially valid. Checking for language availability.")
        for (trans_lang, trans_text) in transcripts:
            if trans_lang == lang:
                logger.info(f"Found transcript in requested language ({lang}) in cache.")
                return trans_text

        # If we have an English transcript but not the requested language, try to translate
        for (trans_lang, trans_text) in transcripts:
            if trans_lang == "en":
                # Translate to requested language
                translated = _translate_with_chatgpt(trans_text, "en", lang)
                # Update cache with the newly translated transcript
                transcripts.append((lang, translated))
                cache_data["transcripts"] = transcripts
                redis_client.set(cache_key, json.dumps(cache_data))
                logger.info(f"Added translated transcript ({lang}) to cache.")
                return translated

    logger.info("Cache is present but does not meet criteria or no suitable transcript found.")
    return None


def generate_design_transcript(img: bytes, lang: str) -> str:
    """
    Sends the image to ChatGPT-4 with a predefined prompt stored in an environment variable (PROMPT).
    The ChatGPT API key is stored in AWS Secret Manager.
    """
    logger.info("Generating design transcript via ChatGPT.")
    openai.api_key = _get_openai_api_key()

    # Here we simulate sending the image to ChatGPT.
    # Since ChatGPT (OpenAI) doesn't natively accept direct images, you'd typically do OCR
    # or some additional step. For demonstration, let's assume we can pass base64 or a reference
    # to an image. Adjust the code for your real usage scenario.

    # This example simply uses the prompt + " (base64 image data)" as context:
    base64_image_data = img.encode('base64') if hasattr(img, 'encode') else "FAKE_IMAGE_DATA"
    system_prompt = PROMPT

    # For ChatGPT-4 usage:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Analyze this design (image data): {base64_image_data}. "
                               f"Return transcript in language: {lang}"
                },
            ]
        )
        transcript = response["choices"][0]["message"]["content"].strip()
        return transcript
    except Exception as e:
        logger.error(f"Error generating transcript from ChatGPT: {e}")
        raise


def _translate_with_chatgpt(text: str, source_lang: str, target_lang: str) -> str:
    """
    Helper function to translate a given text from source_lang to target_lang using ChatGPT.
    """
    logger.info(f"Translating transcript from {source_lang} to {target_lang} via ChatGPT.")
    openai.api_key = _get_openai_api_key()

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Translate from {source_lang} to {target_lang}"},
                {"role": "user", "content": text}
            ]
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Error translating text via ChatGPT: {e}")
        raise


def get_design_transcript(url: str, etag: str, lastmodifieddate: str, lang: str = "en") -> str:
    """
    Main orchestration function:
      1. Cleans the URL of query parameters.
      2. Uses get_cached_design_transcript to check the cache.
      3. If no cache or invalid cache, captures a screenshot via get_screen_shot(),
         calls generate_design_transcript(), and stores in the cache.
      4. Returns the final transcript in the requested language.
    """
    # Clean the URL by removing query parameters
    logger.info(f"Request to get_design_transcript: url={url}, etag={etag}, lastmodifieddate={lastmodifieddate}, lang={lang}")
    if "?" in url:
        url = url.split("?")[0]

    # Check Cache
    cached_transcript = get_cached_design_transcript(url, lang, etag, lastmodifieddate)
    if cached_transcript is not None:
        return cached_transcript

    # Capture screenshot
    img = get_screen_shot(url)

    # Generate transcript from ChatGPT
    transcript = generate_design_transcript(img, lang)

    # Store in cache
    logger.info("Storing transcript in cache.")
    cache_key = f"transcript_cache:{url}"
    cache_value = {
        "etag": etag,
        "lastmodifieddate": lastmodifieddate,
        "transcripts": [
            (lang, transcript)
        ]
    }
    redis_client.set(cache_key, json.dumps(cache_value))

    return transcript

def lambda_handler(event, context):
    """
    Lambda entry point.  
    Expects JSON input (e.g. via API Gateway) with the following keys:
    {
        "url": <string>,
        "etag": <string, optional>,
        "lastmodifieddate": <string, optional>,
        "lang": <string, optional>
    }
    """
    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            url = params["url"]
            etag = params.get("etag", None)
            lastmodifieddate = params.get("lastmodifieddate", None)
            lang = params.get("lang", "en")
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            url = data["url"]
            etag = data.get("etag")
            lastmodifieddate = data.get("lastmodifieddate")
            lang = data.get("lang", "en")

        transcript = get_design_transcript(url, etag, lastmodifieddate, lang)
        return {
            "statusCode": 200,
            "body": json.dumps({"transcript": transcript})
        }

    except Exception as e:
        logger.exception("Error in lambda_handler")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }