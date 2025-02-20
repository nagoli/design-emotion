from ast import main
import os
import json
import logging
from datetime import datetime, timedelta, timezone

import boto3
import redis

import openai

import hashlib
from botocore.exceptions import ClientError
import base64



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
ID_CACHE_LIMIT = int(os.environ.get("ID_CACHE_LIMIT", "60"))
tmp_transcript_cache_limit = 60*60*24*15 # 15j
TRANSCRIPT_CACHE_LIMIT = int(os.environ.get("TRANSCRIPT_CACHE_LIMIT", str(tmp_transcript_cache_limit)))
PROMPT = os.environ.get("PROMPT", """Analyse cette image de site web en te concentrant sur les émotions et l’ambiance générale véhiculées par la structure, les couleurs, et les éléments graphiques. Ignore le contenu textuel sauf s’il contribue directement à l’émotion. Traduis ces émotions en une expérience sensorielle et intellectuelle pour une personne aveugle, en utilisant des références au toucher, au son, aux odeurs, au goût, ou à des concepts abstraits. Par exemple, décris une ambiance comme une sensation de texture douce et chaleureuse, un bruit apaisant ou stimulant, ou une odeur évoquant une atmosphère spécifique. Ne fais aucune référence explicite aux aspects visuels ou à la disposition graphique. Ne soit pas trop ambiance publicité. essaie de faire vivre l’émotion sans enjoliver. Commence par Ce site …
""")




# -----------------------------------------------------------------------------
# Redis Cache Functions
# -----------------------------------------------------------------------------


# Initialize Redis client (ElastiCache)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_cached_design_transcript(url: str, lang: str, etag: str) -> list ( (str, str)):
    """
    Fetches the transcript in the specified language from ElastiCache (Redis).
    If the page's etag has not changed,
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

    # Check ETag match 
    #  # since cache is removed every 2 weeks we do not need to check lastmodifieddate
    cached_etag = cache_data.get("etag")
    transcripts = cache_data.get("transcripts", [])  # List of tuples (lang, transcript)

   
    if (etag) :
        match = (etag == cached_etag) 
        logger.info("Checking cache for ETag : " + str(match))
    else:
        match = True 
    if match:
        logger.info("Cache is valid. Checking for language availability.")
        return transcripts

    logger.info("Cache is present but does not meet criteria or no suitable transcript found.")
    return None


def create_cached_url_info(url: str, lang: str, etag: str) -> str:
    logger.info("Storing url info in cache.")
    #generate unique id
    url_md5 = hashlib.md5(url.encode()).hexdigest()
    short_id = url_md5 #[:8]
    cache_key = f"urlinfo_cache:{short_id}"
    cache_value = {
        "url": url,
        "lang":lang,
        "etag": etag,
    }
    redis_client.set(cache_key, json.dumps(cache_value), ex=ID_CACHE_LIMIT)
    return short_id

def pop_cached_url_info(short_id: str) -> str:
    logger.info("Popping url info from cache.")
    cache_key = f"urlinfo_cache:{short_id}"
    cache_value = redis_client.get(cache_key)
    if cache_value is None:
        return None
    redis_client.delete(cache_key)
    return json.loads(cache_value)


def store_cached_design_transcript(url: str, lang: str, etag: str, transcript: str) -> None:
    logger.info("Storing transcript in cache.")
    cache_key = f"transcript_cache:{url}"
    cache_value = {
        "etag": etag,
        "transcripts": [
            (lang, transcript)
        ]
    }
    redis_client.set(cache_key, json.dumps(cache_value), ex=TRANSCRIPT_CACHE_LIMIT)



# -----------------------------------------------------------------------------
# LLM Functions
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

#####
## Core Functions 
#####

def get_design_transcript(url: str, etag: str,  lang: str = "en") -> (bool, str):
    """
    Main orchestration function:
      1. Cleans the URL of query parameters.
      2. Uses get_cached_design_transcript to check the cache.
      3. If no cache or invalid cache, captures a screenshot via get_screen_shot(),
         calls generate_design_transcript(), and stores in the cache.
      4. Returns the final transcript in the requested language.
    """
    # Clean the URL by removing query parameters
    logger.info(f"Request to get_design_transcript: url={url}, etag={etag}, lang={lang}")
    if "?" in url:
        url = url.split("?")[0]

    # Check Cache
    transcripts = get_cached_design_transcript(url, lang, etag)
    def extract_transcript(transcripts):
        if not transcripts: 
            return None
        for (trans_lang, trans_text) in transcripts:
            if trans_lang == lang:
                logger.info(f"Found transcript in requested language ({lang}) in cache.")
                return trans_text

        # If we have a transcript but not the requested language, translate it
        for (trans_lang, trans_text) in transcripts:
            # Translate to requested language
            translated = _translate_with_chatgpt(trans_text, trans_lang, lang)
            # Update cache with the newly translated transcript
            transcripts.append((lang, translated))
            cache_data["transcripts"] = transcripts
            redis_client.set(cache_key, json.dumps(cache_data), keepttl=True)
            logger.info(f"Added translated transcript ({lang}) to cache.")
            return translated
        return None
    
    cached_transcript = extract_transcript(transcripts)
    if cached_transcript is not None:
        return (True, cached_transcript)
    
    return (False, create_cached_url_info(url,lang,etag))


def get_design_transcript_with_image(id, img) :
    
    info= pop_cached_url_info(id)
    print( f"retrived info = {info}" )
    if (info is None):
        return "Internal Error - try again "
    
    
    # Generate transcript from ChatGPT
    transcript = generate_design_transcript(img, info['lang'])

    # Store in cache
    store_cached_design_transcript(info['url'], info['lang'], info['etag'], transcript)
    
    return transcript



#####
# AWS LAMBDA Functions 
#####

def get_cors_headers():
    return {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
    }

def lambda_handler_transcript(event, context):
    """
    Lambda entry point.  
    Expects JSON input (e.g. via API Gateway) with the following keys:
    {
        "url": <string>,
        "etag": <string, optional>,
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
            lang = params.get("lang", "en")
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            url = data["url"]
            etag = data.get("etag")
            lang = data.get("lang", "en")

        known, param = get_design_transcript(url, etag, lang)
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
            'headers': get_cors_headers(),
            "body": json.dumps({"error": str(e)})
        }

