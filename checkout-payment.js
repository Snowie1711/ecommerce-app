// ...existing code...

// Fix for recursive logDebug function
function logDebug(message) {
  // Don't call logDebug inside itself
  if (DEBUG_MODE) {
    // Use console.log directly instead of calling logDebug again
    console.log(`[DEBUG] ${message}`);
  }
}

// ...existing code...
