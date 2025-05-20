"""
Services de l'application de transcription de design.
"""

from services.dynamodb import (
    get_dynamodb_id_table, is_valid_front_key, add_front_key, remove_front_key,
    add_credits, use_credits, get_usage_history, get_foundings_history,
    get_usage_total, get_foundings_total, get_credits_left, get_credits_used,
    get_credits_total, test_db
)

from services.llm import (_translate_with_chatgpt, generate_design_transcript)

from services.transcript import (
    get_design_transcript, get_design_transcript_with_image,
)

from services.cache import (
    get_cached_design_transcript, create_cached_url_info,
    pop_cached_url_info, store_cached_design_transcript,checkIP,
    create_email_validation_key, get_email_validation_key
)

from services.mails import (
    send_registration_mail
)
