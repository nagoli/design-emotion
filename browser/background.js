// Inclusion de la configuration par défaut
import { DEFAULT_SERVER_URL } from "./config.js";

// Configuration du debugging
const LOG_SCREENSHOTS = false;  // Mettre à true pour sauvegarder les captures d'écran en PNG

// Add this at the top of your background.js and other scripts
const browser = chrome || window.browser;

// Obtention de la langue du navigateur
const browserLang = browser.i18n.getUILanguage();



console.log('🌐 Browser language:', browserLang);

/**
 * Affiche un spinner de chargement et met à jour les messages pour l'accessibilité
 * @returns {Object} - Un objet contenant les références aux éléments créés
 */

function initLoadingSpinner(tabId) {
  browser.scripting.executeScript({
    target: { tabId },
    func: () => {
      if (!document.querySelector('#spinner-animation-designemotionelements')) {
        const styleAnimation = document.createElement('style');
        styleAnimation.id = 'spinner-animation-designemotionelements';
        styleAnimation.textContent = `
          @keyframes spin-designemotionelements {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `;
        document.head.appendChild(styleAnimation);

        loadingContainer = document.createElement('div');
        loadingContainer.className = 'loading-container-designemotionelements';
        loadingContainer.style.position = "fixed";
        loadingContainer.style.top = "20px";
        loadingContainer.style.right = "20px";
        loadingContainer.style.padding = "10px 20px";
        loadingContainer.style.zIndex = "10000";
        loadingContainer.style.backgroundColor = "#007bff";
        loadingContainer.style.color = "#fff";
        loadingContainer.style.border = "none";
        loadingContainer.style.borderRadius = "5px";
        loadingContainer.style.boxShadow = "0 2px 5px rgba(0,0,0,0.2)";
        loadingContainer.style.transition = "opacity 0.3s ease";
        loadingContainer.style.display = "flex";
        loadingContainer.style.alignItems = "center";
        loadingContainer.style.justifyContent = "center";
        loadingContainer.display = "none"; // on ne les montre pas avant qu ils soient utilisés

        
        // Créer le spinner (visible mais caché des lecteurs d'écran)
        const spinner = document.createElement('div');
        spinner.className = 'spinner-designemotionelements';
        spinner.setAttribute('aria-hidden', 'true'); // Cacher aux lecteurs d'écran
        spinner.style.marginRight = "10px";
        spinner.style.width = "16px";
        spinner.style.height = "16px";
        spinner.style.border = "3px solid rgba(255, 255, 255, 0.3)";
        spinner.style.borderRadius = "50%";
        spinner.style.borderTop = "3px solid #fff";
        spinner.style.animation = "spin-designemotionelements 1s linear infinite";

        
        // Créer le message de chargement (visible mais caché des lecteurs d'écran)
        const loadingMessage = document.createElement('span');
        loadingMessage.className = 'loading-message-designemotionelements';
        loadingMessage.setAttribute('aria-hidden', 'true'); // Cacher aux lecteurs d'écran
        loadingMessage.style.fontFamily = "monospace";
        loadingMessage.style.fontSize = "14px";
        loadingMessage.style.fontWeight = "bold";
        
        // Assembler le conteneur de chargement
        loadingContainer.setAttribute('aria-hidden', 'true'); // Cacher aux lecteurs d'écran
        loadingContainer.appendChild(spinner);
        loadingContainer.appendChild(loadingMessage);
        document.body.appendChild(loadingContainer);
      } 
    }
  });
}


/**
 * force liveregion creation at each call (to be used when the transcript is ready)
 * @param {*} tabId 
 * @param {*} txt 
 */
