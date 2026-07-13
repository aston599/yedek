import {
  teamFlagImg,
  teamFlagUrl,
  formatWinnerLines,
  sortedRoundWinners,
} from "/team-race/team-ui.js?v=1";
import { applyArenaCtasToDom } from "/team-race/youtube-ctas-ui.js?v=1";
import { createArenaInfoTicker } from "/team-race/arena-info-ticker.js?v=4";
import {
  renderPhotoBattleOverlay,
  bindPhotoBattleOverlayDom,
} from "/photo-battle/overlay-ui.js?v=1";

const params = new URLSearchParams(
  typeof window.__BULMACA_QUERY__ === "string"
    ? window.__BULMACA_QUERY__
    : window.location.search
);

/** srcdoc önizleme veya OBS — gerçek sunucu kökü (asla "about:" olmamalı) */
function getServerOrigin() {
  if (typeof window.__BULMACA_SERVER__ === "string" && window.__BULMACA_SERVER__) {
    return window.__BULMACA_SERVER__.replace(/\/$/, "");
  }
  const o = window.location.origin;
  if (o && o !== "null" && !o.startsWith("about:")) return o;
  return "http://127.0.0.1:3847";
}

const SERVER_ORIGIN = getServerOrigin();
const layout = params.get("layout") === "horizontal" ? "horizontal" : "vertical";
const roomId = params.get("room");
const urlMode = params.get("mode");
const urlGameMode =
  urlMode === "team-race"
    ? "team-race"
    : urlMode === "photo-battle"
      ? "photo-battle"
      : "puzzle";
/** Admin önizleme ?mode=team-race — sunucu config bunun üzerine yazmasın */
const urlGameModeLocked = params.has("mode");
let overlayGameMode = urlGameMode;
const LAYOUT_STORAGE_KEY = "bulmaca_layout_vertical";
const FRAME_SIZE =
  layout === "horizontal" ? { w: 1920, h: 1080 } : { w: 1080, h: 1920 };
const MOTION_OFF = params.get("motion") === "0" || params.get("fx") === "0";
const EMBED_PREVIEW = params.get("embed") === "1";

if (MOTION_OFF) document.body.classList.add("motion-off");
if (EMBED_PREVIEW) document.body.classList.add("overlay-embed");

let prevFeedSignature = "";
let prevQuestionKey = "";
let prevLastAnswerAt = "";
let prevGameState = "";

const TEXT = {
  idleTitle: "Yayına hazır",
  idleSub: "Panelden Başlat deyin",
  winnerHint: "TEBRİKLER!",
  endedTitle: "Tüm bulmacalar bitti",
  endedSub: "Teşekkürler!",
};

const CELEBRITY_TEXT = {
  idleTitle: "Ünlülerin Yaşını Tahmin Et",
  idleSub: "Sohbette yaşı yazın · Panelden <strong>Başlat</strong>",
  winnerHint: "DOĞRU TAHMİN!",
  endedTitle: "30 ünlü bitti",
  endedSub: "Sıradaki yayında görüşürüz!",
};

let celebrityQuizActive = false;

function applyCelebrityQuizUi(active) {
  celebrityQuizActive = Boolean(active);
  layoutEl.dataset.overlaySubmode = celebrityQuizActive ? "celebrity-age" : "";
}

/** Photo Quiz + ünlü yaş → Lab ile aynı ekran (/celebrity-overlay) */
function redirectToCelebrityOverlay() {
  const p = new URLSearchParams(params);
  p.delete("mode");
  p.delete("layout");
  if (!p.has("motion")) p.set("motion", "1");
  const target = `${SERVER_ORIGIN}/celebrity-overlay?${p}`;
  if (location.href.replace(/\/$/, "") === target.replace(/\/$/, "")) return;
  location.replace(target);
}

function celebrityAgeOverlayMode() {
  return celebrityQuizActive && overlayGameMode === "photo-battle";
}

function overlayCopy(state) {
  return celebrityQuizActive ? CELEBRITY_TEXT : TEXT;
}

let FEED_SLOTS = 7;

const layoutEl = document.getElementById("layout");
layoutEl.dataset.layout = layout;

function normalizeOverlayMode(mode) {
  const v = String(mode || "").toLowerCase();
  if (v === "team-race" || v === "team_race") return "team-race";
  if (v === "photo-battle" || v === "photo_battle" || v === "photo-quiz") {
    return "photo-battle";
  }
  return "puzzle";
}

const photoBattleRoot = document.getElementById("photoBattleOverlay");
const photoBattleEls = photoBattleRoot
  ? bindPhotoBattleOverlayDom(photoBattleRoot)
  : null;

function applyOverlayGameMode(mode) {
  if (!urlGameModeLocked) {
    overlayGameMode = normalizeOverlayMode(mode);
  }
  layoutEl.dataset.overlayMode = overlayGameMode;
  const race = document.getElementById("teamRaceOverlay");
  if (race) {
    race.classList.toggle("hidden", overlayGameMode !== "team-race");
    race.setAttribute("aria-hidden", overlayGameMode !== "team-race" ? "true" : "false");
  }
  if (photoBattleRoot) {
    const showPb = overlayGameMode === "photo-battle";
    photoBattleRoot.classList.toggle("hidden", !showPb);
    photoBattleRoot.setAttribute("aria-hidden", showPb ? "false" : "true");
  }
  if (overlayGameMode === "photo-battle") {
    layoutEl.dataset.state = "active";
  }
}

