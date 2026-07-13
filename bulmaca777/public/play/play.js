import { TeamRaceArena } from "/team-race/arena-physics.js?v=81";
import {
  PLAY_RACE_PRESETS,
  findMatchingRacePresetKey,
  presetSettingsToServerBody,
} from "/play/play-race-presets.js?v=2";
import { applyArenaCtasToDom } from "/team-race/youtube-ctas-ui.js?v=1";
import {
  initPlayCalibration,
  setCalibrationOrientation,
  loadPlayArenaLayout,
  applyPlayArenaLayout,
  shouldSkipAutoHudPosition,
} from "/play/play-calibration.js?v=11";
import { PLAY_ARENA_LAYOUT_DEFAULT } from "/play/arena-layout-default.js";
import { ADMIN_RACE_MOUNT_HTML } from "/team-race/admin-race-template.js?v=26";
import {
  teamFlagImg,
  teamFlagUrl,
  winReasonLabel,
  formatWinnerLines,
  sortedRoundWinners,
} from "/team-race/team-ui.js?v=1";
import { FALLBACK_TEAMS } from "/team-race/teams-data.js";
import {
  generateSimAuthor,
  generateSimChatText,
  shouldRunClientAudienceSim,
  pickClientSimIntervalMs,
} from "/team-race/audience-sim.js?v=1";
import { createArenaInfoTicker } from "/team-race/arena-info-ticker.js?v=4";
import {
  initArenaCmdBand,
  setArenaCmdBandVisible,
  syncArenaCmdBand,
} from "/team-race/arena-cmd-band.js?v=1";
import {
  applyCalSlotLabels,
  clearLayoutOverviewDemo,
  fillLayoutOverviewDemo,
} from "/play/play-layout-overview.js?v=1";

const SESSION_KEY = "bulmaca777-play-session";
const urlParams = new URLSearchParams(location.search);
let activeRoomId = urlParams.get("room");
let isRoomMode = Boolean(activeRoomId);
const layoutParam = urlParams.get("layout");
let isAdminEmbed = false;
let hubRoot = null;
let hubResizeObserver = null;
const embedMode = urlParams.get("embed") === "1";

const API = () => (isRoomMode ? null : "/api/playground/team-race");

let sessionId = null;
let teams = [];
let champions = {};
let roundHistory = [];
let autoSimOn = false;
let autoSimTimer = null;
let clientAudienceSimTimer = null;
let lastRealChatAt = 0;
let simProfileSeq = 0;
const recentSimAuthors = [];
let arena = null;
let arenaInfoTicker = null;
let lastArenaActivityId = "";
let chaosOn = false;
const eliminatedRecent = [];
let elimFlashTimer = null;
let elimFlashSeq = 0;
let phaseTickTimer = null;
let lastSnap = null;
let gatherChaosRequested = false;
let socket = null;
let arenaLayout =
  layoutParam === "horizontal" || layoutParam === "vertical" ? layoutParam : "vertical";
let autoRoundTimer = null;
let autoPlayEnabled = true;
let lastArenaRoundPhase = null;
let lastShockWaveAt = null;
/** Manuel kaos tıklanınca snapshot gathering'e geri çekmesin (ms) */
let manualChaosUntil = 0;
let scenePreviewMode = "off";
const livePickStats = new Map();
const LIVE_PICK_COOLDOWN_MS = 60_000;
let raceAdvancedSettings = {
  chaosSpawnPolicy: "locked",
  chaosSpawnOpenChancePct: 22,
  chaosSpawnWindowMs: 8000,
  chaosSpawnWindowCooldownMs: 14000,
};

const SIM_NAMES = [
  "AhmetYilmaz",
  "Zeynep_42",
  "CanKral",
  "ElifLive",
  "MuratGS",
  "SelinFB",
  "EmreBJK",
  "Deniz1907",
  "Burak61",
  "AyseTrabzon",
  "Kaan1905",
  "Merve_izleyici",
  "YusufCanli",
  "EceFener",
  "OzanKartal",
  "SudeAslan",
  "BarisRize",
  "GamzeGoztepe",
  "Tolga1903",
  "IremSam",
  "HakanGSli",
  "CerenFbFan",
  "ArdaChamp",
  "NazliLive",
  "Serkan61",
  "Pelin1907",
  "UmutBJK",
  "DilaraGS",
  "KemalFener",
  "MelisTrabzon",
];

const SIM_NAME_PREFIXES = [
  "Ali",
  "Ayse",
  "Can",
  "Deniz",
  "Ece",
  "Emir",
  "Mina",
  "Ozan",
  "Sena",
  "Yigit",
  "Arda",
  "Defne",
  "Kerem",
  "Nehir",
  "Bora",
];

/** Gerçek sohbette görülen takım yazıları */
const SIM_TEAM_MSGS = [
  "gs", "GS", "g s", "galatasaray", "GALATASARAY", "cimbom", "aslan",
  "fener", "FENER", "fenerbahce", "Fenerbahçe", "fb", "FB", "kanarya",
  "bjk", "BJK", "besiktas", "beşiktaş", "kartal",
  "trabzon", "ts", "TS", "fırtına",
  "goztepe", "göztepe", "goz", "samsun", "sam",
  "alanya", "antalya", "konya", "kayseri", "rizespor",
  "gs 💛❤️", "fener 💙💛", "bjk 🦅", "gs geliyor", "fener şampiyon",
];

const SIM_NOISE_MSGS = [
  "gg", "harika yayın", "selam", "kaç puan", "🔥🔥🔥", "lol",
  "67", "ban yok mu", "hadi", "wow", "asdf", "test",
  "hangi takım", "ben de gs", "1234", "???",
];

function $(id) {
  if (hubRoot) {
    const scoped = hubRoot.querySelector(`#${id}`);
    if (scoped) return scoped;
  }
  return document.getElementById(id);
}

const els = {};

function rebindEls() {
  Object.assign(els, {
    main: $("playMain"),
    loading: $("playLoading"),
    blocked: $("playBlocked"),
    phase: $("phaseLabel"),
    round: $("roundLabel"),
    hudSub: $("hudSub"),
    winnerCard: $("winnerCard"),
    winnerFlag: $("winnerFlag"),
    winnerName: $("winnerName"),
    spawnFeed: $("spawnFeed"),
    leaderboard: $("leaderboard"),
    championsList: $("championsList"),
    chatFeedback: $("chatFeedback"),
    liveChat: $("liveChatFeed"),
    teamGrid: $("teamQuickGrid"),
    statArena: $("statArena"),
    statSpawns: $("statSpawns"),
    statUnmatched: $("statUnmatched"),
    arenaBadge: $("arenaBadge"),
    elimFlash: $("elimFlash"),
    eliminatedFeed: $("eliminatedFeed"),
    roundHistoryList: $("roundHistoryList"),
    winnerMeta: $("winnerMeta"),
    phaseBanner: $("phaseBanner"),
    phaseBannerTitle: $("phaseBannerTitle"),
    phaseBannerTimer: $("phaseBannerTimer"),
    poolFill: $("poolFill"),
    arenaTopViewers: $("arenaTopViewers"),
    arenaRoundWinners: $("arenaRoundWinners"),
    activityStrip: $("activityStrip"),
  });
}

rebindEls();

const PHASE_LABELS = {
  gathering: "Toplanma",
  chaos: "Kaos",
};

function formatMs(ms) {
  const sec = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function getRaceSettingsFromUI() {
  const gatherSec = Number($("gatherDurationRange")?.value) || 300;
  const cooldownSec = Number($("cooldownRange")?.value) || 5;
  return {
    gatherDurationSec: gatherSec,
    gatherDurationMs: gatherSec * 1000,
    chaosMinEntities: Number($("chaosMinRange")?.value) || 8,
    chaosTrigger: $("chaosTriggerSelect")?.value || "time_or_count",
    minParticipants: Number($("minParticipantsRange")?.value) || 3,
    minTeams: Number($("minTeamsRange")?.value) || 2,
    minTotalSpawns: Number($("minSpawnsRange")?.value) || 3,
    spawnCooldownMs: cooldownSec * 1000,
    chaosSpawnCooldownMs: cooldownSec * 1000,
    autopilot: $("raceAutopilotOn")?.checked !== false,
    autoStartOnConnect: $("raceAutoStartOn")?.checked !== false,
    requireYoutubeForAutostart: $("raceRequireYt")?.checked === true,
    autoNextRoundMs: (Number($("autoNextRoundSec")?.value) || 12) * 1000,
    autoRetryRoundMs: (Number($("autoRetryRoundSec")?.value) || 45) * 1000,
    chaosEliminationGraceMs:
      (Number($("chaosGraceSec")?.value) || 5) * 1000,
    chaosMinDurationMs: (Number($("chaosMinSec")?.value) || 12) * 1000,
    maxRounds: Number($("raceMaxRounds")?.value) || 8,
    audienceSimEnabled: $("raceAudienceSimOn")?.checked !== false,
    ...raceAdvancedSettings,
  };
}

function getSeriesFromSnap(snap) {
  const maxRounds = snap?.series?.maxRounds ?? snap?.settings?.maxRounds ?? 8;
  const completedRounds =
    snap?.series?.completedRounds ?? roundHistory.length ?? 0;
  return {
    maxRounds,
    completedRounds,
    remainingRounds: Math.max(0, maxRounds - completedRounds),
    seriesComplete:
      snap?.series?.seriesComplete ?? completedRounds >= maxRounds,
  };
}

function formatRoundLabel(snap) {
  const series = getSeriesFromSnap(snap);
  const { maxRounds, completedRounds, seriesComplete } = series;
  if (snap?.phase === "running" && snap.round > 0) {
    const idx = Math.min(completedRounds + 1, maxRounds);
    return `Tur ${idx}/${maxRounds}`;
  }
  if (seriesComplete) {
    return `Seri bitti (${completedRounds}/${maxRounds})`;
  }
  if (completedRounds > 0) {
    return `Hazır (${completedRounds}/${maxRounds})`;
  }
  return `${maxRounds} tur`;
}

async function pushSettingsToServer({ quiet = false, body: bodyOverride } = {}) {
  if (!isRoomMode && !sessionId) return;
  try {
    const body = bodyOverride || getRaceSettingsFromUI();
    await api("/settings", {
      method: "PATCH",
      body: isRoomMode ? body : { sessionId, ...body },
    });
    lastFilledSettingsSig = "";
  } catch (e) {
    if (!quiet) throw e;
  }
}

function overlayUrl(layout) {
  const key = layout === "horizontal" ? "horizontal" : "vertical";
  const p = new URLSearchParams({
    room: activeRoomId,
    layout: key,
    mode: "team-race",
    scale: "contain",
  });
  return `${location.origin}/overlay?${p}`;
}

function syncArenaHudPosition() {
  if (shouldSkipAutoHudPosition()) return;
  const arenaEl = $("arena");
  const bounds = arena?._bounds;
  if (!arenaEl || !bounds) return;
  const { cy, r } = bounds;
  const ringTop = cy - r;
  const gap = Math.max(10, Math.round(r * 0.05));
  const hud = $("phaseBanner");
  const hudH =
    hud && !hud.classList.contains("hidden") ? hud.offsetHeight : 0;
  const topPx = Math.max(6, Math.round(ringTop - gap - (hudH || 96)));
  arenaEl.style.setProperty("--arena-hud-top", `${topPx}px`);
}

function applyArenaLayout() {
  const stage = $("playStage");
  if (stage) stage.dataset.arenaLayout = arenaLayout;
  document.body.dataset.arenaLayout = arenaLayout;
  requestAnimationFrame(() => {
    arena?.layout();
    syncArenaHudPosition();
  });
}

function setArenaLayout(layout) {
  arenaLayout = layout === "horizontal" ? "horizontal" : "vertical";
  document.querySelectorAll(".play-layout-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.arenaLayout === arenaLayout);
  });
  setCalibrationOrientation(arenaLayout);
  applyArenaLayout();
  const ov = $("linkOverlay");
  if (ov && activeRoomId) {
    ov.href = overlayUrl(arenaLayout);
    ov.classList.remove("hidden");
  }
}

