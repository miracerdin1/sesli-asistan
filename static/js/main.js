document.addEventListener("DOMContentLoaded", () => {
  const micBtn = document.getElementById("mic-btn");
  const statusText = document.getElementById("status");
  const subtitle = document.getElementById("subtitle");
  const orb = document.getElementById("visualizer-orb");

  // Check for browser support
  if (!("webkitSpeechRecognition" in window)) {
    alert(
      "Tarayıcınız ses tanıma özelliğini desteklemiyor. Lütfen Google Chrome kullanın.",
    );
    statusText.textContent = "Tarayıcı desteklenmiyor.";
    micBtn.disabled = true;
    return;
  }

  const recognition = new webkitSpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.lang = "tr-TR";

  let isListening = false;
  let isSpeaking = false;

  // Helper to set Orb State
  function setOrbState(state) {
    if (!orb) return;
    // Remove all states first
    orb.classList.remove("idle", "listening", "processing", "speaking");
    orb.classList.add(state);

    // Update status text
    if (statusText) {
      if (state === "idle") statusText.textContent = "BEKLİYOR";
      if (state === "listening") statusText.textContent = "DİNLİYOR...";
      if (state === "processing") statusText.textContent = "DÜŞÜNÜYOR...";
      if (state === "speaking") statusText.textContent = "KONUŞUYOR...";
    }
  }

  if (micBtn) {
    micBtn.addEventListener("click", () => {
      if (isListening) {
        recognition.stop();
        isListening = false; // Force flag update immediately
      } else {
        try {
          recognition.start();
        } catch (e) {
          console.log("Start error:", e);
        }
      }
    });
  }

  recognition.onstart = () => {
    isListening = true;
    if (micBtn) {
      micBtn.classList.add("active");
      micBtn.innerHTML = '<i class="fas fa-stop"></i>';
    }
    setOrbState("listening");
  };

  recognition.onend = () => {
    // Restart only if we expect to be listening and we aren't currently speaking
    if (isListening && !window.shouldRestartRecognition) {
      console.log("Restarting speech recognition...");
      try {
        recognition.start();
      } catch (e) {
        console.log("Recognition already started: ", e);
      }
    } else {
      // If we really stopped listening
      if (!isListening) {
        if (micBtn) {
          micBtn.classList.remove("active");
          micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        }
        setOrbState("idle");
      }
    }
  };

  let commandBuffer = "";
  let commandTimeout = null;

  recognition.onresult = (event) => {
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      }
    }

    if (finalTranscript) {
      const trimmed = finalTranscript.trim();
      if (trimmed) {
        console.log("Partial result:", trimmed);
        commandBuffer += (commandBuffer ? " " : "") + trimmed;

        // Show what user said in subtitle
        if (subtitle) {
          subtitle.textContent = `"${commandBuffer}"`;
          subtitle.style.color = "#00f2ff"; // Cyan for user
        }

        if (commandTimeout) clearTimeout(commandTimeout);

        // Wait 2.5s silence
        commandTimeout = setTimeout(() => {
          if (commandBuffer) {
            processCommand(commandBuffer);
            commandBuffer = "";
          }
        }, 2500);
      }
    }
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error", event.error);
    if (statusText) statusText.textContent = "Hata: " + event.error;
    setOrbState("idle");
  };

  async function processCommand(text) {
    setOrbState("processing");
    if (subtitle) subtitle.style.color = "#ffffff"; // White for processing

    try {
      const response = await fetch("/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });

      const data = await response.json();

      // Update subtitle with Assistant's response (briefly or keep user's?)
      // Let's show assistant response text
      if (subtitle) subtitle.textContent = data.response;

      speak(data.response);
    } catch (error) {
      console.error("Error:", error);
      if (subtitle) subtitle.textContent = "Bir hata oluştu.";
      setOrbState("idle");
    }
  }

  function speak(text) {
    if (!text) return;

    // Stop recognition to prevent hearing itself
    window.shouldRestartRecognition = true;
    recognition.stop();

    setOrbState("speaking");
    isSpeaking = true;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "tr-TR";

    utterance.onend = () => {
      isSpeaking = false;
      setOrbState("listening"); // Go back to listening
      window.shouldRestartRecognition = false;

      if (isListening) {
        try {
          recognition.start();
        } catch (e) {}
      }
    };

    window.speechSynthesis.speak(utterance);
  }

  // Initialize state
  setOrbState("idle");
});
