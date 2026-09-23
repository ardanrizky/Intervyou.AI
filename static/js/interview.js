let currentQuestionIndex = 0;
let isRecording = false;
let recognition = null;
let transcriptText = "";

document.addEventListener("DOMContentLoaded", () => {
  setupSpeechRecognition();
  setupModeSwitch();
  setupEvents();
});

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    const statusEl = document.getElementById("voiceStatus");
    if (statusEl) {
      statusEl.textContent = "Browser Anda tidak mendukung Web Speech Recognition. Gunakan Mode Teks.";
    }
    const micBtn = document.getElementById("micBtn");
    if (micBtn) micBtn.disabled = true;
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "id-ID";
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onstart = () => {
    isRecording = true;
    updateMicUI(true);
  };

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        transcriptText += event.results[i][0].transcript + " ";
      } else {
        interim += event.results[i][0].transcript;
      }
    }
    const previewEl = document.getElementById("speechPreview");
    if (previewEl) {
      previewEl.textContent = transcriptText + interim;
    }
  };

  recognition.onerror = (err) => {
    console.warn("Speech error:", err.error);
    isRecording = false;
    updateMicUI(false);
  };

  recognition.onend = () => {
    isRecording = false;
    updateMicUI(false);
  };
}

function updateMicUI(listening) {
  const micBtn = document.getElementById("micBtn");
  const statusEl = document.getElementById("voiceStatus");
  const sendVoiceBtn = document.getElementById("sendVoiceBtn");

  if (listening) {
    micBtn.classList.add("listening");
    statusEl.textContent = "Mendengarkan... Silakan bicara dengan jelas.";
    if (sendVoiceBtn) sendVoiceBtn.classList.add("hidden");
  } else {
    micBtn.classList.remove("listening");
    statusEl.textContent = transcriptText ? "Rekaman selesai. Siap dikirim." : "Klik mikrofon untuk mulai berbicara.";
    if (sendVoiceBtn && transcriptText.trim()) {
      sendVoiceBtn.classList.remove("hidden");
    }
  }
}

function setupModeSwitch() {
  const voiceTab = document.getElementById("voiceTab");
  const textTab = document.getElementById("textTab");
  const voiceArea = document.getElementById("voiceArea");
  const textArea = document.getElementById("textArea");

  if (!voiceTab || !textTab) return;

  voiceTab.addEventListener("click", () => {
    voiceTab.classList.add("active");
    textTab.classList.remove("active");
    voiceArea.classList.remove("hidden");
    textArea.classList.add("hidden");
  });

  textTab.addEventListener("click", () => {
    textTab.classList.add("active");
    voiceTab.classList.remove("active");
    textArea.classList.remove("hidden");
    voiceArea.classList.add("hidden");
  });
}

function setupEvents() {
  const micBtn = document.getElementById("micBtn");
  if (micBtn) {
    micBtn.addEventListener("click", () => {
      if (!recognition) return;
      if (isRecording) {
        recognition.stop();
      } else {
        transcriptText = "";
        const previewEl = document.getElementById("speechPreview");
        if (previewEl) previewEl.textContent = "Mulai berbicara...";
        recognition.start();
      }
    });
  }

  const sendVoiceBtn = document.getElementById("sendVoiceBtn");
  if (sendVoiceBtn) {
    sendVoiceBtn.addEventListener("click", () => {
      submitAnswer(transcriptText);
    });
  }

  const submitTextBtn = document.getElementById("submitTextBtn");
  if (submitTextBtn) {
    submitTextBtn.addEventListener("click", () => {
      const textInput = document.getElementById("textAnswerInput");
      const answer = textInput ? textInput.value.trim() : "";
      submitAnswer(answer);
    });
  }

  const nextBtn = document.getElementById("nextQuestionBtn");
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      resetForNextQuestion();
    });
  }
}

let storedNextQuestion = null;

