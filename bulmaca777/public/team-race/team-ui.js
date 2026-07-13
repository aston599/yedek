/** Paylaşılan takım yarışı UI yardımcıları (bayrak + kazanan metinleri) */

export const WIN_REASON_LABELS = {
  last_standing: "Son kalan takım",
  most_on_arena: "Arenada en çok top",
  most_spawns: "En çok katılım",
};

export function winReasonLabel(code) {
  return WIN_REASON_LABELS[code] || code || "";
}

export function teamFlagUrl(teamCode, flagUrl) {
  if (flagUrl) return flagUrl;
  const c = String(teamCode || "")
    .trim()
    .toLowerCase();
  if (!c) return "";
  return `/team-race/flags/${c}.png`;
}

/**
 * @param {string} src
 * @param {"xs"|"sm"|"md"|"lg"|"xl"|"2xl"} [size]
 * @param {string} [alt]
 */
export function teamFlagImg(src, size = "sm", alt = "") {
  const safeSrc = String(src || "").replace(/"/g, "&quot;");
  const safeAlt = String(alt || "").replace(/"/g, "&quot;");
  return `<img class="team-flag team-flag--${size}" src="${safeSrc}" alt="${safeAlt}" loading="lazy" decoding="async" />`;
}

/** Kazananlar paneli: tur numarasına göre sıralı liste */
export function sortedRoundWinners(history = [], maxRounds = 8) {
  const cap = Math.max(1, Number(maxRounds) || 8);
  return [...history]
    .filter((r) => r?.teamCode)
    .sort((a, b) => (Number(a.round) || 0) - (Number(b.round) || 0))
    .slice(0, cap);
}

export function formatWinnerLines(winner, snapRound) {
  const w = winner || {};
  const round = w.round || snapRound || "?";
  const name = w.teamName || w.teamCode || "—";
  const reason = winReasonLabel(w.winReason);
  const spawns = w.spawnCount ?? 0;
  return {
    title: `Tur ${round} kazananı`,
    name,
    badge: reason,
    meta: `${spawns} top · ${reason}`,
  };
}
