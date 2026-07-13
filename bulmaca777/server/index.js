import "dotenv/config";
import {
  applyYoutubeAxiosDefaults,
  patchYoutubeChatFetch,
} from "./youtubePageFetch.js";

applyYoutubeAxiosDefaults();
patchYoutubeChatFetch();

process.on("unhandledRejection", (reason) => {
  console.error("[unhandledRejection]", reason);
});
process.on("uncaughtException", (err) => {
  console.error("[uncaughtException]", err);
});
import express from "express";
import cookieParser from "cookie-parser";
import { createServer } from "http";
import { Server } from "socket.io";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { readFileSync, existsSync, statSync } from "fs";
import { writeFile } from "fs/promises";
import { RoomManager } from "./rooms.js";
import {
  isTeamRaceMode,
  isPhotoBattleMode,
  isFootballMode,
  roomUsesPuzzleEngine,
  roomUsesPhotoOverlay,
  photoRoomRunsCelebrityAge,
} from "./gameModes.js";
import { parseCelebrityCsv, isCelebrityAgeQuiz } from "./celebrityImport.js";
import {
  footballPlayersToQuestions,
  getFootballPackMeta,
} from "./football/footballImport.js";
import {
  isFootballClubQuiz,
  isFootballNationalityQuiz,
} from "./football/footballMatch.js";
import { canStartRaceRound, getRaceSeriesStatus } from "./teamRace/raceModes.js";
import { normalizeStreamUrlDraft } from "./utils.js";
import {
  createPlaygroundSession,
  getPlaygroundSession,
  deletePlaygroundSession,
  listTeams,
  playgroundChat,
  eliminatePlaygroundEntity,
  setPlaygroundChaos,
  triggerPlaygroundShock,
  stopPlaygroundRound,
  updatePlaygroundSettings,
} from "./playground/teamRacePlayground.js";
import { MockChatService } from "./youtube.js";
import { parseYouTubeVideoId, parseYouTubeVideoIds } from "./utils.js";
import { eventRepo } from "./db.js";
import {
  initAuditLog,
  auditApiRequest,
  auditApiResponse,
  listAuditLog,
  clearAuditLog,
  auditRecord,
} from "./auditLog.js";
import {
  attachSession,
  requireUser,
  registerUser,
  loginUser,
  logoutSession,
  setSessionCookie,
  clearSessionCookie,
} from "./auth.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const PORT = Number(process.env.PORT) || 3847;
/** localhost tek arayÃ¼ze kilitlenir; Windowsâ€™ta iframe bazen dÃ¼ÅŸer â€” yerel geliÅŸtirmede 0.0.0.0 */
const BIND_HOST =
  !process.env.HOST || process.env.HOST === "localhost"
    ? "0.0.0.0"
    : process.env.HOST;
const PUBLIC_HOST =
  process.env.PUBLIC_HOST?.replace(/^https?:\/\//, "").split(":")[0] ||
  "localhost";
/** Varsayılan: InnerYouTubeChatService (youtube-chat) — hesap OAuth gerekmez, canlı video ID yeter */
const CHAT_MODE = (process.env.CHAT_MODE || "youtube").toLowerCase();
const PUZZLE_FEED_MAX = Math.min(
  20,
  Math.max(3, Number(process.env.PUZZLE_FEED_MAX) || 7)
);
const PUBLIC_URL = process.env.PUBLIC_URL || `http://${PUBLIC_HOST}:${PORT}`;
const LAYOUT_VERTICAL_PATH = join(ROOT, "public", "overlay", "layout.vertical.json");

const OVERLAY_QUERY = {
  motion: "1",
  particles: "50",
  ov: "7",
  scale: "cover",
};

const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf-8"));
const APP_VERSION =
  process.env.APP_VERSION || `${pkg.version || "1"}.${process.env.STARTED_AT || Date.now()}`;
const ADMIN_INDEX_PATH = join(ROOT, "public", "admin", "index.html");
const WEBSITE_ROOT = join(ROOT, "website");

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: "*" } });
initAuditLog(io);

app.use(express.json({ limit: "15mb" }));
app.use(cookieParser());
app.use(attachSession);

/** Eski /overlay/?â€¦ linkleri â€” yÃ¶nlendirme dÃ¶ngÃ¼sÃ¼nÃ¼ kÄ±r */
app.use((req, res, next) => {
  if (req.method === "GET" && req.path === "/overlay/" && req.url.includes("?")) {
    return res.redirect(301, `/overlay${req.url.slice("/overlay/".length)}`);
  }
  next();
});

app.get("/favicon.ico", (_req, res) => {
  res.setHeader("Content-Type", "image/svg+xml");
  res.send(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect fill="#7c5cff" width="32" height="32" rx="6"/><text x="16" y="22" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffd54a">777</text></svg>`
  );
});

/** bulmaca777.com tanÄ±tÄ±m sitesi (website/) */
function sendWebsiteHtml(filename, res) {
  const path = join(WEBSITE_ROOT, filename);
  if (!existsSync(path)) {
    return res.status(404).send("Sayfa bulunamadi");
  }
  res.setHeader("Cache-Control", "public, max-age=120");
  return res.type("html").sendFile(path, (err) => {
    if (err && !res.headersSent) res.status(500).send("Sayfa yuklenemedi");
  });
}

app.get("/", (_req, res) => sendWebsiteHtml("index.html", res));
app.get("/privacy.html", (_req, res) => sendWebsiteHtml("privacy.html", res));
app.get("/terms.html", (_req, res) => sendWebsiteHtml("terms.html", res));

app.use(
  express.static(WEBSITE_ROOT, {
    index: false,
    redirect: false,
    setHeaders(res, filePath) {
      if (filePath.endsWith(".css")) {
        res.setHeader("Content-Type", "text/css; charset=utf-8");
        res.setHeader("Cache-Control", "public, max-age=3600");
      }
    },
  })
);

const OVERLAY_INDEX = join(ROOT, "public", "overlay", "index.html");
const CELEBRITY_OVERLAY_INDEX = join(ROOT, "public", "celebrity-age", "index.html");

