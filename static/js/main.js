document.addEventListener("DOMContentLoaded", () => {
  const micBtn = document.getElementById("mic-btn");
  const statusText = document.getElementById("status");
  const chatBox = document.getElementById("chat-box");

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

  micBtn.addEventListener("click", () => {
    if (isListening) {
      recognition.stop();
    } else {
      recognition.start();
    }
  });

  recognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    statusText.textContent = "Dinliyorum...";
    micBtn.innerHTML = '<i class="fas fa-stop"></i>';
  };

  recognition.onend = () => {
    // Automatically restart if we are still in "listening" mode
    // BUT skip if we are just pausing to speak (managed by speak function)
    if (isListening && !window.shouldRestartRecognition) {
      console.log("Restarting speech recognition...");
      try {
        recognition.start();
      } catch (e) {
        console.log("Recognition already started or error: ", e);
      }
    } else if (!isListening) {
      micBtn.classList.remove("listening");
      statusText.textContent = "Dinlemek için mikrofona basın...";
      micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
  };

  let commandBuffer = "";
  let commandTimeout = null;

  recognition.onresult = (event) => {
    let interimTranscript = "";
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }

    if (finalTranscript) {
      const trimmed = finalTranscript.trim();
      if (trimmed) {
        // Show feedback but don't commit to "user" chat yet if we want to combine?
        // Or just append log. Let's append log for now.
        console.log("Partial result:", trimmed);

        commandBuffer += (commandBuffer ? " " : "") + trimmed;
        statusText.textContent =
          "Dinliyorum... (Sözünüzün bitmesini bekliyorum)";

        if (commandTimeout) clearTimeout(commandTimeout);

        // Wait 2.5 seconds of silence before sending
        commandTimeout = setTimeout(() => {
          if (commandBuffer) {
            addMessage(commandBuffer, "user"); // Show full command
            processCommand(commandBuffer);
            commandBuffer = "";
          }
        }, 2500);
      }
    }
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error", event.error);
    statusText.textContent = "Hata: " + event.error;
  };

  function addMessage(text, sender) {
    const div = document.createElement("div");
    div.classList.add("message", sender);
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function processCommand(text) {
    statusText.textContent = "İşleniyor...";

    // Show typing indicator or similar if needed

    fetch("/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: text }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.error) {
          addMessage("Hata: " + data.error, "assistant");
          speak("Bir hata oluştu.");
        } else {
          addMessage(data.response, "assistant");
          speak(data.response);
          statusText.textContent = "Tamamlandı.";
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        addMessage("Sunucu hatası.", "assistant");
        speak("Sunucu ile iletişim kurulamadı.");
        statusText.textContent = "Hata.";
      });
  }

  function speak(text) {
    if ("speechSynthesis" in window) {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      // Stop recognition temporarily to prevent hearing itself
      if (isListening) {
        recognition.stop();
        // We set a flag to know we should restart after speaking
        window.shouldRestartRecognition = true;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "tr-TR";

      // Optional: Adjust pitch and rate
      utterance.pitch = 1;
      utterance.rate = 1;

      utterance.onend = () => {
        // Restart recognition if we were listening before
        if (window.shouldRestartRecognition) {
          console.log("Speech ended, restarting recognition...");
          try {
            recognition.start();
          } catch (e) {
            console.log("Error restarting recognition:", e);
          }
          window.shouldRestartRecognition = false;
        }
      };

      window.speechSynthesis.speak(utterance);
    }
  }
});
