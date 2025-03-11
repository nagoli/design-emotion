#!/bin/bash

# Vérifie qu'un paramètre est passé
if [ -z "$1" ]; then
  echo "Usage: $0 {transcript|transcript-en|transcript-image|cache|clear|clear-key}"
  exit 1
fi

uri="https://nqeyedpmyc.execute-api.eu-west-3.amazonaws.com/dev"
uri="http://localhost:3000"

case "$1" in

  transcript)
    echo "Exécution de la commande transcript..."
    curl -X POST $uri/transcript \
      -H "Content-Type: application/json" \
      -d '{"url": "https://respiration-yoga.fr", "etag": "3260-6212906e91527-br", "lastmodifieddate": "Sat, 25 Jan 2025 12:00:00 GMT", "lang": "french"}'
    ;;

  transcript-en)
    echo "Exécution de la commande transcript..."
    curl -X POST $uri/transcript \
      -H "Content-Type: application/json" \
      -d '{"url": "https://respiration-yoga.fr", "etag": "3260-6212906e91527-br", "lastmodifieddate": "Sat, 25 Jan 2025 12:00:00 GMT", "lang": "english"}'
    ;;

  transcript-fr2)
    echo "Exécution de la commande transcript..."
    curl -X POST $uri/transcript \
      -H "Content-Type: application/json" \
      -d '{"url": "https://respiration-yoga.fr", "etag": "3260-6212906e91527-br", "lastmodifieddate": "Sat, 25 Jan 2025 12:00:00 GMT", "lang": "francais"}'
    ;;



  transcript-image)
    echo "Exécution de la commande transcript-image..."
    curl -X POST $uri/image-transcript \
      -H "Content-Type: application/json" \
      --data-binary @../aws-test/test2_request.json
    ;;

  cache)
    echo "Exécution de la commande cache..."
    curl -X GET "$uri/cache/get" -H "x-api-key: YOUR_API_KEY"
    ;;

  clear)
    echo "Exécution de la commande cache..."
    curl -X DELETE "$uri/cache/clear"
    ;;

  clear-key)
    echo "Exécution de la commande cache..."
    curl -X DELETE "$uri/cache/clear?key=transcript_cache:https://respiration-yoga.fr/"
    ;;

  *)
    echo "Paramètre non reconnu : $1"
    echo "Usage: $0 {transcript|transcript-image|cache|clear|clear-key}"
    exit 1
    ;;
esac