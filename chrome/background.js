// Inclusion de la configuration par défaut
importScripts("config.js");

// Configuration du debugging
const LOG_SCREENSHOTS = false;  // Mettre à true pour sauvegarder les captures d'écran en PNG

const browserLang = chrome.i18n.getUILanguage();
console.log('🌐 Browser language:', browserLang);

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
            speakInTab(activeTab.id, data.transcript, browserLang);
          } else if (data.known === 0 && data.id) {
            // Sinon, capture un screenshot et envoie-le au serveur
            processScreenshotWithModifiedOpacity(activeTab, data.id, serverUrl);
          }
        })
        .catch(err => {
          console.error("❗ Erreur lors du POST transcript:", err);
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
 * Modifie l'opacité des éléments fixes dans la page.
 */
function modifyFixedElementsOpacity() {
  const shift = 30; // Margin to define corners
  window._originalOpacities = new Map();
  
  const allElements = document.querySelectorAll('*');
  Array.from(allElements).forEach(element => {
    const style = window.getComputedStyle(element);
    if (style.position === 'fixed') {
      const rect = element.getBoundingClientRect();
      const inCorner = (
        (rect.top < shift && rect.left < shift && rect.height < window.innerHeight - (2 * shift)) ||  // Top-left corner
        (rect.top < shift && rect.right > window.innerWidth - shift && rect.height < window.innerHeight - (2 * shift)) ||  // Top-right corner
        (rect.bottom > window.innerHeight - shift && rect.right > window.innerWidth - shift && rect.width < window.innerWidth - (2 * shift))  // Bottom-right corner
      );
      if (!inCorner) {
        window._originalOpacities.set(element, element.style.opacity);
        element.style.opacity = 0.3;
      }
    }
  });
}

/**
 * Restaure l'opacité originale des éléments modifiés.
 */
function restoreOriginalOpacity() {
  if (window._originalOpacities) {
    window._originalOpacities.forEach((opacity, element) => {
      element.style.opacity = opacity;
    });
    delete window._originalOpacities;
  }
}

/**
 * Capture un screenshot avec les opacités modifiées.
 */
function processScreenshotWithModifiedOpacity(activeTab, id, serverUrl) {
  chrome.scripting.executeScript({
    target: { tabId: activeTab.id },
    func: modifyFixedElementsOpacity
  }, () => {
    chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
      if (chrome.runtime.lastError || !dataUrl) {
        console.error("Erreur lors de la capture d'écran:", chrome.runtime.lastError);
        return;
      }
      
      // Restaurer l'opacité originale et traiter l'image
      restoreOpacityAndProcessImage(activeTab, dataUrl, serverUrl, id);
    });
  });
}

/**
 * Restaure l'opacité originale et traite l'image capturée.
 */
function restoreOpacityAndProcessImage(activeTab, dataUrl, serverUrl, id) {
  chrome.scripting.executeScript({
    target: { tabId: activeTab.id },
    func: restoreOriginalOpacity
  }, () => {
    cropImage(dataUrl, 1024).then((croppedDataUrl) => {
      const cleanedBase64 = cleanBase64String(croppedDataUrl);
      
      if (LOG_SCREENSHOTS) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        saveBase64AsPNG(cleanedBase64, `debug-image-${timestamp}.png`);
        console.log('📸 Debug image saved:', `debug-image-${timestamp}.png`);
      }

      console.log('🌐 Sending POST to /image-transcript:', {
        url: `${serverUrl}/image-transcript`,
        id: id,
        imageSize: cleanedBase64.length
      });

      fetch(`${serverUrl}/image-transcript`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: id,
          image: cleanedBase64
        })
      })
      .then(response => {
        console.log('📸 /image-transcript Response Headers:', {
          status: response.status,
          headers: Object.fromEntries(response.headers.entries())
        });
        return response.json();
      })
      .then(data2 => {
        console.log('📸 /image-transcript Response Data:', data2);
        if (data2.transcript) {
          speakInTab(activeTab.id, data2.transcript, browserLang);
        }
      })
      .catch(err => {
        console.error("❗ Erreur lors du POST image-transcript:", err);
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

/**
 * Injecte dans l'onglet actif un script pour vocaliser le texte via l'API speechSynthesis.
 */
function speakInTab(tabId, text, lang) {
  console.log("SpeakInTab called");
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
      console.log("SpeakInTab internal func called", speechLang);
      
      // Créer une région live pour les annonces
      const liveRegion = document.createElement('div');
      liveRegion.setAttribute('aria-live', 'polite');
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.style.position = 'absolute';
      liveRegion.style.width = '1px';
      liveRegion.style.height = '1px';
      liveRegion.style.padding = '0';
      liveRegion.style.margin = '-1px';
      liveRegion.style.overflow = 'hidden';
      liveRegion.style.clip = 'rect(0, 0, 0, 0)';
      liveRegion.style.whiteSpace = 'nowrap';
      liveRegion.style.border = '0';
      document.body.appendChild(liveRegion);
      
      // Créer le bouton
      const btn = document.createElement('button');
      btn.textContent = "Click for vocalizing design emotion description : \n" + txt;
      btn.setAttribute('aria-label', 'Cliquez pour écouter la description : ' + txt);
      
      // Style pour rendre le bouton visible et accessible
      btn.style.position = "fixed";
      btn.style.top = "20px";
      btn.style.right = "20px";
      btn.style.padding = "10px 20px";
      btn.style.zIndex = "10000";
      btn.style.backgroundColor = "#007bff";
      btn.style.color = "#fff";
      btn.style.border = "none";
      btn.style.borderRadius = "5px";
      btn.style.cursor = "pointer";
      btn.style.boxShadow = "0 2px 5px rgba(0,0,0,0.2)";
      btn.style.transition = "opacity 0.3s ease";
      
      // Ajoute le bouton dans la page
      document.body.appendChild(btn);
      
      // Annonce le texte dans la région live
      liveRegion.textContent = "Design Emotion Vocalizer : " + txt;
      
      // Fermeture automatique après 15 secondes
      setTimeout(() => {
        btn.style.opacity = '0';
        setTimeout(() => {
          btn.remove();
          liveRegion.remove();
        }, 300); // Attendre la fin de la transition d'opacité
      }, 15000);
    
    // Lors du clic, déclenche la synthèse vocale
    btn.addEventListener('click', function() {
      
      // Annule toute synthèse en cours
      window.speechSynthesis.cancel();
  
      // Crée l'utterance avec le texte et la langue souhaitée
      const utterance = new SpeechSynthesisUtterance(txt);
      utterance.lang = speechLang;
  
      // Fonction pour configurer et lancer la vocalisation
      const speakWhenReady = () => {
        const voices = window.speechSynthesis.getVoices();
        // Choisit une voix correspondant à la langue si possible
        const voice = voices.find(v => v.lang.startsWith(speechLang.split('-')[0])) || voices[0];
        if (voice) {
          utterance.voice = voice;
        }
        console.log("Speaking in tab:", txt);
        window.speechSynthesis.speak(utterance);
      };
  
      // Si aucune voix n'est encore chargée, attend l'événement 'voiceschanged'
      if (window.speechSynthesis.getVoices().length === 0) {
        console.log("Waiting for voices to load...");
        window.speechSynthesis.onvoiceschanged = () => {
          speakWhenReady();
          // Nettoyage de l'écouteur pour éviter plusieurs appels
          window.speechSynthesis.onvoiceschanged = null;
        };
      } else {
        // Optionnel : laisser un petit délai après l'annulation
        setTimeout(speakWhenReady, 100);
      }
    });
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