function wirePlayLayoutUi() {
  document.querySelectorAll(".play-layout-btn").forEach((btn) => {
    if (btn.dataset.wired) return;
    btn.dataset.wired = "1";
    btn.addEventListener("click", () => setArenaLayout(btn.dataset.arenaLayout));
  });
  $("btnSaveRaceSettings")?.addEventListener("click", async () => {
    try {
      await pushSettingsToServer({ quiet: false });
      setFeedback("Tur ayarları kaydedildi (veritabanı).", "ok");
    } catch (e) {
      setFeedback(e.message || "Kaydedilemedi", "bad");
    }
  });
  const stage = $("playStage");
  if (stage && !stage.dataset.layoutRo) {
    stage.dataset.layoutRo = "1";
    new ResizeObserver(() => {
      arena?.layout();
      syncArenaHudPosition();
    }).observe(stage);
  }
  setArenaLayout(arenaLayout);
}

function applyArenaFromSnap(snap) {
  if (!arena || !snap) return;
  let rp = snap.roundPhase || (snap.chaos ? "chaos" : "gathering");
  const graceMs = snap.settings?.chaosEliminationGraceMs ?? 5000;
  arena.setEliminationGraceMs(graceMs);
  const manualChaos = Date.now() < manualChaosUntil;
  if (manualChaos && rp === "gathering" && arena.bodies.size > 0) {
    rp = "chaos";
  }
  if (rp === "chaos") {
    const entering = lastArenaRoundPhase !== "chaos" || arena.roundPhase !== "chaos";
    arena.setRoundPhase(rp);
    if (entering) arena.kickstartChaos();
    else if (manualChaos) arena.forceEnterChaos?.();
  } else if (!manualChaos) {
    arena.setRoundPhase(rp);
  }
  lastArenaRoundPhase = manualChaos ? "chaos" : rp;
  const chaosEffective = rp === "chaos" || Boolean(snap.chaos);
  arena.setChaos(chaosEffective);
  chaosOn = chaosEffective;
  const btn = $("btnChaos");
  if (btn) {
    btn.classList.toggle("is-on", chaosOn);
    btn.textContent = chaosOn ? "Kaos aktif" : "Kaos";
  }
  const shockAt = snap.shockWaveAt || null;
  if (shockAt && shockAt !== lastShockWaveAt && chaosEffective) {
    arena.triggerShockWave?.();
    lastShockWaveAt = shockAt;
  } else if (!shockAt && rp !== "chaos") {
    lastShockWaveAt = null;
  }
}

function updateEngagementChip(el, have, need, done) {
  if (!el) return;
  const strong = el.querySelector("strong");
  if (strong) strong.textContent = `${have}/${need}`;
  el.classList.toggle("is-done", Boolean(done));
}

function chaosGraceRemainingMs(snap) {
  if (!snap || snap.roundPhase !== "chaos" || !snap.chaosStartedAt) return 0;
  const grace = snap.settings?.chaosEliminationGraceMs ?? 5000;
  const elapsed = Date.now() - new Date(snap.chaosStartedAt).getTime();
  return Math.max(0, grace - elapsed);
}

function getShockCountdownSec() {
  return arena?.getShockCountdownSec?.() ?? null;
}

/** Üst HUD alt yazısı — sabit kural metni (sık değişmesin) */
function getHudSubText(snap) {
  if (!snap || snap.phase !== "running") return "";
  const rp = snap.roundPhase;
  if (rp === "gathering") {
    if (snap.gatherBlockedReason) return snap.gatherBlockedReason;
    const ready = Boolean(snap.gatherRequirements?.met);
    const remain = snap.gatherRemainingMs ?? 0;
    const minRemain = snap.gatherMinRemainingMs ?? remain;
    if (remain <= 0 && minRemain <= 0 && ready) {
      return "Süre doldu — kaos başlıyor, çember dönüyor…";
    }
    if (ready && minRemain > 0) {
      return `Katılım tamam — kaos için ${Math.ceil(minRemain / 1000)} sn bekleniyor`;
    }
    if (ready) return "Katılım tamam — toplanma süresi bitince kaos";
    return "Hedefleri tamamlayın, sonra kaos başlar";
  }
  if (chaosGraceRemainingMs(snap) > 0) {
    return "Kaos başladı — toplar yerleşsin, elenme henüz kapalı";
  }
  return "Alttaki çıkıştan düşen elenir — son kalan takım kazanır";
}

/** Büyük sayaç satırı — süreler burada döner */
function getChaosTimerText(snap) {
  const gr = chaosGraceRemainingMs(snap);
  if (gr > 0) return `Elenme kapalı · ${formatMs(gr)}`;

  const shock = getShockCountdownSec();
  if (shock != null && shock <= 15) return `Şok dalgası · ${shock} sn`;

  if (snap.chaosSpawnWindowOpen) {
    const sec = Math.max(
      0,
      Math.ceil((Number(snap.chaosSpawnWindowRemainingMs) || 0) / 1000)
    );
    return `Spawn penceresi · ${sec} sn`;
  }

  return "Elenme açık";
}

function updatePhaseUI(snap) {
  if (!snap) return;
  lastSnap = snap;
  const running = snap.phase === "running";
  const rp = snap.roundPhase;
  const e = snap.engagement || {};
  const req = snap.gatherRequirements || {};
  const ready = Boolean(req.met);

  if (els.phase) {
    els.phase.classList.remove("is-running", "is-chaos");
    if (!running) {
      els.phase.textContent = "Beklemede";
    } else if (rp === "chaos") {
      els.phase.textContent = "Kaos";
      els.phase.classList.add("is-running", "is-chaos");
    } else {
      els.phase.textContent = "Toplanma";
      els.phase.classList.add("is-running");
    }
  }

  const arenaRoot = $("arena");
  if (arenaRoot) applyArenaCtasToDom(arenaRoot, snap.arenaCtas);
  if (els.phaseBanner) {
    els.phaseBanner.classList.toggle("hidden", !running);
    els.phaseBanner.classList.toggle("is-chaos", rp === "chaos");
    els.phaseBanner.classList.toggle("is-gathering", rp === "gathering");
    if (running) requestAnimationFrame(syncArenaHudPosition);
  }
  if (els.phaseBannerTitle) {
    els.phaseBannerTitle.textContent = rp === "chaos" ? "Kaos" : "Toplanma";
  }
  if (els.phaseBannerTimer && running) {
    els.phaseBannerTimer.textContent =
      rp === "gathering"
        ? formatMs(snap.gatherRemainingMs ?? 0)
        : getChaosTimerText(snap);
  }
  if (els.poolFill) {
    const pct = Math.round((snap.poolFillRatio ?? 0) * 100);
    els.poolFill.style.width = `${pct}%`;
  }

  updateEngagementChip(
    $("chipParticipants"),
    e.participants ?? 0,
    req.minParticipants ?? "?",
    (e.participants ?? 0) >= (req.minParticipants ?? 0)
  );
  updateEngagementChip(
    $("chipTeams"),
    e.teams ?? 0,
    req.minTeams ?? "?",
    (e.teams ?? 0) >= (req.minTeams ?? 0)
  );
  updateEngagementChip(
    $("chipSpawns"),
    e.spawns ?? 0,
    req.minTotalSpawns ?? "?",
    (e.spawns ?? 0) >= (req.minTotalSpawns ?? 0)
  );

  const steps = $("phaseSteps");
  if (steps) {
    steps.querySelectorAll(".play-step").forEach((el) => {
      const step = el.dataset.step;
      el.classList.toggle("is-active", running && step === rp);
      el.classList.toggle("is-done", running && rp === "chaos" && step === "gathering");
    });
  }

  if (els.hudSub) {
    els.hudSub.textContent = running ? getHudSubText(snap) : "";
  }
}

function stopPhaseTick() {
  if (phaseTickTimer) clearInterval(phaseTickTimer);
  phaseTickTimer = null;
  gatherChaosRequested = false;
}

async function requestChaosAdvance() {
  if (gatherChaosRequested || !lastSnap || lastSnap.roundPhase !== "gathering") return;
  if (!lastSnap.gatherRequirements?.met) return;
  const remain = lastSnap.gatherRemainingMs ?? 0;
  if (remain > 0) return;
  gatherChaosRequested = true;
  try {
    const data = await api("/chaos", {
      method: "POST",
      body: isRoomMode ? {} : { sessionId },
    });
    if (data?.snapshot) renderSnapshot(data.snapshot);
  } catch {
    gatherChaosRequested = false;
  }
}

function startPhaseTick() {
  stopPhaseTick();
  let pollAt = 0;
  phaseTickTimer = setInterval(() => {
    if (!lastSnap || lastSnap.phase !== "running") return;
    pollAt += 250;
    if (pollAt >= 1000) {
      pollAt = 0;
      refreshState().catch(() => {});
    }
    if (lastSnap.roundPhase === "gathering" && lastSnap.gatherRemainingMs != null) {
      const remain = Math.max(0, lastSnap.gatherRemainingMs - 250);
      lastSnap = { ...lastSnap, gatherRemainingMs: remain };
      if (els.phaseBannerTimer) {
        els.phaseBannerTimer.textContent = formatMs(remain);
      }
      if (remain <= 0) requestChaosAdvance();
    }
    if (lastSnap.entityCount != null && lastSnap.settings?.chaosMinEntities) {
      lastSnap = {
        ...lastSnap,
        poolFillRatio: Math.min(1, lastSnap.entityCount / lastSnap.settings.chaosMinEntities),
      };
      if (els.poolFill) {
        els.poolFill.style.width = `${Math.round(lastSnap.poolFillRatio * 100)}%`;
      }
    }
    if (lastSnap.roundPhase === "chaos" && els.phaseBannerTimer) {
      els.phaseBannerTimer.textContent = getChaosTimerText(lastSnap);
    }
  }, 250);
}