function renderPhotoBattle(state) {
  if (!photoBattleEls) return;
  renderPhotoBattleOverlay(state, photoBattleEls);
  const phase = state?.phase || "idle";
  layoutEl.dataset.state =
    phase === "voting" || phase === "result"
      ? "active"
      : phase === "champion"
        ? "winner"
        : "idle";
}

function formatUsername(name) {
  const n = String(name || "Anonim").trim();
  return n.startsWith("@") ? n : `@${n}`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const raceEls = {
  overlay: () => document.getElementById("teamRaceOverlay"),
  title: () => document.getElementById("raceStatusTitle"),
  sub: () => document.getElementById("raceStatusSub"),
  stats: () => document.getElementById("raceStatsLine"),
  leaderboard: () => document.getElementById("raceLeaderboard"),
  feed: () => document.getElementById("raceSpawnFeed"),
  winnerBanner: () => document.getElementById("raceWinnerBanner"),
  winnerFlag: () => document.getElementById("raceWinnerFlag"),
  winnerName: () => document.getElementById("raceWinnerName"),
  roundWinners: () => document.getElementById("raceRoundWinners"),
  topViewers: () => document.getElementById("raceTopViewers"),
  activityStrip: () => document.getElementById("raceActivityStrip"),
};

let raceRoundHistory = [];
let lastRaceActivityId = "";

function formatRaceActivityLine(row) {
  if (row?.type === "cta" && row.teamName) {
    return `${row.author} → ${row.teamName}`;
  }
  if (row?.type === "spawn" && row.teamName) {
    return `${row.author} ${row.teamName}'ı seçti!`;
  }
  if (row?.type === "unmatched") {
    const t = String(row.text || "").trim();
    return t ? `${row.author}: ${t}` : `${row.author} takım yazmadı`;
  }
  return row?.author || "";
}

function renderRaceRoundWinners(history = raceRoundHistory, snap = null) {
  const ul = raceEls.roundWinners();
  if (!ul) return;
  const maxR = snap?.series?.maxRounds ?? snap?.settings?.maxRounds ?? 8;
  const recent = sortedRoundWinners(history, maxR);
  ul.innerHTML = recent.length
    ? recent
        .map(
          (r) =>
            `<li><span class="race-rw-round">TUR ${r.round}</span>${teamFlagImg(teamFlagUrl(r.teamCode, r.flagUrl), "xs", r.teamName || r.teamCode)}<span>${escapeHtml(r.teamName || r.teamCode)}</span></li>`
        )
        .join("")
    : "";
}

function renderRaceTopViewers(topViewers = []) {
  const ol = raceEls.topViewers();
  if (!ol) return;
  ol.innerHTML = (topViewers || []).length
    ? topViewers
        .map(
          (v) =>
            `<li><span class="race-tv-rank">${v.rank}</span>${v.lastTeamCode || v.flagUrl ? teamFlagImg(teamFlagUrl(v.lastTeamCode, v.flagUrl), "xs", v.author) : ""}<span class="race-tv-name">${escapeHtml(v.author)}${v.simulated ? '<span class="race-tv-sim">sim</span>' : ""}</span><strong title="Sohbet mesaj sayısı">${v.count}×</strong></li>`
        )
        .join("")
    : "";
}

function buildRaceInfoCtx(race) {
  const phase = race?.phase || "idle";
  return {
    phase: phase === "running" ? "running" : phase === "idle" ? "idle" : phase,
    roundPhase: race?.roundPhase,
    chaos: race?.chaos,
  };
}

function raceActivityRowId(row) {
  return row?.id || `${row?.at || ""}-${row?.author || ""}-${row?.type || ""}`;
}

function syncRaceActivityFromSnap(race) {
  const ticker = ensureRaceInfoTicker();
  if (!ticker || !race || race.phase !== "running") return;
  const rows = (race.activityFeed || []).filter((r) => r?.type === "spawn");
  if (!rows.length) return;
  const head = rows[0];
  const id = raceActivityRowId(head);
  if (id === lastRaceActivityId) return;
  lastRaceActivityId = id;
  ticker.pingNewJoin(head, buildRaceInfoCtx(race));
}

function renderRaceLeaderboard(teamCounts = {}) {
  const ul = raceEls.leaderboard();
  if (!ul) return;
  const rows = Object.entries(teamCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  if (!rows.length) {
    ul.innerHTML = "";
    return;
  }
  ul.innerHTML = rows
    .map(
      ([code, count]) =>
        `<li class="race-lb-row">${teamFlagImg(teamFlagUrl(code), "md", code)}<span class="race-lb-count">${count}</span></li>`
    )
    .join("");
}

function renderRaceSpawnFeed(recent = []) {
  const ul = raceEls.feed();
  if (!ul) return;
  ul.innerHTML = recent
    .slice(0, 10)
    .map(
      (s) =>
        `<li class="race-spawn-row race-spawn-row--enter">${teamFlagImg(teamFlagUrl(s.teamCode, s.flagUrl), "md", s.teamName || s.teamCode)}<span class="race-spawn-user">${escapeHtml(formatUsername(s.displayName))}</span><span class="race-spawn-team">${escapeHtml(s.teamName || s.teamCode)}</span></li>`
    )
    .join("");
}

function formatRaceMs(ms) {
  if (ms == null) return "—";
  const sec = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

let raceInfoTicker = null;

function ensureRaceInfoTicker() {
  if (!raceInfoTicker) {
    raceInfoTicker = createArenaInfoTicker(raceEls.winnerBanner());
  }
  return raceInfoTicker;
}

function syncRaceInfoBand(race) {
  const ticker = ensureRaceInfoTicker();
  if (!ticker || !race) return;
  const phase = race.phase || "idle";
  const round = race.round || 0;
  const winnerForRound =
    race.lastWinner &&
    phase === "idle" &&
    (!round || race.lastWinner.round === round);

  if (winnerForRound) {
    ticker.setVisible(true);
    ticker.showWinner(race.lastWinner, round);
    return;
  }

  if (phase === "running" || phase === "idle") {
    ticker.setVisible(true);
    ticker.syncFeed({
      recentSpawns: race.recentSpawns,
      activityFeed: race.activityFeed,
    });
    ticker.setContext(buildRaceInfoCtx(race));
    syncRaceActivityFromSnap(race);
  } else {
    ticker.setVisible(false);
  }
}

function renderRaceWinner(lastWinner, phase, round = 0) {
  /* Bilgi bandı: syncRaceInfoBand içinde yönetiliyor */
  void lastWinner;
  void phase;
  void round;
}

function renderRace(race) {
  if (!race || overlayGameMode !== "team-race") return;
  const phase = race.phase || "idle";
  const overlay = raceEls.overlay();
  if (overlay) overlay.dataset.racePhase = phase;

  const title = raceEls.title();
  const sub = raceEls.sub();
  const stats = raceEls.stats();

  if (phase === "running") {
    const rp = race.roundPhase || (race.chaos ? "chaos" : "gathering");
    if (title) {
      title.textContent =
        rp === "chaos"
          ? `Tur ${race.round} · ⚡ KAOS`
          : race.round
            ? `Tur ${race.round} · Toplanma`
            : "Yarış aktif";
    }
    if (sub) {
      if (rp === "gathering" && race.gatherBlockedReason) {
        sub.textContent = race.gatherBlockedReason;
      } else if (rp === "gathering") {
        const e = race.engagement || {};
        const req = race.gatherRequirements || {};
        sub.textContent = `Toplanma ${formatRaceMs(race.gatherRemainingMs)} — ${e.participants ?? 0}/${req.minParticipants ?? "?"} kişi · ${e.teams ?? 0}/${req.minTeams ?? "?"} takım`;
      } else {
        const graceMs = race.settings?.chaosEliminationGraceMs ?? 5000;
        const gr = race.chaosStartedAt
          ? Math.max(0, graceMs - (Date.now() - new Date(race.chaosStartedAt).getTime()))
          : 0;
        sub.textContent =
          gr > 0
            ? `Kaos — ${formatRaceMs(gr)} elenme kapalı, sonra çıkıştan düşen elenir`
            : "Çıkıştan düşen elenir — kısaltma veya tam ad yaz";
      }
    }
  } else {
    if (title) title.textContent = "Katıl";
    if (sub) {
      sub.textContent =
        "Sohbette: Galatasaray, gs, fener… · beğen · abone · takip";
    }
  }

  const arenaStage = document.querySelector(".team-race-arena-stage");
  if (arenaStage) applyArenaCtasToDom(arenaStage, race.arenaCtas);

  if (stats) {
    const s = race.stats || {};
    stats.textContent = `Spawn: ${s.spawns ?? 0} · Eşleşmeyen: ${s.unmatched ?? 0}`;
  }

  renderRaceLeaderboard(race.activeByTeam || race.teamCounts || {});
  if (Array.isArray(race.roundHistory)) raceRoundHistory = race.roundHistory;
  renderRaceRoundWinners(race.roundHistory || raceRoundHistory, race);
  renderRaceTopViewers(race.topViewers || []);
  syncRaceInfoBand(race);
  renderRaceSpawnFeed(race.recentSpawns || []);

  if (phase === "running") {
    ensureRaceArena().then((a) => syncRaceArenaFromSnapshot(a, race));
  } else if (phase === "idle" && raceArena) {
    raceArena.clear();
  }

  if (stats) {
    const s = race.stats || {};
    const ap = race.autopilot;
    const byTeam = race.activeByTeam || race.teamCounts || {};
    const summed =
      Object.values(byTeam).reduce((acc, n) => acc + (Number(n) || 0), 0) || 0;
    const arenaCount =
      Number.isFinite(Number(race.entityCount))
        ? Number(race.entityCount)
        : Array.isArray(race.activeEntities)
          ? race.activeEntities.length
          : summed;
    if (ap?.armed && ap.statusMessage) {
      stats.textContent = ap.statusMessage;
    } else {
      stats.textContent = `Arenada: ${arenaCount} · Spawn: ${s.spawns ?? 0}`;
    }
  }
}

let raceArena = null;
let raceArenaInit = null;
let lastShockWaveAt = null;

async function syncRaceArenaFromSnapshot(arena, race) {
  if (!arena || !race) return;
  const rp = race.roundPhase || (race.chaos ? "chaos" : "gathering");
  const chaosEffective = Boolean(race.chaos || rp === "chaos");
  arena.setRoundPhase(rp);
  arena.setChaos(chaosEffective);
  const shockAt = race.shockWaveAt || null;
  if (shockAt && shockAt !== lastShockWaveAt && rp === "chaos") {
    arena.triggerShockWave?.();
    lastShockWaveAt = shockAt;
  } else if (!shockAt && rp !== "chaos") {
    lastShockWaveAt = null;
  }

  const entities = race.activeEntities || [];
  const valid = new Set(entities.map((e) => e.id));
  for (const id of [...arena.bodies.keys()]) {
    if (!valid.has(id)) {
      const body = arena.bodies.get(id);
      arena.Matter.World.remove(arena.world, body);
      arena.bodies.delete(id);
    }
  }
  for (const e of entities) {
    if (!arena.bodies.has(e.id)) await arena.spawn(e);
  }
}

async function ensureRaceArena() {
  if (raceArena) return raceArena;
  if (!window.Matter || overlayGameMode !== "team-race") return null;
  if (raceArenaInit) return raceArenaInit;
  raceArenaInit = (async () => {
    const mod = await import("/team-race/arena-physics.js?v=81");
    const canvas = document.getElementById("raceArenaCanvas");
    if (!canvas) return null;
    raceArena = new mod.TeamRaceArena(canvas, {
      onEliminate: (entityId) => {
        if (!roomId) return;
        fetch(
          `${SERVER_ORIGIN}/api/rooms/${encodeURIComponent(roomId)}/race/eliminate`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ entityId }),
          }
        ).catch(() => {});
      },
    });
    raceArena.start();
    window.addEventListener("resize", () => raceArena?.layout());
    return raceArena;
  })();
  return raceArenaInit;
}

