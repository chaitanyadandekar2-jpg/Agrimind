import { useState, useEffect } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { applyTodayLabels, recommendationLabels, sprayStatusLabels } from "../i18n/translations";
import { getWeatherForecast } from "../api";

function getHourlySpraySlots(hourlyWindows, hourlyToday) {
  if (Array.isArray(hourlyWindows) && hourlyWindows.length > 0) {
    const filtered = hourlyWindows.filter((h) => h.hour >= 6 && h.hour <= 17);
    if (filtered.length > 0) return filtered;
  }
  if (!Array.isArray(hourlyToday) || hourlyToday.length === 0) return [];

  return hourlyToday
    .filter((h) => h.hour >= 6 && h.hour <= 17)
    .map((h) => {
      const temp = h.temperature_c ?? 25;
      const wind = h.wind_kmh ?? 0;
      const rainProb = h.precipitation_prob_pct ?? 0;
      const rainMm = h.precipitation_mm ?? 0;
      const humidity = h.humidity_pct ?? 60;

      const unsafe = [];
      const caution = [];
      if (wind >= 15) unsafe.push(`High wind (${wind} km/h) causes spray drift`);
      else if (wind >= 12) caution.push(`Moderate breeze (${wind} km/h) requires drift nozzles`);

      if (temp >= 32) unsafe.push(`High heat (${temp}°C) causes leaf scorch & evaporation`);
      else if (temp >= 30) caution.push(`Elevated temperature (${temp}°C)`);

      if (rainMm >= 0.5 || rainProb >= 40) unsafe.push(`Rain risk (${rainProb}%, ${rainMm}mm) washes off spray`);
      else if (rainProb >= 25) caution.push(`Moderate rain probability (${rainProb}%)`);

      if (humidity < 35) caution.push(`Low humidity (${humidity}%) reduces droplet uptake`);

      let status = "GO";
      let summary = "Optimal spray window: stable winds and favorable leaf absorption.";
      if (unsafe.length > 0) {
        status = "AVOID";
        summary = "Unfavorable: " + unsafe.join("; ");
      } else if (caution.length > 0) {
        status = "CAUTION";
        summary = "Caution: " + caution.join("; ");
      }

      const displayTime = `${h.hour % 12 || 12}:00 ${h.hour < 12 ? "AM" : "PM"}`;
      return {
        hour: h.hour,
        time_label: `${String(h.hour).padStart(2, "0")}:00`,
        display_time: displayTime,
        status,
        temperature_c: temp,
        humidity_pct: humidity,
        precipitation_prob_pct: rainProb,
        precipitation_mm: rainMm,
        wind_kmh: wind,
        reasons: unsafe.length ? unsafe : caution.length ? caution : ["Ideal spray window"],
        summary,
      };
    });
}

