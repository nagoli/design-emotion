from ast import main
import os
import json
import logging
from datetime import datetime, timedelta, timezone

import boto3
import redis
import openai
import playwright.sync_api as sync_playwright
#from playwright_stealth import stealth_sync

import hashlib
from botocore.exceptions import ClientError
import base64


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
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
# Environment variables expected (example):
#   REDIS_HOST: Host of the Redis cluster (ElastiCache).
#   REDIS_PORT: Port of the Redis cluster.
#   OPENAI_SECRET_NAME: Name of the secret in AWS Secrets Manager that holds the OpenAI API key.
#   AWS_REGION: AWS region where the secret is stored.
#   PROMPT: Predefined prompt for ChatGPT to analyze the design.

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
OPENAI_SECRET_NAME = os.environ.get("OPENAI_SECRET_NAME", "openai-key")
AWS_REGION = os.environ.get("AWS_REGION","eu-west-3")
PROMPT = os.environ.get("PROMPT", """Analyse cette image de site web en te concentrant sur les émotions et l’ambiance générale véhiculées par la structure, les couleurs, et les éléments graphiques. Ignore le contenu textuel sauf s’il contribue directement à l’émotion. Traduis ces émotions en une expérience sensorielle et intellectuelle pour une personne aveugle, en utilisant des références au toucher, au son, aux odeurs, au goût, ou à des concepts abstraits. Par exemple, décris une ambiance comme une sensation de texture douce et chaleureuse, un bruit apaisant ou stimulant, ou une odeur évoquant une atmosphère spécifique. Ne fais aucune référence explicite aux aspects visuels ou à la disposition graphique. Ne soit pas trop ambiance publicité. essaie de faire vivre l’émotion sans enjoliver. Commence par Ce site …
""")

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
    secret_name = OPENAI_SECRET_NAME
    region_name = AWS_REGION

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)["OPENAI_API_KEY"]



# -----------------------------------------------------------------------------
# Lambda Functions
# -----------------------------------------------------------------------------

def hideModalElements():
    """
    This is a placeholder Python function referencing the JS snippet above.
    In practice, we inject the JavaScript into the page using Playwright's evaluate method.
    """
    pass  # The actual script is in HIDE_MODAL_ELEMENTS_JS above.



def is_within_two_weeks(date_str: str, cached_date_str: str) -> bool:
    """
    Vérifie si deux dates sont espacées de moins de deux semaines.

    Args:
        date_str (str): La première date. Peut être en format ISO 8601 ou RFC 1123.
        cached_date_str (str): La seconde date. Peut être en format ISO 8601 ou RFC 1123.

    Returns:
        bool: True si les dates sont espacées de moins de deux semaines, False sinon ou en cas d'erreur.
    """
    def parse_date(date_str):
        for fmt in ("%Y-%m-%dT%H:%M:%SZ",  # ISO 8601
                    "%a, %d %b %Y %H:%M:%S GMT"):  # RFC 1123
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Format de date non supporté: {date_str}")

    try:
        date_val = parse_date(date_str)
        cached_date_val = parse_date(cached_date_str)
        
        # Calcul de la différence absolue entre les deux dates
        difference = abs(date_val - cached_date_val)
        
        # Vérifie si la différence est inférieure à deux semaines
        return difference < timedelta(weeks=2)
    except ValueError as ve:
        logger.error(f"Erreur de format de date : {ve}")
        return False
    except Exception as e:
        logger.exception(f"Erreur inattendue : {e}")
        return False


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

    def _within_two_weeks(date_str: str, cached_date_str: str) -> bool:
        try:
            date_val = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            cached_date_val = datetime.fromisoformat(cached_date_str.replace('Z', '+00:00'))
            return abs(date_val - cached_date_val) < timedelta(weeks=2)
        except Exception:
            return False

    # If ETag matches or lastmodifieddate is within two weeks, we can reuse from cache
    match = etag and etag == cached_etag
    logger.info("Checking cache for ETag : " + str(match))
    if not match:
        match = lastmodifieddate and is_within_two_weeks(lastmodifieddate, cached_last_modified)
        logger.info("Checking cache for lastmodifieddate : " + str(match))
    if match:
        logger.info("Cache is valid. Checking for language availability.")
        for (trans_lang, trans_text) in transcripts:
            if trans_lang == lang:
                logger.info(f"Found transcript in requested language ({lang}) in cache.")
                return trans_text

        # If we have an transcript but not the requested language, try to translate
        for (trans_lang, trans_text) in transcripts:
            # Translate to requested language
            translated = _translate_with_chatgpt(trans_text, trans_lang, lang)
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
    print("transcript called")
    logger.info("Generating design transcript via ChatGPT.")
    
    if (False):
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )
    else : 
        client = openai.OpenAI(api_key=_get_openai_api_key())


    # Convert bytes to base64 string
    if isinstance(img, bytes):
        import base64
        base64_image = base64.b64encode(img).decode('utf-8')
    else:
        logger.error("Expected bytes for image data")
        raise ValueError("Image data must be bytes")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this website :",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Return transcript in language: {lang}",
                        },
                    ],
                },
            ],
            max_tokens=1000
        )
        transcript = response.choices[0].message.content.strip()
        return transcript
    except Exception as e:
        logger.error(f"Error generating transcript from ChatGPT: {e}")
        raise