function applyServerMeta(data) {
  if (data?.champions) champions = data.champions;
  if (data?.roundHistory) roundHistory = data.roundHistory;
  if (data?.snapshot?.roundHistory) roundHistory = data.snapshot.roundHistory;
}

function fillSettingsFromSnap(settings = {}, { force = false } = {}) {
  if (!force && Date.now() < skipSettingsSnapUntil) return;
  const sig = JSON.stringify(settings || {});
  if (!force && sig === lastFilledSettingsSig) return;
  lastFilledSettingsSig = sig;
  const s = settings || {};
  raceAdvancedSettings = {
    chaosSpawnPolicy: s.chaosSpawnPolicy === "windowed" ? "windowed" : "locked",
    chaosSpawnOpenChancePct: Number(s.chaosSpawnOpenChancePct) || 22,
    chaosSpawnWindowMs: Number(s.chaosSpawnWindowMs) || 8000,
    chaosSpawnWindowCooldownMs: Number(s.chaosSpawnWindowCooldownMs) || 14000,
  };
  const g = $("gatherDurationRange");
  if (g && s.gatherDurationSec != null) {
    g.value = String(s.gatherDurationSec);
    $("gatherDurationOut").textContent = String(s.gatherDurationSec);
  }
  const map = [
    ["minParticipantsRange", "minParticipantsOut", "minParticipants"],
    ["minTeamsRange", "minTeamsOut", "minTeams"],
    ["minSpawnsRange", "minSpawnsOut", "minTotalSpawns"],
    ["chaosMinRange", "chaosMinOut", "chaosMinEntities"],
  ];
  for (const [rangeId, outId, key] of map) {
    const el = $(rangeId);
    if (el && s[key] != null) {
      el.value = String(s[key]);
      $(outId).textContent = String(s[key]);
    }
  }
  const trig = $("chaosTriggerSelect");
  if (trig && s.chaosTrigger) trig.value = s.chaosTrigger;
  const cd = $("cooldownRange");
  const cooldownMs = s.chaosSpawnCooldownMs ?? s.spawnCooldownMs;
  if (cd && cooldownMs != null) {
    cd.value = String(Math.round(cooldownMs / 1000));
    $("cooldownOut").textContent = cd.value;
  }
  const gSec = $("gatherDurationRange");
  const gatherMs = s.gatherDurationMs ?? (s.gatherDurationSec ? s.gatherDurationSec * 1000 : null);
  if (gSec && gatherMs) {
    gSec.value = String(Math.round(gatherMs / 1000));
    $("gatherDurationOut").textContent = gSec.value;
  }
  if ($("raceAutopilotOn")) $("raceAutopilotOn").checked = s.autopilot !== false;
  if ($("raceAutoStartOn")) $("raceAutoStartOn").checked = s.autoStartOnConnect !== false;
  if ($("raceRequireYt")) $("raceRequireYt").checked = Boolean(s.requireYoutubeForAutostart);
  if ($("autoNextRoundSec") && s.autoNextRoundMs != null) {
    $("autoNextRoundSec").value = String(Math.round(s.autoNextRoundMs / 1000));
  }
  if ($("autoRetryRoundSec") && s.autoRetryRoundMs != null) {
    $("autoRetryRoundSec").value = String(Math.round(s.autoRetryRoundMs / 1000));
  }
  if ($("chaosGraceSec") && s.chaosEliminationGraceMs != null) {
    $("chaosGraceSec").value = String(Math.round(s.chaosEliminationGraceMs / 1000));
  }
  if ($("chaosMinSec") && s.chaosMinDurationMs != null) {
    $("chaosMinSec").value = String(Math.round(s.chaosMinDurationMs / 1000));
  }
  if ($("raceMaxRounds") && s.maxRounds != null) {
    $("raceMaxRounds").value = String(s.maxRounds);
  }
  if ($("raceAudienceSimOn")) {
    $("raceAudienceSimOn").checked = s.audienceSimEnabled !== false;
  }
  refreshRacePresetHighlight();
}

let activeRacePresetKey = null;
/** Kullanıcı ön ayar seçtiyse socket yenilemesi seçimi silmesin */
let pinnedRacePresetKey = null;
let skipSettingsSnapUntil = 0;
let lastFilledSettingsSig = "";

