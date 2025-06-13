"""
Handlers Lambda pour l'application.
"""

import json

from services.dynamodb import is_valid_front_key, add_front_key
from services.mails import send_registration_mail
from services.cache import redis_client, shouldBlockIP, create_email_validation_key, get_email_validation_key
from services.transcript import get_design_transcript, get_design_transcript_with_image

from utils.helpers import logger_business, logger_tech
from utils.exceptions import BusinessException, InvalidFrontKeyException, TooManyRequestException, InvalidEmailValidationKeyException
import traceback


def get_cors_headers():
    return {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
    }

def get_exception_status_for_log(e):
    if isinstance(e, BusinessException):
        return e.status_code+"-"+e.internal_code
    return 500

def manage_exception(e,lang):
    if isinstance(e, BusinessException):
        return {
            'statusCode': e.status_code,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': e.type, 'description': e.get_description(lang)})
        }
    return {
        'statusCode': 500,
        'headers': get_cors_headers(),
        'body': json.dumps({'error': e.args[0], 'traceback': "".join(traceback.format_exception(type(e), e, e.__traceback__)) })
    }


def lambda_handler_transcript(event, context):
    """
    Lambda entry point.  
    Expects JSON input (e.g. via API Gateway) with the following keys:
    {
        "email": <string>,
        "client_key": <string>,
        "client_type": <string>,
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
    lang="en"
    log_data = {"lambda_event": event, "action": "get_transcript", "url": "", "lang": "", "email": "", "credits": 0, "client_type": "", "client_key": ""}
    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            email = params["email"] 
            client_type = params["client_type"]
            client_key = params["client_key"]
            url = params["url"]
            etag = params.get("etag", None)
            lang = params.get("lang", "en")
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            email = data["email"]
            client_type = data["client_type"]
            client_key = data["client_key"]
            url = data["url"]
            etag = data.get("etag")
            lang = data.get("lang", "en")

        log_data["url"] = url
        log_data["lang"] = lang
        log_data["email"] = email
        log_data["client_type"] = client_type
        log_data["client_key"] = client_key
        log_data["credits"] = 0
        
        if not is_valid_front_key(email, client_key):
            raise InvalidFrontKeyException(email)

        known, param = get_design_transcript(email, client_key, url, etag, lang,log_data)
        if known : 
            logger_business.log(status="200", **log_data)
            return {
                "statusCode": 200,
                'headers': get_cors_headers(),
                "body": json.dumps({"known": 1, "transcript": param}, ensure_ascii=False)
            }
        logger_business.log(status="201", **log_data)
        return {
                "statusCode": 201,
                'headers': get_cors_headers(),
                "body": json.dumps({"known": 0, "txid": param}, ensure_ascii=False)
            }

    except Exception as e:
        logger_business.log(status=get_exception_status_for_log(e), **log_data)
        return manage_exception(e, lang)

def lambda_handler_image_transcript(event, context):
    """
    Lambda entry point for direct image processing.
    Expects JSON input with the following keys:
    {
        "email": <string>,
        "url": <string>,
        "txid": <string>,
        "image": <string, base64 encoded image>,
        "lang": <string, optional>
        "client_type": <string>,
        "client_key": <string>,
    }
    """
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': ''
        }
    lang="en"
    log_data = {"lambda_event": event, "action": "get_transcript_from_image", "url": "", "lang": "", "email": "", "credits": 0, "client_type": "", "client_key": ""}
    
    # Vérification du rate limiting par IP
    headers = event.get('headers', {})
    ip_address = headers.get('X-Forwarded-For')
    if ip_address:
        ip_address = ip_address.split(',')[0].strip()
        if shouldBlockIP(ip_address):
            raise TooManyRequestException(ip_address)

    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            email = params["email"]
            url = params["url"]
            txid = params["txid"]
            image = params["image"]
            lang = params.get("lang", lang)
            client_type = params.get("client_type")
            client_key = params.get("client_key")
        else:
            # If triggered by POST with JSON body
            params = json.loads(body)
            email = params["email"]
            url = params["url"]
            txid = params["txid"]
            image = params["image"]
            lang = params.get("lang", lang)
            client_type = params.get("client_type")
            client_key = params.get("client_key")
        
        log_data["lang"] = lang
        log_data["email"] = email
        log_data["client_type"] = client_type
        log_data["client_key"] = client_key
        log_data["credits"] = 0
        log_data["url"] = url
        # Extract parameters from the event
        
        if not txid or not image:
            logger_business.log(status="400", **log_data)
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Missing required parameter: id or image'})
            }

        if not is_valid_front_key(email, client_key):
            raise InvalidFrontKeyException(email)

        # Decode base64 image
        import base64
        try:
            image_bytes = base64.b64decode(image) 
        except Exception as e:
            logger_business.log(status="400", **log_data)
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Invalid base64 image data: {str(e)}'})
            }
  
        # Generate transcript
        transcript = get_design_transcript_with_image(txid, image_bytes)
        logger_business.log(status="200", **log_data)
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'transcript': transcript
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger_business.log(status=get_exception_status_for_log(e), **log_data)
        return manage_exception(e, lang)


def lambda_handler_send_validation_mail(event, context):
    """
    Lambda entry point for email registration.
    Expects JSON input with the following keys:
    {
        "email": <string>,
        "lang": <string, optional>
        "client_type": <string>,
        "client_key": <string>
    }
    """
    lang="en"
    log_data = {"lambda_event": event, "action": "send_validation_mail", "url": "", "lang": "", "email": "", "credits": 0, "client_type": "", "client_key": ""}
    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            email = params["email"]
            lang = params.get("lang", lang)
            client_type = params.get("client_type")
            client_key = params.get("client_key")
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            email = data["email"]
            lang = data.get("lang", lang)
            client_type = data.get("client_type")
            client_key = data.get("client_key")

        log_data["lang"] = lang
        log_data["email"] = email
        log_data["client_type"] = client_type
        log_data["client_key"] = client_key
        
        validation_key = create_email_validation_key(email, client_key, client_type)


        print("#### validation_key", validation_key)


        send_registration_mail(email, validation_key)

        logger_business.log(status="200", **log_data)
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'info': 'registration mail has been sent'})
        }
        
    except Exception as e:
        logger_business.log(status=get_exception_status_for_log(e), **log_data)
        return manage_exception(e, lang)
 

def lambda_handler_register_key_for_email(event, context):
    """
    Lambda entry point for email validation.
    Expects JSON input with the following keys:
    {
        "validation_key": <string>,
        "email": <string>,
        "lang": <string, optional>
    }
    """
    lang="en"
    log_data = {"lambda_event": event, "action": "register_key_for_email", "url": "", "lang": "", "email": "", "credits": 0, "client_type": "email", "client_key": ""}
    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            validation_key = params["validation_key"]
            email = params["email"]
            lang = params.get("lang", lang)
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            validation_key = data["validation_key"]
            email = data["email"]
            lang = data.get("lang", lang)

        log_data["email"] = email
        log_data["lang"] = lang
        
        email_infos = get_email_validation_key(validation_key)
        if email_infos : 
            ## gere la reponse : valide l’email si ok 
            # sinon envoi une erreur
            print(">>>>>>email_infos", email_infos)
            key = email_infos["key"]
            email = email_infos["email"]
            tool = email_infos["tool"]
            add_front_key(email, key, tool)
            
            logger_business.log(status="200", **log_data)
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'info': f"email {email} has been registered"})
            }
        else : 
            raise InvalidEmailValidationKeyException(validation_key)
    except Exception as e:
        logger_business.log(status=get_exception_status_for_log(e), **log_data)
        return manage_exception(e, lang)


def lambda_handler_cache_get(event, context):
    """Affiche le contenu complet du cache Redis"""
    lang="en"
    log_data = {"lambda_event": event, "action": "cache_get", "url": "", "lang": "", "email": "", "credits": 0, "client_type": "", "client_key": ""}
    try:
        cache_keys = redis_client.keys("*")
        cache_data = {key: redis_client.get(key) for key in cache_keys}
        logger_business.log(status="200", **log_data)
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
                'body': json.dumps({
                'cache_entries': len(cache_data),
                'data': cache_data
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger_business.log(status=get_exception_status_for_log(e), **log_data)
        return manage_exception(e, "en")
 


        
def lambda_handler_cache_clear(event, context):
    log_data = {"lambda_event": event, "action": "cache_clear", "url": "", "lang": "", "email": "", "credits": 0, "client_type": "", "client_key": ""}
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
        logger_business.log(status="200", **log_data)
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': message
            }, ensure_ascii=False)
        }
    except Exception as e:
        logger_business.log(status=get_exception_status_for_log(e), **log_data)
        return manage_exception(e, "en")
