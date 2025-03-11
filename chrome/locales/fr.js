// Fichier de configuration pour la langue française
export const fr = {
  // Popup
  "popup_title": "Design Emotion Vocalizer",
  "vocalize_button": "Vocaliser (Ctrl+Maj+Y)",
  "change_shortcut_button": "Modifier le raccourci",
  "footer_copyright": "© 2025 Design Emotion",
  
  // Messages de chargement et d'analyse
  "analyzing_message": "Analyse des émotions provoquées par le design en cours...",
  "transcript_ready_message": "Transcription des émotions du design prête",
  "click_for_description": "Cliquez pour la description des émotions provoquées par le design",
  
  // Popup de transcription
  "popup_header": "Design Emotion Vocalizer",
  "close_button": "Fermer",
  
  // Messages accessibilité
  "loading_aria_message": "Analyse des émotions provoquées par le design en cours. Veuillez patienter.",
  "transcript_ready_aria_message": "Transcription des émotions provoquées par le design prête. Appuyez sur le bouton pour l'afficher.",
};

// Export pour utilisation dans l'extension
if (typeof module !== 'undefined') {
  module.exports = fr;
}
