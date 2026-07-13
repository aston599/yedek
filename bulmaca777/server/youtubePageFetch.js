/**
 * youtube-chat watch sayfası — VPS'te consent / kısıtlı HTML için cookie + geniş parse.
 */
import axios from "axios";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

const BROWSER_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

/** Datacenter IP’de watch HTML kısıtlıysa InnerTube player ile dene (youtube-chat ile uyumlu alanlar). */
const INNERTUBE_PLAYER_CLIENTS = [
  {
    clientName: "ANDROID",
    clientVersion: "20.10.38",
    apiKey: "AIzaSyA8eiZmJq52a6jMjH_BRqqHBqgHZ5wOKb4",
    androidSdkVersion: 30,
  },
  {
    clientName: "TVHTML5",
    clientVersion: "7.20250312.00.00",
    apiKey: "AIzaSyAO_FJ2SluU2l535BLNliJdKXN0KK6-0g",
  },
  {
    clientName: "WEB",
    clientVersion: "2.20250312.00.00",
    apiKey: "AIzaSyAO_FJ2SluU2l535BLNliJdKXN0KK6-0g",
  },
];

let applied = false;
let patched = false;
let globalJar = null;

function parseCookieString(raw = "") {
  const map = new Map();
  for (const part of String(raw).split(";")) {
    const p = part.trim();
    if (!p) continue;
    const eq = p.indexOf("=");
    if (eq < 1) continue;
    map.set(p.slice(0, eq).trim(), p.slice(eq + 1).trim());
  }
  return map;
}

class CookieJar {
  constructor() {
    this.map = new Map();
    const base =
      process.env.YOUTUBE_CONSENT_COOKIE ||
      "SOCS=CAISEQ; CONSENT=YES+cb; PREF=f6=40000000&tz=Europe.Istanbul";
    for (const [k, v] of parseCookieString(base)) {
      this.map.set(k, v);
    }
  }

  set(name, value) {
    if (name) this.map.set(name, value);
  }

  setFromResponse(res) {
    const raw = res?.headers?.["set-cookie"];
    if (!raw) return;
    const lines = Array.isArray(raw) ? raw : [raw];
    for (const line of lines) {
      const part = String(line).split(";")[0];
      const eq = part.indexOf("=");
      if (eq < 1) continue;
      this.set(part.slice(0, eq).trim(), part.slice(eq + 1).trim());
    }
  }

  header() {
    return [...this.map.entries()].map(([k, v]) => `${k}=${v}`).join("; ");
  }
}

function resolveHttpProxy() {
  const raw =
    process.env.YOUTUBE_HTTP_PROXY ||
    process.env.HTTPS_PROXY ||
    process.env.HTTP_PROXY ||
    "";
  return String(raw).trim() || null;
}

function axiosProxyConfig() {
  const url = resolveHttpProxy();
  if (!url) return undefined;
  try {
    const u = new URL(url);
    const port = u.port ? Number(u.port) : u.protocol === "https:" ? 443 : 80;
    const cfg = {
      protocol: u.protocol.replace(":", ""),
      host: u.hostname,
      port,
    };
    if (u.username) {
      cfg.auth = {
        username: decodeURIComponent(u.username),
        password: decodeURIComponent(u.password || ""),
      };
    }
    return cfg;
  } catch {
    console.warn("[youtubePageFetch] Gecersiz YOUTUBE_HTTP_PROXY — yoksayildi");
    return undefined;
  }
}

function requestHeaders(jar, extra = {}) {
  return {
    "User-Agent": BROWSER_UA,
    Accept:
      "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language":
      process.env.YOUTUBE_FETCH_LANG || "en-US,en;q=0.9,tr;q=0.8",
    Cookie: jar.header(),
    ...extra,
  };
}

function axiosGetOpts(jar, extraHeaders = {}) {
  return {
    headers: requestHeaders(jar, extraHeaders),
    validateStatus: () => true,
    timeout: Number(process.env.YOUTUBE_FETCH_TIMEOUT_MS || 25_000),
    proxy: axiosProxyConfig(),
  };
}

