"""
Fonctions DynamoDB pour l'application.
"""

import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key

from utils.config import TECH_CONFIG
from utils.helpers import get_current_date, logger, NotEnoughCreditException

# -----------------------------------------------------------------------------
# DynamoDB Functions 
# Config in TECH_CONFIG 


# The dynamodb structure is as follows:
#{
#  "email": email,
#  "credits-left": creditsLeft,
#  "credits-used": creditsUsed,
#  "frontKeys": list[FrontendKeys],
#  "usage-total": accessCount,
#  "usage-history": list[(date, url, creditCost)],
#  "foundings-total": totalAmount,
#  "foundings-history": list[(date, payedAmount, credits)]
#}

# example : 
# {
#  "email": "client@example.com",
#  "credits-left": 45,
#  "credits-used": 12,
#  "frontKeys": ["key1", "key2"],
#  "usage-total": 12,
#  "usage-history": [("2025-01-01", "www.mysite.org",1)],
#  "foundings-total": 3.99,
#  "foundings-history": [("2025-01-01", "3.99","50")]
#}

# ----------------------------------------------------------------------------
DYNAMODB_ID_TABLE = None

def get_dynamodb_id_table():
    global DYNAMODB_ID_TABLE
    if DYNAMODB_ID_TABLE is None:
        dynamodb = boto3.resource('dynamodb', region_name=TECH_CONFIG['dynamodb_region'])
        DYNAMODB_ID_TABLE = dynamodb.Table(TECH_CONFIG['dynamodb_id_table'])
    return DYNAMODB_ID_TABLE

def is_valid_front_key(email: str, key: str) -> bool:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' not in response:
        return False
    
    if 'frontKeys' not in response['Item']:
        return False
    
    return key in response['Item']['frontKeys']
    
def add_front_key(email: str, key: str, tool: str) -> None:
    table = get_dynamodb_id_table()
    
    # First check if the email exists
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' not in response:
        # Create new user record if not exists
        table.put_item(
            Item={
                'email': email,
                'credits-left': 2,
                'credits-used': 0,
                'frontKeys': [key],
                'tools': [(key,tool)],
                'usage-total': 0,
                'usage-history': [],
                'foundings-total': 0.0,
                'foundings-history': []
            }
        )
    else:
        # Add key to existing user
        front_keys = response['Item'].get('frontKeys', [])
        if key not in front_keys:
            front_keys.append(key)
            table.update_item(
                Key={'email': email},
                UpdateExpression='SET frontKeys = :keys',
                ExpressionAttributeValues={':keys': front_keys}
            )

def remove_front_key(email: str, key: str) -> None:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'frontKeys' in response['Item']:
        front_keys = response['Item']['frontKeys']
        if key in front_keys:
            front_keys.remove(key)
            table.update_item(
                Key={'email': email},
                UpdateExpression='SET frontKeys = :keys',
                ExpressionAttributeValues={':keys': front_keys}
            )

def add_credits(email: str, payed_amount: float, credits: int) -> None:
    table = get_dynamodb_id_table()
    #fixe la date à la date du jour avec l'heure
    date = get_current_date()
    payed_amount = Decimal(payed_amount)
    # Check if user exists
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' not in response:
        # Create new user with credits
        table.put_item(
            Item={
                'email': email,
                'credits-left': credits,
                'credits-used': 0,
                'frontKeys': [],
                'tools': [],
                'usage-total': 0,
                'usage-history': [],
                'foundings-total': payed_amount,
                'foundings-history': [(date, str(payed_amount), str(credits))]
            }
        )
    else:
        # Update existing user
        item = response['Item']
        credits_left = item.get('credits-left', 0) + credits
        foundings_total = Decimal(item.get('foundings-total', 0)) + payed_amount
        foundings_history = item.get('foundings-history', [])
        foundings_history.append((date, str(payed_amount), str(credits)))
        
        table.update_item(
            Key={'email': email},
            UpdateExpression='SET #cl = :credits_left, #ft = :foundings_total, #fh = :foundings_history',
            ExpressionAttributeNames={
                '#cl': 'credits-left',
                '#ft': 'foundings-total',
                '#fh': 'foundings-history'
            },
            ExpressionAttributeValues={
                ':credits_left': credits_left,
                ':foundings_total': foundings_total,
                ':foundings_history': foundings_history
            }
        )