function serveOverlayHtml(req, res) {
  const roomId = String(req.query?.room || "").trim();
  const forceGeneric =
    req.query?.force === "1" || req.query?.generic === "1";
  if (roomId && !forceGeneric) {
    try {
      const room = roomManager.getRoomOrThrow(roomId);
      if (roomUsesPhotoOverlay(room)) {
        const p = new URLSearchParams(req.query);
        p.delete("mode");
        p.delete("layout");
        if (!p.has("motion")) p.set("motion", "1");
        return res.redirect(302, `/celebrity-overlay?${p}`);
      }
    } catch {
      /* oda yok — klasik overlay */
    }
  }
  res.setHeader("Cache-Control", "no-store, must-revalidate");
  res.setHeader("X-Frame-Options", "SAMEORIGIN");
  res.type("html").sendFile(OVERLAY_INDEX, (err) => {
    if (err && !res.headersSent) {
      res.status(500).send("Overlay yuklenemedi");
    }
  });
}

/** YÃ¶nlendirme yok â€” /overlay?â€¦ ve /overlay/?â€¦ aynÄ± sayfa (ERR_TOO_MANY_REDIRECTS Ã¶nlenir) */
app.get(/^\/overlay\/?$/i, serveOverlayHtml);
app.get(/^\/overlay\/index\.html$/i, serveOverlayHtml);

function serveCelebrityOverlayHtml(_req, res) {
  res.setHeader("Cache-Control", "no-store, must-revalidate");
  res.setHeader("X-Frame-Options", "SAMEORIGIN");
  if (!existsSync(CELEBRITY_OVERLAY_INDEX)) {
    return res.status(500).send("Ünlü yaş overlay dosyası eksik");
  }
  res.type("html").sendFile(CELEBRITY_OVERLAY_INDEX, (err) => {
    if (err && !res.headersSent) res.status(500).send("Overlay yüklenemedi");
  });
}

/** Ünlülerin Yaşını Tahmin Et — ayrı 1080×1920 OBS ekranı (Bulmaca şablonu değil) */
app.get(/^\/celebrity-overlay\/?$/i, serveCelebrityOverlayHtml);
app.get(/^\/overlay\/celebrity\/?$/i, serveCelebrityOverlayHtml);

app.get("/api/app/version", (_req, res) => {
  res.setHeader("Cache-Control", "no-store");
  res.json({ version: APP_VERSION });
});

app.get("/api/health", (_req, res) => {
  res.setHeader("Cache-Control", "no-store");
  res.json({
    ok: true,
    port: PORT,
    publicUrl: PUBLIC_URL,
    overlayReady: existsSync(OVERLAY_INDEX),
    celebrityOverlayReady: existsSync(CELEBRITY_OVERLAY_INDEX),
    playgroundEnabled: isPlaygroundAllowed(),
    chatMode: CHAT_MODE,
    puzzleFeedMax: PUZZLE_FEED_MAX,
  });
});

/** Panel / Lab — sohbet modu ve kapasite (giriş gerekmez) */
app.get("/api/app/chat-info", (_req, res) => {
  res.setHeader("Cache-Control", "no-store");
  res.json({
    chatMode: CHAT_MODE,
    youtubeEnabled: CHAT_MODE === "youtube",
    readMethod:
      CHAT_MODE === "youtube"
        ? "inner"
        : "mock",
    readMethodLabel:
      CHAT_MODE === "youtube"
        ? "Canlı yayın video ID → youtube-chat paketi (Google API kotası yok)"
        : "Sadece panel/Lab sahte sohbet — gerçek YouTube okunmaz",
    botPostToYoutube: false,
    botPostNote:
      "Bot cevapları şu an yalnızca panel logunda; YouTube sohbetine yazılmaz (kota tasarrufu).",
    puzzleFeedMax: PUZZLE_FEED_MAX,
    puzzleFeedNote: `Doğru bilenler listesi: en fazla ${PUZZLE_FEED_MAX} kişi (puan sırasına göre).`,
  });
});

function readCelebritySampleCsvText() {
  const candidates = [
    join(ROOT, "public", "play", "celebrity-sample.csv"),
    join(ROOT, "scripts", "celebrity-sample.csv"),
  ];
  for (const p of candidates) {
    if (existsSync(p)) return readFileSync(p, "utf8");
  }
  return "";
}

/** Ünlü Yaş Lab — örnek CSV (giriş gerekmez) */
app.get("/api/celebrity-sample.csv", (_req, res) => {
  const csv = readCelebritySampleCsvText();
  if (!csv.trim()) {
    return res.status(404).json({ error: "Örnek dosya sunucuda yok" });
  }
  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.send(csv);
});

app.get("/api/celebrity-sample/preview", (_req, res) => {
  const csv = readCelebritySampleCsvText();
  const questions = parseCelebrityCsv(csv);
  res.setHeader("Cache-Control", "no-store");
  res.json({
    count: questions.length,
    rows: questions.map((q) => ({
      name: q.meta?.name || q.question,
      age: q.meta?.age,
      birthDate: q.meta?.birthDate,
      imageUrl: q.imageUrl,
    })),
  });
});

/** Oyun alanı (/play/) panel ve overlay gibi varsayılan açık; yalnızca PLAYGROUND=0 ile kapatılır. */
function isPlaygroundAllowed() {
  return process.env.PLAYGROUND !== "0";
}

function requirePlayground(req, res, next) {
  if (!isPlaygroundAllowed()) {
    return res.status(403).json({
      error: "Oyun alanı yönetici tarafından kapatıldı (PLAYGROUND=0).",
    });
  }
  next();
}

function playgroundSessionId(req) {
  return String(req.body?.sessionId || req.query?.sessionId || "").trim();
}

app.get("/api/playground/team-race/teams", requirePlayground, (_req, res) => {
  res.json({ teams: listTeams() });
});

/** Takım listesi — canlı stüdyo / oda (playground oturumu gerekmez) */
app.get("/api/team-race/teams", (_req, res) => {
  res.json({ teams: listTeams() });
});

app.post("/api/playground/team-race/session", requirePlayground, (req, res) => {
  const cooldown = Number(req.body?.spawnCooldownMs);
  const gatherSec = Number(req.body?.gatherDurationSec);
  const data = createPlaygroundSession({
    spawnCooldownMs: Number.isFinite(cooldown) && cooldown >= 1000 ? cooldown : undefined,
    gatherDurationSec: Number.isFinite(gatherSec) ? gatherSec : undefined,
    chaosMinEntities: req.body?.chaosMinEntities,
    chaosTrigger: req.body?.chaosTrigger,
    minParticipants: req.body?.minParticipants,
    minTeams: req.body?.minTeams,
    minTotalSpawns: req.body?.minTotalSpawns,
  });
  res.json(data);
});