function onRaceSpawn(entity) {
  if (!entity || overlayGameMode !== "team-race") return;
  const ul = raceEls.feed();
  if (ul) {
    const li = document.createElement("li");
    li.className = "race-spawn-row race-spawn-row--enter";
    li.innerHTML = `${teamFlagImg(teamFlagUrl(entity.teamCode, entity.flagUrl), "md", entity.teamName || entity.teamCode)}<span class="race-spawn-user">${escapeHtml(formatUsername(entity.displayName))}</span><span class="race-spawn-team">${escapeHtml(entity.teamName || entity.teamCode)}</span>`;
    ul.prepend(li);
    while (ul.children.length > 8) ul.lastElementChild?.remove();
  }
  ensureRaceArena().then((a) => a?.spawn(entity));
  if (!MOTION_OFF) spawnCelebration("correct");
}

applyOverlayGameMode(urlGameMode);

function applyLayoutConfig(cfg) {
  if (!cfg || layout !== "vertical") return;
  const q = cfg.question;
  const a = cfg.answer;
  const f = cfg.feed;
  const c = cfg.counter;
  const qm = cfg.questionMeta;
  const g = cfg.feedGrid;
  const live = cfg.live;
  if (live) {
    if (live.top != null) layoutEl.style.setProperty("--live-top", `${live.top}%`);
    if (live.left != null) layoutEl.style.setProperty("--live-left", `${live.left}%`);
  }
  if (q) {
    layoutEl.style.setProperty("--q-left", `${q.left}%`);
    layoutEl.style.setProperty("--q-top", `${q.top}%`);
    layoutEl.style.setProperty("--q-width", `${q.width}%`);
    layoutEl.style.setProperty("--q-height", `${q.height}%`);
  }
  if (a) {
    layoutEl.style.setProperty("--a-left", `${a.left}%`);
    layoutEl.style.setProperty("--a-top", `${a.top}%`);
    layoutEl.style.setProperty("--a-width", `${a.width}%`);
    layoutEl.style.setProperty("--a-height", `${a.height}%`);
  }
  if (f) {
    layoutEl.style.setProperty("--f-left", `${f.left}%`);
    layoutEl.style.setProperty("--f-top", `${f.top}%`);
    layoutEl.style.setProperty("--f-width", `${f.width}%`);
    layoutEl.style.setProperty("--f-height", `${f.height}%`);
    if (f.padTop != null) layoutEl.style.setProperty("--f-pad-top", `${f.padTop}%`);
    if (f.padX != null) {
      layoutEl.style.setProperty("--feed-pad-left", `${f.padLeft ?? f.padX}%`);
      layoutEl.style.setProperty("--feed-pad-right", `${f.padRight ?? f.padX}%`);
    }
    if (f.padLeft != null) layoutEl.style.setProperty("--feed-pad-left", `${f.padLeft}%`);
    if (f.padRight != null) layoutEl.style.setProperty("--feed-pad-right", `${f.padRight}%`);
  }
  if (c) {
    layoutEl.style.setProperty("--c-top", `${c.top}%`);
    layoutEl.style.setProperty("--c-right", `${c.right}%`);
  }
  if (qm) {
    layoutEl.style.setProperty("--qm-left", `${qm.left}%`);
    layoutEl.style.setProperty("--qm-top", `${qm.top}%`);
    layoutEl.style.setProperty("--qm-width", `${qm.width}%`);
    layoutEl.style.setProperty("--qm-height", `${qm.height}%`);
  } else if (q) {
    layoutEl.style.setProperty("--qm-left", `${q.left}%`);
    layoutEl.style.setProperty("--qm-top", `${q.top}%`);
    layoutEl.style.setProperty("--qm-width", `${q.width}%`);
    layoutEl.style.setProperty("--qm-height", `4.5%`);
  }
  if (g) {
    layoutEl.style.setProperty("--grid-avatar", `${g.avatar}%`);
    layoutEl.style.setProperty("--grid-points", `${g.points ?? 15.5}%`);
    layoutEl.style.setProperty("--grid-check", `${g.check ?? 6.5}%`);
    layoutEl.style.setProperty("--grid-gap", `${g.gap ?? 1.1}%`);
    if (g.pointsInset != null) {
      layoutEl.style.setProperty("--points-inset", `${g.pointsInset}%`);
    }
    if (g.checkInset != null) {
      layoutEl.style.setProperty("--check-inset", `${g.checkInset}%`);
    }
  }
  if (cfg.feedSlots) FEED_SLOTS = cfg.feedSlots;
  if (window.BulmacaLayoutScales) {
    BulmacaLayoutScales.apply(layoutEl, cfg.scales);
  }
}

