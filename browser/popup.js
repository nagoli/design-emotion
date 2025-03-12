import { getLocalizedStrings } from "./localization.js";
const locStrings = getLocalizedStrings();
console.log('popup.js loaded');

const browser = chrome || window.browser; // Supporte les navigateurs non-chrome

// Initialisation de la localisation après chargement des scripts
window.initializeLocalization = function() {
  console.log('Localisation initialisée:');

  // Mise à jour des textes dans le popup
  document.querySelector('.header span').textContent = locStrings.popup_title;
  document.getElementById('vocaliseBtn').textContent = locStrings.vocalize_button;
  document.getElementById('settingsBtn').textContent = locStrings.change_shortcut_button;
  document.querySelector('.footer').textContent = locStrings.footer_copyright;
  
  // Ajout des écouteurs d'événements
  document.getElementById("vocaliseBtn").addEventListener("click", () => {
    // Envoie un message au background pour déclencher le transcript
    browser.runtime.sendMessage({ action: "triggerTranscript" });
    // Ferme la popup
    window.close();
  });
  
  document.getElementById("settingsBtn").addEventListener("click", () => {
    // Ouvre la page des raccourcis selon le navigateur
    try {
      if (navigator.userAgent.indexOf("Firefox") !== -1) {
        // Firefox - Use browser.runtime.openOptionsPage or navigate to extension management
        browser.runtime.sendMessage({ action: "openSettings" });
      } else {
        // Chrome
        chrome.tabs.create({ url: "chrome://extensions/shortcuts" });
      }
    } catch (error) {
      console.error("Error opening settings:", error);
    }
    // Ferme la popup
    window.close();
  });
}


// Importation directe des fichiers de localisation via des tags script
document.addEventListener('DOMContentLoaded', function() {
   window.initializeLocalization();
});