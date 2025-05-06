
import os
import json
import logging

import redis
import boto3

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
 
 
 #----------------------
 # PARAMETERS
 #----------------------

TECH_CONFIG = {
    "redis_host": "crisp-moray-17911.upstash.io",
    "redis_port": "6379",
    "dynamodb_id_table": "design-emotion_id",
    "dynamodb_region": "eu-west-3",
    "secret_name": "openai-key",
    "aws_region": "eu-west-3",
    "moderation-checker-main": "openai",
    "moderation-checker-secondary": "openrouter",
    "openrouter_url": "https://openrouter.ai/api/v1",
}

BUSINESS_CONFIG = {
    "id_cache_limit": 60,
    "transcript_cache_limit": 60*60*24*15,
}
 
LLM_VARIABLES = {
    "gpt4o": {
      "api":   "openai",
      "model": "gpt-4o",
      "prompts": {
        "transcript": """Analyse cette image de site web en te concentrant sur les émotions et l’ambiance générale véhiculées par la structure, les couleurs, et les éléments graphiques. Ignore le contenu textuel sauf s’il contribue directement à l’émotion. Traduis ces émotions en une expérience sensorielle et intellectuelle pour une personne aveugle, en utilisant des références au toucher, au son, aux odeurs, au goût, ou à des concepts abstraits. Par exemple, décris une ambiance comme une sensation de texture douce et chaleureuse, un bruit apaisant ou stimulant, ou une odeur évoquant une atmosphère spécifique. Ne fais aucune référence explicite aux aspects visuels ou à la disposition graphique. Ne soit pas trop ambiance publicité. essaie de faire vivre l’émotion sans enjoliver. Commence par Ce site …
        Fait ce transcript dans la langue : {target_lang}""",
        
        "translate":  "Translate from {source_lang} to {target_lang}. If it is the same language, just return the given text with no additional comment. If you translate, just return the translation.",
        
        "moderated":  "Analyse cette image de site web en te concentrant sur les émotions… (même que transcript)"
      },
    },
    
    "gpt4.1-or": {
      "api":   "openrouter",
      "model": "openai/gpt-4.1",
      "prompts": {
        "transcript": """Analyse cette image de site web en te concentrant sur les émotions et l’ambiance générale véhiculées par la structure, les couleurs, et les éléments graphiques. Ignore le contenu textuel sauf s’il contribue directement à l’émotion. Traduis ces émotions en une expérience sensorielle et intellectuelle pour une personne aveugle, en utilisant des références au toucher, au son, aux odeurs, au goût, ou à des concepts abstraits. Par exemple, décris une ambiance comme une sensation de texture douce et chaleureuse, un bruit apaisant ou stimulant, ou une odeur évoquant une atmosphère spécifique. Ne fais aucune référence explicite aux aspects visuels ou à la disposition graphique et ne prend pas en compte les publicité qui semble hors contexte. 
Pose toi d’abord la question de l’emotion que le designer a voulu faire passer sur ce site. Voit à quelles situations de la vie peut amener des  ambiance similaires et comment les autres sens que le visuels peuvent capter ce type d’émotion. 

Sélectionne l ambiance et 1 ou 2 sens le plus pertinent pour cette situation

Retranscrit cette émotion de façon compacte (entre 400 et 500 caracteres) 
Essaie de faire vivre l’émotion sans enjoliver. 

Commence par Ce site …

Fait ce transcript dans la langue : {target_lang}""",
        "translate":  None,
        "moderated":  None
      }
    }
}

LLM_CONFIG_WITH_VARIABLES = {
  "transcript": {
    "main":      "$$gpt4.1-or/transcript",
    "secondary": "$$gpt4o/transcript"
  },

  "translate": {
    "main":      "$$gpt4o/translate",
    "secondary": "$$gpt4.1-or/translate"
  },

  "moderated": {
    "main":      "$$gpt4o/moderated",
    "secondary": "$$gpt4.1-or/moderated"
  }
} 