function mergeLayoutConfig(base, patch) {
  if (!patch) return base;
  const out = { ...(base || {}) };
  for (const key of Object.keys(patch)) {
    const v = patch[key];
    out[key] =
      v && typeof v === "object" && !Array.isArray(v) && typeof out[key] === "object"
        ? { ...out[key], ...v }
        : v;
  }
  return out;
}

async function loadLayout() {
  let cfg = null;
  const useLocal =
    params.get("layoutSource") === "local" || params.get("cal") === "1";
  const storageKey = roomId
    ? `${LAYOUT_STORAGE_KEY}_${roomId}`
    : LAYOUT_STORAGE_KEY;

  try {
    const bust = params.get("ov") || String(Date.now());
    if (roomId) {
      const roomRes = await fetch(
        `${SERVER_ORIGIN}/api/rooms/${encodeURIComponent(roomId)}/layout/vertical?v=${bust}`,
        { cache: "no-store" }
      );
      if (roomRes.ok) cfg = await roomRes.json();
    }
    if (!cfg) {
      const res = await fetch(
        `${SERVER_ORIGIN}/overlay/layout.vertical.json?v=${bust}`,
        { cache: "no-store" }
      );
      if (res.ok) cfg = await res.json();
    }
  } catch {
    /* varsayılan CSS */
  }

  if (useLocal) {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) cfg = mergeLayoutConfig(cfg, JSON.parse(saved));
    } catch {
      /* yoksay */
    }
  }

  if (cfg) applyLayoutConfig(cfg);
  scheduleQuestionTextFit();
}