function setActiveRacePresetUI(key) {
  activeRacePresetKey = key || null;
  const root = hubRoot || document;
  root.querySelectorAll("[data-race-preset]").forEach((btn) => {
    const on = Boolean(key && btn.dataset.racePreset === key);
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  const label = $("presetActiveLabel");
  const hint = $("presetHint");
  if (key && PLAY_RACE_PRESETS[key]) {
    const p = PLAY_RACE_PRESETS[key];
    label?.classList.add("is-preset");
    if (label) label.textContent = p.label;
    if (hint) hint.textContent = p.hint;
  } else {
    label?.classList.remove("is-preset");
    if (label) label.textContent = "Özel";
    if (hint) hint.textContent = "Kayıtlı ayar ön ayarla tam eşleşmiyor — bir profile tıklayın.";
  }
}

function refreshRacePresetHighlight() {
  if (pinnedRacePresetKey && PLAY_RACE_PRESETS[pinnedRacePresetKey]) {
    setActiveRacePresetUI(pinnedRacePresetKey);
    return;
  }
  setActiveRacePresetUI(findMatchingRacePresetKey(getRaceSettingsFromUI()));
}

async function applyRacePreset(presetKey) {
  const aliasMap = {
    auto: "standard_auto",
    fast: "standard_auto_fast",
  };
  const resolvedKey = aliasMap[presetKey] || presetKey;
  const preset = PLAY_RACE_PRESETS[resolvedKey];
  if (!preset) {
    setFeedback("Bilinmeyen ön ayar", "bad");
    return;
  }
  const s = preset.settings;
  pinnedRacePresetKey = resolvedKey;
  skipSettingsSnapUntil = Date.now() + 1800;
  raceAdvancedSettings = {
    chaosSpawnPolicy: s.chaosSpawnPolicy === "windowed" ? "windowed" : "locked",
    chaosSpawnOpenChancePct: Number(s.chaosSpawnOpenChancePct) || 22,
    chaosSpawnWindowMs: Number(s.chaosSpawnWindowMs) || 8000,
    chaosSpawnWindowCooldownMs: Number(s.chaosSpawnWindowCooldownMs) || 14000,
  };
  const setRange = (id, outId, val) => {
    const el = $(id);
    if (el) el.value = String(val);
    if (outId && $(outId)) $(outId).textContent = String(val);
  };
  setRange("gatherDurationRange", "gatherDurationOut", s.gatherDurationSec);
  setRange("minParticipantsRange", "minParticipantsOut", s.minParticipants);
  setRange("minTeamsRange", "minTeamsOut", s.minTeams);
  setRange("minSpawnsRange", "minSpawnsOut", s.minTotalSpawns);
  setRange("chaosMinRange", "chaosMinOut", s.chaosMinEntities);
  setRange("cooldownRange", "cooldownOut", Math.round((s.chaosSpawnCooldownMs || 5000) / 1000));
  if ($("chaosTriggerSelect")) $("chaosTriggerSelect").value = s.chaosTrigger;
  if ($("raceAutopilotOn")) $("raceAutopilotOn").checked = s.autopilot !== false;
  if ($("raceAutoStartOn")) $("raceAutoStartOn").checked = s.autoStartOnConnect !== false;
  if ($("raceRequireYt")) $("raceRequireYt").checked = Boolean(s.requireYoutubeForAutostart);
  if ($("autoNextRoundSec")) $("autoNextRoundSec").value = String(Math.round(s.autoNextRoundMs / 1000));
  if ($("autoRetryRoundSec")) $("autoRetryRoundSec").value = String(Math.round(s.autoRetryRoundMs / 1000));
  if ($("chaosGraceSec")) $("chaosGraceSec").value = String(Math.round(s.chaosEliminationGraceMs / 1000));
  if ($("chaosMinSec")) $("chaosMinSec").value = String(Math.round(s.chaosMinDurationMs / 1000));
  if ($("raceMaxRounds")) $("raceMaxRounds").value = String(s.maxRounds ?? 8);
  if ($("raceAudienceSimOn")) $("raceAudienceSimOn").checked = s.audienceSimEnabled !== false;
  autoPlayEnabled = s.autopilot !== false;
  setActiveRacePresetUI(resolvedKey);

  if (!embedMode) {
    if (s.simulateChat) {
      if (!autoSimOn) {
        try {
          await toggleAutoSim();
        } catch (e) {
          setFeedback(e.message || "Sohbet simülasyonu açılamadı", "bad");
        }
      }
    } else if (autoSimOn) {
      stopAutoSim();
    }
  }

  if (!isRoomMode && !sessionId) {
    setFeedback(`Ön ayar uygulandı: ${preset.label}`, "ok");
    return;
  }

  try {
    await pushSettingsToServer({
      quiet: false,
      body: presetSettingsToServerBody(s),
    });
    if (isRoomMode) {
      const st = await roomApi("/status");
      fillSettingsFromSnap(st.config?.raceSettings || st.race?.settings, { force: true });
      const matched = findMatchingRacePresetKey(st.config?.raceSettings || st.race?.settings);
      if (matched) pinnedRacePresetKey = matched;
    }
    setFeedback(`Ön ayar: ${preset.label}`, "ok");
  } catch (e) {
    setFeedback(e.message || "Kaydedilemedi", "bad");
  } finally {
    setActiveRacePresetUI(pinnedRacePresetKey);
  }
}

function wireRacePresets() {
  const root = hubRoot || document;
  root.querySelectorAll("[data-race-preset]").forEach((btn) => {
    if (btn.dataset.wired) return;
    btn.dataset.wired = "1";
    btn.addEventListener("click", () => {
      applyRacePreset(btn.dataset.racePreset).catch((e) =>
        setFeedback(e.message || "Ön ayar uygulanamadı", "bad")
      );
    });
  });
  refreshRacePresetHighlight();
}

function wireRacePresetHighlightOnChange() {
  const clearPin = () => {
    pinnedRacePresetKey = null;
    refreshRacePresetHighlight();
  };
  const ids = [
    "gatherDurationRange",
    "minParticipantsRange",
    "minTeamsRange",
    "minSpawnsRange",
    "chaosMinRange",
    "chaosTriggerSelect",
    "cooldownRange",
    "raceAutopilotOn",
    "raceAutoStartOn",
    "raceRequireYt",
    "autoNextRoundSec",
    "autoRetryRoundSec",
    "chaosGraceSec",
    "chaosMinSec",
    "raceMaxRounds",
    "raceAudienceSimOn",
  ];
  for (const id of ids) {
    $(id)?.addEventListener("change", clearPin);
    $(id)?.addEventListener("input", clearPin);
  }
}

function updateAutopilotBanner(ap) {
  const el = $("autopilotBanner");
  if (!el) return;
  if (!ap?.enabled) {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
  el.classList.toggle("is-armed", Boolean(ap.armed));
  el.textContent = ap.statusMessage || (ap.armed ? "Otomatik mod aktif" : "Otomatik mod hazır");
}

function trimFeedList(ul, max = 5) {
  if (!ul) return;
  while (ul.children.length > max) ul.firstElementChild?.remove();
}

async function roomApi(path, options = {}) {
  const res = await fetch(`/api/rooms/${encodeURIComponent(activeRoomId)}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    throw new Error("Giriş gerekli — önce /admin/ üzerinden oturum açın.");
  }
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

async function fetchTeamsList() {
  for (const url of ["/api/team-race/teams", "/api/playground/team-race/teams"]) {
    try {
      const res = await fetch(url, { credentials: "include", cache: "no-store" });
      if (!res.ok) continue;
      const data = await res.json().catch(() => ({}));
      if (Array.isArray(data.teams) && data.teams.length) return data.teams;
    } catch {
      /* sonraki URL */
    }
  }
  return FALLBACK_TEAMS;
}

async function api(path, options = {}) {
  if (isRoomMode) return roomApiFromPlaygroundPath(path, options);
  if (path.startsWith("/teams")) {
    return { teams: await fetchTeamsList() };
  }
  const res = await fetch(`${API()}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

async function roomApiFromPlaygroundPath(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  if (path.startsWith("/teams")) {
    return { teams: await fetchTeamsList() };
  }
  if (path.startsWith("/state")) {
    const st = await roomApi("/status");
    return normalizeRoomStatus(st);
  }
  if (path === "/start" && method === "POST") {
    const st = await roomApi("/game/start", { method: "POST", body: {} });
    return wrapRoomRacePayload(st);
  }
  if (path === "/stop" && method === "POST") {
    const snap = await roomApi("/game/stop", { method: "POST", body: {} });
    return wrapRoomRacePayload(snap);
  }
  if (path === "/reset" && method === "POST") {
    const snap = await roomApi("/game/reset", { method: "POST", body: {} });
    return wrapRoomRacePayload(snap);
  }
  if (path === "/chaos" && method === "POST") {
    const snap = await roomApi("/race/chaos", { method: "POST", body: {} });
    return wrapRoomRacePayload(snap);
  }
  if (path === "/shock" && method === "POST") {
    const snap = await roomApi("/race/shock", { method: "POST", body: {} });
    return wrapRoomRacePayload(snap);
  }
  if (path === "/settings" && method === "PATCH") {
    const body = options.body || getRaceSettingsFromUI();
    await roomApi("/race/settings", {
      method: "PATCH",
      body,
    });
    const st = await roomApi("/status");
    return normalizeRoomStatus(st);
  }
  if (path === "/chat" && method === "POST") {
    const body = options.body || {};
    const out = await roomApi("/mock/comment", {
      method: "POST",
      body: {
        author: body.author,
        text: body.text,
        simulated: Boolean(body.simulated),
      },
    });
    const st = await roomApi("/status");
    const norm = normalizeRoomStatus(st);
    return {
      result: out.result,
      snapshot: norm.snapshot,
      roundEnded: norm.snapshot?.phase === "idle" && norm.snapshot?.lastWinner,
      lastSpawn:
        out.result?.type === "spawn" && out.result.entity
          ? out.result.entity
          : null,
      champions: norm.champions,
      roundHistory: norm.roundHistory,
    };
  }
  if (path === "/eliminate" && method === "POST") {
    const body = options.body || {};
    await roomApi("/race/eliminate", {
      method: "POST",
      body: { entityId: body.entityId },
    });
    const st = await roomApi("/status");
    const norm = normalizeRoomStatus(st);
    return {
      snapshot: norm.snapshot,
      entities: entitiesFromSnap(norm.snapshot),
      roundEnded: norm.snapshot?.phase === "idle" && Boolean(norm.snapshot?.lastWinner),
      champions: norm.champions,
      roundHistory: norm.roundHistory,
    };
  }
  throw new Error(`Desteklenmeyen istek: ${path}`);
}

function entitiesFromSnap(snap) {
  return (snap?.activeEntities || []).map((e) => ({ ...e, eliminated: false }));
}

function wrapRoomRacePayload(snap) {
  return {
    snapshot: snap,
    champions: {},
    roundHistory: snap?.roundHistory || [],
    entities: entitiesFromSnap(snap),
    chaos: Boolean(snap?.chaos),
  };
}

function normalizeRoomStatus(st) {
  const snap = st.race || st.game;
  const roundHistory = snap?.roundHistory || [];
  return {
    snapshot: snap,
    champions: {},
    roundHistory,
    entities: entitiesFromSnap(snap),
    chaos: Boolean(snap?.chaos),
    config: st.config,
    links: st.links,
    roomName: st.roomName,
    autopilot: snap?.autopilot,
  };
}

function setupRoomChrome(st) {
  const tag = $("roomTag");
  if (tag) {
    tag.textContent = st.roomName ? `${st.roomName} · ${activeRoomId}` : activeRoomId;
    tag.classList.remove("hidden");
  }
  const adminHref = `/admin/?room=${encodeURIComponent(activeRoomId)}`;
  for (const id of ["linkAdmin", "linkAdminInline"]) {
    const el = $(id);
    if (el) el.href = adminHref;
  }
  const ov = $("linkOverlay");
  if (ov && activeRoomId) {
    ov.href = overlayUrl(arenaLayout);
    ov.classList.remove("hidden");
  }
}

function connectRoomSocket() {
  if (!isRoomMode || isAdminEmbed || socket) return;
  socket = io({ query: { room: activeRoomId } });
  socket.on("race:state", (s) => {
    applyServerMeta({ snapshot: s, roundHistory: s.roundHistory });
    void (async () => {
      try {
        await syncArenaFromEntities(entitiesFromSnap(s));
      } catch {
        /* yoksay */
      }
      renderSnapshot(s);
    })();
  });
  socket.on("race:spawn", () => {
    refreshState().catch(() => {});
  });
}

function setFeedback(text, tone = "") {
  if (!els.chatFeedback) return;
  els.chatFeedback.textContent = text || "";
  els.chatFeedback.className = "play-feedback" + (tone ? ` ${tone}` : "");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function pushElimination(entry) {
  eliminatedRecent.unshift(entry);
  if (eliminatedRecent.length > 14) eliminatedRecent.length = 14;
  renderEliminatedFeed();
  if (els.elimFlash) {
    const seq = ++elimFlashSeq;
    els.elimFlash.textContent = `${entry.teamName || entry.teamCode} elendi!`;
    els.elimFlash.classList.add("is-visible");
    clearTimeout(elimFlashTimer);
    elimFlashTimer = setTimeout(() => {
      if (seq !== elimFlashSeq) return;
      els.elimFlash?.classList.remove("is-visible");
    }, 1800);
  }
}

function renderEliminatedFeed() {
  if (!els.eliminatedFeed) return;
  els.eliminatedFeed.innerHTML = eliminatedRecent.length
    ? eliminatedRecent
        .map(
          (e) =>
            `<li>${teamFlagImg(teamFlagUrl(e.teamCode, e.flagUrl), "sm", e.teamName || e.teamCode)}<span>${escapeHtml(e.displayName || e.teamCode)} — ${escapeHtml(e.teamName || e.teamCode)}</span></li>`
        )
        .join("")
    : '<li class="muted">Henüz elenen yok</li>';
}

function formatActivityLine(row) {
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

function activityRowId(row) {
  return row?.id || `${row?.at || ""}-${row?.author || ""}-${row?.type || ""}`;
}

function buildActivityLineEl(row, isNew) {
  const li = document.createElement("li");
  li.className = `play-act-line${isNew ? " is-new" : ""}`;
  li.dataset.activityId = activityRowId(row);
  const flag =
    row.teamCode && row.type === "spawn"
      ? teamFlagImg(teamFlagUrl(row.teamCode, row.flagUrl), "xs", row.teamName || row.teamCode)
      : "";
  li.innerHTML = `${flag}<span>${escapeHtml(formatActivityLine(row))}</span>`;
  if (isNew) {
    li.addEventListener("animationend", () => li.classList.remove("is-new"), { once: true });
  }
  return li;
}

function renderActivityStrip(feed = []) {
  const ul = els.activityStrip;
  if (!ul) return;
  const rows = (feed || [])
    .filter((r) => r?.type === "spawn")
    .slice(0, 6);
  if (!rows.length) return;

  const targetIds = rows.map(activityRowId);
  const sig = targetIds.join("|");
  if (sig === ul.dataset.activitySig) return;

  const prevHead = ul.firstElementChild?.dataset.activityId || "";
  const nextHead = targetIds[0] || "";
  const pool = new Map([...ul.children].map((el) => [el.dataset.activityId, el]));

  for (const id of [...pool.keys()]) {
    if (!targetIds.includes(id)) pool.get(id)?.remove();
  }

  const ordered = [];
  let createdHead = false;
  for (const row of rows) {
    const id = activityRowId(row);
    let li = pool.get(id);
    if (!li) {
      li = buildActivityLineEl(row, false);
      if (id === nextHead) createdHead = true;
    } else {
      li.classList.remove("is-new");
    }
    ordered.push(li);
  }

  ul.replaceChildren(...ordered);
  ul.dataset.activitySig = sig;

  if (createdHead && prevHead !== nextHead) {
    const head = ul.firstElementChild;
    if (head) {
      head.classList.add("is-new");
      head.addEventListener("animationend", () => head.classList.remove("is-new"), { once: true });
    }
  }
}

function renderArenaTopViewers(topViewers = []) {
  const ol = els.arenaTopViewers;
  if (!ol) return;
  ol.innerHTML = topViewers.length
    ? topViewers
        .map(
          (v) =>
            `<li>
              <span class="play-top-rank">${v.rank}</span>
              ${v.flagUrl || v.lastTeamCode ? teamFlagImg(teamFlagUrl(v.lastTeamCode, v.flagUrl), "xs", v.author) : ""}
              <span class="play-top-name">${escapeHtml(v.author)}${v.simulated ? '<span class="play-top-sim-tag">sim</span>' : ""}</span>
              <strong class="play-top-count" title="Sohbet mesaj sayısı">${v.count}×</strong>
            </li>`
        )
        .join("")
    : '<li class="muted">Henüz yok</li>';
}

function renderArenaRoundWinners() {
  const ul = els.arenaRoundWinners;
  if (!ul) return;
  const promoEl = $("arenaPromoAlert");
  if (promoEl) {
    promoEl.classList.add("hidden");
    promoEl.textContent = "";
  }
  const maxR = getSeriesFromSnap(lastSnap).maxRounds;
  const recent = sortedRoundWinners(roundHistory, maxR);
  const railTitle = document.querySelector(".play-arena-rail--left .play-rail-title");
  if (railTitle) {
    railTitle.textContent =
      recent.length > 0 ? `Kazananlar (${recent.length}/${maxR})` : `Kazananlar (${maxR} tur)`;
  }
  const winnerRows = recent.length
    ? recent
        .map(
          (r) =>
            `<li>
              <span class="play-win-round">TUR ${r.round}</span>
              ${teamFlagImg(teamFlagUrl(r.teamCode, r.flagUrl), "sm", r.teamName || r.teamCode)}
              <span>${escapeHtml(r.teamName || r.teamCode)}</span>
            </li>`
        )
        .join("")
    : '<li class="muted">Henüz yok</li>';
  ul.innerHTML = winnerRows;
}

function renderRoundHistory() {
  if (!els.roundHistoryList) {
    renderArenaRoundWinners();
    return;
  }
  els.roundHistoryList.innerHTML = roundHistory.length
    ? roundHistory
        .map(
          (r) =>
            `<li>
              <span class="round-num">TUR ${r.round}</span>
              ${teamFlagImg(teamFlagUrl(r.teamCode, r.flagUrl), "sm", r.teamName || r.teamCode)}
              <span>
                <strong>${escapeHtml(r.teamName || r.teamCode)}</strong>
                <span class="round-reason">${escapeHtml(winReasonLabel(r.winReason))} · ${r.spawnCount ?? 0} top</span>
              </span>
            </li>`
        )
        .join("")
    : '<li class="muted">Henüz tur yok</li>';
}

function renderChampions() {
  if (!els.championsList) return;
  const rows = Object.entries(champions).sort((a, b) => b[1] - a[1]);
  els.championsList.innerHTML = rows.length
    ? rows
        .map(
          ([code, n], i) =>
            `<li><span class="play-champ-rank">${i + 1}</span>${teamFlagImg(teamFlagUrl(code), "sm", code)}<span>${code.toUpperCase()}</span><strong>${n}</strong></li>`
        )
        .join("")
    : '<li class="muted">Henüz tur yok</li>';
}

function setScenePreviewCtas(activeMap = {}) {
  const arenaEl = $("arena");
  if (!arenaEl) return;
  arenaEl.querySelectorAll("[data-cta]").forEach((el) => {
    const key = el.dataset.cta;
    const active = Boolean(activeMap[key]);
    el.classList.toggle("is-live", active);
    const who = el.querySelector(".yt-cta__who");
    if (who) who.textContent = active ? `@${activeMap[key]}` : "";
  });
}

function paintScenePreview(mode) {
  const isAll = mode === "all";
  document.body.classList.toggle("play-scene-preview--all", isAll);
  document.body.classList.toggle("play-layout-overview", isAll);

  if (mode === "off") {
    document.body.classList.remove("play-scene-preview-on", "play-scene-preview--all", "play-layout-overview");
    clearLayoutOverviewDemo();
    setScenePreviewCtas({});
    return;
  }

  if (isAll) {
    document.body.classList.add("play-scene-preview-on");
    fillLayoutOverviewDemo({
      teamFlagImg,
      teamFlagUrl,
      arenaInfoTicker,
      setScenePreviewCtas,
      applyArenaCtasToDom,
      initArenaCmdBand,
    });
    return;
  }

  document.body.classList.remove("play-layout-overview", "play-scene-preview--all");
  clearLayoutOverviewDemo();
  document.body.classList.add("play-scene-preview-on");

  const phaseBanner = $("phaseBanner");
  const title = $("phaseBannerTitle");
  const timer = $("phaseBannerTimer");
  const hudSub = $("hudSub");
  const pool = $("poolFill");

  if (phaseBanner) phaseBanner.classList.remove("hidden");
  if (pool) pool.style.width = mode === "gathering" ? "62%" : "88%";
  if (title) title.textContent = mode === "gathering" ? "Toplanma" : "Kaos";
  if (timer) timer.textContent = mode === "gathering" ? "4:56" : "Elenme açık";
  if (hudSub) {
    hudSub.textContent =
      mode === "gathering"
        ? "Hedefleri tamamlayın, sonra kaos başlar"
        : "Çıkıştan düşen elenir — son kalan takım kazanır";
  }
  if (phaseBanner) {
    phaseBanner.classList.toggle("is-gathering", mode === "gathering");
    phaseBanner.classList.toggle("is-chaos", mode !== "gathering");
  }

  const winnerPanel = document.querySelector("[data-arena-info-winner]");
  const hubPanel = document.querySelector("[data-arena-info-hub]");

  if (mode === "winner") {
    hubPanel?.classList.add("hidden");
    winnerPanel?.classList.remove("hidden");
    arenaInfoTicker?.setVisible(true);
    arenaInfoTicker?.showWinner(
      {
        teamCode: "gs",
        teamName: "Galatasaray",
        winReason: "last_standing",
        spawnCount: 12,
        round: 1,
      },
      1
    );
  } else if (mode === "gathering" || mode === "chaos") {
    hubPanel?.classList.remove("hidden");
    winnerPanel?.classList.add("hidden");
    arenaInfoTicker?.setVisible(true);
    arenaInfoTicker?.syncFeed({
      recentSpawns: [
        { displayName: "Ahmet", teamCode: "gs", teamName: "Galatasaray" },
        { displayName: "Ece", teamCode: "fb", teamName: "Fenerbahçe" },
        { displayName: "Can", teamCode: "bjk", teamName: "Beşiktaş" },
      ],
    });
    arenaInfoTicker?.setContext({
      phase: "running",
      roundPhase: mode === "chaos" ? "chaos" : "gathering",
      chaos: mode === "chaos",
    });
  } else if (arenaInfoTicker) {
    arenaInfoTicker.setVisible(false);
  }

  setScenePreviewCtas({});
  applyCalSlotLabels();
}

function buildArenaInfoCtx(snap) {
  const running = snap?.phase === "running";
  return {
    phase: running ? "running" : snap?.phase === "idle" ? "idle" : snap?.phase || "idle",
    roundPhase: snap?.roundPhase,
    chaos: snap?.chaos,
  };
}

function syncArenaInfoFromSnap(snap) {
  if (!arenaInfoTicker || !snap) return;
  const running = snap.phase === "running";
  const winnerForThisRound =
    snap.lastWinner &&
    snap.phase === "idle" &&
    (!snap.round || snap.lastWinner.round === snap.round);

  if (winnerForThisRound) {
    arenaInfoTicker.setVisible(true);
    arenaInfoTicker.showWinner(snap.lastWinner, snap.round);
    return;
  }

  if (running || snap.phase === "idle") {
    arenaInfoTicker.setVisible(true);
    arenaInfoTicker.syncFeed({
      recentSpawns: snap.recentSpawns,
      activityFeed: snap.activityFeed,
    });
    arenaInfoTicker.setContext(buildArenaInfoCtx(snap));
    syncArenaActivityFromSnap(snap);
  } else {
    arenaInfoTicker.setVisible(false);
  }
}

/** Yeni katılım — hub listesinde sırayla vurgula */
function syncArenaActivityFromSnap(snap) {
  if (!arenaInfoTicker || !snap || snap.phase !== "running") return;
  const rows = (snap.activityFeed || []).filter((r) => r?.type === "spawn");
  if (!rows.length) return;
  const head = rows[0];
  const id = activityRowId(head);
  if (id === lastArenaActivityId) return;
  lastArenaActivityId = id;
  arenaInfoTicker.pingNewJoin(head, buildArenaInfoCtx(snap));
}

function renderSnapshot(snap) {
  if (!snap) return;
  if (snap.roundPhase !== "gathering") gatherChaosRequested = false;

  const running = snap.phase === "running";
  applyArenaFromSnap(snap);
  updatePhaseUI(snap);
  syncArenaHudPosition();
  if (running) startPhaseTick();
  else stopPhaseTick();

  if (els.round) els.round.textContent = formatRoundLabel(snap);
  const arenaEl = $("arena");
  if (arenaEl) applyArenaCtasToDom(arenaEl, snap.arenaCtas);
  const cmdBand = $("arenaCmdBand");
  const showCmdBand =
    running ||
    snap.phase === "idle" ||
    document.body.classList.contains("play-layout-overview") ||
    document.body.classList.contains("play-scene-preview-on");
  setArenaCmdBandVisible(cmdBand, showCmdBand);
  syncArenaCmdBand(cmdBand, snap.arenaCtas);

  const st = snap.stats || {};
  if (els.statSpawns) els.statSpawns.textContent = String(st.spawns ?? 0);
  if (els.statUnmatched) els.statUnmatched.textContent = String(st.unmatched ?? 0);
  const byTeam = snap.activeByTeam || {};
  const summed = Object.values(byTeam).reduce((acc, n) => acc + (Number(n) || 0), 0);
  const onArena = Number.isFinite(Number(arena?.bodies?.size))
    ? Number(arena.bodies.size)
    : Number.isFinite(Number(snap.entityCount))
      ? Number(snap.entityCount)
      : summed;
  if (els.statArena) els.statArena.textContent = String(onArena);
  if (els.arenaBadge) {
    els.arenaBadge.textContent = `Arenada: ${onArena}`;
    els.arenaBadge.classList.toggle("is-running", running);
  }

  const active = snap.activeByTeam || {};
  if (els.leaderboard) {
    const rows = Object.entries(active).sort((a, b) => b[1] - a[1]);
    els.leaderboard.innerHTML = rows.length
      ? rows
          .map(
            ([code, n]) =>
              `<li>${teamFlagImg(teamFlagUrl(code), "sm", code)}<span>${code.toUpperCase()}</span><strong>${n}</strong></li>`
          )
          .join("")
      : '<li class="muted">Arena boş</li>';
  }

  const recent = snap.recentSpawns || [];
  if (els.spawnFeed) {
    els.spawnFeed.innerHTML = recent.length
      ? recent
          .map(
            (s) =>
              `<li>${teamFlagImg(teamFlagUrl(s.teamCode, s.flagUrl), "sm", s.teamName)}<span>${escapeHtml(s.displayName)} → ${escapeHtml(s.teamName)}</span></li>`
          )
          .join("")
      : '<li class="muted">Henüz yok</li>';
    trimFeedList(els.spawnFeed, 5);
  }

  if (els.leaderboard) trimFeedList(els.leaderboard, 5);

  syncArenaInfoFromSnap(snap);

  renderRoundHistory();
  renderArenaRoundWinners();
  renderChampions();
  renderArenaTopViewers(snap.topViewers || []);
  syncArenaActivityFromSnap(snap);
  updateAutopilotBanner(snap.autopilot);
  scheduleClientAudienceSim(snap);
  if (snap.settings) fillSettingsFromSnap(snap.settings);
  if (scenePreviewMode !== "off") paintScenePreview(scenePreviewMode);
}

function clearAutoRoundTimer() {
  if (autoRoundTimer) clearTimeout(autoRoundTimer);
  autoRoundTimer = null;
}

async function startNextRoundAuto(reason = "next") {
  if (!autoPlayEnabled) return;
  const series = getSeriesFromSnap(lastSnap);
  if (series.seriesComplete) {
    setFeedback(`Seri tamamlandı (${series.completedRounds}/${series.maxRounds} tur)`, "ok");
    return;
  }
  try {
    if (arena) {
      arena.clear();
      arena.layout();
    }
    eliminatedRecent.length = 0;
    renderEliminatedFeed();
    await pushSettingsToServer();
    const data = await api("/start", {
      method: "POST",
      body: isRoomMode ? {} : { sessionId },
    });
    applyServerMeta(data);
    if (data.entities) await syncArenaFromEntities(data.entities);
    renderSnapshot(data.snapshot);
    startPhaseTick();
    syncArenaInfoFromSnap(data.snapshot);
    const label =
      reason === "retry"
        ? `Tur ${data.snapshot.round} yeniden başladı (otomatik)`
        : `Tur ${data.snapshot.round} başladı (otomatik)`;
    setFeedback(label, "ok");
    appendLiveChatLine("Sistem", label, { type: "ignored", reason: "system" });
  } catch (e) {
    setFeedback(e.message, "bad");
  }
}

function scheduleAutoNextRound(snap) {
  clearAutoRoundTimer();
  if (!autoPlayEnabled) return;
  if (isRoomMode) return;

  const series = getSeriesFromSnap(snap || lastSnap);
  if (series.seriesComplete) {
    setFeedback(
      `Seri bitti — ${series.completedRounds}/${series.maxRounds} tur kazananlar solda`,
      "ok"
    );
    return;
  }

  const settings = snap?.settings || lastSnap?.settings || {};
  const hasWinner = Boolean(snap?.lastWinner);
  const delay = hasWinner
    ? Number(settings.autoNextRoundMs) || 12_000
    : Number(settings.autoRetryRoundMs) || 25_000;

  autoRoundTimer = setTimeout(() => {
    autoRoundTimer = null;
    startNextRoundAuto(hasWinner ? "next" : "retry");
  }, delay);

  setFeedback(
    hasWinner
      ? `Sonraki tur ~${Math.round(delay / 1000)} sn içinde otomatik başlayacak`
      : `Yeniden deneme ~${Math.round(delay / 1000)} sn içinde`,
    "ok"
  );
}

function handleRoundEnded(snap, data = {}) {
  applyServerMeta(data);
  if (arena) arena.clear();
  renderSnapshot(snap);
  const w = snap?.lastWinner;
  if (w) {
    setFeedback(`Tur ${snap.round} bitti — ${w.teamName} kazandı!`, "ok");
    appendLiveChatLine("Sistem", `Tur ${snap.round} kazananı: ${w.teamName}`, {
      type: "spawn",
    });
  }
  if (snap?.phase === "idle") {
    scheduleAutoNextRound(snap);
  }
}

async function syncArenaFromEntities(entities) {
  if (!arena) return;
  const list = (entities || []).filter((e) => !e.eliminated);
  const valid = new Set(list.map((e) => e.id));
  for (const id of [...arena.bodies.keys()]) {
    if (!valid.has(id)) {
      const body = arena.bodies.get(id);
      if (body?.plugin?.fallingOut) continue;
      arena.Matter.World.remove(arena.world, body);
      arena.bodies.delete(id);
    }
  }
  for (const e of list) {
    if (!arena.bodies.has(e.id)) await arena.spawn(e);
  }
}

async function refreshState() {
  const data = await api(`/state?sessionId=${encodeURIComponent(sessionId)}`);
  applyServerMeta(data);
  const snap = data.snapshot || data;
  if (data.chaos != null || snap?.chaos != null || snap?.roundPhase === "chaos") {
    const chaosEffective = snap?.roundPhase === "chaos" || Boolean(snap?.chaos ?? data.chaos);
    chaosOn = chaosEffective;
    arena?.setChaos(chaosOn);
    const btn = $("btnChaos");
    if (btn) {
      btn.textContent = chaosOn ? "⚡ Kaos modu: Açık" : "⚡ Kaos modu: Kapalı";
      btn.classList.toggle("is-on", chaosOn);
    }
  }
  await syncArenaFromEntities(data.entities);
  renderSnapshot(data.snapshot);
  return data;
}

async function newSession() {
  stopAutoSim();
  livePickStats.clear();
  els.liveChat?.replaceChildren();
  eliminatedRecent.length = 0;
  renderEliminatedFeed();
  if (arena) arena.clear();
  const cooldown = Number($("cooldownRange").value) * 1000;
  const data = await api("/session", {
    method: "POST",
    body: { spawnCooldownMs: cooldown, ...getRaceSettingsFromUI() },
  });
  sessionId = data.sessionId;
  try {
    sessionStorage.setItem(SESSION_KEY, sessionId);
  } catch {
    /* yoksay */
  }
  champions = {};
  roundHistory = [];
  lastArenaActivityId = "";
  applyServerMeta(data);
  renderSnapshot(data.snapshot);
  setFeedback("Hazır — Başlat’a basın.", "ok");
}

async function ensureSession() {
  if (isRoomMode) {
    const st = await roomApi("/status");
    if (st.config?.gameMode && st.config.gameMode !== "team-race") {
      throw new Error("Bu yayın takım yarışı modunda değil. Admin panelden modu değiştirin.");
    }
    setupRoomChrome(st);
    const norm = normalizeRoomStatus(st);
    applyServerMeta(norm);
    fillSettingsFromSnap(st.config?.raceSettings || st.race?.settings);
    if (st.race) {
      await syncArenaFromEntities(norm.entities);
      renderSnapshot(st.race);
    }
    connectRoomSocket();
    return true;
  }
  if (sessionId) {
    try {
      const st = await api(`/state?sessionId=${encodeURIComponent(sessionId)}`);
      applyServerMeta(st);
      return true;
    } catch {
      sessionId = null;
    }
  }
  const saved = sessionStorage.getItem(SESSION_KEY);
  if (saved) {
    sessionId = saved;
    try {
      const st = await api(`/state?sessionId=${encodeURIComponent(sessionId)}`);
      applyServerMeta(st);
      await syncArenaFromEntities(st.entities);
      renderSnapshot(st.snapshot);
      return true;
    } catch {
      sessionStorage.removeItem(SESSION_KEY);
      sessionId = null;
    }
  }
  await newSession();
  return true;
}

async function onEliminate(entityId) {
  const localChaos =
    arena?.roundPhase === "chaos" && lastSnap?.roundPhase === "chaos";
  if (!localChaos) {
    // Toplanmada yanlış callback gelirse görsel/istek tetikleme.
    if (lastSnap) {
      await syncArenaFromEntities(getSnapshotEntities(lastSnap));
      renderSnapshot(lastSnap);
    }
    return;
  }
  const body = arena?.bodies?.get(entityId);
  if (body?.plugin) {
    pushElimination({
      teamCode: body.plugin.teamCode,
      teamName: body.plugin.teamName || body.plugin.teamCode,
      displayName: body.plugin.displayName,
      flagUrl: body.plugin.flagUrl,
    });
  }
  try {
    const data = await api("/eliminate", {
      method: "POST",
      body: { sessionId, entityId },
    });
    if (!data?.ok) {
      if (body) {
        delete body.plugin.fallingOut;
        delete body.plugin.fallingOutAt;
        body.collisionFilter.mask = 0xffffffff;
        body.collisionFilter.group = 0;
      }
      return;
    }
    if (data.roundEnded && data.snapshot) {
      handleRoundEnded(data.snapshot, data);
      return;
    }
    await syncArenaFromEntities(data.entities);
    renderSnapshot(data.snapshot);
    applyServerMeta(data);
  } catch {
    if (body) {
      delete body.plugin.fallingOut;
      delete body.plugin.fallingOutAt;
      body.collisionFilter.mask = 0xffffffff;
      body.collisionFilter.group = 0;
    }
  }
}

function randomSimName() {
  return generateSimAuthor();
}

function randomSimMessage() {
  return generateSimChatText();
}

function clearClientAudienceSimTimer() {
  if (clientAudienceSimTimer) clearTimeout(clientAudienceSimTimer);
  clientAudienceSimTimer = null;
}

function scheduleClientAudienceSim(snap) {
  clearClientAudienceSimTimer();
  if (
    !shouldRunClientAudienceSim(snap, lastRealChatAt, {
      isRoomMode,
      autopilot: snap?.autopilot,
      manualBurstOn: autoSimOn,
    })
  ) {
    return;
  }
  const delay = pickClientSimIntervalMs(snap?.settings || {});
  clientAudienceSimTimer = setTimeout(async () => {
    clientAudienceSimTimer = null;
    if (!lastSnap || lastSnap.phase !== "running") return;
    try {
      await sendChat(generateSimChatText(), generateSimAuthor(), { simulated: true });
    } catch {
      /* sunucu kapalı */
    }
    scheduleClientAudienceSim(lastSnap);
  }, delay);
}

function resultMeta(r) {
  switch (r?.type) {
    case "spawn":
      return { cls: "spawn", label: "→ Arena’ya girdi" };
    case "unmatched":
      return { cls: "warn", label: "Takım tanınmadı" };
    case "cooldown":
      return { cls: "warn", label: "Bekleme (aynı izleyici)" };
    case "channel_limit":
      return { cls: "warn", label: "Zaten arenada" };
    case "limit":
      return { cls: "warn", label: "Arena dolu" };
    case "ignored":
      return r.reason === "not_running"
        ? { cls: "warn", label: "Tur kapalı — Başlat" }
        : { cls: "muted", label: "Yoksayıldı" };
    default:
      return { cls: "muted", label: "" };
  }
}

function appendLiveChatLine(author, text, result) {
  const ul = els.liveChat;
  if (!ul) return;
  if (result?.type !== "spawn" || !result?.entity?.teamCode) return;
  const who = String(author || "").trim();
  if (!who || who.toLocaleLowerCase("tr-TR") === "sistem") return;
  const teamCode = result.entity.teamCode;
  const teamName = result.entity.teamName || teamDisplayName(teamCode);
  if (!teamName) return;

  const key = `${who.toLocaleLowerCase("tr-TR")}::${teamCode}`;
  const now = Date.now();
  const row = livePickStats.get(key) || { count: 0, lastShownAt: 0 };
  row.count += 1;
  const shouldShow = row.count === 1 || now - row.lastShownAt >= LIVE_PICK_COOLDOWN_MS;
  livePickStats.set(key, row);
  if (!shouldShow) return;
  row.lastShownAt = now;

  const lineText =
    row.count <= 1
      ? `${who}, ${teamName}'ı seçti!`
      : `${who}, ${row.count}. defa ${teamName}'ı seçti!`;
  if (arenaInfoTicker && lastSnap?.phase === "running") {
    arenaInfoTicker.pingNewJoin(
      {
        type: "spawn",
        author: who,
        teamCode,
        teamName,
        count: row.count,
      },
      buildArenaInfoCtx(lastSnap)
    );
  }
  const meta = resultMeta(result);
  const initial = (who[0] || "?").toLocaleUpperCase("tr-TR");
  const li = document.createElement("li");
  li.className = `chat-line--${meta.cls} is-new`;
  li.addEventListener("animationend", () => li.classList.remove("is-new"), { once: true });
  li.innerHTML = `
    <span class="chat-avatar">${escapeHtml(initial)}</span>
    <span class="chat-body">
      <span class="chat-author">${escapeHtml(who)}</span>
      <span class="chat-text">${escapeHtml(lineText)}</span>
    </span>`;
  ul.appendChild(li);
  trimFeedList(ul, 6);
}

function getSimDelayMs() {
  const speed = Number($("simSpeedRange")?.value) || 6;
  const base = 2200 - speed * 180;
  return Math.max(350, base + (Math.random() - 0.5) * 400);
}

async function sendChat(text, authorOverride, { simulated = false } = {}) {
  const author = (authorOverride ?? $("authorInput").value.trim()) || "Oyuncu";
  const body = String(text ?? $("chatInput").value).trim();
  if (!body) {
    setFeedback("Takım adı yazın.", "warn");
    return null;
  }

  const isSim = simulated || Boolean(authorOverride);
  if (!isSim) lastRealChatAt = Date.now();

  const data = await api("/chat", {
    method: "POST",
    body: { sessionId, author, text: body, simulated: isSim },
  });

  if (!authorOverride) $("chatInput").value = "";

  const r = data.result;
  appendLiveChatLine(author, body, r);

  if (data.roundEnded && data.snapshot) {
    handleRoundEnded(data.snapshot, data);
    return data;
  }

  if (data.snapshot?.roundPhase === "chaos" && data.snapshot?.chaosTriggerReason) {
    setFeedback("⚡ Kaos modu başladı!", "ok");
    appendLiveChatLine("Sistem", "Kaos modu — elenme açıldı", { type: "spawn" });
  }

  const spawnEntity =
    data.lastSpawn ||
    (r?.type === "spawn" && r.entity ? r.entity : null);
  if (spawnEntity && arena) {
    await arena.spawn(spawnEntity);
    if (!autoSimOn) setFeedback(`✓ ${data.lastSpawn.teamName} arena’da!`, "ok");
  } else if (!autoSimOn) {
    if (r?.type === "unmatched") setFeedback("Takım tanınmadı.", "warn");
    else if (r?.type === "cooldown") setFeedback("Bekleme süresi…", "warn");
    else if (r?.type === "ignored" && r.reason === "not_running") setFeedback("Önce Başlat.", "bad");
    else setFeedback(r?.type || "—", "");
  }

  applyServerMeta(data);
  renderSnapshot(data.snapshot);
  return data;
}

function buildTeamButtons() {
  if (!els.teamGrid) return;
  const aliases = {
    gs: "gs",
    fb: "fener",
    bjk: "bjk",
    ts: "trabzon",
    goz: "goztepe",
    sam: "samsun",
    ibfk: "basaksehir",
    ala: "alanyaspor",
    ant: "antalya",
    eyp: "eyup",
    fkg: "karagumruk",
    gfk: "gaziantep",
    gb: "genclerbirligi",
    kas: "kasimpasa",
    kay: "kayseri",
    koc: "kocaeli",
    kon: "konya",
    riz: "rize",
  };
  if (!teams.length) {
    els.teamGrid.innerHTML = '<p class="muted play-team-empty">Takım listesi yüklenemedi — sayfayı yenileyin.</p>';
    return;
  }
  els.teamGrid.innerHTML = teams
    .map(
      (t) =>
        `<button type="button" class="play-team-btn" data-code="${t.code}" title="${escapeHtml(t.name)}">${teamFlagImg(t.flagUrl || teamFlagUrl(t.code), "md", t.name)}<span>${escapeHtml(t.code)}</span></button>`
    )
    .join("");
  els.teamGrid.querySelectorAll(".play-team-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      sendChat(aliases[btn.dataset.code] || btn.dataset.code).catch((e) =>
        setFeedback(e.message, "bad")
      );
    });
  });
}

function stopAutoSim() {
  autoSimOn = false;
  recentSimAuthors.length = 0;
  if (autoSimTimer) clearTimeout(autoSimTimer);
  autoSimTimer = null;
  const btn = $("btnAutoSim");
  if (btn) btn.textContent = "▶ YouTube sohbet akışı";
  const hint = $("autoSimHint");
  if (hint) {
    hint.textContent = "Kapalı — rastgele isim + takım yorumları sürekli akar.";
  }
  refreshRacePresetHighlight();
}

function scheduleNextSimTick() {
  if (!autoSimOn) return;
  autoSimTimer = setTimeout(async () => {
    if (!autoSimOn) return;
    const author = randomSimName();
    const text = randomSimMessage();
    $("authorInput").value = author;
    try {
      await sendChat(text, author, { simulated: true });
      if (autoSimOn && Math.random() < 0.14) {
        const author2 = randomSimName();
        const text2 = randomSimMessage();
        await sendChat(text2, author2, { simulated: true }).catch(() => {});
      }
    } catch {
      /* sunucu hatası — yine de devam */
    }
    scheduleNextSimTick();
  }, getSimDelayMs());
}

async function toggleAutoSim() {
  if (autoSimOn) {
    stopAutoSim();
    return;
  }

  autoSimOn = true;
  refreshRacePresetHighlight();
  simProfileSeq = Math.floor(Math.random() * 500);
  const btn = $("btnAutoSim");
  if (btn) btn.textContent = "■ Sohbeti durdur";
  const hint = $("autoSimHint");
  if (hint) hint.textContent = "Açık — canlı yayın sohbeti simüle ediliyor…";

  try {
    const st = await api(isRoomMode ? "/state" : `/state?sessionId=${encodeURIComponent(sessionId)}`);
    if (st.snapshot?.phase !== "running") {
      if (arena) arena.clear();
      const started = await api("/start", {
        method: "POST",
        body: isRoomMode ? {} : { sessionId },
      });
      renderSnapshot(started.snapshot);
      appendLiveChatLine("Sistem", "Tur otomatik başlatıldı", {
        type: "ignored",
        reason: "system",
      });
    }
  } catch (e) {
    stopAutoSim();
    setFeedback(e.message, "bad");
    return;
  }

  if (els.liveChat && !els.liveChat.children.length) {
    appendLiveChatLine("Sistem", "Sohbet simülasyonu başladı — izleyici yorumları akıyor", {
      type: "ignored",
    });
  }

  scheduleNextSimTick();
}

function ensureHubStyles() {
  if (document.getElementById("playHubCss")) return;
  const link = document.createElement("link");
  link.id = "playHubCss";
  link.rel = "stylesheet";
  link.href = "/play/play.css?v=46";
  document.head.appendChild(link);
}

function loadScriptOnce(src, id) {
  return new Promise((resolve, reject) => {
    if (document.getElementById(id)) return resolve();
    const s = document.createElement("script");
    s.id = id;
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`${src} yüklenemedi`));
    document.head.appendChild(s);
  });
}

async function ensureMatter() {
  if (window.Matter) return;
  await loadScriptOnce("/lib/matter.min.js", "matterJs");
}

function wireHubResize(container) {
  if (hubResizeObserver) hubResizeObserver.disconnect();
  hubResizeObserver = new ResizeObserver(() => arena?.layout());
  hubResizeObserver.observe(container);
}

export function hubApplyRaceState(snap) {
  if (!isAdminEmbed || !snap) return;
  applyServerMeta({ snapshot: snap, roundHistory: snap.roundHistory });
  syncArenaFromEntities(entitiesFromSnap(snap)).catch(() => {});
  renderSnapshot(snap);
}

export function hubOnRaceSpawn() {
  if (!isAdminEmbed) return;
  refreshState().catch(() => {});
}

export function hubResize() {
  arena?.layout();
}

export async function unmountRoomHub() {
  stopPhaseTick();
  clearAutoRoundTimer();
  stopAutoSim();
  if (arena) {
    arena.stop();
    arena = null;
  }
  if (hubResizeObserver) {
    hubResizeObserver.disconnect();
    hubResizeObserver = null;
  }
  if (hubRoot) {
    hubRoot.innerHTML = "";
    hubRoot.classList.remove("play-room-hub", "is-ready");
  }
  hubRoot = null;
  isAdminEmbed = false;
  if (!document.body.classList.contains("play-app")) {
    isRoomMode = false;
    activeRoomId = null;
  }
}

export async function mountRoomHub(container, roomIdArg) {
  if (!container || !roomIdArg) return;
  await unmountRoomHub();
  ensureHubStyles();
  await ensureMatter();

  isAdminEmbed = true;
  isRoomMode = true;
  activeRoomId = roomIdArg;
  hubRoot = container;
  hubRoot.className = "race-studio-mount play-room-hub";
  hubRoot.innerHTML = ADMIN_RACE_MOUNT_HTML;
  rebindEls();

  await initHubCore({ adminEmbed: true });
  wireHubResize(container);
  hubRoot.classList.add("is-ready");
}

async function initHubCore({ adminEmbed = false } = {}) {
  if (adminEmbed) isAdminEmbed = true;

  if (!window.Matter) {
    showBlocked("Matter.js yüklenemedi.");
    return;
  }

  if (!isRoomMode) {
    try {
      const health = await fetch("/api/health").then((r) => r.json());
      if (!health.playgroundEnabled) {
        showBlocked("Oyun alanı kapalı (PLAYGROUND=0).");
        return;
      }
    } catch {
      showBlocked("Sunucu yok — baslat.cmd ile başlatın.");
      return;
    }
  }

  $("btnAutoSim")?.classList.toggle("hidden", embedMode);

  hideLoading();

  const canvas = $("arenaCanvas");
  if (!canvas) {
    showBlocked("Arena yüklenemedi.");
    return;
  }
  if (arena) {
    arena.stop();
    arena = null;
  }
  arena = new TeamRaceArena(canvas, {
    onEliminate: (id) => onEliminate(id),
    showExitLabel: false,
  });
  arena.start();
  arenaInfoTicker = createArenaInfoTicker(els.winnerCard);
  initArenaCmdBand($("arenaCmdBand"));

  teams = await fetchTeamsList();
  buildTeamButtons();
  await ensureSession();

  $("cooldownRange")?.addEventListener("input", () => {
    const out = $("cooldownOut");
    const range = $("cooldownRange");
    if (out && range) out.textContent = range.value;
  });

  $("simSpeedRange")?.addEventListener("input", () => {
    const v = Number($("simSpeedRange").value);
    const labels = ["", "Çok yavaş", "Yavaş", "Normal", "Normal+", "Hızlı", "Çok hızlı", "Turbo", "Turbo+", "Maks", "Deli"];
    const out = $("simSpeedOut");
    if (out) out.textContent = labels[v] || String(v);
  });
  $("simSpeedRange")?.dispatchEvent?.(new Event("input"));

  wireHubControls();
  wireRacePresets();
  wireRacePresetHighlightOnChange();

  initPlayCalibration({
    roomId: activeRoomId,
    orientation: arenaLayout,
    getArena: () => arena,
    onLayoutApplied: () => {
      requestAnimationFrame(() => syncArenaHudPosition());
    },
    onPreviewTeardown: () => {
      if (lastSnap) renderSnapshot(lastSnap);
      else if (arena) {
        arena.clear();
        arena.setRoundPhase("gathering");
        arena.setChaos(false);
      }
    },
  });

  try {
    await loadPlayArenaLayout({ roomId: activeRoomId, orientation: arenaLayout });
  } catch {
    applyPlayArenaLayout(PLAY_ARENA_LAYOUT_DEFAULT, arenaLayout);
  }

  applyArenaLayout();
  if (isRoomMode) wirePlayLayoutUi();

  if (!isAdminEmbed) {
    window.addEventListener("resize", () => {
      arena?.layout();
      syncArenaHudPosition();
    });
  }
}

function wireHubControls() {
  const btnStart = $("btnStart");
  if (btnStart && !btnStart.dataset.wired) {
    btnStart.dataset.wired = "1";
    btnStart.addEventListener("click", async () => {
    const series = getSeriesFromSnap(lastSnap);
    if (series.seriesComplete) {
      setFeedback(
        `Seri tamamlandı (${series.completedRounds}/${series.maxRounds}). Sıfırla ile yeniden başlayın.`,
        "bad"
      );
      return;
    }
    clearAutoRoundTimer();
    autoPlayEnabled = true;
    if (arena) {
      arena.clear();
      arena.layout();
    }
    eliminatedRecent.length = 0;
    renderEliminatedFeed();
    await pushSettingsToServer();
    const data = await api("/start", {
      method: "POST",
      body: isRoomMode ? {} : { sessionId },
    });
    applyServerMeta(data);
    await syncArenaFromEntities([]);
    renderSnapshot(data.snapshot);
    startPhaseTick();
    arenaInfoTicker?.setVisible(false);
    setFeedback(`Tur ${data.snapshot.round} başladı — alttaki çıkıştan düşen elenir!`, "ok");
    });
  }

  const btnStop = $("btnStop");
  if (btnStop && !btnStop.dataset.wired) {
    btnStop.dataset.wired = "1";
    btnStop.addEventListener("click", async () => {
    clearAutoRoundTimer();
    autoPlayEnabled = false;
    const data = await api("/stop", {
      method: "POST",
      body: isRoomMode ? {} : { sessionId },
    });
    if (arena) arena.clear();
    handleRoundEnded(data.snapshot, data);
    });
  }

  const btnReset = $("btnReset");
  if (btnReset && !btnReset.dataset.wired) {
    btnReset.dataset.wired = "1";
    btnReset.addEventListener("click", async () => {
    clearAutoRoundTimer();
    stopAutoSim();
    livePickStats.clear();
    els.liveChat?.replaceChildren();
    eliminatedRecent.length = 0;
    roundHistory = [];
    lastArenaActivityId = "";
    champions = {};
    renderEliminatedFeed();
    if (arena) arena.clear();
    const data = await api("/reset", {
      method: "POST",
      body: isRoomMode ? {} : { sessionId },
    });
    applyServerMeta(data);
    renderSnapshot(data.snapshot);
    setFeedback("Sıfırlandı.", "ok");
    });
  }

  const btnChaos = $("btnChaos");
  if (btnChaos && !btnChaos.dataset.wired) {
    btnChaos.dataset.wired = "1";
    btnChaos.addEventListener("click", async () => {
      try {
        if (!isRoomMode && !sessionId) throw new Error("Oturum yok");
        manualChaosUntil = Date.now() + 8000;
        if (arena?.bodies?.size > 0) arena.forceEnterChaos?.();
        const data = await api("/chaos", {
          method: "POST",
          body: isRoomMode ? {} : { sessionId, enabled: true },
        });
        const snap = data.snapshot;
        if (snap) {
          if (data.entities) await syncArenaFromEntities(data.entities);
          renderSnapshot(snap);
        }
        if (snap?.roundPhase === "chaos" || arena?.roundPhase === "chaos") {
          arena?.forceEnterChaos?.();
          setFeedback("⚡ Kaos başladı — toplar dağılıyor", "ok");
        } else if (arena?.bodies?.size > 0) {
          manualChaosUntil = Date.now() + 12000;
          arena.forceEnterChaos?.();
          setFeedback("Kaos yerelde açıldı — sunucu turu kontrol edin", "warn");
        } else {
          setFeedback("Önce turu başlatın ve toplar gelsin (sohbet/test)", "bad");
        }
      } catch (e) {
        if (arena?.bodies?.size > 0) {
          manualChaosUntil = Date.now() + 12000;
          arena.forceEnterChaos?.();
          setFeedback(`Sunucu: ${e.message} — yerel kaos açıldı`, "warn");
        } else {
          setFeedback(e.message, "bad");
        }
      }
    });
  }
  const btnShock = $("btnShock");
  if (btnShock && !btnShock.dataset.wired) {
    btnShock.dataset.wired = "1";
    btnShock.addEventListener("click", async () => {
      try {
        if (!isRoomMode && !sessionId) throw new Error("Oturum yok");
        const data = await api("/shock", {
          method: "POST",
          body: isRoomMode ? {} : { sessionId },
        });
        const snap = data.snapshot;
        if (snap && arena) {
          const ents = data.entities ?? entitiesFromSnap(snap);
          await syncArenaFromEntities(ents);
          renderSnapshot(snap);
        }
        setFeedback("💥 Şok dalgası tetiklendi", "ok");
      } catch (e) {
        setFeedback(e.message || "Şok tetiklenemedi", "bad");
      }
    });
  }

  const rangeIds = [
    "gatherDurationRange",
    "chaosMinRange",
    "minParticipantsRange",
    "minTeamsRange",
    "minSpawnsRange",
    "chaosTriggerSelect",
    "cooldownRange",
  ];
  const autoFieldIds = [
    "raceAutopilotOn",
    "raceAutoStartOn",
    "raceRequireYt",
    "raceMaxRounds",
    "raceAudienceSimOn",
    "autoNextRoundSec",
    "autoRetryRoundSec",
    "chaosGraceSec",
    "chaosMinSec",
  ];
  for (const id of autoFieldIds) {
    $(id)?.addEventListener("change", () => pushSettingsToServer({ quiet: true }));
  }

  for (const id of rangeIds) {
    $(id)?.addEventListener("change", () => pushSettingsToServer({ quiet: true }));
    $(id)?.addEventListener("input", () => {
      if (id === "gatherDurationRange") $("gatherDurationOut").textContent = $("gatherDurationRange").value;
      if (id === "chaosMinRange") $("chaosMinOut").textContent = $("chaosMinRange").value;
      if (id === "minParticipantsRange") $("minParticipantsOut").textContent = $("minParticipantsRange").value;
      if (id === "minTeamsRange") $("minTeamsOut").textContent = $("minTeamsRange").value;
      if (id === "minSpawnsRange") $("minSpawnsOut").textContent = $("minSpawnsRange").value;
      if (id === "cooldownRange") $("cooldownOut").textContent = $("cooldownRange").value;
    });
  }

  $("btnNewSession")?.addEventListener("click", () =>
    newSession().catch((e) => setFeedback(e.message, "bad"))
  );

  const btnSend = $("btnSend");
  if (btnSend && !btnSend.dataset.wired) {
    btnSend.dataset.wired = "1";
    btnSend.addEventListener("click", () => sendChat().catch((e) => setFeedback(e.message, "bad")));
  }
  const chatInput = $("chatInput");
  if (chatInput && !chatInput.dataset.wired) {
    chatInput.dataset.wired = "1";
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendChat().catch((err) => setFeedback(err.message, "bad"));
    });
  }
  const btnAutoSim = $("btnAutoSim");
  if (btnAutoSim && !btnAutoSim.dataset.wired) {
    btnAutoSim.dataset.wired = "1";
    btnAutoSim.addEventListener("click", toggleAutoSim);
  }
  const btnScenarioMenu = $("btnScenarioMenu");
  const scenarioMenu = $("scenarioMenu");
  if (btnScenarioMenu && scenarioMenu && !btnScenarioMenu.dataset.wired) {
    btnScenarioMenu.dataset.wired = "1";
    btnScenarioMenu.addEventListener("click", (e) => {
      e.stopPropagation();
      scenarioMenu.classList.toggle("hidden");
    });
    scenarioMenu.querySelectorAll("[data-scene-mode]").forEach((btn) => {
      btn.addEventListener("click", () => {
        scenePreviewMode = btn.dataset.sceneMode || "off";
        scenarioMenu.classList.add("hidden");
        if (scenePreviewMode === "off") {
          document.body.classList.remove("play-scene-preview-on");
          if (lastSnap) renderSnapshot(lastSnap);
        } else {
          paintScenePreview(scenePreviewMode);
        }
      });
    });
    document.addEventListener("click", (ev) => {
      if (scenarioMenu.classList.contains("hidden")) return;
      if (scenarioMenu.contains(ev.target) || btnScenarioMenu.contains(ev.target)) return;
      scenarioMenu.classList.add("hidden");
    });
  }
}

async function init() {
  if (!activeRoomId) {
    location.replace("/admin/");
    return;
  }
  if (embedMode) document.body.classList.add("play-embed");
  if (isRoomMode) document.body.classList.add("play-app--studio");
  await initHubCore();
}

function showBlocked(msg) {
  hideLoading();
  if (els.blocked) {
    els.blocked.textContent = msg;
    els.blocked.classList.remove("hidden");
  }
  els.main?.classList.add("hidden");
}

function hideLoading() {
  els.loading?.classList.add("hidden");
  els.main?.classList.remove("hidden");
}

if (document.body.classList.contains("play-app")) {
  init().catch((err) => showBlocked(err.message));
}