function setLiveRegion(tabId, txt) {
  browser.scripting.executeScript({
    target: { tabId },
    func: (txt) => {
      let liveRegion = document.getElementById('live-region-designemotionelements');
      if (!liveRegion) {
        // Créer une région live assertive pour les annonces d'accessibilité  
        liveRegion = document.createElement('div');
      liveRegion.id = 'live-region-designemotionelements';
      liveRegion.setAttribute('aria-live', 'assertive');
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.setAttribute('role', 'alert');
      // Style pour rendre l'élément visuellement caché mais accessible aux lecteurs d'écran
      liveRegion.style.position = 'absolute';
      liveRegion.style.width = '1px';
      liveRegion.style.height = '1px';
      liveRegion.style.padding = '0';
      liveRegion.style.margin = '-1px';
      liveRegion.style.overflow = 'hidden';
      liveRegion.style.clip = 'rect(0, 0, 0, 0)';
      liveRegion.style.whiteSpace = 'nowrap';
      liveRegion.style.border = '0';
      liveRegion.style.display = 'block';
      liveRegion.textContent = '...';
      document.body.appendChild(liveRegion);
      setTimeout(() => {
        console.log('Temporize live region update ', txt);
      }, 100);
      }
      liveRegion.textContent = txt;
      console.log('Live region should vocalize', txt);
    },
    args: [txt]
  });
}


function initShowButton(tabId) {
  browser.scripting.executeScript({
    target: { tabId },
    func: () => {
      const browser = chrome || window.browser;
      // Supprimer tout spinner existant pour éviter les doublons
      const existingSpinner = document.querySelector('.loading-container-designemotionelements');
      if (existingSpinner) {
        existingSpinner.style.display = 'none';
      }  
      
      
      // Créer le bouton pour afficher le transcript (visible uniquement pour les utilisateurs voyants)
      


        const btn = document.createElement('button');
        btn.textContent = browser.i18n.getMessage('click_for_description');
        //btn.setAttribute('aria-label', txt); // Cacher aux lecteurs d'écran
        btn.className = 'design-emotion-btn-designemotionelements';
        
        // Style pour rendre le bouton visible pour les utilisateurs voyants
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
        btn.style.display = "block"; // Le bouton est visible par défaut dans cette fonction
        btn.style.fontFamily = "monospace";
        btn.style.fontSize = "14px";
        btn.style.fontWeight = "bold";
        document.body.appendChild(btn);      
    },
    args: []
  });
}


function initPopup(tabId,txt) {

  browser.scripting.executeScript({
    target: { tabId },
    func: (txt) => {
      const browser = chrome || window.browser;
        // Styles pour la pop-in (en utilisant des classes uniques pour éviter les conflits)
        const styles = document.createElement('style');
        styles.textContent = `
          .overlay-designemotionelements {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10001;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
          }
          
          .overlay-designemotionelements.active {
            opacity: 1;
            visibility: visible;
          }
          
          .popup-designemotionelements {
            background-color: rgba(0, 0, 0, 1);
            border-radius: 12px;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
            width: clamp(300px, 80%, 800px);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transform: scale(0.8);
            transition: transform 0.3s ease;
          }
          
          .overlay-designemotionelements.active .popup-designemotionelements {
            transform: scale(1);
          }
          
          .popup-header-designemotionelements {
            color: white;
            padding: 8px 16px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
          }
          
          .popup-header-designemotionelements h2 {
            margin: 0;
            color: white;
            font-size: 25px;
            font-weight: bold;
            font-family: monospace;
          }
          
          .popup-body-designemotionelements {
            border-radius: 8px;
            padding: 16px;
            color: black;
            background-color: white;
            font-family: monospace;
            font-size: 16px;
            line-height: 1.5;
            overflow-y: auto;
            margin : 0 12px;
          }
          
          .popup-footer-designemotionelements {
            color: white;
            padding: 8px 16px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
          }
          
          .popup-close-btn-designemotionelements {
            background-color: transparent;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            cursor: pointer;
            font-size: 14px;
          }
          
          .popup-close-btn-designemotionelements:hover {
            background-color: #0056b3;
          }
          
          .design-emotion-btn-designemotionelements:hover {
            background-color: #0056b3;
          }
        `;
        document.head.appendChild(styles);
        
        // Créer la structure de la pop-in avec des méthodes DOM sécurisées
        // au lieu d'utiliser innerHTML (pour éviter les risques XSS)
        
        // Créer l'overlay
        const overlay = document.createElement('div');
        overlay.className = 'overlay-designemotionelements';
        
        // Créer le popup
        const popup = document.createElement('div');
        popup.className = 'popup-designemotionelements';
        
        // Créer le header
        const popupHeader = document.createElement('div');
        popupHeader.className = 'popup-header-designemotionelements';
        const headerTitle = document.createElement('h2');
        headerTitle.textContent = browser.i18n.getMessage('popup_header');
        popupHeader.appendChild(headerTitle);
        
        // Créer le body
        const popupBody = document.createElement('div');
        popupBody.className = 'popup-body-designemotionelements';
        const bodyText = document.createElement('p');
        bodyText.textContent = txt;
        popupBody.appendChild(bodyText);
        
        // Créer le footer
        const popupFooter = document.createElement('div');
        popupFooter.className = 'popup-footer-designemotionelements';
        const closeButton = document.createElement('button');
        closeButton.className = 'popup-close-btn-designemotionelements';
        closeButton.textContent = browser.i18n.getMessage('close_button');
        popupFooter.appendChild(closeButton);
        
        // Assembler les éléments
        popup.appendChild(popupHeader);
        popup.appendChild(popupBody);
        popup.appendChild(popupFooter);
        overlay.appendChild(popup);
        
        // Ajouter au DOM
        document.body.appendChild(overlay);
    },
    args: [txt]
  });
}