function fitOverlayToViewport() {
  const el = layoutEl;
  if (!el) return;

  const vw = window.innerWidth || FRAME_SIZE.w;
  const vh = window.innerHeight || FRAME_SIZE.h;
  const fw = FRAME_SIZE.w;
  const fh = FRAME_SIZE.h;
  const scaleMode = params.get("scale") || "cover";

  el.style.width = `${fw}px`;
  el.style.height = `${fh}px`;

  const nativeOk =
    scaleMode === "native" ||
    (Math.abs(vw - fw) <= 4 && Math.abs(vh - fh) <= 4);

  if (nativeOk) {
    document.documentElement.classList.add("overlay-native");
    document.body.classList.add("overlay-native");
    el.style.left = "0";
    el.style.top = "0";
    el.style.transform = "none";
    document.documentElement.style.width = `${fw}px`;
    document.documentElement.style.height = `${fh}px`;
    document.body.style.width = `${fw}px`;
    document.body.style.height = `${fh}px`;
    return;
  }

  document.documentElement.classList.remove("overlay-native");
  document.body.classList.remove("overlay-native");
  document.documentElement.style.width = "";
  document.documentElement.style.height = "";
  document.body.style.width = `${vw}px`;
  document.body.style.height = `${vh}px`;

  const sx = vw / fw;
  const sy = vh / fh;
  const scale =
    scaleMode === "contain" ? Math.min(sx, sy) : Math.max(sx, sy);

  el.style.left = "50%";
  el.style.top = "50%";
  el.style.transform = `translate(-50%, -50%) scale(${scale})`;
  el.style.transformOrigin = "center center";
}

function showOverlayError(message) {
  const box = document.getElementById("overlayError");
  if (!box) return;
  box.textContent = message;
  box.classList.remove("hidden");
}

function hideOverlayError() {
  document.getElementById("overlayError")?.classList.add("hidden");
}

function getQuestionTextScale() {
  const v = getComputedStyle(layoutEl).getPropertyValue("--scale-question").trim();
  const n = parseFloat(v);
  return Number.isFinite(n) && n > 0 ? n : 1;
}

