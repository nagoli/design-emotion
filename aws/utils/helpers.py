"""
Fonctions utilitaires diverses.
"""
import logging
import datetime

def get_current_date():
    """
    Renvoie la date en cours sous la forme '%Y-%m-%d %H:%M:%S'
    """
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')



logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
 