export function applyYoutubeAxiosDefaults() {
  if (applied) return;
  applied = true;
  axios.defaults.headers.common["User-Agent"] = BROWSER_UA;
  axios.defaults.headers.common["Accept-Language"] =
    process.env.YOUTUBE_FETCH_LANG || "en-US,en;q=0.9,tr;q=0.8";
  axios.defaults.timeout = Number(process.env.YOUTUBE_FETCH_TIMEOUT_MS || 25_000);
  if (globalJar) {
    axios.defaults.headers.common.Cookie = globalJar.header();
  }
}

function chunkAroundVideoId(data, videoId, radius = 28_000) {
  const needle = `"videoId":"${videoId}"`;
  const idx = data.indexOf(needle);
  if (idx < 0) return data;
  const start = Math.max(0, idx - 4000);
  return data.slice(start, idx + radius);
}

function findContinuationInText(text) {
  const contPatterns = [
    /"liveChatRenderer":\{[^}]*"continuation":"([^"]+)"/,
    /"continuation":"(Eg[a-zA-Z0-9_\-%.]+)"/,
    /"continuation":"([^"]{40,})"/,
    /['"]continuation['"]:\s*['"]([^'"]+)['"]/,
  ];
  for (const re of contPatterns) {
    const m = text.match(re);
    if (m?.[1] && m[1].length >= 20) return m[1];
  }
  return null;
}

function findContinuationInObject(obj, depth = 0) {
  if (!obj || depth > 14) return null;
  if (typeof obj === "string") return null;
  if (typeof obj !== "object") return null;
  if (typeof obj.continuation === "string" && obj.continuation.length >= 20) {
    return obj.continuation;
  }
  const reload = obj.reloadContinuationData?.continuation;
  if (typeof reload === "string" && reload.length >= 20) return reload;
  const timed = obj.timedContinuationData?.continuation;
  if (typeof timed === "string" && timed.length >= 20) return timed;
  for (const v of Object.values(obj)) {
    const found = findContinuationInObject(v, depth + 1);
    if (found) return found;
  }
  return null;
}

function detectBlockKind(data) {
  const text = String(data || "");
  if (
    /Sign in to confirm you.?re not a bot/i.test(text) ||
    /unusual traffic/i.test(text) ||
    /automated queries/i.test(text) ||
    /captcha/i.test(text)
  ) {
    return "bot";
  }
  if (/consent\.youtube\.com|Before you continue to YouTube/i.test(text)) {
    return "consent";
  }
  if (text.length < 50_000 && !/"videoId"/.test(text) && !/"INNERTUBE_API_KEY"/.test(text)) {
    return "incomplete";
  }
  return null;
}

async function fetchInnertubePlayerOptions(videoId, jar) {
  const urlBase = "https://www.youtube.com/youtubei/v1/player";
  for (const client of INNERTUBE_PLAYER_CLIENTS) {
    const body = {
      context: {
        client: {
          clientName: client.clientName,
          clientVersion: client.clientVersion,
          hl: "en",
          gl: "US",
          utcOffsetMinutes: 0,
          ...(client.androidSdkVersion
            ? { androidSdkVersion: client.androidSdkVersion }
            : {}),
        },
      },
      videoId,
    };
    try {
      const res = await axios.post(
        `${urlBase}?key=${encodeURIComponent(client.apiKey)}`,
        body,
        {
          headers: {
            ...requestHeaders(jar, {
              "Content-Type": "application/json",
              Origin: "https://www.youtube.com",
              Referer: `https://www.youtube.com/watch?v=${videoId}`,
            }),
          },
          validateStatus: () => true,
          timeout: 20_000,
          proxy: axiosProxyConfig(),
        }
      );
      if (res.status < 200 || res.status >= 300 || !res.data) continue;
      const payload = res.data;
      if (payload?.playabilityStatus?.status === "LOGIN_REQUIRED") continue;
      if (payload?.playabilityStatus?.status === "ERROR") continue;
      const continuation =
        findContinuationInObject(payload) || findContinuationInText(JSON.stringify(payload));
      if (!continuation) continue;
      return {
        liveId: videoId,
        apiKey: client.apiKey,
        clientVersion: client.clientVersion,
        continuation,
        requestedVideoId: videoId,
        pageCanonicalId: videoId,
        source: `innertube:${client.clientName}`,
      };
    } catch {
      /* sonraki istemci */
    }
  }
  return null;
}

