"""
Fonctions principales pour la génération de transcripts de design.
"""

from services.dynamodb import use_credits, test_db

from services.cache import (
    get_cached_design_transcript, store_cached_design_transcript, 
    create_cached_url_info, pop_cached_url_info
)
from services.llm import generate_design_transcript, _translate_with_chatgpt

from utils.helpers import logger_tech, logger_business


def get_design_transcript(email: str, key: str, url: str, etag: str,  lang: str = "en", log_data: dict = {}) -> (bool, str):
    """
    Main orchestration function:
      1. Cleans the URL of query parameters.
      2. Uses get_cached_design_transcript to check the cache.
      3. If no cache or invalid cache, captures a screenshot via get_screen_shot(),
         calls generate_design_transcript(), and stores in the cache.
      4. Returns the final transcript in the requested language.
    """
    ## test dynamodb access
    use_credits(email, 1, url)
    
    test_db()
    
    
    
    # Clean the URL by removing query parameters
    logger_tech.debug(f"Request to get_design_transcript: url={url}, etag={etag}, lang={lang}")
    if "?" in url:
        url = url.split("?")[0]

    # Check Cache
    transcripts = get_cached_design_transcript(url, lang, etag)
    def extract_transcript(transcripts):
        if not transcripts: 
            return None
        for (trans_lang, trans_text) in transcripts:
            if trans_lang == lang:
                logger_tech.debug(f"Found transcript in requested language ({lang}) in cache.")
                return trans_text

        # If we have a transcript but not the requested language, translate it
        for (trans_lang, trans_text) in transcripts:
            # Translate to requested language
            translated = _translate_with_chatgpt(trans_text, trans_lang, lang)
            # Update cache with the newly translated transcript
            store_cached_design_transcript(url, lang, etag, translated)
            
            log_data["action"] = "translate_transcript"
            logger_business.log(status="200", **log_data)
            logger_tech.debug(f"Added translated transcript ({lang}) to cache.")
            
            return translated
        return None
    
    cached_transcript = extract_transcript(transcripts)
    if cached_transcript is not None:
        return (True, cached_transcript)
    
    return (False, create_cached_url_info(url,lang,etag))


def get_design_transcript_with_image(id, img) :
    
    info= pop_cached_url_info(id)
    logger_tech.debug( f"retrived info = {info}" )
    if (info is None):
        return "Internal Error - try again "
    
    
    # Generate transcript from ChatGPT
    transcript = generate_design_transcript(img, info['lang'])

    # Store in cache
    store_cached_design_transcript(info['url'], info['lang'], info['etag'], transcript)
    
    return transcript