def use_credits(email: str, credits_cost: int, url: str = "test-url") -> None:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response:
        item = response['Item']
        credits_left = item.get('credits-left', 0)
        
        # Check if user has enough credits
        if credits_left >= credits_cost:
            credits_left -= credits_cost
            credits_used = item.get('credits-used', 0) + credits_cost
            usage_total = item.get('usage-total', 0) + 1
            usage_history = item.get('usage-history', [])
            date = get_current_date()
            usage_history.append((date, url, str(credits_cost)))
            
            table.update_item(
                Key={'email': email},
                UpdateExpression='SET #cl = :credits_left, #cu = :credits_used, #ut = :usage_total, #uh = :usage_history',
                ExpressionAttributeNames={
                    '#cl': 'credits-left',
                    '#cu': 'credits-used',
                    '#ut': 'usage-total',
                    '#uh': 'usage-history'
                },
                ExpressionAttributeValues={
                    ':credits_left': credits_left,
                    ':credits_used': credits_used,
                    ':usage_total': usage_total,
                    ':usage_history': usage_history
                }
            )
        else : 
            raise NotEnoughCreditException(credits_cost, credits_left)
            

def get_usage_history(email: str) -> list:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'usage-history' in response['Item']:
        return response['Item']['usage-history']
    return []

def get_foundings_history(email: str) -> list:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'foundings-history' in response['Item']:
        return response['Item']['foundings-history']
    return []

def get_usage_total(email: str) -> int:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'usage-total' in response['Item']:
        return response['Item']['usage-total']
    return 0

def get_foundings_total(email: str) -> float:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'foundings-total' in response['Item']:
        return response['Item']['foundings-total']
    return 0.0

def get_credits_left(email: str) -> int:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'credits-left' in response['Item']:
        return response['Item']['credits-left']
    return 0

def get_credits_used(email: str) -> int:
    table = get_dynamodb_id_table()
    
    response = table.get_item(
        Key={'email': email}
    )
    
    if 'Item' in response and 'credits-used' in response['Item']:
        return response['Item']['credits-used']
    return 0

def get_credits_total(email: str) -> int:
    return get_credits_left(email) + get_credits_used(email)


def test_db():
    # Test add_credits
    add_credits("olivier.motelet@gmail.com", 1.5, 2)
    logger.info(">>>> test DB : oli credit left : " + str(get_credits_left("olivier.motelet@gmail.com")))
    
    # Test use_credits
    logger.info(">>>> test DB : oli credit left after use : " + str(get_credits_left("olivier.motelet@gmail.com")))
    logger.info(">>>> test DB : oli credit used : " + str(get_credits_used("olivier.motelet@gmail.com")))
    
    # Test get_credits_total
    logger.info(">>>> test DB : oli credit total : " + str(get_credits_total("olivier.motelet@gmail.com")))
    
    # Test get_usage_history
    logger.info(">>>> test DB : oli usage history : " + str(get_usage_history("olivier.motelet@gmail.com")))
    
    # Test get_foundings_history
    logger.info(">>>> test DB : oli foundings history : " + str(get_foundings_history("olivier.motelet@gmail.com")))
    
    # Test get_usage_total
    logger.info(">>>> test DB : oli usage total : " + str(get_usage_total("olivier.motelet@gmail.com")))
    
    # Test get_foundings_total
    logger.info(">>>> test DB : oli foundings total : " + str(get_foundings_total("olivier.motelet@gmail.com")))
      