function HourlySprayTimelineComponent({ slots, t, lang }) {
  const [selectedHour, setSelectedHour] = useState(slots[0]?.hour ?? 6);

  useEffect(() => {
    if (slots.length > 0 && !slots.some((s) => s.hour === selectedHour)) {
      const preferred = slots.find((s) => s.status === "GO") || slots[0];
      if (preferred) setSelectedHour(preferred.hour);
    }
  }, [slots, selectedHour]);

  if (!slots || slots.length === 0) return null;

  const current = slots.find((s) => s.hour === selectedHour) || slots[0];
  const statusDict = sprayStatusLabels[lang] || sprayStatusLabels.en;

  const safeCount = slots.filter((s) => s.status === "GO").length;
  const cautionCount = slots.filter((s) => s.status === "CAUTION").length;
  const avoidCount = slots.filter((s) => s.status === "AVOID").length;

  return (
    <div className="space-y-3 pt-3 border-t border-soil-200">
      {/* Header and statistics pills */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-soil-900 flex items-center gap-1.5">
            <span>⏱️</span>
            <span>{t("hourlySprayTimeline")}</span>
          </h4>
          <p className="text-xs text-soil-500">{t("hourlySpraySubtitle")}</p>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono">
          <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
            ● {safeCount} {t("spraySafeBadge")}
          </span>
          {cautionCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
              ● {cautionCount} {t("sprayCautionBadge")}
            </span>
          )}
          {avoidCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200 font-semibold">
              ● {avoidCount} {t("sprayAvoidBadge")}
            </span>
          )}
        </div>
      </div>

      {/* 12-Hour Timeline Strip (06:00 to 17:00 / 6 AM to 5 PM) */}
      <div className="overflow-x-auto pb-2 -mx-1 px-1">
        <div className="grid grid-flow-col auto-cols-[minmax(72px,1fr)] gap-2 min-w-[760px] sm:min-w-0 sm:grid-cols-6 lg:grid-cols-12">
          {slots.map((s) => {
            const isSelected = s.hour === selectedHour;
            const isGo = s.status === "GO";
            const isCaution = s.status === "CAUTION";

            const badgeBg = isGo
              ? "bg-emerald-600 text-white"
              : isCaution
              ? "bg-amber-500 text-white"
              : "bg-rose-500 text-white";

            const cardBorder = isSelected
              ? "border-soil-900 ring-2 ring-soil-900 shadow-md bg-white"
              : isGo
              ? "border-emerald-200 bg-emerald-50/40 hover:bg-emerald-50"
              : isCaution
              ? "border-amber-200 bg-amber-50/40 hover:bg-amber-50"
              : "border-rose-200 bg-rose-50/40 hover:bg-rose-50";

            return (
              <button
                key={s.hour}
                type="button"
                onClick={() => setSelectedHour(s.hour)}
                className={`p-2 rounded-xl border text-center transition-all cursor-pointer flex flex-col justify-between items-center ${cardBorder}`}
              >
                <div className="text-[11px] font-bold text-soil-800">
                  {s.time_label}
                </div>
                <div className="text-[10px] text-soil-500 font-mono mb-1">
                  {s.display_time.split(" ")[1]}
                </div>

                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider mb-1.5 ${badgeBg}`}>
                  {s.status === "GO" ? "GO" : s.status === "CAUTION" ? "WARN" : "STOP"}
                </span>

                <div className="w-full text-[10px] text-soil-600 space-y-0.5 pt-1 border-t border-soil-200/60 font-mono">
                  <div className="font-semibold text-soil-900">{Math.round(s.temperature_c)}°C</div>
                  <div className="text-soil-500">{Math.round(s.wind_kmh)}k</div>
                  <div className={s.precipitation_prob_pct > 25 ? "text-blue-600 font-semibold" : "text-soil-400"}>
                    {s.precipitation_prob_pct}%
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="text-[11px] text-soil-500 italic flex items-center justify-between">
        <span>💡 {t("clickHourDetail")}</span>
        <span className="font-mono text-soil-400">06:00 – 17:00 (12h)</span>
      </div>

      {/* Selected Hour Full Agronomic Diagnosis Box */}
      {current && (
        <div
          className={`p-4 rounded-xl border transition-colors ${
            current.status === "GO"
              ? "bg-emerald-50/60 border-emerald-300"
              : current.status === "CAUTION"
              ? "bg-amber-50/60 border-amber-300"
              : "bg-rose-50/60 border-rose-300"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="text-base font-semibold text-soil-900">
                🎯 {t("selectedHourInfo")} <span className="underline decoration-soil-400">{current.display_time} ({current.time_label})</span>
              </span>
            </div>
            <span
              className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider ${
                current.status === "GO"
                  ? "bg-emerald-600 text-white"
                  : current.status === "CAUTION"
                  ? "bg-amber-600 text-white"
                  : "bg-rose-600 text-white"
              }`}
            >
              {statusDict[current.status] || current.status}
            </span>
          </div>

          {/* Metrics breakdown row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
            <div className="bg-white/80 p-2 rounded-lg border border-soil-200 text-xs">
              <span className="text-soil-500 block text-[10px]">{t("tempLabel")}</span>
              <span className="font-bold text-soil-900 text-sm">{current.temperature_c}°C</span>
              <span className="block text-[10px] text-soil-500">
                {current.temperature_c >= 32
                  ? "⚠️ Evaporation/Burn risk"
                  : current.temperature_c >= 30
                  ? "⚠️ Warm conditions"
                  : "✓ Safe absorption (<30°C)"}
              </span>
            </div>
            <div className="bg-white/80 p-2 rounded-lg border border-soil-200 text-xs">
              <span className="text-soil-500 block text-[10px]">{t("windLabel")}</span>
              <span className="font-bold text-soil-900 text-sm">{current.wind_kmh} km/h</span>
              <span className="block text-[10px] text-soil-500">
                {current.wind_kmh >= 15
                  ? "⚠️ High spray drift risk"
                  : current.wind_kmh >= 12
                  ? "⚠️ Moderate breeze"
                  : "✓ Safe wind (<12 km/h)"}
              </span>
            </div>
            <div className="bg-white/80 p-2 rounded-lg border border-soil-200 text-xs">
              <span className="text-soil-500 block text-[10px]">{t("rainLabel")}</span>
              <span className="font-bold text-soil-900 text-sm">
                {current.precipitation_prob_pct}% ({current.precipitation_mm}mm)
              </span>
              <span className="block text-[10px] text-soil-500">
                {current.precipitation_prob_pct >= 40
                  ? "⚠️ Wash-off hazard"
                  : current.precipitation_prob_pct >= 25
                  ? "⚠️ Shower chance"
                  : "✓ Dry foliage"}
              </span>
            </div>
            <div className="bg-white/80 p-2 rounded-lg border border-soil-200 text-xs">
              <span className="text-soil-500 block text-[10px]">{t("humidityLabel")}</span>
              <span className="font-bold text-soil-900 text-sm">{current.humidity_pct}%</span>
              <span className="block text-[10px] text-soil-500">
                {current.humidity_pct < 35 ? "⚠️ Fast droplet drying" : "✓ Good leaf penetration"}
              </span>
            </div>
          </div>

          {/* Advice / Agronomic reasoning */}
          <div className="text-xs text-soil-800 bg-white/90 p-2.5 rounded-lg border border-soil-200 space-y-1">
            <span className="font-semibold block text-soil-900">🌾 Agronomic Spray Assessment:</span>
            <p className="leading-relaxed">{current.summary}</p>
            {current.reasons && current.reasons.length > 0 && (
              <ul className="list-disc list-inside text-soil-600 text-[11px] pt-1 space-y-0.5">
                {current.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function WeatherPanel({ applicationWindow, location = "", onLocationChange }) {
  const { t, lang } = useLanguage();
  const applyLabel = (code) => (applyTodayLabels[lang] || applyTodayLabels.en)[code] || code;
  const recLabel = (code) => (recommendationLabels[lang] || recommendationLabels.en)[code] || code;

  const [inputLoc, setInputLoc] = useState(location);
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (location && location !== inputLoc) {
      setInputLoc(location);
    }
  }, [location]);

  // Auto-fetch weather forecast if location is set and forecastData is missing
  useEffect(() => {
    if (location && !forecastData && !loading) {
      fetchWeather(location);
    }
  }, [location]);

  async function fetchWeather(targetLoc) {
    const loc = (targetLoc || inputLoc).trim();
    if (!loc) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getWeatherForecast(loc);
      setForecastData(data);
      if (onLocationChange && loc !== location) {
        onLocationChange(loc);
      }
    } catch (err) {
      setError(err.message || "Failed to load weather");
    } finally {
      setLoading(false);
    }
  }

  // 1. If recommendation result's applicationWindow is provided (after uploading soil test report)
  if (applicationWindow) {
    const {
      recommendation,
      apply_today,
      reason,
      next_window,
      forecast_summary,
      morning_window,
      evening_window,
      hourly_windows,
      application_type,
    } = applicationWindow;
    const isGo = apply_today === "GO";

    const slots = getHourlySpraySlots(
      hourly_windows || forecastData?.spray_timeline,
      forecastData?.hourly_today
    );

    return (
      <div className="bg-white/70 backdrop-blur rounded-2xl border border-soil-300 p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-soil-900">{t("weatherHeading")}</h3>
          {application_type === "foliar" && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
              Foliar Spray Window
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1.5 rounded-full text-xs font-mono uppercase tracking-wide font-bold ${
              isGo ? "bg-leaf-600 text-white" : "bg-wheat-400 text-soil-900"
            }`}
          >
            {t("todayLabel")}: {applyLabel(apply_today)}
          </span>
          <span className="text-xs text-soil-600 font-mono">
            {t("recommendationLabel")}: <strong className="text-soil-900">{recLabel(recommendation)}</strong>
          </span>
        </div>

        <p className="text-sm text-soil-700 leading-relaxed">{reason}</p>

        {/* Quick summary: Morning & Evening */}
        {(morning_window || evening_window) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-soil-200">
            {morning_window && (
              <div className="bg-soil-50 rounded-lg p-2.5 text-xs border border-soil-200 space-y-1">
                <span className="font-semibold text-soil-800 block">🌅 Morning (06:00-10:00)</span>
                <span className="text-soil-600">{morning_window}</span>
              </div>
            )}
            {evening_window && (
              <div className="bg-soil-50 rounded-lg p-2.5 text-xs border border-soil-200 space-y-1">
                <span className="font-semibold text-soil-800 block">🌇 Evening (16:00-19:00)</span>
                <span className="text-soil-600">{evening_window}</span>
              </div>
            )}
          </div>
        )}

        {/* Hourly Agricultural Spray Feasibility Timeline (06:00 AM - 05:00 PM) */}
        {slots.length > 0 && (
          <HourlySprayTimelineComponent slots={slots} t={t} lang={lang} />
        )}

        {next_window && (
          <p className="text-sm text-soil-800 font-medium pt-2 border-t border-soil-200">
            {t("nextWindowLabel")}: <span className="data-readout font-bold text-leaf-700">{next_window}</span>
          </p>
        )}

        {forecast_summary && (
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-soil-200">
            {forecast_summary.precipitation_mm != null && (
              <div className="text-xs text-soil-600">
                {t("rainLabel")}:{" "}
                <span className="data-readout font-medium">
                  {forecast_summary.precipitation_mm} mm ({forecast_summary.precipitation_probability_pct}%)
                </span>
              </div>
            )}
            {forecast_summary.temp_max_c != null && (
              <div className="text-xs text-soil-600">
                {t("tempLabel")}:{" "}
                <span className="data-readout font-medium">
                  {forecast_summary.temp_min_c}–{forecast_summary.temp_max_c}°C
                </span>
              </div>
            )}
            {forecast_summary.wind_max_kmh != null && (
              <div className="text-xs text-soil-600">
                {t("windLabel")}:{" "}
                <span className="data-readout font-medium">{forecast_summary.wind_max_kmh} km/h</span>
              </div>
            )}
            {forecast_summary.humidity_max_pct != null && (
              <div className="text-xs text-soil-600">
                {t("humidityLabel")}:{" "}
                <span className="data-readout font-medium">{forecast_summary.humidity_max_pct}%</span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // 2. Standalone Weather View (accessible without uploading PDF report)
  const today = forecastData?.days?.[0];
  const morningSlot = forecastData?.windows?.morning;
  const eveningSlot = forecastData?.windows?.evening;
  const standaloneSlots = getHourlySpraySlots(
    forecastData?.spray_timeline,
    forecastData?.hourly_today
  );

  return (
    <div className="bg-white/70 backdrop-blur rounded-2xl border border-soil-300 p-6 space-y-5 shadow-sm">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="font-display text-lg font-semibold text-soil-900">{t("weatherHeading")}</h3>
          <p className="text-xs text-soil-500">{t("enterLocationForWeather")}</p>
        </div>
        {location && (
          <span className="text-xs font-mono bg-leaf-50 text-leaf-800 border border-leaf-200 px-2.5 py-1 rounded-full">
            📍 {location}
          </span>
        )}
      </div>

      {/* Location Search Bar */}
      <div className="flex gap-2">
        <input
          value={inputLoc}
          onChange={(e) => setInputLoc(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && fetchWeather()}
          placeholder="e.g. Nagpur, Maharashtra, India"
          className="flex-1 px-3 py-2 rounded-lg border border-soil-300 text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 bg-white"
        />
        <button
          onClick={() => fetchWeather()}
          disabled={loading || !inputLoc.trim()}
          className="px-4 py-2 rounded-lg bg-soil-900 hover:bg-soil-800 text-white text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {loading ? t("loadingWeather") : t("checkWeather")}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* Loaded Forecast Overview */}
      {today && (
        <div className="space-y-4 pt-1">
          {/* Key metrics grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-soil-50 rounded-xl border border-soil-200">
              <span className="text-[11px] text-soil-500 block">{t("tempLabel")}</span>
              <span className="text-base font-semibold text-soil-900">
                {today.temp_min_c}° – {today.temp_max_c}°C
              </span>
            </div>
            <div className="p-3 bg-soil-50 rounded-xl border border-soil-200">
              <span className="text-[11px] text-soil-500 block">{t("rainLabel")}</span>
              <span className="text-base font-semibold text-soil-900">
                {today.precipitation_mm} mm ({today.precipitation_probability_pct}%)
              </span>
            </div>
            <div className="p-3 bg-soil-50 rounded-xl border border-soil-200">
              <span className="text-[11px] text-soil-500 block">{t("windLabel")}</span>
              <span className="text-base font-semibold text-soil-900">
                {today.wind_max_kmh} km/h
              </span>
            </div>
            <div className="p-3 bg-soil-50 rounded-xl border border-soil-200">
              <span className="text-[11px] text-soil-500 block">{t("humidityLabel")}</span>
              <span className="text-base font-semibold text-soil-900">
                {today.humidity_max_pct}%
              </span>
            </div>
          </div>

          {/* Quick summary: Morning & Evening */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-soil-600">
              Quick Morning & Evening Overview
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {morningSlot && (
                <div className="p-3 rounded-xl border border-soil-200 bg-white space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-soil-800">🌅 Morning (06:00 – 10:00)</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        morningSlot.status === "GO"
                          ? "bg-leaf-600 text-white"
                          : "bg-wheat-300 text-soil-900"
                      }`}
                    >
                      {morningSlot.status}
                    </span>
                  </div>
                  <p className="text-xs text-soil-600">{morningSlot.detail}</p>
                  <p className="text-[11px] text-soil-400">
                    Temp: {morningSlot.temp_avg_c}°C · Wind: {morningSlot.wind_max_kmh} km/h · Rain: {morningSlot.rain_prob_pct}%
                  </p>
                </div>
              )}

              {eveningSlot && (
                <div className="p-3 rounded-xl border border-soil-200 bg-white space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-soil-800">🌇 Evening (16:00 – 19:00)</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        eveningSlot.status === "GO"
                          ? "bg-leaf-600 text-white"
                          : "bg-wheat-300 text-soil-900"
                      }`}
                    >
                      {eveningSlot.status}
                    </span>
                  </div>
                  <p className="text-xs text-soil-600">{eveningSlot.detail}</p>
                  <p className="text-[11px] text-soil-400">
                    Temp: {eveningSlot.temp_avg_c}°C · Wind: {eveningSlot.wind_max_kmh} km/h · Rain: {eveningSlot.rain_prob_pct}%
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Full Hourly Agricultural Spray Feasibility Timeline (06:00 AM - 05:00 PM) */}
          {standaloneSlots.length > 0 && (
            <HourlySprayTimelineComponent slots={standaloneSlots} t={t} lang={lang} />
          )}

          {/* 5-Day Outlook */}
          {forecastData?.days?.length > 1 && (
            <div className="pt-2 border-t border-soil-200">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-soil-600 mb-2">
                5-Day Forecast Outlook
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {forecastData.days.map((d, idx) => (
                  <div key={idx} className="p-2 bg-soil-50 rounded-lg text-center text-xs border border-soil-200">
                    <span className="block font-medium text-soil-700 text-[11px]">
                      {idx === 0 ? "Today" : d.date.slice(5)}
                    </span>
                    <span className="block font-bold text-soil-900 text-xs">
                      {d.temp_max_c}° / {d.temp_min_c}°
                    </span>
                    <span className="block text-[10px] text-soil-500">
                      🌧 {d.precipitation_probability_pct}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
