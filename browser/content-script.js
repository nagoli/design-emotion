/**
 * Script de contenu pour l'extension Design Emotion Vocalizer
 * Ce script est injecté dans toutes les pages web visitées
 * et gère les interactions UI directement dans le DOM
 */

// Récupère la référence du navigateur
const browser = chrome || window.browser;


const BTN_TIMEOUT = 200000;

// Constantes pour les ID et classes des éléments UI
// IDs pour les conteneurs principaux
const UI_OVERLAY_ID = 'ui-overlay-designemotionelements';
const UI_SPINNER_ID = 'loading-spinner-designemotionelements';
const UI_TXT_CONTENT_ID = 'txt-content-designemotionelements';
const UI_VOCALIZE_BUTTON_ID = 'vocalize-button-designemotionelements';
const UI_CLOSE_BTN_ID = 'close-button-designemotionelements';

const UI_LIVE_REGION_ID = 'live-region-designemotionelements';

const ACTIVE_CLASS = 'active-designemotionelements';

// Classes pour les éléments secondaires
const OVERLAY_CLASS = 'overlay-designemotionelements';
const SPINNER_CLASS = 'spinner-designemotionelements';
const POPIN_CLASS = 'popup-designemotionelements';
const POPIN_HEADER_CLASS = 'popup-header-designemotionelements';
const POPIN_BODY_CLASS = 'popup-body-designemotionelements';
const POPIN_FOOTER_CLASS = 'popup-footer-designemotionelements';
const POPIN_CLOSE_BTN_CLASS = 'popup-close-btn-designemotionelements';
const POPIN_INTERNAL_BTN_CLASS = 'popup-internal-btn-designemotionelements';
const POPIN_TXT_CLASS = 'popup-txt-designemotionelements';

let transcriptText='';

/**
 * Caches un élément en modifiant sa propriété display
 * @param {string} id - ID de l'élément à cacher
 */
function hideElement(id) {
  const element = document.getElementById(id);
  if (element) {
    element.classList.remove(ACTIVE_CLASS);
  }
}

function hideAllElements() {
  hideElement(UI_SPINNER_ID);
  hideElement(UI_TXT_CONTENT_ID);
  hideElement(UI_VOCALIZE_BUTTON_ID);
  hideElement(UI_CLOSE_BTN_ID);
  //clearTimeout(autoCloseTimeout);
}

/**
 * Affiche un élément en modifiant sa propriété display
 * @param {string} id - ID de l'élément à afficher
 * @returns {boolean} - Retourne true si l'élément a été affiché, false sinon
 */
function showElement(id) {
  const element = document.getElementById(id);
  if (!element) {
    return false;
  }
  if (!element.classList.contains(ACTIVE_CLASS)) {
    element.classList.add(ACTIVE_CLASS);
  }
  return true;
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
  console.log('🧹 Nettoyage des éléments design emotion ');
  removeElement(UI_OVERLAY_ID);
}