def resolve_llm_config(variables, config):
    """
    Replace each "$$modelX/promptY" in config by a dict:
      {
        "api":   variables[modelX]["api"],
        "model": variables[modelX]["model"],
        "prompt": variables[modelX]["prompts"][promptY]
      }
    """
    def resolve_entry(ref: str):
        # On s'attend à une string de la forme "$$modelX/promptY"
        if not isinstance(ref, str) or not ref.startswith("$$"):
            raise ValueError(f"Reference invalide: {ref}")
        model_key, prompt_key = ref[2:].split("/", 1)
        model_def = variables[model_key]
        prompt_text = model_def["prompts"][prompt_key]
        return {
            "api":    model_def["api"],
            "model":  model_def["model"],
            "prompt": prompt_text
        }

    resolved = {}
    for block_name, block in config.items():
        resolved_block = {}
        for role, ref in block.items():  # role = "main" ou "secondary"
            resolved_block[role] = resolve_entry(ref)
        resolved[block_name] = resolved_block
    return resolved

# Utilisation
LLM_CONFIG = resolve_llm_config(LLM_VARIABLES, LLM_CONFIG_WITH_VARIABLES)

# -----------------------------------------------------------------------------
# Redis Cache Functions
# -----------------------------------------------------------------------------

_keycache = None 
def _get_keys():
    """
    Retrieves the OpenAI API key from AWS Secrets Manager.
    Assumes the secret is a JSON with a field named 'API_KEY'.
    """
    global _keycache 
    if _keycache is None :
        secret_name = TECH_CONFIG['secret_name']
        region_name = TECH_CONFIG['aws_region']

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
        _keycache = json.loads(secret)
    return _keycache


# Initialize Redis client
print("create redis client")
try:
    # Configuration pour Upstash en production
    if TECH_CONFIG['redis_host'] != "localhost" and TECH_CONFIG['redis_host'] != "host.docker.internal":
        redis_client = redis.Redis(
            host=TECH_CONFIG['redis_host'],
            port=TECH_CONFIG['redis_port'],
            password=_get_keys()['REDIS_KEY'],
            ssl=True,
            decode_responses=True
        )
        print(f"Connected to Upstash Redis at {TECH_CONFIG['redis_host']}")
    # Configuration locale pour le développement
    else:
        redis_client = redis.Redis(
            host="127.0.0.1",
            port=TECH_CONFIG['redis_port'],
            decode_responses=True
        )
        print(f"Connected to local Redis at {TECH_CONFIG['redis_host']}")
    
    # Test de connexion
    redis_client.ping()
    print("Redis connection test successful")
    
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {str(e)}")
    raise e
except Exception as e:
    print(f"Unexpected error while connecting to Redis: {str(e)}")
    raise e


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
    redis_client.set(cache_key, json.dumps(cache_value), ex=BUSINESS_CONFIG['id_cache_limit'])
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
    
    # Check if an entry already exists
    existing_cache = redis_client.get(cache_key)
    if existing_cache:
        existing_value = json.loads(existing_cache)
        # If same etag, update the transcripts list
        if existing_value.get("etag") == etag:
            # Check if this language already exists in the transcripts
            transcripts = existing_value.get("transcripts", [])
            for i, (existing_lang, _) in enumerate(transcripts):
                if existing_lang == lang:
                    # Replace existing language entry
                    transcripts[i] = (lang, transcript)
                    break
            else:
                # Language not found, append it
                transcripts.append((lang, transcript))
            
            # Update cache with modified transcripts
            existing_value["transcripts"] = transcripts
            redis_client.set(cache_key, json.dumps(existing_value), ex=BUSINESS_CONFIG['transcript_cache_limit'])
            return
    
    # No existing cache or different etag, create new entry
    cache_value = {
        "etag": etag,
        "transcripts": [
            (lang, transcript)
        ]
    }
    redis_client.set(cache_key, json.dumps(cache_value), ex=BUSINESS_CONFIG['transcript_cache_limit'])


# -----------------------------------------------------------------------------
# Rate Limiting Functions
# -----------------------------------------------------------------------------

