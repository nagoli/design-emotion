/**
 * Script de contenu pour l'extension Design Emotion Vocalizer
 * Ce script est injecté dans toutes les pages web visitées
 * et gère les interactions UI directement dans le DOM
 */

// Récupère la référence du navigateur
const browser = chrome || window.browser;

// Constantes pour les ID et classes des éléments UI
// IDs pour les conteneurs principaux
const UI_OVERLAY_ID = 'ui-overlay-designemotionelements';
const LOADING_INFO_CONTAINER_ID = 'loading-container-designemotionelements';
const LOADING_TXT_ID = 'loading-message-designemotionelements';
const VOCALIZE_BUTTON_ID = 'design-emotion-btn-designemotionelements';
const TRANSCRIPT_OVERLAY_ID = 'overlay-designemotionelements';
const TRANSCRIPT_TXT_ID = 'popup-body-designemotionelements';

const LIVE_REGION_ID = 'live-region-designemotionelements';

// Classes pour les éléments secondaires
const SPINNER_CLASS = 'spinner-designemotionelements';
const TRANSCRIPT_CLASS = 'popup-designemotionelements';
const TRANSCRIPT_HEADER_CLASS = 'popup-header-designemotionelements';
const TRANSCRIPT_FOOTER_CLASS = 'popup-footer-designemotionelements';
const TRANSCRIPT_CLOSE_BTN_CLASS = 'popup-close-btn-designemotionelements';

let transcriptText='';

/**
 * Caches un élément en modifiant sa propriété display
 * @param {string} id - ID de l'élément à cacher
 */
function hideElement(id) {
  const element = document.getElementById(id);
  if (element) {
    element.style.display = 'none';
  }
}

/**
 * Affiche un élément en modifiant sa propriété display
 * @param {string} id - ID de l'élément à afficher
 * @returns {boolean} - Retourne true si l'élément a été affiché, false sinon
 */
function showElement(id) {
  const element = document.getElementById(id);
  if (element) {
    element.style.display = 'block';
    return true;
  }
  return false; 
}

/**
 * Supprime un élément du DOM
 * @param {string} id - ID de l'élément à supprimer
 */
function removeElement(id) {
  const element = document.getElementById(id);
  if (element) {
    element.remove();
  }
}


/**
 * Nettoie les éléments existants pour éviter les doublons
 */
function cleanupElements() {
  removeElement(LIVE_REGION_ID);
  removeElement(LOADING_INFO_CONTAINER_ID);
  removeElement(VOCALIZE_BUTTON_ID);
  removeElement(TRANSCRIPT_OVERLAY_ID);
}


function createElements() {
  const htmlStructure = `
          <div id="${LIVE_REGION_ID}"
              aria-live="assertive"
              aria-atomic="true"
              role="alert">
          </div>

          <div id="${LOADING_INFO_CONTAINER_ID}" style="display: none;" aria-hidden="true" role="presentation">
            <div class="${SPINNER_CLASS}" aria-hidden="true"></div>
            <span id="${LOADING_TXT_ID}" aria-hidden="true"></span>
          </div>

          <button id="${VOCALIZE_BUTTON_ID}" aria-hidden="true" role="presentation" style="display: none;">
            ${browser.i18n.getMessage('click_for_description')}
          </button>

          <div id="${TRANSCRIPT_OVERLAY_ID}" aria-hidden="true" role="presentation" style="display: none;">
            <div class="${TRANSCRIPT_CLASS}">
              <div class="${TRANSCRIPT_HEADER_CLASS}">
                <h2>${browser.i18n.getMessage('popup_header')}</h2>
              </div>
              <div id="${TRANSCRIPT_TXT_ID}">
                <p>${browser.i18n.getMessage('popup_body')}</p>
              </div>
              <div class="${TRANSCRIPT_FOOTER_CLASS}">
                <button class="${TRANSCRIPT_CLOSE_BTN_CLASS}">
                  ${browser.i18n.getMessage('close_button')}
                </button>
              </div>
            </div>
          </div>
        `;

  document.body.insertAdjacentHTML('beforeend', htmlStructure);
}


/**
 * Ajoute les interactions au bouton et à la popup
 */
