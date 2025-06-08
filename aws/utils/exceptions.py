
from .i18n import getTranslatedText, MSG_BUSINESS_EXCEPTION, MSG_NOT_ENOUGH_CREDIT, MSG_INVALID_FRONT_KEY, MSG_INVALID_EMAIL_KEY, MSG_TOO_MANY_REQUESTS

#### Business exception 

# exceptions are raised for business purposes with the 422 error code

BUSINESS_EXCEPTION_STATUS_CODE = 422

class BusinessException(Exception) : 
    def __init__(self, type:str, status_code:int = BUSINESS_EXCEPTION_STATUS_CODE) -> None:
        super().__init__()
        self.type = type
        self.status_code = status_code   
    
    def get_description(self, lang: str = "en") -> str:
        return getTranslatedText(MSG_BUSINESS_EXCEPTION, lang)


class NotEnoughCreditException(BusinessException) : 
    def __init__(self, credits_needed:int, credits_left:int) -> None:
        super().__init__("NotEnoughCredit")
        self.credits_needed = credits_needed
        self.credits_left = credits_left
        
    def get_description(self, lang: str = "en") -> str:
        return getTranslatedText(MSG_NOT_ENOUGH_CREDIT, lang, needed=self.credits_needed, left=self.credits_left)
    
class InvalidFrontKeyException(BusinessException) : 
    def __init__(self, email) -> None:
        super().__init__("InvalidFrontKey")
        self.email = email
        
    def get_description(self, lang: str = "en") -> str:
        return getTranslatedText(MSG_INVALID_FRONT_KEY, lang, email=self.email)

class InvalidEmailValidationKeyException(BusinessException) : 
    def __init__(self, validation_key) -> None:
        super().__init__("InvalidEmailValidationKey")
        self.validation_key = validation_key
        
    def get_description(self, lang: str = "en") -> str:
        return getTranslatedText(MSG_INVALID_EMAIL_KEY, lang)
          
class TooManyRequestException(BusinessException) :
    def __init__(self) -> None:
        super().__init__("TooManyRequest")
        
    def get_description(self, lang: str = "en") -> str:
        return getTranslatedText(MSG_TOO_MANY_REQUESTS, lang)