def checkIP(ip: str) -> bool:
    """
    Vérifie si une IP peut faire une requête.
    - Si l'IP n'est pas dans le cache, l'ajoute avec TTL=60s et retourne True
    - Si l'IP est dans le cache, change le TTL à 120s et retourne False
    """
    cache_key = f"iplog:{ip}"
    
    # Vérifie si l'IP est dans le cache
    if redis_client.exists(cache_key):
        # IP trouvée, on étend le TTL à 120s
        redis_client.expire(cache_key, 120)
        return False
    else:
        # Nouvelle IP, on l'ajoute avec TTL=60s
        redis_client.set(cache_key, "1", ex=60)
        return True


# -----------------------------------------------------------------------------
# DynamoDB Functions 
# Config in TECH_CONFIG 
# The dynamodb structure is as follows:
#{
#  "email": email,
#  "credits-left": creditsLeft,
#  "credits-used": creditsUsed,
#  "frontKeys": list[FrontendKeys],
#  "usage-total": accessCount,
#  "usage-history": list[(date, url, creditCost)],
#  "foundings-total": totalAmount,
#  "foundings-history": list[(date, payedAmount, credits)]
#}

# example : 
# {
#  "email": "client@example.com",
#  "credits-left": 45,
#  "credits-used": 12,
#  "frontKeys": ["key1", "key2"],
#  "usage-total": 12,
#  "usage-history": [("2025-01-01", "www.mysite.org",1)],
#  "foundings-total": 3.99,
#  "foundings-history": [("2025-01-01", "3.99","50")]
#}

# -----------------------------------------------------------------------------
import boto3

DYNAMODB_ID_TABLE = None

def get_dynamodb_id_table():
    global DYNAMODB_ID_TABLE
    if DYNAMODB_ID_TABLE is None:
        dynamodb = boto3.resource('dynamodb', region_name=TECH_CONFIG['dynamodb_region'])
        DYNAMODB_ID_TABLE = dynamodb.Table(TECH_CONFIG['dynamodb_id_table'])
    return DYNAMODB_ID_TABLE

def isValidFrontKey(email: str, key: str) -> bool:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' not in response:
        return False
    
    if 'frontKeys' not in response['Item']:
        return False
    
    return key in response['Item']['frontKeys']
    
def addFrontKey(email: str, key: str) -> None:
    table = get_dynamodb_id_table()
    
    # First check if the email exists
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' not in response:
        # Create new user record if not exists
        table.put_item(
            Item={
                'email': email,
                'credits-left': 0,
                'credits-used': 0,
                'frontKeys': [key],
                'usage-total': 0,
                'usage-history': [],
                'foundings-total': 0.0,
                'foundings-history': []
            }
        )
    else:
        # Add key to existing user
        front_keys = response['Item'].get('frontKeys', [])
        if key not in front_keys:
            front_keys.append(key)
            table.update_item(
                Key={'email': email},
                UpdateExpression='SET frontKeys = :keys',
                ExpressionAttributeValues={':keys': front_keys}
            )

def removeFrontKey(email: str, key: str) -> None:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'frontKeys' in response['Item']:
        front_keys = response['Item']['frontKeys']
        if key in front_keys:
            front_keys.remove(key)
            table.update_item(
                Key={'email': email},
                UpdateExpression='SET frontKeys = :keys',
                ExpressionAttributeValues={':keys': front_keys}
            )

def addCredits(email: str, date: str, payedAmount: float, credits: int) -> None:
    table = get_dynamodb_id_table()
    
    # Check if user exists
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' not in response:
        # Create new user with credits
        table.put_item(
            Item={
                'email': email,
                'credits-left': credits,
                'credits-used': 0,
                'frontKeys': [],
                'usage-total': 0,
                'usage-history': [],
                'foundings-total': payedAmount,
                'foundings-history': [(date, str(payedAmount), str(credits))]
            }
        )
    else:
        # Update existing user
        item = response['Item']
        credits_left = item.get('credits-left', 0) + credits
        foundings_total = item.get('foundings-total', 0.0) + payedAmount
        foundings_history = item.get('foundings-history', [])
        foundings_history.append((date, str(payedAmount), str(credits)))
        
        table.update_item(
            Key={'email': email},
            UpdateExpression='SET #cl = :credits_left, #ft = :foundings_total, #fh = :foundings_history',
            ExpressionAttributeNames={
                '#cl': 'credits-left',
                '#ft': 'foundings-total',
                '#fh': 'foundings-history'
            },
            ExpressionAttributeValues={
                ':credits_left': credits_left,
                ':foundings_total': foundings_total,
                ':foundings_history': foundings_history
            }
        )