app.patch("/api/playground/team-race/settings", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  const out = updatePlaygroundSettings(id, {
    spawnCooldownMs: req.body?.spawnCooldownMs,
    gatherDurationMs: req.body?.gatherDurationMs,
    gatherDurationSec: req.body?.gatherDurationSec,
    chaosMinEntities: req.body?.chaosMinEntities,
    chaosTrigger: req.body?.chaosTrigger,
    minParticipants: req.body?.minParticipants,
    minTeams: req.body?.minTeams,
    minTotalSpawns: req.body?.minTotalSpawns,
    gatherExtendMs: req.body?.gatherExtendMs,
  });
  if (out.status) return res.status(out.status).json({ error: out.error });
  res.json({ sessionId: id, settings: out.settings, snapshot: out.snapshot });
});

app.get("/api/playground/team-race/state", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  const row = getPlaygroundSession(id);
  if (!row) return res.status(404).json({ error: "Oturum bulunamadı" });
  res.json({
    sessionId: id,
    snapshot: row.engine.getSnapshot(),
    entities: row.engine.entities.filter((e) => !e.eliminated),
    champions: { ...row.champions },
    roundHistory: [...row.roundHistory],
    chaos: row.chaos,
  });
});

app.post("/api/playground/team-race/start", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  const row = getPlaygroundSession(id);
  if (!row) return res.status(404).json({ error: "Oturum bulunamadı" });
  if (!canStartRaceRound(row.engine.settings, row.roundHistory)) {
    const series = getRaceSeriesStatus(row.engine.settings, row.roundHistory);
    return res.status(409).json({
      error: `Seri tamamlandı (${series.completedRounds}/${series.maxRounds} tur). Sıfırla ile yeniden başlayın.`,
    });
  }
  const snap = row.engine.start();
  res.json({
    sessionId: id,
    snapshot: snap,
    series: getRaceSeriesStatus(row.engine.settings, row.roundHistory),
    champions: { ...row.champions },
    roundHistory: [...row.roundHistory],
  });
});

app.post("/api/playground/team-race/stop", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  const out = stopPlaygroundRound(id);
  if (out.status) return res.status(out.status).json({ error: out.error });
  res.json({ sessionId: id, snapshot: out.snapshot, champions: out.champions });
});

app.post("/api/playground/team-race/eliminate", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  const entityId = String(req.body?.entityId || "").trim();
  if (!entityId) return res.status(400).json({ error: "entityId gerekli" });
  const out = eliminatePlaygroundEntity(id, entityId);
  if (out.status) return res.status(out.status).json({ error: out.error });
  res.json({ sessionId: id, ...out });
});

app.post("/api/playground/team-race/chaos", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  if (!id) return res.status(400).json({ error: "sessionId gerekli" });
  const enabled =
    req.body && Object.prototype.hasOwnProperty.call(req.body, "enabled")
      ? Boolean(req.body.enabled)
      : true;
  const out = setPlaygroundChaos(id, enabled);
  if (out.status) return res.status(out.status).json({ error: out.error });
  res.json({ sessionId: id, chaos: out.chaos, snapshot: out.snapshot });
});

app.post("/api/playground/team-race/shock", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  if (!id) return res.status(400).json({ error: "sessionId gerekli" });
  const out = triggerPlaygroundShock(id);
  if (out.status) return res.status(out.status).json({ error: out.error });
  if (!out.ok) {
    return res.status(400).json({
      error: "Şok dalgası için tur kaosta olmalı.",
      snapshot: out.snapshot,
    });
  }
  res.json({ sessionId: id, ok: true, chaos: out.chaos, snapshot: out.snapshot });
});

app.post("/api/playground/team-race/reset", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  const row = getPlaygroundSession(id);
  if (!row) return res.status(404).json({ error: "Oturum bulunamadı" });
  row.roundHistory = [];
  row.champions = {};
  res.json({
    sessionId: id,
    snapshot: row.engine.reset(),
    champions: {},
    roundHistory: [],
  });
});

app.post("/api/playground/team-race/chat", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  const out = playgroundChat(id, {
    author: req.body?.author,
    text: req.body?.text,
    simulated: Boolean(req.body?.simulated),
  });
  if (out.status) return res.status(out.status).json({ error: out.error });
  res.json({
    sessionId: id,
    ...out,
  });
});

app.delete("/api/playground/team-race/session", requirePlayground, (req, res) => {
  const id = playgroundSessionId(req);
  deletePlaygroundSession(id);
  res.json({ ok: true });
});

/** Panel: yapÄ±ÅŸtÄ±rÄ±lan yayÄ±n linkinden video ID Ã¶nizlemesi */
app.get("/api/utils/parse-youtube", (req, res) => {
  const raw = String(req.query.url || req.query.u || "").trim();
  const videoIds = parseYouTubeVideoIds(raw);
  const videoId = videoIds[0] || parseYouTubeVideoId(raw);
  res.json({
    ok: Boolean(videoId),
    videoId: videoId || "",
    videoIds,
    watchUrl: videoId ? `https://www.youtube.com/watch?v=${videoId}` : "",
  });
});

function sendAdminHtml(res) {
  let html = readFileSync(ADMIN_INDEX_PATH, "utf-8");
  const adminJsPath = join(ROOT, "public", "admin", "admin.js");
  const mtime = existsSync(adminJsPath) ? statSync(adminJsPath).mtimeMs : Date.now();
  const v = encodeURIComponent(`${APP_VERSION}.${mtime}`);
  html = html
    .replace(/href="admin\.css(\?[^"]*)?"/, `href="admin.css?v=${v}"`)
    .replace(/src="admin\.js(\?[^"]*)?"/, `src="admin.js?v=${v}"`)
    .replace(
      "</head>",
      `  <meta name="app-version" content="${APP_VERSION}" />\n</head>`
    );
  res.setHeader("Cache-Control", "no-store, must-revalidate");
  res.type("html").send(html);
}

app.get("/admin", (_req, res) => sendAdminHtml(res));
app.get("/admin/", (_req, res) => sendAdminHtml(res));
/** Panel canlÄ± Ã¶nizleme â€” admin ile aynÄ± oturum, iframe srcdoc/fetch ile uyumlu */
app.get(/^\/admin\/preview\/?$/i, requireUser, serveOverlayHtml);
app.get("/admin/index.html", (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  res.redirect(301, `/admin/${q ? `?${q}` : ""}`);
});

const PLAY_INDEX_PATH = join(ROOT, "public", "play", "index.html");

function sendPlayStudioHtml(res) {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Content-Type", "text/html; charset=UTF-8");
  let html = readFileSync(PLAY_INDEX_PATH, "utf8");
  if (html.charCodeAt(0) === 0xfeff) html = html.slice(1);
  res.send(html);
}

