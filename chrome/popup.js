import { getLocalizedStrings } from "./localization.js";
const locStrings = getLocalizedStrings();
console.log('popup.js loaded');

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
    chrome.runtime.sendMessage({ action: "triggerTranscript" });
    // Ferme la popup
    window.close();
  });
  
  document.getElementById("settingsBtn").addEventListener("click", () => {
    // Ouvre la page des raccourcis Chrome pour permettre la configuration du raccourci clavier
    chrome.tabs.create({ url: "chrome://extensions/shortcuts" });
    // Ferme la popup
    window.close();
  });
}


// Importation directe des fichiers de localisation via des tags script
document.addEventListener('DOMContentLoaded', function() {
   window.initializeLocalization();
});