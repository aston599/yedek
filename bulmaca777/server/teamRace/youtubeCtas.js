/** YouTube sohbetinden arenada yanan etkileşim rozetleri */

export const CTA_PULSE_MS = 12_000;

export const YOUTUBE_CTA_SLOTS = {
  like: {
    label: "2× ekrana tıkla",
    patterns: [
      /\b(beğen|begeni|begen|like|👍|❤️|💖)\b/i,
      /\b(çift|iki)\s*(kez\s*)?(tık|tik|tap)\b/i,
      /\b2\s*[x×]\s*(tık|tik|tap|ekran)\b/i,
      /\b2\s*kere\s*(tık|tik|tap|ekran)?\b/i,
      /\bdouble\s*tap\b/i,
    ],
  },
  subscribe: {
    label: "Abone ol",
    patterns: [/\babone\b/i, /\bsubscribe\b/i, /\bsubs?\b/i, /\büye\s*ol\b/i],
  },
  follow: {
    label: "Takip et",
    patterns: [/\btakip\b/i, /\bfollow\b/i, /\btakipçi\b/i],
  },
};

/**
 * @param {string} text
 * @returns {Array<keyof typeof YOUTUBE_CTA_SLOTS>}
 */
export function detectYoutubeCtas(text) {
  const raw = String(text || "").trim();
  if (!raw) return [];
  const hits = [];
  for (const [key, slot] of Object.entries(YOUTUBE_CTA_SLOTS)) {
    if (slot.patterns.some((re) => re.test(raw))) hits.push(key);
  }
  return hits;
}

/**
 * @param {Record<string, { until?: number, author?: string | null }>} pulses
 */
export function buildArenaCtasSnapshot(pulses) {
  const now = Date.now();
  const out = {};
  for (const [key, slot] of Object.entries(YOUTUBE_CTA_SLOTS)) {
    const row = pulses[key] || {};
    const until = Number(row.until) || 0;
    const active = until > now;
    out[key] = {
      active,
      label: slot.label,
      author: active ? row.author || null : null,
      remainingMs: active ? until - now : 0,
    };
  }
  return out;
}
