/** Türkçe karakterleri normalize ederek cevap karşılaştırması */
export function normalizeAnswer(text) {
  if (!text || typeof text !== "string") return "";
  return text
    .trim()
    .toLocaleLowerCase("tr-TR")
    .replace(/ı/g, "i")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ş/g, "s")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c")
    .replace(/\s+/g, " ");
}

export function answersMatch(userText, acceptedAnswers) {
  const normalized = normalizeAnswer(userText);
  if (!normalized) {
    const num = String(userText || "").match(/\b(\d{1,3})\b/);
    if (num) {
      const n = num[1];
      return acceptedAnswers.some((a) => String(a).replace(/\D/g, "") === n);
    }
    return false;
  }
  if (acceptedAnswers.some((a) => normalizeAnswer(a) === normalized)) return true;
  const digits = normalized.replace(/\D/g, "");
  if (digits) {
    return acceptedAnswers.some((a) => String(normalizeAnswer(a)).replace(/\D/g, "") === digits);
  }
  return false;
}

/** Yorumdan cevap çıkar: "cevap" veya "cevap - isim" formatları */
export function extractAnswerFromComment(text) {
  const trimmed = text.trim();
  const dashSplit = trimmed.split(/\s*[-–—]\s*/);
  if (dashSplit.length >= 2) {
    return dashSplit[0].trim();
  }
  return trimmed;
}

/** "cevap - isim" formatında isim varsa döner */
export function extractNameFromComment(text) {
  const trimmed = text.trim();
  const dashSplit = trimmed.split(/\s*[-–—]\s*/);
  if (dashSplit.length >= 2) {
    return dashSplit.slice(1).join(" - ").trim() || null;
  }
  return null;
}

export function fillTemplate(template, vars) {
  return template.replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? "");
}

/** YouTube watch, youtu.be, /live/, embed linklerinden video ID */
export function parseYouTubeVideoId(input) {
  if (!input || typeof input !== "string") return null;
  const raw = input.trim();
  if (!raw) return null;

  if (/^[a-zA-Z0-9_-]{11}$/.test(raw)) return raw;

  let url;
  try {
    url = new URL(raw.startsWith("http") ? raw : `https://${raw}`);
  } catch {
    return null;
  }

  const host = url.hostname.replace(/^www\./, "");
  if (host === "youtu.be") {
    const id = url.pathname.split("/").filter(Boolean)[0];
    return id && /^[a-zA-Z0-9_-]{11}$/.test(id) ? id : null;
  }

  if (host === "studio.youtube.com") {
    const parts = url.pathname.split("/").filter(Boolean);
    const vidIdx = parts.indexOf("video");
    if (vidIdx >= 0 && parts[vidIdx + 1]) {
      const id = parts[vidIdx + 1];
      if (/^[a-zA-Z0-9_-]{11}$/.test(id)) return id;
    }
  }

  if (host === "youtube.com" || host === "m.youtube.com" || host === "music.youtube.com") {
    const v = url.searchParams.get("v");
    if (v && /^[a-zA-Z0-9_-]{11}$/.test(v)) return v;

    const parts = url.pathname.split("/").filter(Boolean);
    const liveIdx = parts.indexOf("live");
    if (liveIdx >= 0 && parts[liveIdx + 1]) {
      const id = parts[liveIdx + 1];
      if (/^[a-zA-Z0-9_-]{11}$/.test(id)) return id;
    }
    if (parts[0] === "embed" && parts[1] && /^[a-zA-Z0-9_-]{11}$/.test(parts[1])) {
      return parts[1];
    }
    if (parts[0] === "shorts" && parts[1] && /^[a-zA-Z0-9_-]{11}$/.test(parts[1])) {
      return parts[1];
    }
  }

  return null;
}

/** Panel / API'den gelen yayın taslağını metne çevirir (nesne veya dizi gönderimini düzeltir). */
export function normalizeStreamUrlDraft(value) {
  if (value == null) return "";
  if (typeof value === "string") {
    const s = value.trim();
    if (s === "[object Object]") return "";
    return s.slice(0, 4000);
  }
  if (Array.isArray(value)) {
    return value
      .map((v) => (typeof v === "string" ? v : v?.url || v?.href || ""))
      .map((s) => String(s || "").trim())
      .filter(Boolean)
      .join("\n")
      .slice(0, 4000);
  }
  if (typeof value === "object") {
    if (typeof value.url === "string") return normalizeStreamUrlDraft(value.url);
    if (typeof value.href === "string") return normalizeStreamUrlDraft(value.href);
    if (Array.isArray(value.streamUrls)) {
      return normalizeStreamUrlDraft(value.streamUrls);
    }
    if (Array.isArray(value.videoIds)) {
      return value.videoIds
        .map((id) => `https://www.youtube.com/watch?v=${id}`)
        .join("\n")
        .slice(0, 4000);
    }
  }
  const s = String(value).trim();
  return s === "[object Object]" ? "" : s.slice(0, 4000);
}

