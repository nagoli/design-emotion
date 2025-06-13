# Log métier ( avec logger_business)
Elles sont toutes accompagnées des parametres suivants : 
action, status, url, lang, email, credits, position, client_type, client_key 

## Actions : 

### Actions liées à l’usage 
get_transcript 
translate_transcript
get_transcript_from_image

### Actions liées à l’enregistrement (url = "")
send_validation_mail
register_key_for_email (client_type = "email", client_key = "")

### Actions liées au paiement (url = "")
payment (client_type = "stripe", client_key = "")


## Status : 
200 : ok

400 : paramètres manquants

422-1 : not enough credit
422-2 : invalid front key
422-3 : invalid email key
422-4 : too many requests

500 : ko
