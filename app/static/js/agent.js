/**
 * ShaktiGuard Agent Audio, Voice & Strobe Subsystem
 * Implements Web Speech API (STT & TTS) and Web Audio API Siren
 */

class AgentAudioController {
  constructor() {
    this.audioCtx = null;
    this.sirenOscillator1 = null;
    this.sirenOscillator2 = null;
    this.sirenGain = null;
    this.isSirenPlaying = false;
    this.sirenInterval = null;

    this.isStrobeActive = false;
    this.isTTSActive = false;
    this.recognition = null;
    this.isRecording = false;

    this.initSpeechRecognition();
  }

  // ================= 1. WEB AUDIO API SIREN =================
  toggleSiren(btnElement) {
    if (this.isSirenPlaying) {
      this.stopSiren();
      if (btnElement) btnElement.innerText = "OFF";
    } else {
      this.startSiren();
      if (btnElement) btnElement.innerText = "ON (ACTIVE)";
    }
  }

  startSiren() {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContext();

      this.sirenOscillator1 = this.audioCtx.createOscillator();
      this.sirenOscillator2 = this.audioCtx.createOscillator();
      this.sirenGain = this.audioCtx.createGain();

      this.sirenOscillator1.type = "sawtooth";
      this.sirenOscillator2.type = "sine";

      this.sirenOscillator1.frequency.setValueAtTime(650, this.audioCtx.currentTime);
      this.sirenOscillator2.frequency.setValueAtTime(950, this.audioCtx.currentTime);

      this.sirenGain.gain.setValueAtTime(0.3, this.audioCtx.currentTime);

      this.sirenOscillator1.connect(this.sirenGain);
      this.sirenOscillator2.connect(this.sirenGain);
      this.sirenGain.connect(this.audioCtx.destination);

      this.sirenOscillator1.start();
      this.sirenOscillator2.start();
      this.isSirenPlaying = true;

      // Frequency modulation for classic emergency siren wail
      let high = false;
      this.sirenInterval = setInterval(() => {
        if (!this.audioCtx || this.audioCtx.state === "closed") return;
        const targetFreq1 = high ? 600 : 960;
        const targetFreq2 = high ? 850 : 1250;
        this.sirenOscillator1.frequency.linearRampToValueAtTime(targetFreq1, this.audioCtx.currentTime + 0.4);
        this.sirenOscillator2.frequency.linearRampToValueAtTime(targetFreq2, this.audioCtx.currentTime + 0.4);
        high = !high;
      }, 450);

    } catch (e) {
      console.warn("AudioContext error on siren start:", e);
    }
  }

  stopSiren() {
    if (this.sirenInterval) {
      clearInterval(this.sirenInterval);
      this.sirenInterval = null;
    }
    if (this.sirenOscillator1) {
      try { this.sirenOscillator1.stop(); } catch (e) {}
      this.sirenOscillator1 = null;
    }
    if (this.sirenOscillator2) {
      try { this.sirenOscillator2.stop(); } catch (e) {}
      this.sirenOscillator2 = null;
    }
    if (this.audioCtx) {
      try { this.audioCtx.close(); } catch (e) {}
      this.audioCtx = null;
    }
    this.isSirenPlaying = false;
  }

  // ================= 2. SCREEN STROBE =================
  toggleStrobe(overlayElement, btnElement) {
    this.isStrobeActive = !this.isStrobeActive;
    if (overlayElement) {
      overlayElement.style.display = this.isStrobeActive ? "block" : "none";
    }
    if (btnElement) {
      btnElement.innerText = this.isStrobeActive ? "ON (FLASHING)" : "OFF";
    }
  }

  // ================= 3. SPEECH RECOGNITION (STT) =================
  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Web Speech API recognition not natively supported in this browser.");
      return;
    }
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = "en-US";
  }

  startListening(onResult, onEnd) {
    if (!this.recognition) {
      alert("Voice recognition is not supported in this browser. Please type your situation in the text box.");
      return;
    }
    this.isRecording = true;
    this.recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        transcript += event.results[i][0].transcript;
      }
      onResult(transcript);
    };

    this.recognition.onerror = (err) => {
      console.error("Speech recognition error:", err);
      this.isRecording = false;
      if (onEnd) onEnd();
    };

    this.recognition.onend = () => {
      this.isRecording = false;
      if (onEnd) onEnd();
    };

    try {
      this.recognition.start();
    } catch (e) {
      console.warn("Recognition already active:", e);
    }
  }

  stopListening() {
    if (this.recognition && this.isRecording) {
      this.recognition.stop();
      this.isRecording = false;
    }
  }

  // ================= 4. TEXT-TO-SPEECH (TTS) CALM GUIDE =================
  speakGuidance(steps, btnElement) {
    if (!('speechSynthesis' in window)) return;

    if (this.isTTSActive) {
      window.speechSynthesis.cancel();
      this.isTTSActive = false;
      if (btnElement) btnElement.innerText = "OFF";
      return;
    }

    if (!steps || steps.length === 0) return;
    this.isTTSActive = true;
    if (btnElement) btnElement.innerText = "SPEAKING...";

    const textToRead = "ShaktiGuard Emergency Instructions: " + steps.join(". Next step: ");
    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    utterance.onend = () => {
      this.isTTSActive = false;
      if (btnElement) btnElement.innerText = "OFF";
    };

    window.speechSynthesis.speak(utterance);
  }
}

window.agentAudio = new AgentAudioController();