async function submitAnswer(answer) {
  if (!answer) {
    alert("Harap berikan jawaban sebelum mengirim.");
    return;
  }

  setLoadingState(true);

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answer: answer,
        question_index: currentQuestionIndex
      })
    });

    const data = await res.json();
    setLoadingState(false);

    if (!data.success) {
      alert(data.message || "Gagal mengevaluasi jawaban.");
      return;
    }

    displayEvaluationResult(data);
  } catch (err) {
    setLoadingState(false);
    console.error("Evaluation error:", err);
    alert("Terjadi kendala saat menghubungkan ke server.");
  }
}

function setLoadingState(loading) {
  const btns = [document.getElementById("submitTextBtn"), document.getElementById("sendVoiceBtn")];
  btns.forEach(b => {
    if (b) {
      b.disabled = loading;
      b.textContent = loading ? "Menganalisis Jawaban..." : "Kirim Jawaban";
    }
  });
}

function displayEvaluationResult(data) {
  const evalCard = document.getElementById("evalCard");
  const scoreNum = document.getElementById("evalScoreNum");
  const feedbackText = document.getElementById("evalFeedbackText");
  const matchedTags = document.getElementById("matchedTags");
  const missingTags = document.getElementById("missingTags");
  const nextBtn = document.getElementById("nextQuestionBtn");
  const finishCard = document.getElementById("finishCard");

  if (evalCard) evalCard.classList.remove("hidden");
  if (scoreNum) scoreNum.textContent = data.score;
  if (feedbackText) feedbackText.textContent = data.feedback;

  if (matchedTags) {
    matchedTags.innerHTML = "";
    if (data.matched_keywords && data.matched_keywords.length > 0) {
      data.matched_keywords.forEach(kw => {
        const span = document.createElement("span");
        span.className = "tag-matched";
        span.textContent = "✓ " + kw;
        matchedTags.appendChild(span);
      });
    } else {
      matchedTags.innerHTML = "<span style='color: var(--text-subtle); font-size: 13px;'>Tidak ada istilah kunci yang cocok</span>";
    }
  }

  if (missingTags) {
    missingTags.innerHTML = "";
    if (data.missing_keywords && data.missing_keywords.length > 0) {
      data.missing_keywords.forEach(kw => {
        const span = document.createElement("span");
        span.className = "tag-missing";
        span.textContent = "+ " + kw;
        missingTags.appendChild(span);
      });
    } else {
      missingTags.innerHTML = "<span style='color: var(--accent-emerald); font-size: 13px;'>Kosakata teknis sangat lengkap</span>";
    }
  }

  if (data.is_finished) {
    if (nextBtn) nextBtn.classList.add("hidden");
    if (finishCard) {
      finishCard.classList.remove("hidden");
      const avgScoreEl = document.getElementById("finalAvgScore");
      const overallFbEl = document.getElementById("overallFeedbackText");
      if (avgScoreEl) avgScoreEl.textContent = data.final_avg_score;
      if (overallFbEl) overallFbEl.textContent = data.overall_feedback;
    }
  } else {
    storedNextQuestion = data.next_question;
    currentQuestionIndex = data.next_question_index;
    if (nextBtn) nextBtn.classList.remove("hidden");
  }

  evalCard.scrollIntoView({ behavior: "smooth" });
}

function resetForNextQuestion() {
  const evalCard = document.getElementById("evalCard");
  if (evalCard) evalCard.classList.add("hidden");

  const questionContent = document.getElementById("questionContent");
  const questionIndexBadge = document.getElementById("questionIndexBadge");

  if (questionContent && storedNextQuestion) {
    questionContent.textContent = storedNextQuestion;
  }
  if (questionIndexBadge) {
    questionIndexBadge.textContent = "Pertanyaan " + (currentQuestionIndex + 1);
  }

  transcriptText = "";
  const previewEl = document.getElementById("speechPreview");
  if (previewEl) previewEl.textContent = "Jawaban suara Anda akan muncul di sini...";

  const textInput = document.getElementById("textAnswerInput");
  if (textInput) textInput.value = "";

  const sendVoiceBtn = document.getElementById("sendVoiceBtn");
  if (sendVoiceBtn) sendVoiceBtn.classList.add("hidden");

  window.scrollTo({ top: 0, behavior: "smooth" });
}
