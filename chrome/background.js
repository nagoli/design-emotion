// Inclusion de la configuration par défaut
importScripts("config.js");

// Configuration du debugging
const LOG_SCREENSHOTS = true;  // Mettre à true pour sauvegarder les captures d'écran en PNG

/**
 * Fonction principale qui déclenche le processus de transcription
 */
function triggerTranscript() {
    console.log("Design emotion appelé")
  chrome.storage.sync.get("serverUrl", (data) => {
    const serverUrl = data.serverUrl || DEFAULT_SERVER_URL;
    // Récupère l'onglet actif
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs.length) return;
      const activeTab = tabs[0];
      const pageUrl = activeTab.url;

      // Injection de script dans l'onglet actif pour récupérer d'autres infos de la page
      // Récupérer les infos de la page et la langue du navigateur
      const browserLang = chrome.i18n.getUILanguage();
      console.log('🌐 Browser language:', browserLang);
      
      chrome.scripting.executeScript({
        target: { tabId: activeTab.id },
        func: () => {
          return {
            etag: document.querySelector('meta[http-equiv="etag"]')
                  ? document.querySelector('meta[http-equiv="etag"]').content
                  : "",
            lastModified: document.lastModified
          };
        }
      }, (results) => {
        if (chrome.runtime.lastError || !results || !results[0]) {
          console.error("Erreur lors de l'exécution du script dans la page.");
          return;
        }
        const pageInfo = results[0].result;
        const payload = {
          url: pageUrl,
          etag: pageInfo.etag,
          lastmodifieddate: pageInfo.lastModified,
          lang: browserLang
        };

        // Envoie du POST pour récupérer le statut known et éventuellement un id
        console.log('🌐 Sending POST to /transcript:', {
          url: `${serverUrl}/transcript`,
          payload
        });
        fetch(`${serverUrl}/transcript`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
          console.log('📦 /transcript Response Data:', data);
          if (data.known === 1 && data.transcript) {
            // Si le transcript est déjà connu, le vocaliser directement
            console.log('🔊 Speaking in tab:', data.transcript);
            speakInTab(activeTab.id, data.transcript, browserLang);
          } else if (data.known === 0 && data.id) {
            // Sinon, capture un screenshot et envoie-le au serveur
            chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
              if (chrome.runtime.lastError || !dataUrl) {
                console.error("Erreur lors de la capture d'écran:", chrome.runtime.lastError);
                return;
              }
              cropImage(dataUrl, 1024).then((croppedDataUrl) => {
                // Clean the base64 string
                const cleanedBase64 = cleanBase64String(croppedDataUrl);
                
                if (LOG_SCREENSHOTS) {
                  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                  saveBase64AsPNG(cleanedBase64, `debug-image-${timestamp}.png`);
                  console.log('📸 Debug image saved:', `debug-image-${timestamp}.png`);
                }

                console.log('🌐 Sending POST to /image-transcript:', {
                  url: `${serverUrl}/image-transcript`,
                  id: data.id,
                  imageSize: cleanedBase64.length
                });
                fetch(`${serverUrl}/image-transcript`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    id: data.id,
                    image: cleanedBase64
                  })
                })
                .then(response => {
                  console.log('📥 /image-transcript Response Headers:', {
                    status: response.status,
                    headers: Object.fromEntries(response.headers.entries())
                  });
                  return response.json();
                })
                .then(data2 => {
                  console.log('📦 /image-transcript Response Data:', data2);
                  if (data2.transcript) {
                    console.log('🔊 Speaking in tab:', data2.transcript);
                    speakInTab(activeTab.id, data2.transcript, browserLang);
                  }
                })
                .catch(err => {
                  console.error("❌ Erreur lors du POST image-transcript:", err);
                  // Log additional error details if available
                  if (err instanceof Error) {
                    console.error('Error details:', {
                      message: err.message,
                      stack: err.stack
                    });
                  }
                });
              })
              .catch(err => console.error("Erreur lors du recadrage de l'image:", err));
            });
          }
        })
        .catch(err => {
          console.error("❌ Erreur lors du POST transcript:", err);
          // Log additional error details if available
          if (err instanceof Error) {
            console.error('Error details:', {
              message: err.message,
              stack: err.stack
            });
          }
        });
      });
    });
  });
}