/** youtube-chat ile aynı çıktı; istenen videoId öncelikli (VPS consent sayfasında yanlış canonical önlenir) */
export function parseInnerChatOptions(html, fallbackVideoId = "") {
  const data = String(html || "");
  const requested = String(fallbackVideoId || "").trim();

  const canonicalId = data.match(
    /<link rel="canonical" href="https:\/\/www.youtube.com\/watch\?v=(.+?)">/
  )?.[1];
  const ogId = data.match(
    /property="og:url" content="https:\/\/www\.youtube\.com\/watch\?v=([^"]+)"/
  )?.[1];

  const liveId =
    /^[a-zA-Z0-9_-]{11}$/.test(requested) ? requested : canonicalId || ogId || null;

  if (!liveId || !/^[a-zA-Z0-9_-]{11}$/.test(liveId)) {
    throw new Error("Live Stream was not found");
  }

  const scope = /^[a-zA-Z0-9_-]{11}$/.test(requested)
    ? chunkAroundVideoId(data, requested)
    : data;

  if (/['"]isReplay['"]:\s*true/.test(scope)) {
    throw new Error(`${liveId} is finished live`);
  }

  const apiKey =
    data.match(/['"]INNERTUBE_API_KEY['"]:\s*['"]([^'"]+)['"]/)?.[1] ||
    data.match(/INNERTUBE_API_KEY\\":\\"([^"\\]+)\\"/)?.[1] ||
    data.match(/innertubeApiKey['"]:\s*['"]([^'"]+)['"]/)?.[1] ||
    data.match(/"INNERTUBE_API_KEY":"([^"]+)"/)?.[1] ||
    data.match(/INNERTUBE_API_KEY\\":\\"([A-Za-z0-9_-]+)\\"/)?.[1];
  if (!apiKey) {
    if (/consent\.youtube\.com|Before you continue to YouTube/i.test(data)) {
      throw new Error("YouTube consent page — cookie/consent akisi gerekli");
    }
    if (data.length < 50_000 && !/"videoId"/.test(data)) {
      throw new Error("Watch page incomplete — bot or network block");
    }
    throw new Error("API Key was not found");
  }

  const clientVersion =
    data.match(/['"]INNERTUBE_CONTEXT_CLIENT_VERSION['"]:\s*['"]([^'"]+)['"]/)?.[1] ||
    data.match(/INNERTUBE_CONTEXT_CLIENT_VERSION\\":\\"([^"\\]+)\\"/)?.[1] ||
    data.match(/['"]clientVersion['"]:\s*['"]([\d.]+[^'"]*)['"]/)?.[1] ||
    data.match(/"clientVersion":"([\d.]+)"/)?.[1];
  if (!clientVersion) throw new Error("Client Version was not found");

  let continuation =
    findContinuationInText(scope) || findContinuationInText(data);
  if (!continuation) throw new Error("Continuation was not found");

  return {
    liveId,
    apiKey,
    clientVersion,
    continuation,
    requestedVideoId: requested || null,
    pageCanonicalId: canonicalId || ogId || null,
  };
}

function parseWatchHtml(html, fallbackVideoId = "") {
  const data = String(html || "");
  let innerChatOptions = null;
  let parseError = null;
  try {
    innerChatOptions = parseInnerChatOptions(data, fallbackVideoId);
  } catch (err) {
    parseError = err.message;
  }

  const title = data.match(/<title>([^<]*)<\/title>/i);
  const titleText = title?.[1]?.trim() || null;
  const consentWall =
    /consent\.youtube\.com/i.test(data) ||
    /Before you continue to YouTube/i.test(data) ||
    /devam etmeden önce/i.test(data) ||
    /action="https:\/\/consent\.youtube\.com/i.test(data) ||
    (titleText === "- YouTube" && !innerChatOptions);

  const blockKind = detectBlockKind(data);

  return {
    htmlBytes: data.length,
    title: titleText,
    requestedVideoId: fallbackVideoId || null,
    pageCanonicalId: innerChatOptions?.pageCanonicalId || null,
    canonicalVideoId: innerChatOptions?.liveId || null,
    hasApiKey: Boolean(innerChatOptions?.apiKey),
    hasClientVersion: Boolean(innerChatOptions?.clientVersion),
    hasContinuation: Boolean(innerChatOptions?.continuation),
    isReplay: /['"]isReplay['"]:\s*true/.test(data),
    isLiveBadge:
      /"simpleText":"CANLI"/i.test(data) ||
      /"style":"LIVE"/i.test(data) ||
      /"badgeStyle":"LIVE"/i.test(data) ||
      /"LIVE"/i.test(data),
    consentWall,
    blockKind,
    botHint: blockKind === "bot",
    innerChatWouldWork: Boolean(innerChatOptions),
    parseError,
    fetchSource: innerChatOptions?.source || null,
  };
}

async function runConsentFlow(jar, videoId) {
  const continueUrl = `https://www.youtube.com/watch?v=${videoId}&hl=en&gl=US&persist_hl=1&persist_gl=1`;

  const mPage = await axios.get("https://consent.youtube.com/m", {
    params: { continue: continueUrl, gl: "US", hl: "en", m: 0, pc: "yt", src: 1 },
    ...axiosGetOpts(jar),
    maxRedirects: 0,
  });
  jar.setFromResponse(mPage);

  const save = await axios.get("https://consent.youtube.com/save", {
    params: {
      continue: continueUrl,
      set_ytc: true,
      set_apyt: true,
      set_eom: false,
    },
    ...axiosGetOpts(jar),
    maxRedirects: 8,
  });
  jar.setFromResponse(save);
  return jar;
}

async function tryFetchHtml(jar, url, videoId) {
  const res = await axios.get(url, axiosGetOpts(jar));
  jar.setFromResponse(res);
  const meta = parseWatchHtml(res.data, videoId);
  return { res, meta };
}

/** Consent + cookie ile tam watch HTML; VPS bot blokunda InnerTube / live_chat yedekleri */
export async function fetchWatchPageHtml(videoId) {
  applyYoutubeAxiosDefaults();
  const jar = new CookieJar();
  const watchUrl = `https://www.youtube.com/watch?v=${videoId}&hl=en&gl=US&persist_hl=1&persist_gl=1`;
  const strategies = [];

  let res = (await tryFetchHtml(jar, watchUrl, videoId)).res;
  let meta = parseWatchHtml(res.data, videoId);
  strategies.push(`watch:${meta.htmlBytes}b`);

  if (!meta.innerChatWouldWork && (meta.consentWall || !meta.canonicalVideoId)) {
    await runConsentFlow(jar, videoId);
    const again = await tryFetchHtml(jar, watchUrl, videoId);
    res = again.res;
    meta = again.meta;
    strategies.push(`watch+consent:${meta.htmlBytes}b`);
  }

  const altUrls = [
    `https://www.youtube.com/live_chat?is_popout=1&v=${videoId}`,
    `https://m.youtube.com/watch?v=${videoId}`,
    `https://www.youtube.com/embed/${videoId}`,
  ];
  for (const url of altUrls) {
    if (meta.innerChatWouldWork) break;
    try {
      const alt = await tryFetchHtml(jar, url, videoId);
      if (alt.meta.innerChatWouldWork) {
        res = alt.res;
        meta = alt.meta;
        strategies.push(`html:${new URL(url).pathname}`);
        break;
      }
      strategies.push(`skip:${new URL(url).pathname}(${alt.meta.htmlBytes}b)`);
    } catch {
      strategies.push(`fail:${url}`);
    }
  }

  if (!meta.innerChatWouldWork) {
    const playerOpts = await fetchInnertubePlayerOptions(videoId, jar);
    if (playerOpts) {
      meta = {
        ...meta,
        innerChatWouldWork: true,
        hasApiKey: true,
        hasClientVersion: true,
        hasContinuation: true,
        canonicalVideoId: videoId,
        parseError: null,
        fetchSource: playerOpts.source,
        blockKind: null,
        botHint: false,
      };
      strategies.push(playerOpts.source);
      globalJar = jar;
      axios.defaults.headers.common.Cookie = jar.header();
      return {
        html: JSON.stringify(playerOpts),
        meta,
        cookieHeader: jar.header(),
        innertubeOptions: playerOpts,
        strategies: strategies.join(" → "),
      };
    }
    strategies.push("innertube:fail");
  }

  globalJar = jar;
  axios.defaults.headers.common.Cookie = jar.header();
  return {
    html: String(res.data),
    meta: { ...meta, strategies: strategies.join(" → ") },
    cookieHeader: jar.header(),
    innertubeOptions: null,
    strategies: strategies.join(" → "),
  };
}

/** youtube-chat fetchLivePage → VPS uyumlu HTML parse */
export function patchYoutubeChatFetch() {
  if (patched) return;
  patched = true;
  applyYoutubeAxiosDefaults();
  try {
    const requests = require("youtube-chat/dist/requests.js");
    const origFetchLivePage = requests.fetchLivePage;
    requests.fetchLivePage = async (id) => {
      if (!id || !("liveId" in id) || !id.liveId) {
        return origFetchLivePage(id);
      }
      const fetched = await fetchWatchPageHtml(id.liveId);
      if (fetched.innertubeOptions) {
        return fetched.innertubeOptions;
      }
      return parseInnerChatOptions(fetched.html, id.liveId);
    };
  } catch (err) {
    console.warn("[youtubePageFetch] patch skipped:", err.message);
  }
}

export async function diagnoseYoutubeWatchPage(videoId) {
  const out = {
    videoId,
    url: `https://www.youtube.com/watch?v=${videoId}`,
    httpStatus: 200,
    error: null,
    parse: null,
    cookiePreview: null,
    httpProxy: Boolean(resolveHttpProxy()),
    hints: [],
  };

  try {
    const { meta, cookieHeader, strategies, innertubeOptions } =
      await fetchWatchPageHtml(videoId);
    out.parse = meta;
    out.strategies = strategies;
    out.innertubeFallback = Boolean(innertubeOptions);
    out.cookiePreview = cookieHeader?.slice(0, 120) + (cookieHeader?.length > 120 ? "…" : "");
    if (!meta.innerChatWouldWork && meta.parseError) {
      out.hints.push(`Parse: ${meta.parseError}`);
    }
  } catch (err) {
    out.error = err.message || String(err);
    out.hints.push("Ağ/DNS veya YouTube erişim hatası.");
    return out;
  }

  const p = out.parse;
  if (p.consentWall && !p.innerChatWouldWork) {
    out.hints.push(
      "Consent sayfası — patch sonrası hâlâ başarısız; IP kısıtı olabilir."
    );
  }
  if ((p.blockKind === "bot" || p.botHint) && !p.innerChatWouldWork) {
    out.hints.push(
      "VPS IP bot duvarı — tarayıcıdan YOUTUBE_CONSENT_COOKIE veya YOUTUBE_HTTP_PROXY (ev/residential) deneyin."
    );
  }
  if (p.blockKind === "incomplete" && !p.innerChatWouldWork) {
    out.hints.push(
      "Watch HTML çok kısa — DigitalOcean/Hetzner IP’leri sık kısıtlanır; InnerTube yedek de başarısız."
    );
  }
  if (out.httpProxy) {
    out.hints.push("HTTP proxy aktif (YOUTUBE_HTTP_PROXY / HTTPS_PROXY).");
  }
  if (p.isReplay) {
    out.hints.push("Yayın bitmiş (isReplay).");
  }
  if (p.innerChatWouldWork) {
    const via = p.fetchSource || (out.innertubeFallback ? "innertube" : "html");
    out.hints.push(`Parse OK (${via}) — InnerChat bu sunucuda çalışmalı.`);
  } else if (!p.consentWall) {
    out.hints.push("Sayfa geldi ama sohbet continuation bulunamadı.");
  }
  if (out.strategies) {
    out.hints.push(`Denenen: ${out.strategies}`);
  }

  return out;
}
