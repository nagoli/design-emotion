
from utils.helpers import logger


TECH_CONFIG = {
    "redis_host": "crisp-moray-17911.upstash.io",
    "redis_port": "6379",
    "dynamodb_id_table": "design_emotion_id",
    "dynamodb_region": "eu-west-3",
    "secret_name": "openai-key",
    "aws_region": "eu-west-3",
    "moderation-checker-main": "openai",
    "moderation-checker-secondary": "openrouter",
    "openrouter_url": "https://openrouter.ai/api/v1",
}

BUSINESS_CONFIG = {
    "id_cache_limit": 240,
    "transcript_cache_limit": 60*60*24*15,
    "email_validation_limit": 60*60*24,
    "ip_limit": 120
}
 
LLM_VARIABLES = {
    "gpt4o": {
      "api":   "openai",
      "model": "gpt-4o",
      "prompts": {
        "transcript": """Analyse cette image de site web en te concentrant sur les émotions et l’ambiance générale véhiculées par la structure, les couleurs, et les éléments graphiques. Ignore le contenu textuel sauf s’il contribue directement à l’émotion. Traduis ces émotions en une expérience sensorielle et intellectuelle pour une personne aveugle, en utilisant des références au toucher, au son, aux odeurs, au goût, ou à des concepts abstraits. Par exemple, décris une ambiance comme une sensation de texture douce et chaleureuse, un bruit apaisant ou stimulant, ou une odeur évoquant une atmosphère spécifique. Ne fais aucune référence explicite aux aspects visuels ou à la disposition graphique. Ne soit pas trop ambiance publicité. essaie de faire vivre l’émotion sans enjoliver. Commence par Ce site …
        Fait ce transcript dans la langue : {target_lang}""",
        
        "translate":  "Translate from {source_lang} to {target_lang}. If it is the same language, just return the given text with no additional comment. If you translate, just return the translation.",
        
        "moderated":  "Analyse cette image de site web en te concentrant sur les émotions… (même que transcript)"
      },
    },
    
    "gpt4.1-or": {
      "api":   "openrouter",
      "model": "openai/gpt-4.1",
      "prompts": {
        "transcript": """Analyse cette image de site web en te concentrant sur les émotions et l’ambiance générale véhiculées par la structure, les couleurs, et les éléments graphiques. Ignore le contenu textuel sauf s’il contribue directement à l’émotion. Traduis ces émotions en une expérience sensorielle et intellectuelle pour une personne aveugle, en utilisant des références au toucher, au son, aux odeurs, au goût, ou à des concepts abstraits. Par exemple, décris une ambiance comme une sensation de texture douce et chaleureuse, un bruit apaisant ou stimulant, ou une odeur évoquant une atmosphère spécifique. Ne fais aucune référence explicite aux aspects visuels ou à la disposition graphique et ne prend pas en compte les publicité qui semble hors contexte. 
Pose toi d’abord la question de l’emotion que le designer a voulu faire passer sur ce site. Voit à quelles situations de la vie peut amener des  ambiance similaires et comment les autres sens que le visuels peuvent capter ce type d’émotion. 

Sélectionne l ambiance et 1 ou 2 sens le plus pertinent pour cette situation

Retranscrit cette émotion de façon compacte (entre 400 et 500 caracteres) 
Essaie de faire vivre l’émotion sans enjoliver. 

Commence par Ce site …

Fait ce transcript dans la langue : {target_lang}""",
        "translate":  None,
        "moderated":  None
      }
    }
}

LLM_CONFIG_WITH_VARIABLES = {
  "transcript": {
    "main":      "$$gpt4.1-or/transcript",
    "secondary": "$$gpt4o/transcript"
  },

  "translate": {
    "main":      "$$gpt4o/translate",
    "secondary": "$$gpt4.1-or/translate"
  },

  "moderated": {
    "main":      "$$gpt4o/moderated",
    "secondary": "$$gpt4.1-or/moderated"
  }
} 

def resolve_llm_config(variables, config):
    """
    Replace each "$$modelX/promptY" in config by a dict:
      {
        "api":   variables[modelX]["api"],
        "model": variables[modelX]["model"],
        "prompt": variables[modelX]["prompts"][promptY]
      }
    """
    def resolve_entry(ref: str):
        # On s'attend à une string de la forme "$$modelX/promptY"
        if not isinstance(ref, str) or not ref.startswith("$$"):
            raise ValueError(f"Reference invalide: {ref}")
        model_key, prompt_key = ref[2:].split("/", 1)
        model_def = variables[model_key]
        prompt_text = model_def["prompts"][prompt_key]
        return {
            "api":    model_def["api"],
            "model":  model_def["model"],
            "prompt": prompt_text
        }

    resolved = {}
    for block_name, block in config.items():
        resolved_block = {}
        for role, ref in block.items():  # role = "main" ou "secondary"
            resolved_block[role] = resolve_entry(ref)
        resolved[block_name] = resolved_block
    
    logger.info("LLM config resolved")
    return resolved

# Utilisation
LLM_CONFIG = resolve_llm_config(LLM_VARIABLES, LLM_CONFIG_WITH_VARIABLES)
