"""
Handlers Lambda pour l'application.
"""

import json

from services.dynamodb import is_valid_front_key
from services.mail import send_registration_mail
from services.cache import redis_client, checkIP, create_email_validation_key, get_email_validation_key
from services.transcript import get_design_transcript, get_design_transcript_with_image

from utils.helpers import logger


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
        "email": <string>,
        "key": <string>,
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
            email = params["email"]
            key = params["key"]
            url = params["url"]
            etag = params.get("etag", None)
            lang = params.get("lang", "en")
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            email = data["email"]
            key = data["key"]
            url = data["url"]
            etag = data.get("etag")
            lang = data.get("lang", "en")

        if not is_valid_front_key(email, key):
            return {
                'statusCode': 401,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Invalid front key'})
            }

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
        "email": <string>,
        "key": <string>,
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
            email = params["email"]
            key = params["key"]
            id = params["id"]
            image = params["image"]
        else:
            # If triggered by POST with JSON body
            params = json.loads(body)
            email = params["email"]
            key = params["key"]
            id = params["id"]
            image = params["image"]
        
        
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

        if not is_valid_front_key(email, key):
                    return {
                        'statusCode': 401,
                        'headers': get_cors_headers(),
                        'body': json.dumps({'error': 'Invalid front key'})
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


def lambda_handler_register_mail(event, context):
    """
    Lambda entry point for email registration.
    Expects JSON input with the following keys:
    {
        "email": <string>,
        "key": <string>,
        "tool": <string>
    }
    """
    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            email = params["email"]
            key = params["key"]
            tool = params.get("tool", "front")
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            email = data["email"]
            key = data["key"]
            tool = data.get("tool", "front")

        validation_key = create_email_validation_key(email, key, tool)
        send_email(email, validation_key)

        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'info': 'registration mail has been sent'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }
 

def lambda_handler_validate_mail(event, context):
    """
    Lambda entry point for email validation.
    Expects JSON input with the following keys:
    {
        "validation_key": <string>
    }
    """
    try:
        body = event.get("body")
        if body is None:
            # If triggered by GET with queryStringParameters
            params = event.get("queryStringParameters", {})
            validation_key = params["validation_key"]
        else:
            # If triggered by POST with JSON body
            data = json.loads(body)
            validation_key = data["validation_key"]

        email_infos = get_email_validation_key(validation_key)
        if email_infos : 
            ## gere la reponse : valide l’email si ok 
            # sinon envoi une erreur

            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'info': 'registration mail has been sent'})
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
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