/** /play/ — room= ile canlı stüdyo; odasız istek admin panele */
app.get(/^\/play\/?$/i, (req, res) => {
  const room = String(req.query?.room || "").trim();
  if (!room) {
    const q = new URLSearchParams(req.query).toString();
    return res.redirect(302, `/admin/${q ? `?${q}` : ""}`);
  }
  sendPlayStudioHtml(res);
});

/** OBS overlay /overlay altında; /play/overlay yanlış adres → yönlendir */
app.get(/^\/play\/overlay\/?$/i, (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  res.redirect(302, `/overlay${q ? `?${q}` : ""}`);
});

app.use(
  "/media/rooms",
  express.static(join(ROOT, "data", "rooms"), {
    maxAge: "60s",
    fallthrough: true,
  })
);

const roomManager = new RoomManager({
  io,
  chatMode: CHAT_MODE,
  gameDefaults: {
    winMessageTemplate: process.env.WIN_MESSAGE,
    nextQuestionDelayMs: Number(process.env.NEXT_QUESTION_DELAY_MS) || 5000,
    feedMax: PUZZLE_FEED_MAX,
    holdWinnerUntilNextCorrect: process.env.HOLD_WINNER_UNTIL_NEXT !== "0",
    celebrityCloseYears: Number(process.env.CELEBRITY_CLOSE_YEARS) || 2,
    celebrityWarmYears: Number(process.env.CELEBRITY_WARM_YEARS) || 5,
    broadcastHoldMs: Number(process.env.BROADCAST_HOLD_MS) || 6500,
    celebrityCorrectFlashMs:
      Number(process.env.CELEBRITY_CORRECT_FLASH_MS) || 5000,
    celebrityPrRotateMs: Number(process.env.CELEBRITY_PR_ROTATE_MS) || 5500,
    celebrityPrizeLabel:
      (process.env.CELEBRITY_PRIZE_LABEL || "").trim() || undefined,
    wrongBroadcastHoldMs: Number(process.env.WRONG_BROADCAST_HOLD_MS) || 5000,
    wrongBroadcastQueueMax: Math.min(
      30,
      Math.max(5, Number(process.env.WRONG_BROADCAST_QUEUE_MAX) || 15)
    ),
  },
});

function overlayUrl(roomId, layout, gameMode, opts = {}) {
  if ((opts.celebrityQuiz || opts.footballQuiz) && layout === "vertical") {
    return celebrityOverlayUrl(roomId);
  }
  const p = new URLSearchParams({
    room: roomId,
    layout,
    ...OVERLAY_QUERY,
  });
  if (isTeamRaceMode(gameMode)) p.set("mode", "team-race");
  else if (isPhotoBattleMode(gameMode)) p.set("mode", "photo-battle");
  else if (isFootballMode(gameMode)) p.set("mode", gameMode);
  return `${PUBLIC_URL}/overlay?${p}`;
}

function celebrityOverlayUrl(roomId) {
  const p = new URLSearchParams({ room: roomId, motion: "1", ...OVERLAY_QUERY });
  return `${PUBLIC_URL}/celebrity-overlay?${p}`;
}

function roomPhotoOverlayOpts(room) {
  const celebrityQuiz = isCelebrityAgeQuiz(room.game.questions);
  const footballQuiz =
    isFootballMode(room.config.gameMode) ||
    isFootballClubQuiz(room.game.questions) ||
    isFootballNationalityQuiz(room.game.questions);
  return { celebrityQuiz, footballQuiz };
}

function roomLinks(roomId, gameMode, opts = {}) {
  const q = `room=${roomId}`;
  const photoScreen = Boolean(opts.celebrityQuiz || opts.footballQuiz);
  return {
    admin: `${PUBLIC_URL}/admin/?${q}`,
    overlayHorizontal: overlayUrl(roomId, "horizontal", gameMode, opts),
    overlayVertical: photoScreen
      ? celebrityOverlayUrl(roomId)
      : overlayUrl(roomId, "vertical", gameMode, opts),
    overlayCelebrity: celebrityOverlayUrl(roomId),
  };
}

/** OBS overlay â€” oda yerleÅŸimi (herkese aÃ§Ä±k okuma; oda kodu gizli sayÄ±lÄ±r) */
app.get("/api/rooms/:roomId/layout/vertical", (req, res) => {
  const room = roomManager.getRoom(req.params.roomId);
  if (!room) {
    return res.status(404).json({ error: "YayÄ±n bulunamadÄ±" });
  }
  const layout = roomManager.readRoomLayoutVertical(req.params.roomId);
  if (!layout) {
    return res.status(404).json({ error: "YerleÅŸim tanÄ±mlÄ± deÄŸil" });
  }
  res.setHeader("Cache-Control", "no-store");
  res.json(layout);
});

app.post("/api/rooms/:roomId/layout/vertical", requireUser, handleRoom(async (req, res) => {
  roomManager.saveRoomLayoutVertical(
    req.params.roomId,
    req.user.id,
    req.body
  );
  res.json({ ok: true, roomId: req.params.roomId });
}));

app.get("/api/rooms/:roomId/layout/play", (req, res) => {
  const room = roomManager.getRoom(req.params.roomId);
  if (!room) {
    return res.status(404).json({ error: "Yayın bulunamadı" });
  }
  const layout = roomManager.readRoomLayoutPlay(req.params.roomId);
  if (!layout) {
    return res.status(404).json({ error: "Play yerleşimi tanımlı değil" });
  }
  res.setHeader("Cache-Control", "no-store");
  res.json(layout);
});

app.post("/api/rooms/:roomId/layout/play", requireUser, handleRoom(async (req, res) => {
  roomManager.saveRoomLayoutPlay(req.params.roomId, req.user.id, req.body);
  res.json({ ok: true, roomId: req.params.roomId });
}));

/** @deprecated â€” oda bazlÄ± POST kullanÄ±n */
app.post("/api/layout/vertical", requireUser, async (req, res) => {
  try {
    const body = req.body;
    if (!body || typeof body !== "object") {
      return res.status(400).json({ error: "GeÃ§ersiz yerleÅŸim verisi" });
    }
    await writeFile(LAYOUT_VERTICAL_PATH, `${JSON.stringify(body, null, 2)}\n`, "utf8");
    io.emit("layout:updated", {});
    res.json({ ok: true, deprecated: true });
  } catch (err) {
    res.status(500).json({ error: err.message || "KayÄ±t baÅŸarÄ±sÄ±z" });
  }
});

