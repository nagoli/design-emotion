#!/bin/bash

# Vérifie qu'un paramètre est passé
if [ -z "$1" ]; then
  echo "Usage: $0 {transcript|transcript-image|cache|clear|clear-key}"
  exit 1
fi

uri="nqeyedpmyc.execute-api.eu-west-3.amazonaws.com/dev"

case "$1" in

  transcript)
    echo "Exécution de la commande transcript..."
    curl -X POST https://$uri/transcript \
      -H "Content-Type: application/json" \
      -d '{"url": "https://respiration-yoga.fr", "etag": "3260-6212906e91527-br", "lastmodifieddate": "Sat, 25 Jan 2025 12:00:00 GMT", "lang": "french"}'
    ;;

  transcript-image)
    echo "Exécution de la commande transcript-image..."
    curl -X POST https://$uri/image-transcript \
      -H "Content-Type: application/json" \
      --data-binary @../aws-test/test2_request.json
    ;;

  cache)
    echo "Exécution de la commande cache..."
    curl -X GET "https://$uri/cache/get" -H "x-api-key: YOUR_API_KEY"
    ;;

  clear)
    echo "Exécution de la commande cache..."
    curl -X DELETE "https://$uri/cache/clear"
    ;;

  clear-key)
    echo "Exécution de la commande cache..."
    curl -X DELETE "https://$uri/cache/clear?key=transcript_cache:https://respiration-yoga.fr/"
    ;;

  *)
    echo "Paramètre non reconnu : $1"
    echo "Usage: $0 {transcript|transcript-image|cache|clear|clear-key}"
    exit 1
    ;;
esac