function addButtonAndPopupInteractions(tabId, text, speechLang){
  browser.scripting.executeScript({
    target: { tabId },
    func: (txt, speechLang) => {
      const browser = chrome || window.browser;
      
      // Stocker l'élément actuellement focalisé pour y revenir plus tard
      const previouslyFocusedElement = document.activeElement;
      
      
      // Focus automatique sur le bouton quand il apparaît (pour les utilisateurs voyants)
      //FOCUS : btn.focus();
      
    
      
      // Récupérer les éléments de la pop-in
      const overlay = document.querySelector('.overlay-designemotionelements');
      const closeBtn = document.querySelector('.popup-close-btn-designemotionelements');
      const btn = document.querySelector('.design-emotion-btn-designemotionelements');
      
      // Fonction pour ouvrir la pop-in
      const openPopup = () => {
        overlay.classList.add('active');
        btn.remove();
        overlay.querySelector('h2').focus();
      };
      
      // Fonction pour fermer la pop-in
      const closePopup = () => {
        // Arrêter toute synthèse vocale en cours
        window.speechSynthesis.cancel();
        
        overlay.classList.remove('active');
        // Redonner le focus à l'élément précédemment focalisé
        if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
          //FOCUS : previouslyFocusedElement.focus();
        }
      };
      
      
      // Écouteurs d'événements
      btn.addEventListener('click', openPopup);
      closeBtn.addEventListener('click', closePopup);
      
      // Fermer la pop-in en cliquant en dehors
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          closePopup();
        }
      });
      
      // Pour accessibilité : fermer avec la touche Escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && overlay.classList.contains('active')) {
          closePopup();
        }
      });
      
      // Fermeture automatique après 5 secondes si pas d'interaction
      let buttonTimeout = setTimeout(() => {
        btn.style.opacity = '0';
        setTimeout(() => {
          btn.remove();
          // Ne pas retirer les régions live car elles peuvent être réutilisées
          
          // Redonner le focus à l'élément précédemment focalisé si le bouton n'a pas été activé
          if (document.activeElement === btn && previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
            //FOCUS : previouslyFocusedElement.focus();
          }
        }, 300); // Attendre la fin de la transition d'opacité
      }, 20000); // Réduit à 20 secondes pour moins encombrer l'interface
      
      // Annuler le timeout si le bouton est cliqué
      btn.addEventListener('click', () => {
        clearTimeout(buttonTimeout);
      });
    
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
    args: [text, speechLang]
  });
}


/**
 * Met à jour le message de chargement
 */
