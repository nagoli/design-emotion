"""
Module d'internationalisation pour la gestion des traductions via JSON.
"""
import os
import json
from typing import Dict, Any

# Définition des langues supportées
SUPPORTED_LANGUAGES = ['en', 'fr', 'es', 'de', 'ja', 'pt', 'ru', 'it', 'nl', 'pl', 'zh']
DEFAULT_LANGUAGE = 'en'

# Chemin vers le dossier des traductions
LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locales')

# Cache des traductions par langue
_translations: Dict[str, Dict[str, str]] = {}

# Identifiants de messages
MSG_BUSINESS_EXCEPTION = 'business_exception_generic'
MSG_NOT_ENOUGH_CREDIT = 'not_enough_credit'
MSG_INVALID_FRONT_KEY = 'invalid_front_key'
MSG_INVALID_EMAIL_KEY = 'invalid_email_key'
MSG_TOO_MANY_REQUESTS = 'too_many_requests'

def load_translations(lang: str) -> Dict[str, str]:
    """
    Charge les traductions pour une langue donnée depuis un fichier JSON.
    Si le fichier n'existe pas ou n'est pas valide, retourne un dictionnaire vide.
    """
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    # Utiliser le cache si disponible
    if lang in _translations:
        return _translations[lang]
    
    # Chemin vers le fichier de traduction
    json_file = os.path.join(LOCALE_DIR, f"{lang}.json")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        _translations[lang] = translations
        return translations
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Erreur de chargement des traductions pour {lang}: {e}")
        
        # Si la langue par défaut échoue, retourner un dict vide
        if lang != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        return {}

def getTranslatedText(msg_id: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Traduit un message identifié par son ID dans la langue spécifiée.
    Les paramètres supplémentaires sont utilisés pour le formatage.
    """
    translations = load_translations(lang)
    msg = translations.get(msg_id, msg_id)  # Fallback à l'ID si traduction absente
    
    if kwargs:
        try:
            return msg.format(**kwargs)
        except KeyError as e:
            print(f"Erreur de formatage pour {msg_id} ({lang}): {e}")
            return msg
    return msg

