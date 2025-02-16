#!/bin/bash

# Vérifie qu'un paramètre est passé
if [ -z "$1" ]; then
  echo "Usage: $0 {transcript|transcript-image|cache}"
  exit 1
fi

case "$1" in
  transcript)
    echo "Exécution de la commande transcript..."
    curl -X POST http://127.0.0.1:3000/transcript \
      -H "Content-Type: application/json" \
      -d '{"url": "https://respiration-yoga.fr", "etag": "3260-6212906e91527-br", "lastmodifieddate": "Sat, 25 Jan 2025 12:00:00 GMT", "lang": "french"}'
    ;;
  transcript-image)
    echo "Exécution de la commande transcript-image..."
    curl -X POST http://127.0.0.1:3000/image-transcript \
      -H "Content-Type: application/json" \
      -d "{\"id\": \"4ca040f08ecdaf45c36eaf07a8f9e0cc\", \"image\": \"$(cat aws/test2.base64)\"}"
    ;;
  cache)
    echo "Exécution de la commande cache..."
    curl -X GET "http://localhost:3000/cache" -H "x-api-key: YOUR_API_KEY"
    ;;
  *)
    echo "Paramètre non reconnu : $1"
    echo "Usage: $0 {transcript|transcript-image|cache}"
    exit 1
    ;;
esac