function updateLoadingMessage(tabId, message) {
  browser.scripting.executeScript({
    target: { tabId },
    func: (msg) => {
      const loadingContainer = document.querySelector('.loading-container-designemotionelements');
      if (loadingContainer) loadingContainer.style.display = 'flex';

      const loadingMessage = document.querySelector('.loading-message-designemotionelements');
      
      if (loadingMessage) loadingMessage.textContent = msg;
      
      // effacer le message après 15s
      setTimeout(() => {
        if (loadingMessage) loadingMessage.style.display = 'none';
      }, 15000);
    },
    args: [message]
  });
}

/**
 * Cache le spinner et affiche le bouton
 */
function hideSpinnerShowButton(tabId) {
  browser.scripting.executeScript({
    target: { tabId },
    func: () => {
      const browser = chrome || window.browser;

      const loadingContainer = document.querySelector('.loading-container-designemotionelements');
      if (loadingContainer) loadingContainer.style.display = 'none';
      
      const btn = document.querySelector('.design-emotion-btn-designemotionelements');
      if (btn) btn.style.display = 'block';
    },
    args: []
  });
}

/**
 * Fonction principale qui déclenche le processus de transcription
 */
function triggerTranscript() {
    console.log("Design emotion appelé")
     // Map des codes de langue aux voix disponibles
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

  browser.storage.sync.get("serverUrl", (data) => {
    const serverUrl = data.serverUrl || DEFAULT_SERVER_URL;
    // Récupère l'onglet actif
    browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs.length) return;
      const activeTab = tabs[0];
      const pageUrl = activeTab.url;
      
      // Afficher le spinner dès le début du processus
      initLoadingSpinner(activeTab.id);
      
      // Injection de script dans l'onglet actif pour récupérer d'autres infos de la page
      // Récupérer les infos de la page et la langue du navigateur
      updateLoadingMessage(activeTab.id, browser.i18n.getMessage('analyzing_message'));
      setLiveRegion(activeTab.id, browser.i18n.getMessage('analyzing_message'));
      
      browser.scripting.executeScript({
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
        if (browser.runtime.lastError || !results || !results[0]) {
          console.error("Erreur lors de l'exécution du script dans la page.");
          return;
        }
        const pageInfo = results[0].result;

        const payload = {
          url: pageUrl,
          etag: pageInfo.etag,
          lastmodifieddate: pageInfo.lastModified,
          lang: longLang
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
            // Si le transcript est déjà connu, mettre à jour le message et le vocaliser directement
            updateLoadingMessage(activeTab.id, browser.i18n.getMessage('transcript_ready_message'));
            setLiveRegion(activeTab.id, browser.i18n.getMessage('transcript_ready_message'));
            // Attendre un court instant pour montrer le message de génération
            setTimeout(() => {
              speakInTab(activeTab.id, data.transcript, browserLang, true);
            }, 3000);
          } else if (data.known === 0 && data.id) {
            // Sinon, mettre à jour le message puis capturer un screenshot et l'envoyer au serveur
            updateLoadingMessage(activeTab.id, browser.i18n.getMessage('analyzing_message2'));
            setLiveRegion(activeTab.id, browser.i18n.getMessage('analyzing_message2'));
            processScreenshotWithModifiedOpacity(activeTab, data.id, serverUrl);

          }
          else {
            // Si le transcript n'est pas connu, afficher un message d'erreur
            updateLoadingMessage(activeTab.id, browser.i18n.getMessage('error_message'));
            setLiveRegion(activeTab.id, browser.i18n.getMessage('error_message'));
          } 
        })
        .catch(err => {
          console.error("❗ Erreur lors du POST transcript:", err);
          updateLoadingMessage(activeTab.id, locStrings.error_message);
          setLiveRegion(activeTab.id, locStrings.error_message);
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
 * Injecte dans l'onglet actif un script pour vocaliser le texte via l'API speechSynthesis.
 */
function speakInTab(tabId, text, lang, skipSpinner = false) {
  console.log("SpeakInTab called");
 
  initShowButton(tabId);
  initPopup(tabId, text);
  addButtonAndPopupInteractions(tabId, text, lang);
  setLiveRegion(tabId, browser.i18n.getMessage('transcript_intro_message') +  text);
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