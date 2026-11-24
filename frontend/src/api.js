const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

export async function uploadSoilReport(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/soil/upload`, {
    method: "POST",
    body: formData,
  });
  return handle(res);
}

export async function getRecommendation(payload) {
  const res = await fetch(`${API_BASE}/api/recommendation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}

export async function getWeatherForecast(locationName) {
  const params = new URLSearchParams({ location_name: locationName });
  const res = await fetch(`${API_BASE}/api/weather/forecast?${params.toString()}`);
  return handle(res);
}

export function getSpeechAudioUrl(text, language = "en") {
  const params = new URLSearchParams({
    text,
    language,
  });
  return `${API_BASE}/api/voice/tts?${params.toString()}`;
}

export async function sendChatMessage(message, optionsOrSoil = {}, selectedCrop = null, language = "en") {
  // Support both object payload and legacy positional arguments
  let payload = {};
  if (optionsOrSoil && typeof optionsOrSoil === "object" && !("nitrogen" in optionsOrSoil) && !("ph" in optionsOrSoil) && ("soil" in optionsOrSoil || "message" in optionsOrSoil)) {
    payload = { ...optionsOrSoil, message };
  } else {
    payload = {
      message,
      soil: optionsOrSoil || null,
      selected_crop: selectedCrop,
      language,
    };
  }

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}
