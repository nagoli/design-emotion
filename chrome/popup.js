document.getElementById("vocaliseBtn").addEventListener("click", () => {
    // Envoie un message au background pour déclencher le transcript
    chrome.runtime.sendMessage({ action: "triggerTranscript" });
  });
  
document.getElementById("settingsBtn").addEventListener("click", () => {
    // Ouvre la page des raccourcis Chrome pour permettre la configuration du raccourci clavier
    chrome.tabs.create({ url: "chrome://extensions/shortcuts" });
  });