/** Uzun sorularda yazı boyutunu kutuya ve alt boşluğa göre küçültür */
function fitActiveQuestionText() {
  const card = document.getElementById("questionCard");
  const body = card?.querySelector(".question-body");
  const hintEl = document.getElementById("hintText");
  const textEl = document.getElementById("questionText");
  if (!body || !textEl || !card || card.classList.contains("hidden")) return;

  const text = (textEl.textContent || "").trim();
  if (!text) {
    textEl.style.fontSize = "";
    return;
  }

  const scale = getQuestionTextScale();
  const minPx = Math.max(12, Math.round(13 * scale));
  const maxPx = Math.round(30 * scale);
  const width = Math.max(72, body.clientWidth - 10);
  const hintH =
    hintEl && (hintEl.textContent || "").trim() ? hintEl.offsetHeight + 8 : 0;

  const slot = card.closest(".slot-puzzle");
  const slotRect = slot?.getBoundingClientRect();
  const frameRect = layoutEl.getBoundingClientRect();
  const extraDown =
    slotRect && frameRect
      ? Math.max(0, frameRect.bottom - slotRect.bottom - 20)
      : 0;
  const maxH = Math.max(56, body.clientHeight - hintH + extraDown * 0.9);

  textEl.style.maxWidth = `${width}px`;
  textEl.style.whiteSpace = "normal";
  textEl.style.wordBreak = "break-word";
  textEl.style.overflowWrap = "anywhere";

  let lo = minPx;
  let hi = maxPx;
  let best = minPx;

  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2);
    textEl.style.fontSize = `${mid}px`;
    const okW = textEl.scrollWidth <= width + 2;
    const okH = textEl.scrollHeight <= maxH + 2;
    if (okW && okH) {
      best = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }

  textEl.style.fontSize = `${best}px`;
}

function scheduleQuestionTextFit() {
  requestAnimationFrame(() => {
    fitActiveQuestionText();
    requestAnimationFrame(fitActiveQuestionText);
  });
}

function scheduleFit() {
  fitOverlayToViewport();
  fitActiveQuestionText();
  requestAnimationFrame(() => {
    fitOverlayToViewport();
    fitActiveQuestionText();
  });
}

loadLayout().then(() => {
  scheduleFit();
  window.addEventListener("resize", scheduleFit);
  setTimeout(scheduleFit, 150);
  setTimeout(scheduleFit, 600);
});

