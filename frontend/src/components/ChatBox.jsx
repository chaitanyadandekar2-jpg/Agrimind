import { useState, useRef, useEffect } from "react";
import { sendChatMessage, getSpeechAudioUrl } from "../api";
import { useLanguage } from "../i18n/LanguageContext";

const BENCHMARK_QUESTIONS = [
  "Which crop should I grow according to my soil?",
  "Can I spray fertilizer this evening?",
  "Which fertilizer is suitable for my crop?",
  "What is the deficiency in my soil?",
  "Which organic fertilizer can I use?",
  "Why is nitrogen low?",
  "What should I do to improve organic carbon?",
  "What should I do next?",
];

const LANG_LOCALE_MAP = {
  en: "en-IN",
  hi: "hi-IN",
  mr: "mr-IN",
};

export default function ChatBox({ soil, selectedCrop, location, recommendationResult }) {
  const { t, lang } = useLanguage();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speakingIdx, setSpeakingIdx] = useState(null);
  const [availableVoices, setAvailableVoices] = useState([]);
  const [sessionId, setSessionId] = useState(() => "session_" + Math.random().toString(36).substring(2, 9));
  const scrollRef = useRef(null);
  const recognitionRef = useRef(null);
  const activeUtterancesRef = useRef([]);
  const audioPlayerRef = useRef(null);

  // Dynamically retrieve suggested questions in current language
  const currentQuestions =
    Array.isArray(t("suggestedQuestions")) && t("suggestedQuestions").length > 0
      ? t("suggestedQuestions")
      : BENCHMARK_QUESTIONS;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Pre-load and cache browser speech synthesis voices
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;

    function populateVoices() {
      const v = window.speechSynthesis.getVoices();
      if (v && v.length > 0) {
        setAvailableVoices(v);
      }
    }

    populateVoices();
    window.speechSynthesis.onvoiceschanged = populateVoices;
  }, []);

  function stopAudio() {
    if (audioPlayerRef.current) {
      try {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      } catch {}
      audioPlayerRef.current = null;
    }
    if (typeof window !== "undefined" && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch {}
    }
    activeUtterancesRef.current = [];
    setSpeakingIdx(null);
  }

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
      stopAudio();
    };
  }, []);

  function handleClearChat() {
    stopAudio();
    setMessages([]);
    setSessionId("session_" + Math.random().toString(36).substring(2, 9));
  }

  function toggleListening() {
    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
      setIsListening(false);
      return;
    }

    const SpeechRecognition =
      typeof window !== "undefined" &&
      (window.SpeechRecognition || window.webkitSpeechRecognition);

    if (!SpeechRecognition) {
      alert(t("voiceNotSupported"));
      return;
    }

    stopAudio();

    try {
      const recognition = new SpeechRecognition();
      const targetLocale = LANG_LOCALE_MAP[lang] || "en-IN";
      recognition.lang = targetLocale;
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let fullTranscript = "";
        for (let i = 0; i < event.results.length; i++) {
          fullTranscript += event.results[i][0].transcript + " ";
        }
        fullTranscript = fullTranscript.trim();
        if (fullTranscript) {
          setInput(fullTranscript);
        }
      };

      recognition.onerror = (e) => {
        if (e.error === "no-speech") {
          // Normal pause while user is thinking, keep mic active
          return;
        }
        console.warn("Speech recognition error:", e.error);
        if (e.error === "not-allowed" || e.error === "service-not-allowed") {
          alert(
            "Microphone access is blocked or not supported inside VS Code's internal browser preview.\n\nPlease open http://localhost:5173 directly in Google Chrome or Microsoft Edge to use voice input!"
          );
        } else if (e.error === "audio-capture") {
          alert("No microphone was detected. Please check that your microphone is plugged in and unmuted in Windows settings.");
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Failed to start speech recognition:", err);
      setIsListening(false);
    }
  }

  function handleToggleSpeak(index, textToSpeak) {
    if (speakingIdx === index) {
      stopAudio();
      return;
    }

    stopAudio();

    // Strip Markdown symbols for natural reading
    const cleanText = textToSpeak
      .replace(/[*_#`~]/g, "")
      .replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1")
      .replace(/^[•\-\*]\s+/gm, "")
      .trim();

    if (!cleanText) return;

    setSpeakingIdx(index);

    // 1. Primary Engine: High-fidelity native Marathi/Hindi/English audio stream from backend
    try {
      const audioUrl = getSpeechAudioUrl(cleanText, lang);
      const audio = new Audio(audioUrl);
      audioPlayerRef.current = audio;

      audio.onended = () => {
        setSpeakingIdx(null);
        audioPlayerRef.current = null;
      };

      audio.onerror = (e) => {
        console.warn("Backend TTS stream failed, attempting browser fallback:", e);
        audioPlayerRef.current = null;
        playBrowserSpeechFallback(cleanText, index);
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          console.warn("Audio autoplay blocked, attempting browser fallback:", err);
          playBrowserSpeechFallback(cleanText, index);
        });
      }
    } catch (err) {
      console.warn("Failed to instantiate Audio, falling back:", err);
      playBrowserSpeechFallback(cleanText, index);
    }
  }

  function playBrowserSpeechFallback(cleanText, index) {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      setSpeakingIdx(null);
      return;
    }

    setTimeout(() => {
      try {
        window.speechSynthesis.resume();
        const targetLang = LANG_LOCALE_MAP[lang] || "en-IN";
        const voices =
          availableVoices.length > 0 ? availableVoices : window.speechSynthesis.getVoices();

        let chosenVoice = null;
        if (lang === "mr") {
          chosenVoice =
            voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith("mr")) ||
            voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith("hi")) ||
            voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-") === "en-in");
        } else if (lang === "hi") {
          chosenVoice =
            voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith("hi")) ||
            voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-") === "en-in");
        } else {
          chosenVoice =
            voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-") === "en-in") ||
            voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("en"));
        }

        const u = new SpeechSynthesisUtterance(cleanText);
        u.lang = targetLang;
        u.rate = 0.95;
        if (chosenVoice) u.voice = chosenVoice;

        u.onend = () => {
          setSpeakingIdx(null);
          activeUtterancesRef.current = [];
        };
        u.onerror = () => {
          setSpeakingIdx(null);
          activeUtterancesRef.current = [];
        };

        activeUtterancesRef.current = [u];
        window.speechSynthesis.speak(u);
      } catch {
        setSpeakingIdx(null);
      }
    }, 50);
  }

  async function handleSend(customText = null) {
    const text = (typeof customText === "string" ? customText : input).trim();
    if (!text || sending) return;

    if (isListening && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      setIsListening(false);
    }

    setMessages((m) => [...m, { role: "user", text }]);
    if (!customText) setInput("");
    setSending(true);

    try {
      const payload = {
        message: text,
        session_id: sessionId,
        soil: soil || null,
        selected_crop: selectedCrop || null,
        location_name: location || null,
        language: lang,
        previous_crop_scores: recommendationResult?.crop_scores || null,
        previous_fertilizer_options: recommendationResult?.fertilizer_options || null,
        previous_application_window: recommendationResult?.application_window || null,
      };

      const res = await sendChatMessage(text, payload);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.answer,
          contradiction: res.contradiction_flag,
          evidence: res.evidence || [],
          intent: res.intent,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Sorry, something went wrong: ${err.message}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bg-white/70 backdrop-blur rounded-2xl border border-soil-300 flex flex-col h-96 shadow-sm">
      <div className="px-4 py-3 border-b border-soil-200 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-soil-900 flex items-center gap-2">
          <span>{t("chatHeading")}</span>
          <span className="text-[11px] font-normal text-soil-500 font-mono">
            [{LANG_LOCALE_MAP[lang] || "en-IN"}]
          </span>
        </h3>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="text-[11px] text-soil-500 hover:text-soil-800 underline transition-colors"
              title="Reset conversation"
            >
              {t("clearChat")}
            </button>
          )}
          <span className="text-[10px] font-mono text-leaf-700 bg-leaf-50 px-2 py-0.5 rounded border border-leaf-200">
            OpenRouter · LangChain RAG
          </span>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="space-y-3">
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-xl px-3 py-2 text-sm bg-soil-100 text-soil-900">
                {t("chatGreeting")}
              </div>
            </div>

            <div className="pt-1">
              <p className="text-[11px] font-medium text-soil-500 mb-2">
                {t("quickQuestions")}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {currentQuestions.slice(0, 5).map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    disabled={sending}
                    className="text-left text-xs bg-soil-50 hover:bg-leaf-50 hover:text-leaf-800 border border-soil-200 hover:border-leaf-300 text-soil-700 px-2.5 py-1.5 rounded-lg transition-colors"
                  >
                    💬 {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-sm space-y-2 ${
                m.role === "user" ? "bg-leaf-600 text-white" : "bg-soil-100 text-soil-900 border border-soil-200"
              }`}
            >
              {m.contradiction && (
                <div className="text-xs bg-red-100 border border-red-300 text-red-800 rounded px-2 py-1 font-medium">
                  ⚠ {m.contradiction}
                </div>
              )}

              <p className="whitespace-pre-line leading-relaxed">{m.text}</p>

              {m.evidence && m.evidence.length > 0 && (
                <div className="pt-1 border-t border-soil-200/60 flex flex-wrap gap-1">
                  <span className="text-[10px] font-mono text-soil-500 uppercase">Sources:</span>
                  {m.evidence.slice(0, 2).map((ev, ei) => (
                    <span
                      key={ei}
                      className="text-[10px] font-mono bg-white/80 px-1.5 py-0.5 rounded text-leaf-800 border border-leaf-200"
                    >
                      {ev.source}
                    </span>
                  ))}
                </div>
              )}

              {m.role === "assistant" && (
                <div className="pt-1 border-t border-soil-200/60 flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => handleToggleSpeak(i, m.text)}
                    className={`flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-lg transition-all ${
                      speakingIdx === i
                        ? "bg-leaf-700 text-white font-medium shadow-sm animate-pulse"
                        : "text-soil-600 hover:text-soil-900 bg-white hover:bg-soil-50 border border-soil-200"
                    }`}
                    title={speakingIdx === i ? t("voiceStop") : t("voiceSpeak")}
                  >
                    {speakingIdx === i ? (
                      <>
                        <span className="text-xs">⏹</span>
                        <span>{t("voiceStop")}</span>
                      </>
                    ) : (
                      <>
                        <span className="text-xs">🔊</span>
                        <span>{t("voiceSpeak")}</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {sending && <div className="text-xs text-soil-400 italic">{t("chatThinking")}</div>}
      </div>

      {messages.length > 0 && (
        <div className="px-3 py-1.5 bg-soil-50/70 border-t border-soil-100 flex items-center gap-1.5 overflow-x-auto text-[11px] whitespace-nowrap">
          <span className="text-soil-400 text-[10px] uppercase font-mono">Suggested:</span>
          {currentQuestions.slice(0, 4).map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              disabled={sending}
              className="text-soil-600 hover:text-leaf-800 hover:bg-leaf-100 px-2 py-0.5 rounded border border-soil-200 bg-white transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {isListening && (
        <div className="px-3 py-2 bg-red-50 border-t border-red-200 text-red-700 text-xs flex items-center justify-between animate-fadeIn">
          <span className="flex items-center gap-2 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
            <span>{t("voiceListening")} ({LANG_LOCALE_MAP[lang] || "en-IN"})</span>
          </span>
          <button
            type="button"
            onClick={toggleListening}
            className="text-red-700 hover:text-red-900 font-semibold underline text-xs"
          >
            {t("voiceStop")}
          </button>
        </div>
      )}

      <div className="p-3 border-t border-soil-200 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder={isListening ? t("voiceListening") : t("chatInputPlaceholder")}
          className={`flex-1 px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 bg-white transition-colors ${
            isListening ? "border-red-400 ring-2 ring-red-200" : "border-soil-300"
          }`}
        />

        <button
          type="button"
          onClick={toggleListening}
          disabled={sending}
          title={isListening ? t("voiceStop") : `${t("voiceInput")} (${LANG_LOCALE_MAP[lang] || "en-IN"})`}
          className={`p-2.5 rounded-lg border transition-all flex items-center justify-center ${
            isListening
              ? "bg-red-500 text-white border-red-600 ring-2 ring-red-300 shadow-sm animate-pulse"
              : "bg-soil-100 hover:bg-leaf-100 text-soil-700 hover:text-leaf-800 border-soil-300"
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
          </svg>
        </button>

        <button
          onClick={() => handleSend()}
          disabled={sending || (!input.trim() && !isListening)}
          className="px-4 py-2 rounded-lg bg-soil-900 hover:bg-soil-800 text-white text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {t("chatSend")}
        </button>
      </div>
    </div>
  );
}
