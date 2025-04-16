// Inclusion de la configuration par défaut
import { DEFAULT_SERVER_URL } from "./config.js";

// Configuration du debugging
const LOG_SCREENSHOTS = false;  // Mettre à true pour sauvegarder les captures d'écran en PNG

// Add this at the top of your background.js and other scripts
const browser = chrome || window.browser;

// Obtention de la langue du navigateur
const browserLang = browser.i18n.getUILanguage();

/**
 * 
 * 
 * GESTION CHARGEMENT CONTENT SCRIPT
 * 
 */


// Variable pour suivre les onglets où le content script a été injecté
const injectedTabs = new Set();

/**
 * Vérifie si le content script est chargé dans l'onglet spécifié et l'injecte si nécessaire
 * @param {number} tabId - ID de l'onglet à vérifier
 * @returns {Promise<boolean>} - Promise résolue avec true si le content script est chargé
 */
async function ensureContentScriptLoaded(tabId) {
  // Si nous savons déjà que le script a été injecté, pas besoin de vérifier
  if (injectedTabs.has(tabId)) {
    return true;
  }

  try {
    // Essayer d'envoyer un message ping pour vérifier si le content script est chargé car il n est pas chargé directement si le plugin n est pas actif au moment du chargement de la page 
    await browser.tabs.sendMessage(tabId, { action: 'ping' });
    injectedTabs.add(tabId);
    return true;
  } catch (error) {
    // Le content script n'est pas chargé, l'injecter manuellement
    try {
      console.log('Injecting content script into tab:', tabId);
      await browser.scripting.executeScript({
        target: { tabId },
        files: ['content-script.js']
      });
      
      // Injecter également le CSS
      await browser.scripting.insertCSS({
        target: { tabId },
        files: ['content-script.css']
      });
      
      // Attendre un court instant pour que le script se charge complètement
      await new Promise(resolve => setTimeout(resolve, 100));
      
      injectedTabs.add(tabId);
      return true;
    } catch (injectError) {
      console.error('Erreur lors de l\'injection du content script:', injectError);
      return false;
    }
  }
}

// Nettoyer la liste des onglets injectés lorsqu'un onglet est fermé
browser.tabs.onRemoved.addListener((tabId) => {
  injectedTabs.delete(tabId);
});



/**
 * 
 * 
 * INTERACTION AVEC CONTENT SCRIPT
 * 
 * */


console.log('🌐 Browser language:', browserLang);



/**
 * Initialise l'interface utilisateur dans l'onglet spécifié
 * @param {number} tabId - ID de l'onglet où initialiser l'interface utilisateur
 */
async function initUI(tabId ) {
  try{
    await browser.tabs.sendMessage(tabId, {
      action: 'initUI'
    });
  } catch (error) {
    console.error('Erreur lors de l\'initialisation de l\'interface utilisateur:', error);
  }
}

/**
 * Met à jour le message de chargement
 * @param {number} tabId - ID de l'onglet où mettre à jour le message
 * @param {string} message - Le message à afficher
 */
async function updateLoadingMessage(tabId, message) {
  try {
    await browser.tabs.sendMessage(tabId, {
      action: 'updateLoadingMessage',
      message: message
    });
  } catch (error) {
    console.error('Erreur lors de la mise à jour du message de chargement:', error);
  }
}

/**
 * Met à jour le message d'erreur
 * @param {number} tabId - ID de l'onglet où mettre à jour le message
 * @param {string} message - Le message à afficher
 */
async function updateErrorMessage(tabId, message) {
  try {
    await browser.tabs.sendMessage(tabId, {
      action: 'updateErrorMessage',
      message: message
    });
  } catch (error) {
    console.error('Erreur lors de la mise à jour du message d\'erreur:', error);
  }
}


async function setTranscript(tabId, transcript) {
  try {
    await browser.tabs.sendMessage(tabId, {
      action: 'setTranscript',
      transcript: transcript
    });
  } catch (error) {
    console.error('Erreur lors de la mise à jour du transcript:', error);
  }
}



/**
 * 
 * 
 * MOTEUR DE TRANSCRIPTION
 * 
 * */


// Fonction utilitaire pour promisifier les fonctions callback-based
const promisify = (fn, ...args) =>
  new Promise((resolve, reject) => {
    fn(...args, (result) => {
      if (browser.runtime.lastError) {
        reject(new Error(browser.runtime.lastError));
      } else {
        resolve(result);
      }
    });
  });



/**
 * Fonction principale qui déclenche le processus de transcription
 */
