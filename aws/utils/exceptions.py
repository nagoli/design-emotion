
#### Business execption 

# exceptions are raised for business purposes with the 413 error code

BUSINESS_EXCEPTION_STATUS_CODE = 413

class BusinessException(Exception) : 
    def __init__(self) -> None:
        super().__init__("")
    
    def get_description( lang : str = "en") -> str:
        return None


class NotEnoughCreditException(BusinessException) : 
    def __init__(self, credits_needed:int, credits_left:int) -> None:
        super().__init__("")
        self.credits_needed = credits_needed
        self.credits_left = credits_left
        
    def get_description(lang: str = "en") -> str:
        return f"not enough credits : {self.credits_needed} needed but {self.credits_left} left"
    
class InvalidFrontKeyException(BusinessException) : 
    def __init__(self, email) -> None:
        super().__init__("")
        self.email = email
        
    def get_description(lang: str = "en") -> str:
        return f"Your email {email} has not been confirmed and associated with for the tool you are using."
          
          
class TooManyRequestException(BusinessException) :
    