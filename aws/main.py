

from lambdas.handlers import *
import base64


if __name__ == "__main__":
    if (False) :
        screen_shot = get_screen_shot("https://www.respiration-yoga.fr")
        #export to file
        with open("screenshot.png", "wb") as f:
            f.write(screen_shot)

    if (False) : 
        event_get = {
            "queryStringParameters": {
                "url": "https://respiration-yogae.fr/",
                "etag": "3260-6212906e91527-br",
                "lang": "french"
            }
        }   
        context = {}
        response_get = lambda_handler_transcript(event_get, context)
        print("Réponse GET :", response_get)
        
    if (True) : 
        screenshot = None
        image=None
        with open("screenshot.png") as f:
            f.read(screenshot)
        base64.encode(screenshot, image)
        event_get = {
            "queryStringParameters": {
                "id": "68f90748e770518b3171369d3edf3235",
                "image": image
            }
        }   
        context = {}
        response_get = lambda_handler_image_transcript(event_get, context)
        print("Réponse GET :", response_get)
         
    