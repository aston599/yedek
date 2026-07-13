/**
 * Kalibrasyon — tüm arena öğelerini doldurur + canlı fizik önizlemesi
 */
import {
  applyCalSlotLabels,
  clearLayoutOverviewDemo,
  fillLayoutOverviewDemo,
} from "./play-layout-overview.js?v=1";
import { initArenaCmdBand } from "/team-race/arena-cmd-band.js?v=1";

const DEMO_TEAMS = [
  { code: "gs", name: "Galatasaray" },
  { code: "fb", name: "Fenerbahçe" },
  { code: "bjk", name: "Beşiktaş" },
  { code: "ts", name: "Trabzonspor" },
];

let active = false;
let spawnTimer = null;
let flashTimer = null;
let spawnSeq = 0;
let getArenaRef = () => null;
let onTeardown = null;

function $(id) {
  return document.getElementById(id);
}

function teamFlagUrl(code) {
  return `/team-race/flags/${code}.png`;
}

function teamFlagImg(code, size = "sm", alt = "") {
  return `<img class="team-flag team-flag--${size}" src="${teamFlagUrl(code)}" alt="${alt || code}" width="24" height="24" />`;
}

function fillStaticPreview() {
  document.body.classList.add("play-layout-overview");
  fillLayoutOverviewDemo({
    teamFlagImg,
    teamFlagUrl: (code) => `/team-race/flags/${code}.png`,
    initArenaCmdBand,
  });
}

function clearStaticPreview() {
  document.body.classList.remove("play-layout-overview");
  clearLayoutOverviewDemo();
  $("phaseBanner")?.classList.remove("is-cal-preview", "is-chaos", "is-gathering");
  document.querySelectorAll(".is-cal-preview").forEach((el) => {
    el.classList.remove("is-cal-preview", "is-live");
  });
  $("arenaBadge")?.classList.remove("is-running");
  $("winnerCard")?.classList.add("hidden");
  const flash = $("elimFlash");
  if (flash) {
    flash.textContent = "";
    flash.classList.remove("is-visible", "is-flash");
  }
}

async function spawnDemoBall(arena) {
  const t = DEMO_TEAMS[spawnSeq++ % DEMO_TEAMS.length];
  const id = `cal-${spawnSeq}`;
  await arena.spawn({
    id,
    teamCode: t.code,
    teamName: t.name,
    flagUrl: teamFlagUrl(t.code),
    displayName: `Demo${spawnSeq}`,
  });
}

async function seedArena(arena) {
  arena.clear();
  arena.layout();
  arena.setRoundPhase("chaos");
  arena.setChaos(true);
  for (let i = 0; i < 7; i++) {
    await spawnDemoBall(arena);
  }
  arena.kickstartChaos();
}

export function startCalibrationLivePreview(options = {}) {
  if (active) return;
  active = true;
  getArenaRef = options.getArena || (() => null);
  onTeardown = options.onTeardown || null;
  document.body.classList.add("play-cal-preview-on");
  fillStaticPreview();

  const arena = getArenaRef();
  if (arena) {
    seedArena(arena).catch(() => {});
    spawnTimer = setInterval(() => {
      const a = getArenaRef();
      if (!a || !active) return;
      if (a.bodies.size < 14) spawnDemoBall(a).catch(() => {});
    }, 2400);

    flashTimer = setInterval(() => {
      const flash = $("elimFlash");
      if (!flash || !active) return;
      const t = DEMO_TEAMS[Math.floor(Math.random() * DEMO_TEAMS.length)];
      flash.textContent = `${t.name} elendi!`;
      flash.classList.add("is-visible");
      setTimeout(() => flash.classList.remove("is-visible"), 1200);
    }, 4500);
  }
}

export function stopCalibrationLivePreview() {
  if (!active) return;
  active = false;
  if (spawnTimer) clearInterval(spawnTimer);
  if (flashTimer) clearInterval(flashTimer);
  spawnTimer = null;
  flashTimer = null;

  document.body.classList.remove("play-cal-preview-on");
  clearStaticPreview();

  const arena = getArenaRef();
  if (arena) {
    arena.clear();
    arena.setRoundPhase("gathering");
    arena.setChaos(false);
  }

  onTeardown?.();
  onTeardown = null;
}

export function isCalibrationPreviewActive() {
  return active;
}