def useCredits(email: str, date: str, url: str, creditCost: int) -> None:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response:
        item = response['Item']
        credits_left = item.get('credits-left', 0)
        
        # Check if user has enough credits
        if credits_left >= creditCost:
            credits_left -= creditCost
            credits_used = item.get('credits-used', 0) + creditCost
            usage_total = item.get('usage-total', 0) + 1
            usage_history = item.get('usage-history', [])
            usage_history.append((date, url, creditCost))
            
            table.update_item(
                Key={'email': email},
                UpdateExpression='SET #cl = :credits_left, #cu = :credits_used, #ut = :usage_total, #uh = :usage_history',
                ExpressionAttributeNames={
                    '#cl': 'credits-left',
                    '#cu': 'credits-used',
                    '#ut': 'usage-total',
                    '#uh': 'usage-history'
                },
                ExpressionAttributeValues={
                    ':credits_left': credits_left,
                    ':credits_used': credits_used,
                    ':usage_total': usage_total,
                    ':usage_history': usage_history
                }
            )

def getUsageHistory(email: str) -> list:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'usage-history' in response['Item']:
        return response['Item']['usage-history']
    return []

def getFoundingsHistory(email: str) -> list:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'foundings-history' in response['Item']:
        return response['Item']['foundings-history']
    return []

def getUsageTotal(email: str) -> int:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'usage-total' in response['Item']:
        return response['Item']['usage-total']
    return 0

def getFoundingsTotal(email: str) -> float:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'foundings-total' in response['Item']:
        return response['Item']['foundings-total']
    return 0.0

def getCreditsLeft(email: str) -> int:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'credits-left' in response['Item']:
        return response['Item']['credits-left']
    return 0

def getCreditsUsed(email: str) -> int:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'credits-used' in response['Item']:
        return response['Item']['credits-used']
    return 0

def getCreditsTotal(email: str) -> int:
    return getCreditsLeft(email) + getCreditsUsed(email)




# -----------------------------------------------------------------------------
# LLM Functions
# -----------------------------------------------------------------------------



def _translate_with_chatgpt(text: str, source_lang: str, target_lang: str, use_secondary:bool = False) -> str:
    """
    Helper function to translate a given text from source_lang to target_lang using ChatGPT.
    """
    print("translate called")
    logger.info(f"Translating transcript from {source_lang} to {target_lang} via ChatGPT.")
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
        logger.error(f"Error translating text via ChatGPT: {e}")
        raise




def generate_design_transcript(img: bytes, lang: str, use_secondary:bool = False) -> str:
    """
    Sends the image to ChatGPT-4 with a predefined prompt stored in an environment variable (PROMPT).
    The ChatGPT API key is stored in AWS Secret Manager.
    """
    print("transcript called")
    logger.info("Generating design transcript via ChatGPT.")
    
    config = LLM_CONFIG["transcript"]["main"]
    if use_secondary:
        config = LLM_CONFIG["transcript"]["secondary"]
    
    if (config["api"] == "openrouter"):
        client = openai.OpenAI(
            base_url=TECH_CONFIG["openrouter_url"],
            api_key=_get_keys()["OPENROUTER_API_KEY"],
        )
    elif (config["api"] == "openai"):
        client = openai.OpenAI(api_key=_get_keys()["OPENAI_API_KEY"])
    else:
        raise ValueError("Invalid LLM API specified in configuration.")


    # Convert bytes to base64 string
    if isinstance(img, bytes):
        import base64
        base64_image = base64.b64encode(img).decode('utf-8')
    else:
        logger.error("Expected bytes for image data")
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
            store_cached_design_transcript(url, lang, etag, translated)
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
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': ''
        }

    # Vérification du rate limiting par IP
    headers = event.get('headers', {})
    ip_address = headers.get('X-Forwarded-For')
    if ip_address:
        ip_address = ip_address.split(',')[0].strip()
        if not checkIP(ip_address):
            return {
                'statusCode': 429,  # Too Many Requests
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Rate limit exceeded. Please wait before making another request.'
                })
            }

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
         
    