async function triggerTranscript() {
  console.log("Design emotion appelé")
  


  const langMap = {
    'fr': 'french',
    'en': 'english',
    'es': 'spanish',
    'de': 'german',
    'it': 'italian',
    'pt': 'portuguese',
    'ru': 'russian',
    'ja': 'japanese',
    'zh': 'chinese',
    'ko': 'korean',
    'ar': 'arabic',
    'hi': 'hindi'
  };

  // Convertir le code de langue au format BCP 47
  const longLang = langMap[browserLang.toLowerCase()] || 'english';
  
   
  try {
    // Récupérer le serverUrl depuis le stockage
    const data = await promisify(browser.storage.sync.get, "serverUrl");
    const serverUrl = data.serverUrl || DEFAULT_SERVER_URL;

    // Obtenir l'onglet actif
    const tabs = await promisify(browser.tabs.query, { active: true, currentWindow: true });
    if (!tabs || !tabs.length) {
      return;
    }
    
    const activeTab = tabs[0];
    const pageUrl = activeTab.url;

    // S'assurer que le content script est chargé
    await ensureContentScriptLoaded(activeTab.id);

    // Initialiser l'UI
    await initUI(activeTab.id);

    // Mettre à jour le message de chargement
    updateLoadingMessage(activeTab.id, browser.i18n.getMessage('analyzing_message'));

    // Récupére les infos de la page
    const results = await new Promise((resolve, reject) => {
      browser.scripting.executeScript({
        target: { tabId: activeTab.id },
        func: () => ({
          etag: document.querySelector('meta[http-equiv="etag"]') ?
                  document.querySelector('meta[http-equiv="etag"]').content : "",
          lastModified: document.lastModified
        })
      }, (results) => {
        if (browser.runtime.lastError || !results || !results[0]) {
          reject(new Error("Erreur lors de l'exécution du script dans la page."));
        } else {
          resolve(results[0].result);
        }
      });
    });

    // Construire le payload à envoyer
    const payload = {
      url: pageUrl,
      etag: results.etag,
      lastmodifieddate: results.lastModified,
      lang: longLang
    };

    console.log('🌐 Sending POST to /transcript:', {
      url: `${serverUrl}/transcript`,
      payload
    });

    // Effectuer l'appel POST vers le serveur
    const response = await fetch(`${serverUrl}/transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const postData = await response.json();
    console.log('📦 /transcript Response Data:', postData);

    // Traiter la réponse du serveur
    if (postData.known === 1 && postData.transcript) {
      // Si le transcript est déjà connu, mettre à jour le message et le vocaliser directement
      updateLoadingMessage(activeTab.id, browser.i18n.getMessage('transcript_ready_message'));
      // Petite pause avant de vocaliser le transcript
      setTimeout(() => {
        setTranscript(activeTab.id, postData.transcript);
      }, 3000);
    } else if (postData.known === 0 && postData.id) {
      // Sinon, mettre à jour le message d’attente et  capturer un screenshot et l'envoyer au serveur
      updateLoadingMessage(activeTab.id, browser.i18n.getMessage('analyzing_message2'));
      processScreenshotWithModifiedOpacity(activeTab, postData.id, serverUrl);
    } else {
      updateErrorMessage(activeTab.id, browser.i18n.getMessage('error_message'));
    }
  } catch (err) {
    console.error("❗ Erreur lors de l'exécution du script:", err);
    try {
      const tabs = await promisify(browser.tabs.query, { active: true, currentWindow: true });
      if (tabs && tabs.length) {
        updateErrorMessage(tabs[0].id, browser.i18n.getMessage('error_message'));
      }
    } catch (e) {
      console.error("❗ Erreur lors de la mise à jour du message d’erreur dans l'UI:", e);
    }
  }
}



/**
 * 
 * GESTION DES LISTENERS POPUP ou RACCOURCI CLAVIER
 * 
 */


// Écoute du raccourci clavier défini dans manifest.json
browser.commands.onCommand.addListener((command) => {
  if (command === "trigger-transcript") {
    triggerTranscript();
  }
});

// Écoute des messages provenant de la popup
browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "triggerTranscript") {
    triggerTranscript();
  } else if (msg.action === "openSettings") {
    // Gestion spécifique pour Firefox - ouvrir les paramètres d'extension
    if (navigator.userAgent.indexOf("Firefox") !== -1) {
      // Ouvrir la page de gestion des extensions de Firefox
      try {
        // Méthode 1: Tenter d'ouvrir directement la page des paramètres
        browser.runtime.openOptionsPage().catch(error => {
          console.log("Impossible d'ouvrir les options, essai alternatif:", error);
          
          // Méthode 2: Ouvrir la page de gestion des modules complémentaires
          browser.management.getSelf().then(selfInfo => {
            browser.tabs.create({
              url: `https://support.mozilla.org/kb/manage-extension-shortcuts-firefox`
            });
          }).catch(err => {
            console.error("Impossible d'ouvrir les paramètres de l'extension:", err);
          });
        });
      } catch (error) {
        console.error("Erreur lors de la tentative d'ouverture des paramètres:", error);
        // Méthode 3: En dernier recours, ouvrir la page d'aide de Firefox
        browser.tabs.create({
          url: `https://support.mozilla.org/kb/keyboard-shortcuts-perform-firefox-tasks-quickly`
        });
      }
    }
  }
});



/**
 * 
 * GESTION SCREENSHOT
 * 
 */



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
  browser.scripting.executeScript({
    target: { tabId: activeTab.id },
    func: modifyFixedElementsOpacity
  }, () => {
    browser.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
      if (browser.runtime.lastError || !dataUrl) {
        console.error("Erreur lors de la capture d'écran:", browser.runtime.lastError);
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
  browser.scripting.executeScript({
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
          speakInTab(activeTab.id, data2.transcript, browserLang, true);
        }
      })
      .catch(err => {
        console.error("❗ Erreur lors du POST image-transcript:", err);
        updateLoadingMessage(activeTab.id, locStrings.error_message);
        setLiveRegion(activeTab.id, locStrings.error_message);
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
      browser.downloads.download({
        url: reader.result,
        filename: filename,
        saveAs: false
      });
    };
  } catch (error) {
    console.error('Erreur lors de la conversion en PNG:', error);
  }
}