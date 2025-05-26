"""
gestion des emails envoyés au client
"""



import boto3
from botocore.exceptions import ClientError
import json
from utils.config import TECH_CONFIG
from utils.helpers import logger


def send_registration_mail(email: str, validation_key: str):
    """
    Send a registration confirmation email with a validation link to the user.
    Uses AWS SES to deliver the email.
    
    Args:
        email: The recipient's email address
        validation_key: The validation key to verify the email
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    # Create SES client
    ses = boto3.client('ses', region_name=TECH_CONFIG["aws_region"])
    
    # Construct validation URL with the key as a query parameter
    validation_url = f"https://design-emotion.org/validate-email?validation_key={validation_key}"
    
    # Prepare email content
    subject = "Confirmez votre inscription - Design Emotion"
    html_content = f"""
    <html>
    <head></head>
    <body>
        <h1>Bienvenue sur Design Emotion!</h1>
        <p>Merci pour votre inscription. Pour valider votre adresse email, veuillez cliquer sur le lien ci-dessous:</p>
        <p><a href="{validation_url}">Valider mon email</a></p>
        <p>Si vous n'avez pas demandé cette inscription, vous pouvez ignorer cet email.</p>
        <p>L'équipe Design Emotion</p>
    </body>
    </html>
    """
    
    text_content = f"""
    Bienvenue sur Design Emotion!
    
    Merci pour votre inscription. Pour valider votre adresse email, veuillez cliquer sur le lien ci-dessous:
    
    {validation_url}
    
    Si vous n'avez pas demandé cette inscription, vous pouvez ignorer cet email.
    
    L'équipe Design Emotion
    """
    
    # Set email parameters
    email_message = {
        'Subject': {'Data': subject},
        'Body': {
            'Html': {'Data': html_content},
            'Text': {'Data': text_content}
        }
    }
    
    # Try to send the email
    try:
        response = ses.send_email(
            Source='noreply@design-emotion.org',  # Must be a verified sender in SES
            Destination={'ToAddresses': [email]},
            Message=email_message
        )
        logger.info(f"Email sent to {email}. MessageId: {response['MessageId']}")
        return True
    except ClientError as e:
        logger.error(f"Failed to send email: {e}")
        return False