io.on("connection", (socket) => {
  const roomId = socket.handshake.query.room;
  if (!roomId) {
    socket.emit("error", { message: "room parametresi gerekli" });
    return;
  }
  const room = roomManager.getRoom(roomId);
  if (!room) {
    socket.emit("error", { message: "Oda bulunamadi" });
    return;
  }
  socket.join(roomId);
  roomManager.ensureQuestionsSynced(room);
  if (isTeamRaceMode(room.config.gameMode)) {
    socket.emit("race:state", roomManager._raceStatePayload(room));
  } else if (
    isPhotoBattleMode(room.config.gameMode) &&
    !photoRoomRunsCelebrityAge(room)
  ) {
    socket.emit("photo-battle:state", room.photoBattle.getSnapshot());
  } else if (roomUsesPuzzleEngine(room)) {
    socket.emit("game:state", room.game.getSnapshot());
  }
  socket.emit("config", {
    chatMode: CHAT_MODE,
    gameMode: room.config.gameMode,
    youtubeLinked: Boolean(room.youtubeChatConnected),
    roomId,
    roomName: room.name,
    botName: room.config.botName,
  });
});

function handleRoom(handler) {
  return async (req, res) => {
    const started = Date.now();
    auditApiRequest(req);
    res.on("finish", () => {
      auditApiResponse(req, res, Date.now() - started);
    });
    try {
      await handler(req, res);
    } catch (err) {
      auditRecord({
        roomId: req.params?.roomId,
        userId: req.user?.id ?? null,
        category: "api",
        level: "error",
        message: err.message || "handler error",
        detail: { path: req.originalUrl || req.url },
      });
      if (!res.headersSent) {
        res.status(err.status || 500).json({ error: err.message });
      }
    }
  };
}

/* â€”â€”â€” Kullanici (SQLite) â€”â€”â€” */

app.post("/api/auth/register", (req, res) => {
  try {
    const { username, password } = req.body ?? {};
    const user = registerUser(username, password);
    const session = loginUser(username, password);
    setSessionCookie(res, session.token);
    res.status(201).json(session);
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
});

app.post("/api/auth/login", (req, res) => {
  try {
    const { username, password } = req.body ?? {};
    const session = loginUser(username, password);
    setSessionCookie(res, session.token);
    res.json(session);
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
});

app.post("/api/auth/logout", (req, res) => {
  logoutSession(req.sessionToken);
  clearSessionCookie(res);
  res.json({ ok: true });
});

app.get("/api/auth/me", (req, res) => {
  if (!req.user) return res.json({ user: null });
  res.json({ user: req.user });
});

/* â€”â€”â€” Odalar â€”â€”â€” */

app.get("/api/rooms", requireUser, (_req, res) => {
  res.json(roomManager.listRooms(_req.user.id));
});

app.post("/api/rooms", requireUser, (req, res) => {
  const name = (req.body?.name || "Yayin").trim() || "Yayin";
  const room = roomManager.createRoom(name, req.user.id, {
    gameMode: req.body?.gameMode,
  });
  roomManager.log(room.id, `YayÄ±n oluÅŸturuldu: ${room.name}`, { kind: "system" });
  res.status(201).json({
    ...roomManager.getPublicInfo(room.id),
    links: roomLinks(room.id, room.config.gameMode),
  });
});

app.post("/api/rooms/:roomId/copy", requireUser, handleRoom((req, res) => {
  const name = typeof req.body?.name === "string" ? req.body.name.trim() : "";
  const { room, sourceId } = roomManager.copyRoom(
    req.params.roomId,
    req.user.id,
    name || undefined
  );
  res.status(201).json({
    ...roomManager.getPublicInfo(room.id),
    links: roomLinks(room.id, room.config.gameMode),
    copiedFrom: sourceId,
    youtubeLinked: false,
  });
}));

app.delete("/api/rooms/:roomId", requireUser, handleRoom((req, res) => {
  const result = roomManager.deleteRoom(req.params.roomId, req.user.id);
  res.json(result);
}));

app.get("/api/rooms/:roomId", requireUser, handleRoom((req, res) => {
  roomManager.ensureRoomAccess(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  res.json({
    ...roomManager.getPublicInfo(room.id),
    links: roomLinks(room.id, room.config.gameMode, roomPhotoOverlayOpts(room)),
    chatMode: CHAT_MODE,
    youtubeLinked: Boolean(room.youtubeChatConnected),
    game: roomUsesPuzzleEngine(room) ? room.game.getSnapshot() : null,
    race: isTeamRaceMode(room.config.gameMode) ? roomManager._raceStatePayload(room) : null,
    photoBattle:
      isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)
        ? room.photoBattle.getSnapshot()
        : null,
    config: room.config,
    celebrityQuiz: isCelebrityAgeQuiz(room.game.questions),
    footballQuiz: isFootballMode(room.config.gameMode),
  });
}));

app.patch("/api/rooms/:roomId/config", requireUser, handleRoom((req, res) => {
  const {
    videoId,
    videoIds,
    liveChatId,
    botName,
    announceWrong,
    winMessage,
    wrongMessage,
    gameMode,
    photoBattleSettings,
    streamUrlDraft,
  } = req.body ?? {};
  const patch = {};
  if (videoId !== undefined) patch.videoId = videoId;
  if (videoIds !== undefined) patch.videoIds = videoIds;
  if (liveChatId !== undefined) patch.liveChatId = liveChatId;
  if (botName !== undefined) patch.botName = botName;
  if (announceWrong !== undefined) patch.announceWrong = announceWrong;
  if (winMessage !== undefined) patch.winMessage = winMessage;
  if (wrongMessage !== undefined) patch.wrongMessage = wrongMessage;
  if (gameMode !== undefined) patch.gameMode = gameMode;
  if (photoBattleSettings !== undefined) patch.photoBattleSettings = photoBattleSettings;
  if (streamUrlDraft !== undefined) {
    patch.streamUrlDraft = normalizeStreamUrlDraft(streamUrlDraft);
  }
  const config = roomManager.updateConfig(
    req.params.roomId,
    patch,
    req.user.id
  );
  const logMsg = patch.gameMode !== undefined ? "Oyun modu kaydedildi." : "Bot ayarlarÄ± kaydedildi.";
  roomManager.log(req.params.roomId, logMsg, {
    highlight: true,
    kind: "system",
  });
  res.json(config);
}));

app.get("/api/rooms/:roomId/status", handleRoom(async (req, res) => {
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  roomManager.ensureQuestionsSynced(room);
  res.json({
    chatMode: CHAT_MODE,
    roomId: room.id,
    roomName: roomManager.getRoomDisplayName(room),
    botName: room.config.botName,
    youtubeLinked: Boolean(room.youtubeChatConnected),
    youtube: await roomManager.getYouTubeStatus(room),
    game: roomUsesPuzzleEngine(room) ? room.game.getSnapshot() : null,
    race: isTeamRaceMode(room.config.gameMode) ? roomManager._raceStatePayload(room) : null,
    photoBattle:
      isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)
        ? room.photoBattle.getSnapshot()
        : null,
    config: room.config,
    celebrityQuiz: isCelebrityAgeQuiz(room.game.questions),
    celebrityInPhotoMode: roomUsesPuzzleEngine(room) && isPhotoBattleMode(room.config.gameMode),
    footballQuiz: isFootballMode(room.config.gameMode),
    puzzleFeedMax: room.game.feedMax,
    puzzleFeedCount: (room.game.answerFeed || []).length,
    links: roomLinks(room.id, room.config.gameMode, roomPhotoOverlayOpts(room)),
  });
}));

app.get("/api/youtube/setup", requireUser, (_req, res) => {
  res.json(roomManager.getYouTubeApiConfig());
});

app.get("/api/rooms/:roomId/youtube/status", requireUser, handleRoom(async (req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  res.json(await roomManager.getYouTubeStatus(room));
}));

app.post("/api/rooms/:roomId/youtube/connect", requireUser, handleRoom(async (req, res) => {
  const { streamUrl, url, streamUrls } = req.body ?? {};
  let link = "";
  if (Array.isArray(streamUrls) && streamUrls.length) {
    link = normalizeStreamUrlDraft(streamUrls);
  } else {
    link = normalizeStreamUrlDraft(streamUrl || url);
  }
  if (!link.trim()) {
    return res.status(400).json({ error: "streamUrl gerekli (yayin linki)" });
  }
  const status = await roomManager.connectYouTube(
    req.params.roomId,
    link,
    req.user.id
  );
  res.json(status);
}));

app.post("/api/rooms/:roomId/youtube/disconnect", requireUser, handleRoom(async (req, res) => {
  const status = await roomManager.disconnectYouTube(req.params.roomId, req.user.id);
  res.json(status);
}));

/** InnerChat ham mesaj tap (geçici debug — oda sahibi) */
app.get("/api/rooms/:roomId/inner-chat/tap", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  res.json(roomManager.getInnerChatTap(room));
}));