/** Birden fazla YouTube link/id metninden benzersiz video ID listesi çıkarır. */
export function parseYouTubeVideoIds(input) {
  if (input == null) return [];
  if (Array.isArray(input)) {
    return parseYouTubeVideoIds(input.map((v) => String(v || "").trim()).join("\n"));
  }
  if (typeof input === "object") {
    if (Array.isArray(input.streamUrls)) {
      return parseYouTubeVideoIds(input.streamUrls.join("\n"));
    }
    if (Array.isArray(input.videoIds)) {
      return [...new Set(input.videoIds.map((v) => String(v || "").trim()).filter((id) => /^[a-zA-Z0-9_-]{11}$/.test(id)))];
    }
    const asUrl = input.url || input.href || input.streamUrl;
    if (asUrl) return parseYouTubeVideoIds(String(asUrl));
    return [];
  }
  if (typeof input !== "string") return [];
  const parts = input
    .split(/[\n\r,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const out = [];
  const seen = new Set();
  for (const raw of parts) {
    const id = parseYouTubeVideoId(raw);
    if (!id || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

/** Google APIs / Gaxios hata metni */
export function formatApiError(err) {
  const data = err?.response?.data?.error;
  if (data?.message) {
    const reason = data.errors?.[0]?.reason;
    return reason ? `${data.message} (${reason})` : data.message;
  }
  return err?.message || String(err);
}

/** YouTube Data API günlük kota aşıldı mı */
export function isQuotaExceededError(err) {
  const data = err?.response?.data?.error;
  const reasons = (data?.errors || []).map((e) => String(e.reason || ""));
  if (reasons.some((r) => r === "quotaExceeded")) return true;
  const msg = formatApiError(err).toLowerCase();
  return msg.includes("quotaexceeded") || msg.includes("exceeded your quota");
}

/** Canlı yayın / sohbet sona erdi mi (polling durdurulur) */
export function isStreamEndedError(err) {
  if (err?.code === "STREAM_ENDED") return true;
  const data = err?.response?.data?.error;
  const reasons = (data?.errors || []).map((e) => String(e.reason || ""));
  if (
    reasons.some((r) =>
      /^(liveChatEnded|liveChatNotFound|videoNotFound|broadcastCompleted)$/i.test(
        r
      )
    )
  ) {
    return true;
  }
  const msg = formatApiError(err).toLowerCase();
  return (
    msg.includes("live chat ended") ||
    msg.includes("live broadcast is not") ||
    msg.includes("no longer live") ||
    msg.includes("broadcast completed")
  );
}

/** Abone sayısı (kısa Türkçe) */
export function formatSubscriberCount(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return raw ? String(raw) : "";
  if (n >= 1_000_000) {
    const v = n / 1_000_000;
    return `${v >= 10 ? Math.round(v) : v.toFixed(1).replace(/\.0$/, "")}M abone`;
  }
  if (n >= 10_000) {
    const v = n / 1_000;
    return `${v >= 100 ? Math.round(v) : v.toFixed(1).replace(/\.0$/, "")}B abone`;
  }
  return `${n.toLocaleString("tr-TR")} abone`;
}

/** ISO tarih → «3 sa önce» */
export function formatRelativeTimeTr(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const diff = Date.now() - d.getTime();
  if (diff < 0) return "az önce";
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "az önce";
  if (mins < 60) return `${mins} dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 48) return `${hrs} sa önce`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days} gün önce`;
  return d.toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" });
}

/** ISO 8601 süre (PT1H2M3S) */
export function formatIso8601Duration(iso) {
  if (!iso || typeof iso !== "string") return "";
  const m = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/i);
  if (!m) return "";
  const h = Number(m[1] || 0);
  const min = Number(m[2] || 0);
  const s = Number(m[3] || 0);
  const parts = [];
  if (h) parts.push(`${h} sa`);
  if (min) parts.push(`${min} dk`);
  if (s && !h && !min) parts.push(`${s} sn`);
  return parts.join(" ") || "";
}

/** Canlı sohbet okuma aralığı (ms) — oyun aktifken alt sınır. Varsayılan 10 sn. */
export function resolveYoutubeMinPollMs() {
  const raw =
    process.env.YOUTUBE_MIN_POLL_MS ?? process.env.CHAT_POLL_MS ?? "10000";
  const n = Number(raw);
  const ms = Number.isFinite(n) ? n : 10_000;
  return Math.max(5000, Math.min(120_000, ms));
}

/** Üst sınır — API 5 sn dese bile daha seyrek (varsayılan 12 sn). */
export function resolveYoutubeMaxPollMs() {
  const raw = process.env.YOUTUBE_MAX_POLL_MS ?? "12000";
  const n = Number(raw);
  const ms = Number.isFinite(n) ? n : 12_000;
  return Math.max(resolveYoutubeMinPollMs(), Math.min(120_000, ms));
}

/** Oyun başlamadan / arada bekleme — list çağrısı yapılmaz, sadece zamanlayıcı. */
export function resolveYoutubeIdlePollMs() {
  const raw = process.env.YOUTUBE_IDLE_POLL_MS ?? "45000";
  const n = Number(raw);
  const ms = Number.isFinite(n) ? n : 45_000;
  return Math.max(15_000, Math.min(300_000, ms));
}

/** Yayın canlılık kontrolü kaç aktif poll’da bir (varsayılan 60 ≈ ~10 dk @10sn). */
export function resolveYoutubeLiveCheckEveryPolls() {
  const n = Number(process.env.YOUTUBE_LIVE_CHECK_EVERY_POLLS);
  if (Number.isFinite(n) && n >= 1) return Math.floor(n);
  return 60;
}

/** Kazanan ekranında da sohbet oku (varsayılan hayır — kota). */
export function resolveYoutubePollInWinner() {
  const raw = String(process.env.YOUTUBE_POLL_IN_WINNER ?? "off").toLowerCase();
  return !["off", "false", "0", "no"].includes(raw);
}

/**
 * «Sohbete bağlan» sonrası dinleme oyun durumundan bağımsız açık kalsın (InnerChat).
 * Kapatmak için YOUTUBE_CHAT_STAY_CONNECTED=0
 */
export function resolveYoutubeChatStayConnected() {
  const raw = String(process.env.YOUTUBE_CHAT_STAY_CONNECTED ?? "1").toLowerCase();
  return !["0", "false", "off", "no"].includes(raw);
}

/** youtube-chat poll aralığı (ms) — düşük = daha çok 400 riski */
export function resolveInnerChatPollMs() {
  const n = Number(process.env.INNER_CHAT_POLL_MS);
  if (Number.isFinite(n) && n >= 2500) return Math.min(15_000, Math.floor(n));
  return 4500;
}

export function resolveInnerChatErrorBackoffBaseMs() {
  const n = Number(process.env.INNER_CHAT_ERROR_BACKOFF_MS);
  if (Number.isFinite(n) && n >= 5000) return Math.min(180_000, Math.floor(n));
  return 12_000;
}

/** Son X sn içinde sohbet geldiyse videos.list atlansın (varsayılan 3 dk). */
export function resolveYoutubeLiveCheckQuietSec() {
  const n = Number(process.env.YOUTUBE_LIVE_CHECK_QUIET_SEC);
  if (Number.isFinite(n) && n >= 0) return Math.floor(n);
  return 180;
}

export function resolveYoutubeAnnounceGameStart() {
  const raw = String(process.env.YOUTUBE_ANNOUNCE_GAME_START ?? "off").toLowerCase();
  return !["off", "false", "0", "no"].includes(raw);
}

export function resolveYoutubeWelcomeOnConnect() {
  const raw = String(
    process.env.YOUTUBE_WELCOME_ON_CONNECT ?? "off"
  ).toLowerCase();
  if (["off", "false", "0", "no"].includes(raw)) return "off";
  if (raw === "full") return "full";
  return "short";
}

/** Botun kendi sohbet mesajlarını ( [BotAdı] … ) yoksay */
export function isBotFormattedChat(text, botName) {
  const name = String(botName || "").trim();
  if (!name) return false;
  const t = String(text || "").trimStart();
  return t.startsWith(`[${name}]`);
}

export const YOUTUBE_QUOTA_USER_HINT =
  "YouTube Data API günlük kotası doldu (varsayılan ~10.000 birim/gün). " +
  "Kota Pasifik saati gece yarısı sıfırlanır. Google Cloud Console → YouTube Data API v3 → Kotayı artırın. " +
  "Panelde gereksiz «API test» ve tekrarlı «Sohbete bağlan» denemelerinden kaçının.";

export const YOUTUBE_LOCAL_PAUSE_HINT =
  "Sunucu API'yi geçici durdurdu (kota koruması). Google Cloud'da kotayı artırdıysanız " +
  "«Kotayı yeniden dene» veya «API test» ile kontrol edin; hâlâ doluysa Pasifik gece yarısını bekleyin.";

/** !ping, !yardim vb. */
export function parseChatCommand(text) {
  const t = String(text || "").trim();
  if (!t.startsWith("!")) return null;
  const m = t.match(/^!(\w+)(?:\s+(.*))?$/i);
  if (!m) return null;
  return { command: m[1].toLowerCase(), args: (m[2] || "").trim() };
}