def lambda_handler_image_transcript(event, context):
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
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Missing required parameter: id'})
            }

        if not image:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Missing required parameter: image'})
            }

        # Decode base64 image
        import base64
        try:
            image_bytes = base64.b64decode(image) 
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Invalid base64 image data: {str(e)}'})
            }
  
        # Generate transcript
        transcript = get_design_transcript_with_image(id, image_bytes)

        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'transcript': transcript
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f'Error processing image: {str(e)}', exc_info=True)
        return {
            'statusCode': 500,  
            'headers': get_cors_headers(),
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def lambda_handler_cache_get(event, context):
    """Affiche le contenu complet du cache Redis"""
    try:
        cache_keys = redis_client.keys("*")
        cache_data = {key: redis_client.get(key) for key in cache_keys}

        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
                'body': json.dumps({
                'cache_entries': len(cache_data),
                'data': cache_data
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }
 


        
def lambda_handler_cache_clear(event, context):
    try:
        # Vérifier si une clé spécifique est fournie
        params = event.get("queryStringParameters", {})
        specific_key = None
        if (params) : 
            specific_key = params.get("key", None)
        if specific_key:
            # Supprimer une clé spécifique
            if redis_client.exists(specific_key):
                redis_client.delete(specific_key)
                message = f"Cache key '{specific_key}' deleted successfully"
            else:
                message = f"Cache key '{specific_key}' not found"
        else:
            # Supprimer tout le cache
            redis_client.flushall()
            message = "All cache entries cleared successfully"

        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': message
            }, ensure_ascii=False)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
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
                "lang": "french"
            }
        }   
        context = {}
        response_get = lambda_handler_transcript(event_get, context)
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
        response_get = lambda_handler_image_transcript(event_get, context)
        print("Réponse GET :", response_get)
         
    