app.post("/api/rooms/:roomId/inner-chat/tap/clear", requireUser, handleRoom((req, res) => {
  res.json(roomManager.clearInnerChatTap(req.params.roomId, req.user.id));
}));

app.get("/api/rooms/:roomId/inner-chat/diagnostic", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  res.json(roomManager.getInnerChatDiagnostic(room));
}));

app.get("/api/rooms/:roomId/audit-log", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const limit = Math.min(300, Math.max(20, Number(req.query.limit) || 150));
  const category = req.query.category ? String(req.query.category) : null;
  res.json({
    items: listAuditLog(req.params.roomId, { limit, category }),
    enabled: !["0", "false", "off", "no"].includes(
      String(process.env.AUDIT_LOG ?? "1").toLowerCase()
    ),
  });
}));

app.post("/api/rooms/:roomId/audit-log/clear", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  res.json(clearAuditLog(req.params.roomId));
}));

app.get("/api/rooms/:roomId/questions", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  roomManager.ensureQuestionsSynced(room);
  res.json({
    questions: room.game.questions,
    count: room.game.questions.length,
    game: roomUsesPuzzleEngine(room) ? room.game.getSnapshot() : null,
    photoBattle:
      isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)
        ? room.photoBattle.getSnapshot()
        : null,
    config: { gameMode: room.config.gameMode },
    celebrityQuiz: isCelebrityAgeQuiz(room.game.questions),
    footballQuiz: isFootballMode(room.config.gameMode),
  });
}));

app.get("/api/football/pack-meta", requireUser, (_req, res) => {
  res.json(getFootballPackMeta());
});

function importFootballPackHandler(req, res) {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  const kind = String(req.body?.kind || "").trim().toLowerCase();
  if (kind !== "club" && kind !== "nationality") {
    return res.status(400).json({
      error: 'kind: "club" veya "nationality" gerekli',
    });
  }
  const parsed = footballPlayersToQuestions(kind);
  if (!parsed.length) {
    return res.status(400).json({
      error: "Futbol oyuncu listesi boş (data/football/players.json)",
    });
  }
  const prev = room.game.questions || [];
  const next =
    req.body?.mode === "append" ? [...prev, ...parsed] : parsed;
  try {
    room.game.setQuestions(next);
    roomManager.persistQuestions(room);
    roomManager.ensureQuestionsSynced(room);
  } catch (err) {
    return res.status(err.status || 500).json({
      error: err.message || "Sorular kaydedilemedi",
    });
  }
  const label =
    kind === "club" ? "Güncel takım" : "Milliyet";
  roomManager.log(
    req.params.roomId,
    `${parsed.length} futbol sorusu yüklendi (${label}, toplam ${next.length}).`,
    { kind: "system", highlight: true }
  );
  const overlayOpts = roomPhotoOverlayOpts(room);
  res.json({
    questions: room.game.questions,
    count: room.game.questions.length,
    imported: parsed.length,
    kind,
    footballQuiz: true,
    gameMode: room.config.gameMode,
    game: room.game.getSnapshot(),
    links: roomLinks(room.id, room.config.gameMode, overlayOpts),
  });
}

app.post(
  "/api/rooms/:roomId/football/load-pack",
  requireUser,
  handleRoom(importFootballPackHandler)
);

function importCelebrityQuestionsHandler(req, res) {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  let room = roomManager.getRoomOrThrow(req.params.roomId);
  const { csv, hint, mode } = req.body ?? {};
  const parsed = parseCelebrityCsv(String(csv || ""), { hint });
  if (!parsed.length) {
    return res.status(400).json({
      error: "Geçerli satır bulunamadı. Format: isim,yaş,doğum_tarihi,foto_url",
    });
  }
  const prev = room.game.questions || [];
  const next = mode === "append" ? [...prev, ...parsed] : parsed;
  try {
    room.game.setQuestions(next);
    roomManager.persistQuestions(room);
    roomManager.ensureQuestionsSynced(room);
  } catch (err) {
    return res.status(err.status || 500).json({
      error: err.message || "Sorular kaydedilemedi",
    });
  }
  const modeNote = isPhotoBattleMode(room.config.gameMode)
    ? "Photo Quiz modu korundu — ünlü yaş tahmini aktif."
    : "Bulmaca modu.";
  roomManager.log(
    req.params.roomId,
    `${parsed.length} ünlü soru ${mode === "append" ? "eklendi" : "yüklendi"} (toplam ${next.length}). ${modeNote}`,
    { kind: "system", highlight: true }
  );
  const overlayOpts = roomPhotoOverlayOpts(room);
  res.json({
    questions: room.game.questions,
    count: room.game.questions.length,
    imported: parsed.length,
    celebrityQuiz: overlayOpts.celebrityQuiz,
    footballQuiz: overlayOpts.footballQuiz,
    gameMode: room.config.gameMode,
    game: room.game.getSnapshot(),
    links: roomLinks(room.id, room.config.gameMode, overlayOpts),
  });
}

