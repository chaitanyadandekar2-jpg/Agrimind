import { useLanguage } from "../i18n/LanguageContext";

export default function LanguageSwitcher() {
  const { lang, setLang, languages, t } = useLanguage();

  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-mono uppercase tracking-wider text-soil-500">{t("languageLabel")}</span>
      <div className="flex rounded-full border border-soil-300 overflow-hidden bg-white/80">
        {languages.map((l) => (
          <button
            key={l.code}
            onClick={() => setLang(l.code)}
            className={`px-3 py-1 text-xs font-medium transition-colors ${
              lang === l.code ? "bg-leaf-600 text-white" : "text-soil-700 hover:bg-soil-100"
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>
    </div>
  );
}
