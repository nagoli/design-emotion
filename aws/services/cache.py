"""
Fonctions de gestion du cache Redis.
"""

import redis
import json
import hashlib
import uuid

from utils.config import TECH_CONFIG, BUSINESS_CONFIG
from utils.auth import _get_keys
from utils.helpers import logger


# -----------------------------------------------------------------------------
# Redis Cache Functions
# -----------------------------------------------------------------------------



# Initialize Redis client
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
        logger.info(f"Connected to Upstash Redis at {TECH_CONFIG['redis_host']}")
    # Configuration locale pour le développement
    else:
        redis_client = redis.Redis(
            host="127.0.0.1",
            port=TECH_CONFIG['redis_port'],
            decode_responses=True
        )
        logger.info(f"Connected to local Redis at {TECH_CONFIG['redis_host']}")
    
    # Test de connexion
    redis_client.ping()
    logger.info("Redis connection test successful")
    
except redis.ConnectionError as e:
    logger.info(f"Failed to connect to Redis: {str(e)}")
    raise e
except Exception as e:
    logger.info(f"Unexpected error while connecting to Redis: {str(e)}")
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

def shouldBlockIP(ip: str) -> bool:
    """
    Vérifie si une IP peut faire une requête.
    - Si l'IP n'est pas dans le cache, l'ajoute avec TTL=60s et retourne True
    - Si l'IP est dans le cache, change le TTL à 120s et retourne False
    """
    cache_key = f"iplog:{ip}"
    
    # Vérifie si l'IP est dans le cache
    if redis_client.exists(cache_key):
        # IP trouvée, on étend le TTL à 120s
        # verifie la durée restante
        time = redis_client.ttl(cache_key)
        redis_client.expire(cache_key, time*2)
        if (time > 100) : 
            return True
    else:
        # Nouvelle IP, on l'ajoute avec TTL=60s
        redis_client.set(cache_key, "1", ex=30)
    return False


""""
Email registration validation key cache
"""

def create_email_validation_key( email: str, key:str, tool:str) -> str:
    logger.info("Storing validation_key info in cache.")
    #generate unique id randomly
    short_id = str(uuid.uuid4())
    cache_key = f"email_validation_key:{short_id}"
    cache_value = {
        "email": email,
        "key":key,
        "tool": tool,
    }
    redis_client.set(cache_key, json.dumps(cache_value), ex=BUSINESS_CONFIG['email_validation_limit'])
    return short_id

def get_email_validation_key(validation_key: str) -> str:
    logger.info("Popping url info from cache.")
    cache_key = f"email_validation_key:{validation_key}"
    cache_value = redis_client.get(cache_key)
    if cache_value is None:
       return None
    # on efface pas le cache pour si la validation est utilisé plusieurs fois ainsi on ne renvoie pas une erreur pour rien - le cache s’efface après 24h
    #redis_client.delete(cache_key)
    return json.loads(cache_value)