app.post(
  "/api/rooms/:roomId/questions/import-celebrities",
  requireUser,
  handleRoom(importCelebrityQuestionsHandler)
);
/** Kısa yol — aynı işlem */
app.post(
  "/api/rooms/:roomId/import-celebrities",
  requireUser,
  handleRoom(importCelebrityQuestionsHandler)
);

app.put("/api/rooms/:roomId/questions", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  const { questions } = req.body;
  if (!Array.isArray(questions)) {
    return res.status(400).json({ error: "questions dizisi gerekli" });
  }
  try {
    room.game.setQuestions(questions);
    roomManager.persistQuestions(room);
    roomManager.ensureQuestionsSynced(room);
  } catch (err) {
    return res.status(err.status || 500).json({
      error: err.message || "Sorular kaydedilemedi",
    });
  }
  const count = room.game.questions.length;
  roomManager.log(req.params.roomId, `${count} soru kaydedildi.`, {
    kind: "system",
  });
  res.json({
    questions: room.game.questions,
    count,
    game: room.game.getSnapshot(),
  });
}));

app.post("/api/rooms/:roomId/game/start", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)) {
    const snap = roomManager.startPhotoBattle(room);
    res.json({ photoBattle: snap });
    return;
  }
  if (isTeamRaceMode(room.config.gameMode)) {
    const snap = roomManager.startTeamRace(room);
    const ap = room.raceAutopilot?.getPublicStatus?.();
    roomManager.log(
      req.params.roomId,
      ap?.armed
        ? `Otomatik yayın açıldı — tur #${snap.round} (sohbet analiz ediliyor)`
        : `Takım yarışı turu #${snap.round} başladı.`,
      { highlight: true, kind: "game" }
    );
    res.json(roomManager._raceStatePayload(room));
    return;
  }
  if (req.body?.demo === true) {
    room.game.seedDemoPreview();
    roomManager.log(req.params.roomId, "Ã–nizleme demosu baÅŸlatÄ±ldÄ±.", {
      highlight: true,
      kind: "system",
    });
    res.json(room.game.getSnapshot());
    return;
  }
  roomManager.ensureQuestionsSynced(room);
  if (!room.game.questions.length) {
    return res.status(400).json({
      error: "Ã–nce en az bir soru ekleyip Â«SorularÄ± kaydetÂ» deyin.",
    });
  }
  roomManager.wireChat(room);
  room.game.start();
  roomManager.persistGameState(room);
  roomManager._syncYoutubePollingMode(room, room.game.getSnapshot());
  auditRecord({
    roomId: req.params.roomId,
    userId: req.user?.id ?? null,
    category: "game",
    level: "info",
    message: "Oyun başlatıldı",
    detail: {
      gameMode: room.config.gameMode,
      questions: room.game.questions?.length ?? 0,
      youtubeConnected: room.youtubeChatConnected,
    },
  });
  roomManager.log(req.params.roomId, "Oyun baÅŸladÄ±.", { highlight: true, kind: "game" });
  roomManager.announceGameStarted(room).catch((err) => {
    console.error("[game start chat]", err.message);
  });
  res.json(room.game.getSnapshot());
}));

app.post("/api/rooms/:roomId/game/stop", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)) {
    const snap = roomManager.stopPhotoBattle(room);
    roomManager.log(req.params.roomId, "Photo Quiz durduruldu.", { kind: "game" });
    res.json({ photoBattle: snap });
    return;
  }
  if (isTeamRaceMode(room.config.gameMode)) {
    const snap = roomManager.stopTeamRace(room);
    const win = snap.lastWinner;
    roomManager.log(
      req.params.roomId,
      win
        ? `Tur bitti — önde: ${win.teamName} (${win.spawnCount} spawn)`
        : "Takım yarışı turu durduruldu.",
      { kind: "game", highlight: Boolean(win) }
    );
    res.json(snap);
    return;
  }
  room.game.stop();
  roomManager.log(req.params.roomId, "Oyun durduruldu.", { kind: "game" });
  res.json(room.game.getSnapshot());
}));

app.post("/api/rooms/:roomId/game/reset", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)) {
    const snap = roomManager.resetPhotoBattle(room);
    roomManager.log(req.params.roomId, "Photo Quiz sıfırlandı.", {
      highlight: true,
      kind: "game",
    });
    res.json({ photoBattle: snap });
    return;
  }
  if (isTeamRaceMode(room.config.gameMode)) {
    const snap = roomManager.resetTeamRace(room);
    roomManager.log(req.params.roomId, "Takım yarışı sıfırlandı.", {
      highlight: true,
      kind: "game",
    });
    res.json(snap);
    return;
  }
  room.game.reset();
  roomManager.log(req.params.roomId, "Oyun sÄ±fÄ±rlandÄ± (puanlar ve sÄ±ra).", {
    highlight: true,
    kind: "game",
  });
  res.json(room.game.getSnapshot());
}));

app.post("/api/rooms/:roomId/game/skip", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)) {
    const snap = roomManager.skipPhotoBattleVote(room);
    res.json({ photoBattle: snap });
    return;
  }
  if (isTeamRaceMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Sonraki soru yalnızca bulmaca modunda kullanılır." });
  }
  const idxBefore = room.game.currentIndex;
  room.game.skip();
  const snap = room.game.getSnapshot();
  if (room.game.currentIndex !== idxBefore) {
    roomManager.log(req.params.roomId, "Sonraki soruya geçildi.", { kind: "game" });
  }
  res.json(snap);
}));

app.post("/api/rooms/:roomId/game/demo-preview", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (isTeamRaceMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Önizleme demosu yalnızca bulmaca modunda kullanılır." });
  }
  room.game.seedDemoPreview();
  roomManager.log(req.params.roomId, "Ã–nizleme demosu yÃ¼klendi.", {
    highlight: true,
    kind: "system",
  });
  res.json(room.game.getSnapshot());
}));

