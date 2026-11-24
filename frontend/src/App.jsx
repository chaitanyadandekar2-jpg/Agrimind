import { useState } from "react";
import InputPanel from "./components/InputPanel";
import SoilCore from "./components/SoilCore";
import RecommendationPanel from "./components/RecommendationPanel";
import WeatherPanel from "./components/WeatherPanel";
import WhyPanel from "./components/WhyPanel";
import ChatBox from "./components/ChatBox";
import LanguageSwitcher from "./components/LanguageSwitcher";
import { uploadSoilReport, getRecommendation } from "./api";
import { useLanguage } from "./i18n/LanguageContext";

export default function App() {
  const { lang, t } = useLanguage();
  const [file, setFile] = useState(null);
  const [soil, setSoil] = useState(null);
  const [location, setLocation] = useState("");
  const [crop, setCrop] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("analysis"); // "analysis" | "weather" | "chat"

  async function handleFileSelect(selected) {
    setFile(selected);
    setError(null);
    try {
      const parsed = await uploadSoilReport(selected);
      setSoil(parsed);
    } catch (err) {
      setError(`Could not read soil report: ${err.message}`);
    }
  }

  async function handleAnalyze() {
    if (!soil) {
      setError(t("uploadFirstError"));
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const rec = await getRecommendation({
        soil,
        selected_crop: crop || null,
        location_name: location || null,
        language: lang,
      });
      setResult(rec);
      setActiveTab("analysis");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen">
      {/* Hero: soil cross-section motif */}
      <header className="relative overflow-hidden border-b border-soil-300">
        <div
          className="absolute inset-0 -z-10"
          style={{
            background:
              "linear-gradient(180deg, #f6f1ea 0%, #f6f1ea 35%, #e9dcc9 55%, #c9a877 75%, #8a5a34 100%)",
          }}
        />
        <div className="max-w-6xl mx-auto px-6 py-14">
          <div className="flex items-start justify-between flex-wrap gap-4 mb-3">
            <p className="font-mono text-xs uppercase tracking-[0.3em] text-leaf-700">
              {t("tagline")}
            </p>
            <LanguageSwitcher />
          </div>
          <h1 className="font-display text-5xl md:text-6xl font-semibold text-soil-900 tracking-tight">
            {t("appTitle")}
          </h1>
          <p className="mt-4 max-w-xl text-soil-700 text-base leading-relaxed">
            {t("heroDescription")}
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: inputs */}
        <div className="lg:col-span-1 space-y-6">
          <InputPanel
            fileName={file?.name}
            onFileSelect={handleFileSelect}
            location={location}
            onLocationChange={setLocation}
            crop={crop}
            onCropChange={setCrop}
            onAnalyze={handleAnalyze}
            loading={loading}
            error={error}
          />

          {soil && (
            <div>
              <h3 className="font-display text-sm font-semibold text-soil-800 mb-2 uppercase tracking-wide">
                {t("soilHealthHeading")}
              </h3>
              <SoilCore deficiencies={result?.deficiencies || []} soil={soil} />
              {soil.extraction_warnings?.length > 0 && (
                <p className="mt-2 text-xs text-soil-500 italic">
                  {t("extractionWarning", soil.extraction_warnings.length)}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Middle + right columns: results with modern 3-tab navigation */}
        <div className="lg:col-span-2 space-y-4">
          {/* Tabs Bar */}
          <div className="bg-white/80 backdrop-blur rounded-2xl border border-soil-300 p-1.5 flex items-center gap-1.5 shadow-sm">
            <button
              onClick={() => setActiveTab("analysis")}
              className={`flex-1 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-1.5 ${
                activeTab === "analysis"
                  ? "bg-soil-900 text-white shadow-sm"
                  : "text-soil-600 hover:text-soil-900 hover:bg-soil-100"
              }`}
            >
              <span>📋</span>
              <span className="truncate">{t("tabAnalysis")}</span>
              {result && (
                <span className="w-2 h-2 rounded-full bg-leaf-400 inline-block" title="Ready" />
              )}
            </button>

            <button
              onClick={() => setActiveTab("weather")}
              className={`flex-1 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-1.5 ${
                activeTab === "weather"
                  ? "bg-soil-900 text-white shadow-sm"
                  : "text-soil-600 hover:text-soil-900 hover:bg-soil-100"
              }`}
            >
              <span>🌤️</span>
              <span className="truncate">{t("tabWeather")}</span>
            </button>

            <button
              onClick={() => setActiveTab("chat")}
              className={`flex-1 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-1.5 ${
                activeTab === "chat"
                  ? "bg-soil-900 text-white shadow-sm"
                  : "text-soil-600 hover:text-soil-900 hover:bg-soil-100"
              }`}
            >
              <span>💬</span>
              <span className="truncate">{t("tabChat")}</span>
              <span className="text-[10px] bg-leaf-100 text-leaf-800 px-1.5 py-0.5 rounded font-mono hidden sm:inline">
                🎙️ Voice
              </span>
            </button>
          </div>

          {/* TAB 1: Analysis & Recommendations */}
          {activeTab === "analysis" && (
            <div className="space-y-6">
              {!result && (
                <div className="rounded-2xl border-2 border-dashed border-soil-300 p-12 text-center text-soil-400 bg-white/40 space-y-2">
                  <p className="text-base font-semibold text-soil-700">
                    {t("awaitingAnalysis")}
                  </p>
                  <p className="text-xs text-soil-500 max-w-md mx-auto">
                    Upload a soil test report (PDF) on the left and click Analyze to view crop suitability, targeted fertilizers, and soil parameters.
                  </p>
                  <div className="pt-3 flex justify-center gap-2">
                    <button
                      onClick={() => setActiveTab("weather")}
                      className="text-xs px-3 py-1.5 bg-soil-100 hover:bg-soil-200 text-soil-800 rounded-lg border border-soil-300 font-medium transition-colors"
                    >
                      🌤️ Check Weather & Spray Timing
                    </button>
                    <button
                      onClick={() => setActiveTab("chat")}
                      className="text-xs px-3 py-1.5 bg-leaf-50 hover:bg-leaf-100 text-leaf-900 rounded-lg border border-leaf-300 font-medium transition-colors"
                    >
                      💬 Ask AgriMind AI
                    </button>
                  </div>
                </div>
              )}

              {result && (
                <>
                  <RecommendationPanel
                    cropScores={result.crop_scores}
                    fertilizerOptions={result.fertilizer_options}
                  />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <WeatherPanel
                      applicationWindow={result.application_window}
                      location={location}
                      onLocationChange={setLocation}
                    />
                    <ChatBox
                      soil={soil}
                      selectedCrop={crop || null}
                      location={location || null}
                      recommendationResult={result}
                    />
                  </div>
                  <WhyPanel why={result.why} />
                  {result.llm_explanation && (
                    <div className="bg-leaf-50 border border-leaf-200 rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold text-leaf-800 mb-2">
                        {t("plainTermsHeading")}
                      </h3>
                      <p className="text-sm text-soil-800 leading-relaxed whitespace-pre-line">
                        {result.llm_explanation}
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* TAB 2: Weather & Timing (Available anytime) */}
          {activeTab === "weather" && (
            <div className="space-y-4">
              <WeatherPanel
                applicationWindow={result?.application_window}
                location={location}
                onLocationChange={setLocation}
              />
            </div>
          )}

          {/* TAB 3: Ask AgriMind Voice & Chat (Available anytime) */}
          {activeTab === "chat" && (
            <div className="space-y-4">
              <ChatBox
                soil={soil}
                selectedCrop={crop || null}
                location={location || null}
                recommendationResult={result}
              />
            </div>
          )}
        </div>
      </main>

      <footer className="max-w-6xl mx-auto px-6 py-8 text-xs text-soil-400 border-t border-soil-200">
        {t("footerDisclaimer")}
      </footer>
    </div>
  );
}