def _translate_with_chatgpt(text: str, source_lang: str, target_lang: str) -> str:
    """
    Helper function to translate a given text from source_lang to target_lang using ChatGPT.
    """
    print("translate called")
    logger.info(f"Translating transcript from {source_lang} to {target_lang} via ChatGPT.")
    client = openai.OpenAI(api_key=_get_openai_api_key())

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Translate from {source_lang} to {target_lang}"},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error translating text via ChatGPT: {e}")
        raise


def create_cached_url_info(url: str, lang: str, etag: str, lastmodifieddate: str) -> str:
    logger.info("Storing url info in cache.")
    #generate unique id
    url_md5 = hashlib.md5(url.encode()).hexdigest()
    short_id = url_md5 #[:8]
    cache_key = f"urlinfo_cache:{short_id}"
    cache_value = {
        "url": url,
        "lang":lang,
        "etag": etag,
        "lastmodifieddate": lastmodifieddate,
    }
    redis_client.set(cache_key, json.dumps(cache_value))
    return short_id

def pop_cached_url_info(short_id: str) -> str:
    logger.info("Popping url info from cache.")
    cache_key = f"urlinfo_cache:{short_id}"
    cache_value = redis_client.get(cache_key)
    if cache_value is None:
        return None
    redis_client.delete(cache_key)
    return json.loads(cache_value)


def store_cached_design_transcript(url: str, lang: str, etag: str, lastmodifieddate: str, transcript: str) -> None:
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



def get_design_transcript(url: str, etag: str, lastmodifieddate: str, lang: str = "en") -> (bool, str):
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
        return (True, cached_transcript)
    
    return (False, create_cached_url_info(url,lang,etag,lastmodifieddate))


def get_design_transcript_with_image(id, img) :
    
    info= pop_cached_url_info(id)
    print(info )
    
    # Generate transcript from ChatGPT
    transcript = generate_design_transcript(img, info['lang'])

    # Store in cache
    store_cached_design_transcript(info['url'], info['lang'], info['etag'], info['lastmodifieddate'], transcript)
    
    return transcript




def get_cors_headers():
    return {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
    }

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
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': ''
        }

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

        known, param = get_design_transcript(url, etag, lastmodifieddate, lang)
        if known : 
            return {
                "statusCode": 200,
                'headers': get_cors_headers(),
                "body": json.dumps({"known": 1, "transcript": param}, ensure_ascii=False)
            }
        return {
                "statusCode": 200,
                'headers': get_cors_headers(),
                "body": json.dumps({"known": 0, "id": param}, ensure_ascii=False)
            }

    except Exception as e:
        logger.exception("Error in lambda_handler")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def lambda_handler_image(event, context):
    """
    Lambda entry point for direct image processing.
    Expects JSON input with the following keys:
    {
        "id": <string>,
        "image": <string, base64 encoded image>,
        "lang": <string, optional>
    }
    """
    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            id = params["id"]
            image = params["image"]
        else:
            # If triggered by POST with JSON body
            params = json.loads(body)
            id = params["id"]
            image = params["image"]
        
        print(event)
        # Extract parameters from the event
        
        if not id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameter: id'})
            }

        if not image:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameter: image'})
            }

        # Decode base64 image
        import base64
        try:
            image_bytes = base64.b64decode(image) 
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid base64 image data: {str(e)}'})
            }
  
        # Generate transcript
        transcript = get_design_transcript_with_image(id, image_bytes)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            'body': json.dumps({
                'transcript': transcript
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f'Error processing image: {str(e)}', exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def lambda_handler_cache(event, context):
    """Affiche le contenu complet du cache Redis"""
    try:
        cache_keys = redis_client.keys("*")
        cache_data = {key: redis_client.get(key) for key in cache_keys}

        return {
            'statusCode': 200,
             'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
            },
            'body': json.dumps({
                'cache_entries': len(cache_data),
                'data': cache_data
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
 
        
if __name__ == "__main__":
    if (False) :
        screen_shot = get_screen_shot("https://www.respiration-yoga.fr")
        #export to file
        with open("screenshot.png", "wb") as f:
            f.write(screen_shot)

    if (False) : 
        event_get = {
            "queryStringParameters": {
                "url": "https://respiration-yogae.fr/",
                "etag": "3260-6212906e91527-br",
                "lastmodifieddate": "Mon, 02 Sep 2024 20:45:53 GMT",
                "lang": "french"
            }
        }   
        context = {}
        response_get = lambda_handler(event_get, context)
        print("Réponse GET :", response_get)
        
    if (True) : 
        screenshot = None
        image=None
        with open("screenshot.png") as f:
            f.read(screenshot)
        base64.encode(screenshot, image)
        event_get = {
            "queryStringParameters": {
                "id": "68f90748e770518b3171369d3edf3235",
                "image": image
            }
        }   
        context = {}
        response_get = lambda_handler_image(event_get, context)
        print("Réponse GET :", response_get)
         
    