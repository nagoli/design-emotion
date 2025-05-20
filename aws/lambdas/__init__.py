"""
Points d'entrée Lambda pour l'application.
"""

from lambdas.handlers import (
    get_cors_headers, lambda_handler_transcript, lambda_handler_image_transcript,
    lambda_handler_cache_get, lambda_handler_cache_clear
)
