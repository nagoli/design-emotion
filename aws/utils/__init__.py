"""
Fonctions utilitaires pour l'application de transcription de design.
"""

from utils.auth import _get_keys
from utils.helpers import get_current_date, logger_business, logger_tech
from utils.config import TECH_CONFIG, BUSINESS_CONFIG, LLM_CONFIG

from utils.exceptions import BUSINESS_EXCEPTION_STATUS_CODE, BusinessException, NotEnoughCreditException, InvalidFrontKeyException, InvalidEmailValidationKeyException