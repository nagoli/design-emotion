/**
 * Gestionnaire de localisation simple pour l'extension Design Emotion
 */

import { fr } from "./locales/fr.js";
import { en } from "./locales/en.js";


/**
 * Obtient les chaînes de texte localisées basées sur la langue du navigateur
 * @returns {Object} - L'objet contenant les chaînes de texte localisées
 */
export function getLocalizedStrings() {
  // Récupérer la langue du navigateur
  const browserLang = chrome.i18n.getUILanguage().toLowerCase().split('-')[0];
  console.log('Langue du navigateur détectée:', browserLang);
  
  // Vérifier que les objets fr et en sont disponibles
  if (typeof fr === 'undefined' || typeof en === 'undefined') {
    console.error('Fichiers de localisation non chargés correctement');
    // Renvoyer un objet vide pour éviter les erreurs
    return {};
  }
  
  // Sélectionner le fichier de langue approprié (par défaut: anglais)
  switch (browserLang) {
    case 'fr':
      return fr;
    default:
      return en;
  }
}

