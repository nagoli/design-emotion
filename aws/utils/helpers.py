"""
Fonctions utilitaires diverses.
"""
import logging
import json
import sys
from datetime import datetime


def get_location(lambda_event):
    """
    Renvoie la localisation de l'utilisateur (pays et ville) de manière sécurisée.
    Si une valeur ne peut être lue, elle est remplacée par une chaîne vide.
    """
    country = ""
    city = ""
    try:
        # Accès sécurisé aux en-têtes, qui sont en minuscules dans l'événement Lambda@Edge
        headers = lambda_event['Records'][0]['cf']['request']['headers']

        # Lecture du pays
        country_header = headers.get('cloudfront-viewer-country-name', [])
        if country_header:
            country = country_header[0].get('value', '')

        # Lecture de la ville
        city_header = headers.get('cloudfront-viewer-city', [])
        if city_header:
            city = city_header[0].get('value', '')

    except (KeyError, IndexError):
        # En cas de structure d'événement inattendue, les valeurs restent des chaînes vides.
        pass

    return country, city


def get_current_date():
    """
    Renvoie la date en cours sous la forme '%Y-%m-%d %H:%M:%S'
    """
    return datetime.now().isoformat() + "Z"




class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage()
        }
        return json.dumps(log_record)





import logging
import sys
import json
from datetime import datetime

# --- Formatter JSON commun ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage()
        }

        # Ajout des champs métier si présents
        for key in ["action", "email", "url", "credits", "status"]:
            if hasattr(record, key):
                log_record[key] = getattr(record, key)

        return json.dumps(log_record)

# --- Initialisation unique (à appeler dans chaque lambda) ---
def get_logger_tech():
    logger_tech = logging.getLogger("tech")
    
    # Logger technique
    if not logger_tech.handlers:
        handler_tech = logging.StreamHandler(sys.stdout)
        handler_tech.setLevel(logging.INFO)
        handler_tech.setFormatter(JsonFormatter())
        logger_tech.setLevel(logging.INFO)
        logger_tech.addHandler(handler_tech)

    return logger_tech

def get_logger_business():
    logger_business = logging.getLogger("business")

    # Logger métier
    if not logger_business.handlers:
        handler_business = logging.StreamHandler(sys.stdout)
        handler_business.setLevel(logging.INFO)
        handler_business.setFormatter(JsonFormatter())
        logger_business.setLevel(logging.INFO)
        logger_business.addHandler(handler_business)

    return logger_business

class LoggerBusiness:
    def __init__(self):
        self._logger = get_logger_business()
    
    # action, status, url, lang, email, credits, client_type, client_key
    def log(self, lambda_event, action, status, url, lang, email, credits, client_type, client_key):
        """
        Enregistre un log métier avec les attributs spécifiques fournis.
        
        Args:
            lambda_event (dict): Event de la lambda
            action (str): Action effectuée
            status (str): Statut de l'opération ()
            url (str): URL concernée
            lang (str): Langue de l'utilisateur
            email (str): Email de l'utilisateur
            credits (int): Nombre de crédits
            client_type (str): Type de client
            client_key (str): Clé du client
        """
        country, city = get_location(lambda_event)
        
        # Utilisation directe de l'argument extra du logger
        # Ces champs seront ajoutés au JSON par JsonFormatter
        extra = {
            'action': action,
            'status': status,
            'url': url,
            'lang': lang,
            'email': email,
            'credits': credits,
            'client_type': client_type,
            'client_key': client_key,
            'country': country,
            'city': city
        }
        
        # Utilisation de la méthode info standard avec l'argument extra
        self._logger.info("", extra=extra)
 
logger_tech = get_logger_tech()
logger_business = LoggerBusiness()