function createElements() {
  const htmlStructure = `
          <div id="${UI_LIVE_REGION_ID}"
              aria-live="assertive"
              aria-atomic="true"
              role="alert">
          </div>

          <div id="${UI_OVERLAY_ID}" class="${OVERLAY_CLASS}" aria-hidden="true" role="presentation">

            <div class="${POPIN_CLASS}" >
              <div class="${POPIN_HEADER_CLASS}">
                <h2>${browser.i18n.getMessage('popup_header')}</h2>
              </div>
              <div class="${POPIN_BODY_CLASS}">
                
                
                <div id="${UI_TXT_CONTENT_ID}" class="${POPIN_TXT_CLASS}"></div>

                <button id="${UI_VOCALIZE_BUTTON_ID}" class="${POPIN_INTERNAL_BTN_CLASS}">
                  ${browser.i18n.getMessage('click_for_description')}
                </button>

                <div id="${UI_SPINNER_ID}" class="${SPINNER_CLASS}"></div> 


              </div>
              <div class="${POPIN_FOOTER_CLASS}">
                <button id ="${UI_CLOSE_BTN_ID}" class="${POPIN_CLOSE_BTN_CLASS}">
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
function addInteractions() {
  try {
    const getter = (id) => document.getElementById(id);
    
    // Fonction pour fermer la pop-in
    const closePlugin = () => {
      // Arrêter toute synthèse vocale en cours
      window.speechSynthesis.cancel();
      cleanupElements();
    };
    
    const overlay = getter(UI_OVERLAY_ID);
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closePlugin();
      }
    });
    
    getter(UI_CLOSE_BTN_ID).addEventListener('click', closePlugin);
    
    // Pour accessibilité : fermer avec la touche Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.classList.contains('active')) {
        closePlugin();
      }
    });
  


    // Lors du clic sur le bouton vocalizer, ouvre la popup de transcript et déclenche la synthèse vocale
    getter(UI_VOCALIZE_BUTTON_ID).addEventListener('click', function() {
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
  } catch (error) {
    console.error('Error setting up button and popup interactions:', error);
  }
}

// let autoCloseTimeout;

// function autoClose() {
//   autoCloseTimeout = setTimeout(() => {
//     closePlugin();
//   }, BTN_TIMEOUT);
// }



/**
 * Crée ou met à jour la région live pour l'accessibilité
 * @param {string} txt - Texte à annoncer dans la région live
 */
function setInLiveRegion(txt = '') {
  const liveRegion = document.getElementById(UI_LIVE_REGION_ID);
  if (!liveRegion) {
    console.error('Live region element not found');
    return;
  }
  if (txt) {
    liveRegion.textContent = txt;
    console.log('Live region should vocalize : ', txt);
  }
}


/**
 * Met à jour le message affiché et vocalisé par le lecteur d’écran
 * @param {string} message - Le nouveau message à afficher
 */
function updateTextContent(message) {
  // Mettre à jour la région live pour l'accessibilité
  try {
    setInLiveRegion(message);
    // Mettre à jour le message et afficher le container
    document.getElementById(UI_TXT_CONTENT_ID).textContent = message;
  } catch (error) {
    console.error('Error updating loading message:', error);
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
      addInteractions();
      sendResponse({ status: 'UI initialized' });
      break;
      
    case 'updateLoadingMessage':
      hideAllElements();
      updateTextContent(message.message);
      showElement(UI_TXT_CONTENT_ID);
      showElement(UI_SPINNER_ID);
      sendResponse({ status: 'Message updated' });
      break;

    case 'updateErrorMessage':
      hideAllElements();
      updateTextContent(message.message);
      showElement(UI_TXT_CONTENT_ID);
      sendResponse({ status: 'Message updated' });
      break;
      
    case 'setTranscript':
      hideAllElements();
      transcriptText = message.transcript;
      updateTextContent(browser.i18n.getMessage('transcript_intro_message') + transcriptText);
      showElement(UI_TXT_CONTENT_ID);
      showElement(UI_VOCALIZE_BUTTON_ID);
      sendResponse({ status: 'Transcript shown' });
      break;
      
    default:
      sendResponse({ status: 'Unknown action' });
  }
  
  return true; // Indique que sendResponse sera appelé de manière asynchrone
});




// Selection du lien d’évitement 
if (False) {
  document.addEventListener('DOMContentLoaded', () => {
  const skipSelectors = [
    'a[href="#main"]',
    'a[href="#content"]',
    'a[href="#main-content"]',
    '#skip-link',
    '.skipto',
    '.govuk-skip-link',
    '.lbh-skip-link'
  ].join(', ');

  const skipLink = document.querySelector(skipSelectors);
  const actionBtn = document.getElementById('blind-action-btn');

  if (skipLink) {
    skipLink.after(actionBtn);
  } else {
    document.body.prepend(actionBtn);
  }
});
};