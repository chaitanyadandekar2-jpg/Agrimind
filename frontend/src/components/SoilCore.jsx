import { useLanguage } from "../i18n/LanguageContext";

const STATUS_COLOR = {
  LOW: "bg-wheat-400/90 text-soil-900",
  MEDIUM: "bg-leaf-400/80 text-soil-900",
  HIGH: "bg-leaf-700 text-soil-50",
  UNKNOWN: "bg-soil-100 text-soil-500 italic",
};

// Micronutrients only have two real states (deficient/sufficient), so the
// badge reads more clearly than reusing the N/P/K LOW/MEDIUM/HIGH wording.
// Internally status is still "LOW"/"HIGH" (API contract unchanged); this
// just maps to the DEFICIENT/SUFFICIENT translation key for display.
const MICRO_BADGE_KEY = { LOW: "DEFICIENT", HIGH: "SUFFICIENT", UNKNOWN: "UNKNOWN" };

/**
 * Renders soil nutrient status as horizontal strata, like a soil core
 * sample cross-section pulled from the ground - the app's signature visual.
 */
export default function SoilCore({ deficiencies, soil }) {
  const { t, statusLabel, nutrientLabel } = useLanguage();

  const rows = ["nitrogen", "phosphorus", "potassium", "organic_carbon"].map((key) => {
    const d = deficiencies.find((x) => x.nutrient === key);
    const field = soil?.[key];
    const status = d ? d.status : "UNKNOWN";
    return {
      key,
      label: nutrientLabel(key),
      status,
      badgeText: statusLabel(status),
      value: field ? `${field.value}${field.unit ? " " + field.unit : ""}` : "—",
    };
  });

  const microRows = ["zinc", "iron", "sulphur"]
    .map((key) => {
      const d = deficiencies.find((x) => x.nutrient === key);
      const field = soil?.[key];
      if (!field) return null; // only show micronutrients actually present in the report
      const status = d ? d.status : "UNKNOWN";
      return {
        key,
        label: nutrientLabel(key),
        status,
        badgeText: statusLabel(MICRO_BADGE_KEY[status]),
        value: `${field.value}${field.unit ? " " + field.unit : ""}`,
      };
    })
    .filter(Boolean);

  return (
    <div className="rounded-xl overflow-hidden border border-soil-300 shadow-sm">
      {rows.map((row) => (
        <div
          key={row.key}
          className={`flex items-center justify-between px-4 py-3 layer-divider ${STATUS_COLOR[row.status]}`}
        >
          <span className="font-body text-sm font-medium">{row.label}</span>
          <div className="flex items-center gap-3">
            <span className="data-readout text-sm">{row.value}</span>
            <span className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-black/10">
              {row.badgeText}
            </span>
          </div>
        </div>
      ))}
      {soil?.ph && (
        <div className="flex items-center justify-between px-4 py-3 bg-soil-50 border-t border-soil-300">
          <span className="font-body text-sm font-medium text-soil-700">{t("soilPh")}</span>
          <span className="data-readout text-sm text-soil-900">{soil.ph.value}</span>
        </div>
      )}

      {microRows.length > 0 && (
        <>
          <div className="px-4 py-2 bg-soil-900 text-soil-300 text-[11px] font-mono uppercase tracking-wider">
            {t("micronutrientsHeading")}
          </div>
          {microRows.map((row) => (
            <div
              key={row.key}
              className={`flex items-center justify-between px-4 py-3 layer-divider ${STATUS_COLOR[row.status]}`}
            >
              <span className="font-body text-sm font-medium">{row.label}</span>
              <div className="flex items-center gap-3">
                <span className="data-readout text-sm">{row.value}</span>
                <span className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-black/10">
                  {row.badgeText}
                </span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
