
#### Business execption 

# exceptions are raised for business purposes with the 422 error code

BUSINESS_EXCEPTION_STATUS_CODE = 422

class BusinessException(Exception) : 
    def __init__(self,type:str, status_code:int = BUSINESS_EXCEPTION_STATUS_CODE) -> None:
        super().__init__()
        self.type = type
        self.status_code = status_code   
        
    
    def get_description(self, lang: str = "en") -> str:
        return "No description for business exception"


class NotEnoughCreditException(BusinessException) : 
    def __init__(self, credits_needed:int, credits_left:int) -> None:
        super().__init__("NotEnoughCredit")
        self.credits_needed = credits_needed
        self.credits_left = credits_left
        
    def get_description(self, lang: str = "en") -> str:
        return f"not enough credits : {self.credits_needed} needed but {self.credits_left} left"
    
class InvalidFrontKeyException(BusinessException) : 
    def __init__(self, email) -> None:
        super().__init__("InvalidFrontKey")
        self.email = email
        
    def get_description(self, lang: str = "en") -> str:
        return f"Your email {self.email} has not been confirmed and associated with for the tool you are using."

class InvalidEmailValidationKeyException(BusinessException) : 
    def __init__(self, validation_key) -> None:
        super().__init__("InvalidEmailValidationKey")
        self.validation_key = validation_key
        
    def get_description(self, lang: str = "en") -> str:
        return f"Your validation key is outdated. Please validate your email again with the browser extension."
          
class TooManyRequestException(BusinessException) :
    def __init__(self) -> None:
        super().__init__("TooManyRequest")
        
    def get_description(self, lang: str = "en") -> str:
        return f"You made too many request in a few time. Please wait for a while then try again."