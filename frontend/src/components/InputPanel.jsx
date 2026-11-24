import { useRef } from "react";
import { useLanguage } from "../i18n/LanguageContext";

const CROPS = [
  "",
  "Tomato",
  "Wheat",
  "Rice (Paddy)",
  "Cotton",
  "Soybean",
  "Onion",
  "Sugarcane",
  "Chickpea (Gram)",
  "Maize",
  "Groundnut",
  "Mustard",
  "Potato",
];

export default function InputPanel({
  fileName,
  onFileSelect,
  location,
  onLocationChange,
  crop,
  onCropChange,
  onAnalyze,
  loading,
  error,
}) {
  const fileInputRef = useRef(null);
  const { t, cropLabel } = useLanguage();

  return (
    <div className="bg-white/70 backdrop-blur rounded-2xl border border-soil-300 p-6 space-y-5">
      <div>
        <label className="block text-xs font-mono uppercase tracking-wider text-soil-500 mb-2">
          {t("step1Title")}
        </label>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full text-left px-4 py-3 rounded-lg border-2 border-dashed border-soil-300 hover:border-leaf-500 transition-colors bg-soil-50 text-sm"
        >
          {fileName ? (
            <span className="text-soil-900 font-medium">{fileName}</span>
          ) : (
            <span className="text-soil-500">{t("step1Placeholder")}</span>
          )}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && onFileSelect(e.target.files[0])}
        />
      </div>

      <div>
        <label className="block text-xs font-mono uppercase tracking-wider text-soil-500 mb-2">
          {t("step2Title")}
        </label>
        <input
          type="text"
          value={location}
          onChange={(e) => onLocationChange(e.target.value)}
          placeholder={t("step2Placeholder")}
          className="w-full px-4 py-3 rounded-lg border border-soil-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500"
        />
      </div>

      <div>
        <label className="block text-xs font-mono uppercase tracking-wider text-soil-500 mb-2">
          {t("step3Title")}
        </label>
        <select
          value={crop}
          onChange={(e) => onCropChange(e.target.value)}
          className="w-full px-4 py-3 rounded-lg border border-soil-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500"
        >
          <option value="">{t("cropAutoRank")}</option>
          {CROPS.filter(Boolean).map((c) => (
            <option key={c} value={c}>
              {cropLabel(c)}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}

      <button
        onClick={onAnalyze}
        disabled={loading}
        className="w-full py-3 rounded-lg bg-leaf-600 hover:bg-leaf-700 disabled:opacity-50 text-white font-display font-semibold tracking-wide transition-colors"
      >
        {loading ? t("analyzing") : t("analyze")}
      </button>
    </div>
  );
}