if (!roomId) {
  showOverlayError("OBS URL'de room parametresi eksik. Admin panelden kopyalayın.");
} else {

const els = {
  idle: document.getElementById("idle"),
  questionCard: document.getElementById("questionCard"),
  winnerCard: document.getElementById("winnerCard"),
  endedCard: document.getElementById("endedCard"),
  questionText: document.getElementById("questionText"),
  questionPhotoWrap: document.getElementById("questionPhotoWrap"),
  questionPhoto: document.getElementById("questionPhoto"),
  hintText: document.getElementById("hintText"),
  winnerName: document.getElementById("winnerName"),
  winnerHint: document.getElementById("winnerHint"),
  winnerAvatar: document.getElementById("winnerAvatar"),
  winnerAnswer: document.getElementById("winnerAnswer"),
  counter: document.getElementById("counter"),
  questionMeta: document.getElementById("questionMeta"),
  feedList: document.getElementById("feedList"),
};
function hideQuestionLayers() {
  els.idle.classList.add("hidden");
  els.questionCard.classList.add("hidden");
  els.winnerCard.classList.add("hidden");
  els.endedCard.classList.add("hidden");
}

function initial(name) {
  const t = String(name || "?").trim();
  return (t[0] || "?").toLocaleUpperCase("tr-TR");
}

function formatUsername(name) {
  const n = String(name || "Anonim").trim();
  return n.startsWith("@") ? n : `@${n}`;
}

function formatPoints(n) {
  const v = Math.max(0, Math.round(Number(n) || 0));
  if (v <= 0) return "—";
  return `${v.toLocaleString("tr-TR")} Puan`;
}

function avatarHtml(item) {
  if (item?.avatarUrl) {
    return `<img src="${escapeHtml(item.avatarUrl)}" alt="" loading="lazy" />`;
  }
  return escapeHtml(initial(item?.displayName));
}

function feedSignature(feed = []) {
  return feed
    .slice(0, FEED_SLOTS)
    .map((item) =>
      item ? `${item.displayName}:${Math.round(Number(item.points) || 0)}` : ""
    )
    .join("|");
}

function renderFeed(feed = [], animate = true) {
  const items = feed.slice(0, FEED_SLOTS);
  const signature = feedSignature(items);
  const feedChanged = animate && signature !== prevFeedSignature && items.some(Boolean);
  prevFeedSignature = signature;

  els.feedList.innerHTML = "";

  for (let i = 0; i < FEED_SLOTS; i++) {
    const item = items[i];
    const li = document.createElement("li");
    li.className = "feed-row";
    if (!item) {
      li.classList.add("feed-row--empty");
      li.innerHTML =
        '<span class="feed-avatar"></span><span class="feed-name"></span><span class="feed-points"></span><span class="feed-check"></span>';
    } else {
      if (item.rank === 1) li.classList.add("rank-1");
      else if (item.rank === 2) li.classList.add("rank-2");
      else if (item.rank === 3) li.classList.add("rank-3");
      if (feedChanged) {
        li.classList.add("feed-row--enter");
        li.style.animationDelay = `${i * 0.07}s`;
      }
      const pts = Math.max(0, Math.round(Number(item.points) || 0));
      li.innerHTML = `
        <span class="feed-avatar">${avatarHtml(item)}</span>
        <span class="feed-name">${escapeHtml(formatUsername(item.displayName))}</span>
        <span class="feed-points">${escapeHtml(formatPoints(pts))}</span>
        <span class="feed-check">✓</span>`;
    }
    els.feedList.appendChild(li);
  }
}

function pulseQuestionCard() {
  if (MOTION_OFF || !els.questionCard) return;
  els.questionCard.classList.remove("question-pulse");
  void els.questionCard.offsetWidth;
  els.questionCard.classList.add("question-pulse");
}

function truncateText(text, max = 28) {
  const t = String(text || "").trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function triggerFrameFlash(correct) {
  if (MOTION_OFF) return;
  layoutEl.classList.remove("flash-correct", "flash-wrong");
  void layoutEl.offsetWidth;
  layoutEl.classList.add(correct ? "flash-correct" : "flash-wrong");
  window.setTimeout(() => {
    layoutEl.classList.remove("flash-correct", "flash-wrong");
  }, 700);
}

function spawnCelebration(kind = "correct") {
  if (MOTION_OFF) return;
  const host = document.getElementById("fxCelebration");
  if (!host) return;
  const count = kind === "winner" ? 70 : kind === "correct" ? 40 : 18;
  const colors =
    kind === "wrong"
      ? ["#ff6b6b", "#ff9f43", "#ff5252"]
      : ["#ffd54a", "#3dd68c", "#7c5cff", "#ff6b9f", "#7adfff", "#fff"];
  for (let i = 0; i < count; i++) {
    const el = document.createElement("span");
    el.className = "fx-confetti";
    const left = 8 + Math.random() * 84;
    const top = kind === "winner" ? 18 + Math.random() * 35 : 28 + Math.random() * 40;
    el.style.left = `${left}%`;
    el.style.top = `${top}%`;
    el.style.background = colors[Math.floor(Math.random() * colors.length)];
    el.style.setProperty("--dx", `${(Math.random() - 0.5) * 280}px`);
    el.style.setProperty("--dy", `${160 + Math.random() * 320}px`);
    el.style.setProperty("--rot", `${Math.random() * 720 - 360}deg`);
    el.style.setProperty("--dur", `${1.2 + Math.random() * 1.4}s`);
    el.style.width = `${6 + Math.random() * 8}px`;
    el.style.height = `${6 + Math.random() * 10}px`;
    host.appendChild(el);
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }
}

function playWinnerCelebrate() {
  if (MOTION_OFF) return;
  spawnCelebration("winner");
  els.winnerCard?.classList.remove("winner-celebrate");
  void els.winnerCard?.offsetWidth;
  els.winnerCard?.classList.add("winner-celebrate");
}

/** Yayında metin göstermez; yalnızca doğru/yanlış için kısa görsel efekt (panelde istatistikler var). */
function renderInteraction(interaction, gameState) {
  if (gameState !== "active" && gameState !== "winner") return;

  const last = interaction?.lastAnswer;
  const at = last?.at || "";
  if (!last?.displayName || !at || at === prevLastAnswerAt) return;

  prevLastAnswerAt = at;
  if (MOTION_OFF) return;
  triggerFrameFlash(!!last.correct);
  spawnCelebration(last.correct ? "correct" : "wrong");
}

function renderWinnerDetails(winner) {
  if (!winner) return;
  if (els.winnerName) els.winnerName.textContent = formatUsername(winner.displayName);
  if (els.winnerAnswer) {
    const ans = truncateText(winner.answer, 36);
    els.winnerAnswer.textContent = ans ? `Cevap: ${ans}` : "";
  }
  if (els.winnerAvatar) {
    els.winnerAvatar.classList.remove("winner-avatar--initial");
    if (winner.avatarUrl) {
      els.winnerAvatar.innerHTML = `<img src="${escapeHtml(winner.avatarUrl)}" alt="" loading="lazy" />`;
    } else {
      els.winnerAvatar.innerHTML = "";
      els.winnerAvatar.textContent = initial(winner.displayName);
      els.winnerAvatar.classList.add("winner-avatar--initial");
    }
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatQuestionCounter(state) {
  const total = Number(state.totalQuestions) || 0;
  if (!total) return "Soru yok";

  const qPts = Math.round(Number(state.question?.points) || 0);
  const ptsBit = qPts > 0 ? ` · ${qPts}p` : "";

  if (state.state === "idle") {
    return `0 / ${total} · hazır`;
  }
  if (state.state === "ended") {
    return `${total} / ${total} · bitti`;
  }

  const idx = Math.max(1, (state.currentIndex ?? -1) + 1);
  return `Soru ${idx} / ${total}${ptsBit}`;
}

function render(state) {
  const copy = overlayCopy(state);
  const counterText = formatQuestionCounter(state);
  els.counter.textContent = counterText;
  if (els.questionMeta) {
    els.questionMeta.textContent =
      state.state === "active" ? counterText : "";
  }

  layoutEl.dataset.state = state.state || "idle";

  renderFeed(state.feed || []);
  renderInteraction(state.interaction, state.state);
  hideQuestionLayers();

  const enteredWinner = state.state === "winner" && prevGameState !== "winner";
  prevGameState = state.state || "idle";

  switch (state.state) {
    case "idle":
      els.idle.classList.remove("hidden");
      document.getElementById("idleTitle").textContent = copy.idleTitle;
      document.getElementById("idleSub").innerHTML = copy.idleSub.includes("<strong>")
        ? copy.idleSub
        : copy.idleSub.replace("Başlat", "<strong>Başlat</strong>");
      break;
    case "active":
      els.questionCard.classList.remove("hidden");
      if (state.question) {
        const hint = (state.question.hint || "").trim();
        const q = state.question.question || "";
        const qKey = state.question.id || `${hint}|${q}`;
        if (qKey !== prevQuestionKey) {
          prevQuestionKey = qKey;
          prevLastAnswerAt = "";
          pulseQuestionCard();
        }
        els.hintText.textContent = hint
          ? hint.toUpperCase()
          : celebrityQuizActive
            ? "ÜNLÜLERİN YAŞINI TAHMİN ET"
            : "";
        els.questionText.textContent = celebrityQuizActive
          ? q.replace(/\s*kaç\s+yaşında\??\s*$/i, "").trim() || q
          : q;
        const imgUrl = (state.question.imageUrl || "").trim();
        if (imgUrl && els.questionPhoto && els.questionPhotoWrap) {
          els.questionPhotoWrap.classList.remove("hidden");
          els.questionPhoto.src = imgUrl;
          els.questionPhoto.alt = q;
          els.questionPhoto.onload = () => scheduleQuestionTextFit();
          els.questionPhoto.onerror = () => {
            els.questionPhotoWrap.classList.add("hidden");
            scheduleQuestionTextFit();
          };
        } else if (els.questionPhotoWrap) {
          els.questionPhotoWrap.classList.add("hidden");
        }
        scheduleQuestionTextFit();
      }
      break;
    case "winner":
      els.winnerCard.classList.remove("hidden");
      if (state.winner) {
        els.winnerHint.textContent = copy.winnerHint;
        renderWinnerDetails(state.winner);
        if (enteredWinner) playWinnerCelebrate();
      }
      break;
    case "ended":
      els.endedCard.classList.remove("hidden");
      document.getElementById("endedTitle").textContent = copy.endedTitle;
      document.getElementById("endedSub").textContent = copy.endedSub;
      break;
    default:
      els.idle.classList.remove("hidden");
  }
}

const socket = io(SERVER_ORIGIN, {
  path: "/socket.io",
  query: { room: roomId },
  transports: ["websocket", "polling"],
});

socket.on("game:state", (state) => {
  hideOverlayError();
  if (
    state?.question?.imageUrl &&
    /kaç\s+yaşında/i.test(state.question?.question || "")
  ) {
    applyCelebrityQuizUi(true);
  }
  if (overlayGameMode === "puzzle" || celebrityAgeOverlayMode()) {
    if (celebrityAgeOverlayMode() && photoBattleRoot) {
      photoBattleRoot.classList.add("hidden");
      photoBattleRoot.setAttribute("aria-hidden", "true");
    }
    render(state);
  }
});

socket.on("photo-battle:state", (state) => {
  hideOverlayError();
  if (celebrityAgeOverlayMode()) return;
  if (overlayGameMode === "photo-battle") renderPhotoBattle(state);
});

socket.on("race:state", (race) => {
  hideOverlayError();
  renderRace(race);
});

socket.on("race:spawn", (entity) => {
  lastRaceActivitySig = "";
  onRaceSpawn(entity);
});

socket.on("config", (cfg) => {
  if (cfg?.gameMode) applyOverlayGameMode(cfg.gameMode);
});

socket.on("error", (data) => {
  showOverlayError(data?.message || "Bağlantı hatası");
});

socket.on("layout:updated", () => {
  loadLayout().then(() => {
    scheduleFit();
    if (window.BulmacaParticles?.refresh) window.BulmacaParticles.refresh();
  });
});

socket.on("connect_error", () => {
  showOverlayError("Sunucuya bağlanılamadı. npm start çalışıyor mu?");
});

fetch(`${SERVER_ORIGIN}/api/rooms/${encodeURIComponent(roomId)}/status`)
  .then((r) => {
    if (!r.ok) throw new Error("Oda bulunamadı — önce admin panelden oda oluşturun.");
    return r.json();
  })
  .then((d) => {
    hideOverlayError();
    if (d.config?.gameMode) applyOverlayGameMode(d.config.gameMode);
    applyCelebrityQuizUi(
      Boolean(d.celebrityQuiz || d.celebrityInPhotoMode)
    );
    if (
      celebrityQuizActive &&
      (overlayGameMode === "photo-battle" || d.celebrityInPhotoMode)
    ) {
      redirectToCelebrityOverlay();
      return;
    }
    if (overlayGameMode === "team-race" && d.race) renderRace(d.race);
    else if (overlayGameMode === "photo-battle" && d.photoBattle) {
      renderPhotoBattle(d.photoBattle);
    } else if (overlayGameMode === "puzzle" && d.game) render(d.game);
  })
  .catch((err) => showOverlayError(err.message || "Durum alınamadı"));
}
