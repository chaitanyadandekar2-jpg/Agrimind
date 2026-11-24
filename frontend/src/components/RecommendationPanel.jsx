import { useLanguage } from "../i18n/LanguageContext";

export default function RecommendationPanel({ cropScores, fertilizerOptions }) {
  const { t, cropLabel, fertilizerTypeLabel } = useLanguage();

  return (
    <div className="bg-white/70 backdrop-blur rounded-2xl border border-soil-300 p-6 space-y-6 shadow-sm">
      {/* Crop Suitability Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-lg font-semibold text-soil-900">{t("cropSuitabilityHeading")}</h3>
          <span className="text-[11px] font-mono text-soil-500 uppercase tracking-wider">Deterministic Engine</span>
        </div>

        <div className="space-y-3">
          {cropScores.length === 0 && <p className="text-sm text-soil-500">{t("noCropScores")}</p>}
          {cropScores.map((c) => {
            const isTop = c.score >= 80;
            return (
              <div key={c.name} className="border border-soil-200/80 rounded-xl p-3 bg-soil-50/60 space-y-2">
                <div className="flex items-center gap-3">
                  <span className="w-36 text-sm font-semibold text-soil-900 truncate">{cropLabel(c.name)}</span>
                  <div className="flex-1 h-2 rounded-full bg-soil-200/60 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${isTop ? "bg-leaf-600" : c.score >= 50 ? "bg-wheat-500" : "bg-red-400"}`}
                      style={{ width: `${c.score}%` }}
                    />
                  </div>
                  <span className="data-readout text-xs font-bold text-soil-800 w-12 text-right">{c.score}/100</span>
                  {c.suitability_category && (
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full ${
                        isTop ? "bg-leaf-100 text-leaf-800 border border-leaf-300" : "bg-soil-200 text-soil-700"
                      }`}
                    >
                      {c.suitability_category}
                    </span>
                  )}
                </div>

                {/* Limiting factors or required improvements */}
                {c.limiting_factors && c.limiting_factors.length > 0 && (
                  <div className="text-xs text-soil-600 pl-1 border-l-2 border-wheat-400">
                    <span className="font-medium text-soil-700">Limits: </span>
                    {c.limiting_factors.join("; ")}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Fertilizer & Soil Amendments Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-lg font-semibold text-soil-900">{t("fertilizerHeading")}</h3>
          <span className="text-[11px] font-mono text-soil-500 uppercase tracking-wider">Deficiency-Driven</span>
        </div>

        {fertilizerOptions.length === 0 ? (
          <p className="text-sm text-soil-500">{t("noFertilizerNeeded")}</p>
        ) : (
          <ul className="space-y-3">
            {fertilizerOptions.map((f, i) => {
              const isOrganic = f.type === "organic";
              const isFoliar = f.application_method === "foliar";
              return (
                <li key={i} className="border border-soil-200 rounded-xl p-3 bg-white shadow-xs space-y-1.5">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="font-semibold text-sm text-soil-900">{f.name}</span>
                    <div className="flex items-center gap-1.5">
                      {isFoliar && (
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                          Foliar Spray
                        </span>
                      )}
                      <span
                        className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full ${
                          isOrganic ? "bg-leaf-100 text-leaf-800 border border-leaf-300" : "bg-wheat-100 text-soil-800 border border-wheat-300"
                        }`}
                      >
                        {fertilizerTypeLabel(f.type)}
                      </span>
                    </div>
                  </div>

                  {f.growth_stage && (
                    <p className="text-xs text-leaf-700 font-medium">
                      Stage: <span className="text-soil-700">{f.growth_stage}</span>
                    </p>
                  )}

                  <p className="text-xs text-soil-600 leading-relaxed">{f.application_notes}</p>

                  {f.compatibility_notes && (
                    <p className="text-[11px] text-soil-500 italic">
                      Tip: {f.compatibility_notes}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
