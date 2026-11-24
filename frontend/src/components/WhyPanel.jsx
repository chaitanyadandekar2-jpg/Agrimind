import { useLanguage } from "../i18n/LanguageContext";

export default function WhyPanel({ why }) {
  const { t } = useLanguage();
  if (!why) return null;

  const confidencePct = Math.round((why.confidence ?? 0) * 100);
  const confidenceColor =
    confidencePct >= 80 ? "bg-leaf-500" : confidencePct >= 50 ? "bg-wheat-400" : "bg-red-400";

  return (
    <div className="bg-soil-900 text-soil-50 rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-semibold">{t("whyHeading")}</h3>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-soil-300">{t("confidenceLabel")}</span>
          <div className="w-20 h-1.5 rounded-full bg-soil-700 overflow-hidden">
            <div className={`h-full ${confidenceColor}`} style={{ width: `${confidencePct}%` }} />
          </div>
          <span className="data-readout text-xs">{confidencePct}%</span>
        </div>
      </div>

      {why.contradictions?.length > 0 && (
        <div className="bg-red-950/60 border border-red-800 rounded-lg px-3 py-2">
          {why.contradictions.map((c, i) => (
            <p key={i} className="text-sm text-red-200">
              ⚠ {c}
            </p>
          ))}
        </div>
      )}

      {/* reason_soil, weather_factor, and evidence text all come straight
          from the engine/RAG knowledge base in English -- not localized,
          since the knowledge base itself (markdown source docs) is
          English-only. The LLM "In plain terms" box above/below this panel
          is where the localized explanation lives. */}
      <p className="text-sm text-soil-200 leading-relaxed">{why.reason_soil}</p>

      {why.weather_factor && (
        <p className="text-sm text-soil-200">
          <span className="text-soil-400 font-mono text-xs uppercase mr-2">{t("weatherFactorLabel")}</span>
          {why.weather_factor}
        </p>
      )}

      {why.evidence?.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-soil-700">
          <p className="text-[11px] font-mono uppercase tracking-wider text-soil-400">{t("retrievedEvidenceLabel")}</p>
          {why.evidence.map((e, i) => (
            <div key={i} className="text-xs text-soil-300 bg-soil-800/60 rounded-lg px-3 py-2">
              <div className="flex justify-between mb-1">
                <span className="text-leaf-400 font-mono">{e.source}</span>
                <span className="text-soil-500 font-mono">{t("relevanceLabel")} {e.score}</span>
              </div>
              <p className="text-soil-200">{e.text.slice(0, 220)}{e.text.length > 220 ? "…" : ""}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