// Écoute du raccourci clavier défini dans manifest.json
chrome.commands.onCommand.addListener((command) => {
  if (command === "trigger-transcript") {
    triggerTranscript();
  }
});

// Écoute des messages provenant de la popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "triggerTranscript") {
    triggerTranscript();
  }
});

/**
 * Injecte dans l'onglet actif un script pour vocaliser le texte via l'API speechSynthesis.
 */
function speakInTab(tabId, text, lang) {
  // Map des codes de langue aux voix disponibles
  const langMap = {
    'fr': 'fr-FR',
    'french': 'fr-FR',
    'en': 'en-US',
    'english': 'en-US',
    'es': 'es-ES',
    'spanish': 'es-ES',
    'de': 'de-DE',
    'german': 'de-DE'
  };

  // Convertir le code de langue au format BCP 47
  const bcp47Lang = langMap[lang.toLowerCase()] || 'en-US';

  chrome.scripting.executeScript({
    target: { tabId },
    func: (txt, speechLang) => {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(txt);
      utterance.lang = speechLang;
      
      // Trouver la meilleure voix disponible pour cette langue
      const voices = window.speechSynthesis.getVoices();
      const voice = voices.find(v => v.lang.startsWith(speechLang.split('-')[0])) || voices[0];
      if (voice) {
        utterance.voice = voice;
      }
      
      window.speechSynthesis.speak(utterance);
    },
    args: [text, bcp47Lang]
  });
}

/**
 * Recadre une image (au format dataURL) aux premiers `maxHeight` pixels.
 * @param {string} dataUrl - L'image au format base64.
 * @param {number} maxHeight - Hauteur maximale souhaitée.
 * @returns {Promise<string>} - L'image recadrée au format dataURL.
 */
async function cropImage(dataUrl, maxHeight) {
  const response = await fetch(dataUrl);
  const blob = await response.blob();
  const imageBitmap = await createImageBitmap(blob);
  const width = imageBitmap.width;
  const height = Math.min(imageBitmap.height, maxHeight);

  const offscreen = new OffscreenCanvas(width, height);
  const ctx = offscreen.getContext("2d");
  ctx.drawImage(imageBitmap, 0, 0, width, height, 0, 0, width, height);
  const croppedBlob = await offscreen.convertToBlob();
  return blobToDataURL(croppedBlob);
}

/**
 * Convertit un Blob en dataURL.
 * @param {Blob} blob 
 * @returns {Promise<string>}
 */
function blobToDataURL(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Convertit une image base64 en PNG et la sauvegarde
 * @param {string} base64Data - L'image en base64 (avec ou sans le préfixe data:image)
 * @param {string} filename - Le nom du fichier de sortie
 */
function cleanBase64String(base64Data) {
  // Remove data URL prefix if present
  let cleaned = base64Data.replace(/^data:image\/[a-z]+;base64,/, '');
  
  // Remove any whitespace
  cleaned = cleaned.replace(/\s/g, '');
  
  // Ensure string length is valid for base64 (multiple of 4)
  const padding = cleaned.length % 4;
  if (padding) {
    cleaned += '='.repeat(4 - padding);
  }
  
  return cleaned;
}

async function saveBase64AsPNG(base64Data, filename) {
  try {
    // Convert base64 to binary
    const byteString = atob(base64Data);
    const arrayBuffer = new ArrayBuffer(byteString.length);
    const uint8Array = new Uint8Array(arrayBuffer);
    
    for (let i = 0; i < byteString.length; i++) {
      uint8Array[i] = byteString.charCodeAt(i);
    }
    
    // Create PNG blob
    const blob = new Blob([uint8Array], { type: 'image/png' });
    
    // Convert to data URL and download
    const reader = new FileReader();
    reader.readAsDataURL(blob);
    reader.onloadend = () => {
      chrome.downloads.download({
        url: reader.result,
        filename: filename,
        saveAs: false
      });
    };
  } catch (error) {
    console.error('Erreur lors de la conversion en PNG:', error);
  }
}