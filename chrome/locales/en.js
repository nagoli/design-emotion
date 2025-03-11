// Configuration file for English language
export const en = {
  // Popup
  "popup_title": "Design Emotion Vocalizer",
  "vocalize_button": "Vocalize (Ctrl+Shift+Y)",
  "change_shortcut_button": "Change Shortcut",
  "footer_copyright": "© 2025 Design Emotion",
  
  // Loading and analysis messages
  "analyzing_message": "Analyzing design emotion...",
  "transcript_ready_message": "Design emotion transcript ready",
  "click_for_description": "Click for design emotion description",
  
  // Transcript popup
  "popup_header": "Design Emotion Vocalizer",
  "close_button": "Close",
  
  // Accessibility messages
  "loading_aria_message": "Analyzing design emotion. Please wait.",
  "transcript_ready_aria_message": "Design emotion transcript ready. Click the button to view.",
};

// Export for use in the extension
if (typeof module !== 'undefined') {
  module.exports = en;
}