app.get("/api/rooms/:roomId/events", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const limit = Math.min(250, Math.max(1, Number(req.query.limit) || 100));
  const rows = eventRepo.listByRoom(req.params.roomId, limit);
  res.setHeader("Cache-Control", "no-store");
  res.json(rows);
}));

app.post("/api/rooms/:roomId/events", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const { message, highlight } = req.body ?? {};
  if (!message || !String(message).trim()) {
    return res.status(400).json({ error: "message gerekli" });
  }
  const entry = roomManager.log(req.params.roomId, String(message).trim(), {
    highlight: Boolean(highlight),
    kind: "info",
  });
  res.status(201).json(entry);
}));

app.patch("/api/rooms/:roomId/race/settings", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isTeamRaceMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda takım yarışı modunda değil." });
  }
  const config = roomManager.updateConfig(req.params.roomId, { raceSettings: req.body ?? {} }, req.user.id);
  res.json({
    raceSettings: config.raceSettings,
    snapshot: roomManager._raceStatePayload(room),
  });
}));

app.post("/api/rooms/:roomId/race/eliminate", handleRoom((req, res) => {
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isTeamRaceMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda takım yarışı modunda değil." });
  }
  const entityId = String(req.body?.entityId || "").trim();
  if (!entityId) return res.status(400).json({ error: "entityId gerekli" });
  roomManager.eliminateTeamRaceEntity(room, entityId);
  res.json({ snapshot: room.teamRace.getSnapshot() });
}));

app.post("/api/rooms/:roomId/race/chaos", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isTeamRaceMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda takım yarışı modunda değil." });
  }
  if (!room.teamRace.isRunning()) {
    room.teamRace.start();
  }
  if (!room.teamRace.isChaos()) {
    const ok = room.teamRace.forceChaos();
    if (!ok) {
      return res.status(400).json({
        error: "Kaos başlatılamadı.",
        snapshot: room.teamRace.getSnapshot(),
      });
    }
    roomManager._syncYoutubePollingMode(room);
    room.teamRace.onStateChange?.();
  }
  res.json(roomManager._raceStatePayload(room));
}));

app.post("/api/rooms/:roomId/race/shock", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isTeamRaceMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda takım yarışı modunda değil." });
  }
  const ok = roomManager.triggerTeamRaceShock(room);
  if (!ok) return res.status(400).json({ error: "Şok dalgası için tur kaosta olmalı." });
  res.json(roomManager._raceStatePayload(room));
}));

app.get("/api/rooms/:roomId/photo-battle/pool", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isPhotoBattleMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda Photo Quiz modunda değil." });
  }
  res.json(roomManager.getPhotoBattlePool(room));
}));

app.post("/api/rooms/:roomId/photo-battle/pool", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isPhotoBattleMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda Photo Quiz modunda değil." });
  }
  const { images } = req.body ?? {};
  const result = roomManager.addPhotoBattleImages(room, images);
  roomManager.log(
    req.params.roomId,
    `${result.added.length} görsel havuza eklendi (toplam ${result.pool.length}).`,
    { kind: "system", highlight: true }
  );
  res.json(result);
}));

app.delete("/api/rooms/:roomId/photo-battle/pool/:photoId", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isPhotoBattleMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda Photo Quiz modunda değil." });
  }
  res.json(roomManager.removePhotoBattleImage(room, req.params.photoId));
}));

app.delete("/api/rooms/:roomId/photo-battle/pool", requireUser, handleRoom((req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  if (!isPhotoBattleMode(room.config.gameMode)) {
    return res.status(400).json({ error: "Bu oda Photo Quiz modunda değil." });
  }
  res.json(roomManager.clearPhotoBattlePool(room));
}));

app.post("/api/rooms/:roomId/chat/test", requireUser, handleRoom(async (req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  const { author = "Test", text, simulated = false } = req.body ?? {};
  const result = await roomManager.injectTestComment(room, author, text, { simulated });
  res.json(result);
}));

/** Eski panel istekleri â€” chat/test ile aynÄ± */
app.post("/api/rooms/:roomId/mock/comment", requireUser, handleRoom(async (req, res) => {
  roomManager.assertRoomOwner(req.params.roomId, req.user.id);
  const room = roomManager.getRoomOrThrow(req.params.roomId);
  const { author = "Test", text, simulated = false } = req.body ?? {};
  const result = await roomManager.injectTestComment(room, author, text, { simulated });
  res.json(result);
}));

app.use(
  express.static(join(ROOT, "public"), {
    redirect: false,
    setHeaders(res, filePath) {
      const noStore =
        /[/\\]admin[/\\]/.test(filePath) ||
        /[/\\]login[/\\]/.test(filePath) ||
        /[/\\]play[/\\]/.test(filePath) ||
        /[/\\]celebrity-age[/\\]/.test(filePath) ||
        /[/\\]team-race[/\\]arena-physics/.test(filePath) ||
        /[/\\]team-race[/\\].*-template\.js$/.test(filePath) ||
        /[/\\]play[/\\]play\.(js|css)$/.test(filePath);
      if (noStore) {
        res.setHeader("Cache-Control", "no-store, must-revalidate");
      }
      if (filePath.endsWith(".html")) {
        res.setHeader("Content-Type", "text/html; charset=utf-8");
      } else if (filePath.endsWith(".js")) {
        res.setHeader("Content-Type", "application/javascript; charset=utf-8");
      } else if (filePath.endsWith(".css")) {
        res.setHeader("Content-Type", "text/css; charset=utf-8");
      }
    },
  })
);

httpServer.listen(PORT, BIND_HOST, () => {
  const playLine = isPlaygroundAllowed()
    ? `|  Oyun alani:  ${PUBLIC_URL}/play/\n`
    : "";
  const celebLine = `|  Unlu yas OBS: ${PUBLIC_URL}/celebrity-overlay?room=ODA\n`;
  console.log(
    [
      "",
      "+----------------------------------------------------------+",
      "|  Bulmaca777 - YouTube canli yayin bulmacalari            |",
      "+----------------------------------------------------------+",
      `|  Ana sayfa:  ${PUBLIC_URL}/`,
      `|  Giris:      ${PUBLIC_URL}/login/`,
      `|  Panel:      ${PUBLIC_URL}/admin/`,
      celebLine.trimEnd(),
      playLine.trimEnd(),
      `|  Sohbet:     ${CHAT_MODE === "youtube" ? "InnerChat (youtube-chat, video link)" : "mock (panel testi)"}`,
      "+----------------------------------------------------------+",
      "",
    ]
      .filter(Boolean)
      .join("\n")
  );
});