function addButtonAndPopupInteractions() {
  // Stocker l'élément actuellement focalisé pour y revenir plus tard
  const previouslyFocusedElement = document.activeElement;
  
  const btn = document.getElementById(VOCALIZE_BUTTON_ID);
  if (!btn) {
    console.error('Button element not found');
    return;
  }

  // Récupérer les éléments de la pop-in
  const overlay = document.getElementById(TRANSCRIPT_OVERLAY_ID);
  if (!overlay) {
    console.error('Overlay element not found');
    return;
  }
  const closeBtn = overlay.querySelector(`.${TRANSCRIPT_CLOSE_BTN_CLASS}`);
  
  if (!closeBtn) {
    console.error('Close button element not found');
    return;
  }
  

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
    
    // Cacher également l'overlay global
    const uiOverlay = document.getElementById(UI_OVERLAY_ID);
    if (uiOverlay) {
      uiOverlay.classList.remove('active');
    }
  
    // Redonner le focus à l'élément précédemment focalisé
    if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
      // previouslyFocusedElement.focus();
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
  
  // Fermeture automatique après 20 secondes si pas d'interaction
  let buttonTimeout = setTimeout(() => {
    if (btn) {
      btn.style.opacity = '0';
      setTimeout(() => {
        if (btn) btn.remove();
        
        // Redonner le focus à l'élément précédemment focalisé
        if (document.activeElement === btn && previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
          // previouslyFocusedElement.focus();
        }
      }, 300); // Attendre la fin de la transition d'opacité
    }
  }, 20000);
  
  // Annuler le timeout si le bouton est cliqué
  btn.addEventListener('click', () => {
    clearTimeout(buttonTimeout);
  });
  
  // Lors du clic, déclenche la synthèse vocale
  btn.addEventListener('click', function() {
    // Annule toute synthèse en cours
    window.speechSynthesis.cancel();
    
    // Crée l'utterance avec le texte et la langue souhaitée
    const utterance = new SpeechSynthesisUtterance(transcriptText);
    utterance.lang = browser.i18n.getUILanguage();
    
    // Fonction pour configurer et lancer la vocalisation
    const speakWhenReady = () => {
      const voices = window.speechSynthesis.getVoices();
      // Choisit une voix correspondant à la langue si possible
      const voice = voices.find(v => v.lang.startsWith(browser.i18n.getUILanguage().split('-')[0])) || voices[0];
      if (voice) {
        utterance.voice = voice;
      }
      console.log("Speaking in tab:", transcriptText);
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
}




/**
 * Crée ou met à jour la région live pour l'accessibilité
 * @param {string} txt - Texte à annoncer dans la région live
 */
function setInLiveRegion(txt = '') {
  const liveRegion = document.getElementById(LIVE_REGION_ID);
  if (!liveRegion) {
    console.error('Live region element not found');
    return;
  }
  if (txt) {
    liveRegion.textContent = txt;
    console.log('Live region should vocalize', txt);
  }
}


/**
 * Met à jour le message de chargement
 * @param {string} message - Le nouveau message à afficher
 */
function updateLoadingMessage(message) {
  // Mettre à jour la région live pour l'accessibilité
  setInLiveRegion(message);

  // Récupérer le container de chargement et l'overlay
  const loadingContainer = document.getElementById(LOADING_INFO_CONTAINER_ID);
  if (!loadingContainer) {
    console.error('Loading container not found');
    return;
  } 
  const loadingMessage = document.getElementById(LOADING_TXT_ID);
  if (!loadingMessage) {
    console.error('Loading message not found');
    return;
  }

  // Mettre à jour le message et afficher le container
  loadingMessage.textContent = message;
  loadingContainer.style.display = 'flex';

}

/**
 * Vocalise le texte donné en utilisant l'API SpeechSynthesis
 * @param {string} text - Texte à vocaliser
 * @param {string} lang - Langue pour la synthèse vocale
 */
function setTranscript(text) {
  setInLiveRegion(browser.i18n.getMessage('transcript_intro_message') + text);
  transcriptText = text;
  const transcript = document.getElementById(TRANSCRIPT_TXT_ID);
  if (!transcript) {
    console.error('Transcript element not found');
    return;
  }
  if (text) {
    transcript.textContent = text;
    console.log('Transcript should vocalize', text);
  }
}


// Écouteur pour les messages du background script
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Message reçu dans content-script:', message);
  
  switch (message.action) {
    // Message de ping pour vérifier si le content script est chargé
    case 'ping':
      sendResponse({ status: 'content-script-loaded' });
      break;
    
    case 'initUI':
      cleanupElements();
      createElements();
      addButtonAndPopupInteractions();
      sendResponse({ status: 'UI initialized' });
      break;
      
    case 'updateLoadingMessage':
      updateLoadingMessage(message.message);
      sendResponse({ status: 'Message updated' });
      break;

    case 'updateErrorMessage':
      updateLoadingMessage(message.message);
      sendResponse({ status: 'Message updated' });
      break;
      
    case 'setTranscript':
      setTranscript(message.text); 
      hideElement(LOADING_INFO_CONTAINER_ID);
      showElement(VOCALIZE_BUTTON_ID);
      sendResponse({ status: 'Transcript shown' });
      break;
      
    default:
      sendResponse({ status: 'Unknown action' });
  }
  
  return true; // Indique que sendResponse sera appelé de manière asynchrone
});
