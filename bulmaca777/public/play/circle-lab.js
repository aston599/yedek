/**
 * Circle Lab — sadece arena top/halka fizik test ekranı
 */
import { TeamRaceArena } from "/team-race/arena-physics.js?v=81";
import {
  ARENA_PHYSICS_CFG,
  resetArenaPhysicsConfig,
} from "/team-race/arena-physics-config.js";
import { FALLBACK_TEAMS } from "/team-race/teams-data.js";

const $ = (id) => document.getElementById(id);

let arena = null;
let running = true;
let spawnSeq = 0;
let statsTimer = null;

const TEAMS = FALLBACK_TEAMS.slice(0, 12);

function currentPhase() {
  return document.querySelector('input[name="phase"]:checked')?.value || "gathering";
}

function setLabHint(msg) {
  const el = $("labHint");
  if (el) el.textContent = msg;
  else console.warn("[circle-lab]", msg);
}

function syncPhaseUi() {
  const phase = arena?.roundPhase || currentPhase();
  const label = $("ringLabel");
  const wrap = document.querySelector(".circle-lab-arena");
  if (label) label.textContent = phase === "chaos" ? "KAOS" : "TOPLANMA";
  if (wrap) wrap.dataset.phase = phase;
  $("statPhase").textContent = phase;
}

function readSlidersIntoCfg() {
  const g = ARENA_PHYSICS_CFG.gathering;
  const c = ARENA_PHYSICS_CFG.chaos;
  g.gravityAccel = Number($("cfgGravity").value);
  g.maxSpeedPx = Number($("cfgMaxSpeed").value);
  g.ballRestitution = Number($("cfgRestitution").value);
  ARENA_PHYSICS_CFG.shellCount = Number($("cfgShellCount").value);
  ARENA_PHYSICS_CFG.ballRadiusFactor = Number($("cfgBallFactor").value);
  c.gravityAccel = 0;
  c.ringSpinRadPerSec = Number($("cfgRingSpin")?.value ?? c.ringSpinRadPerSec);
  c.centerSpinRadPerSec = Number($("cfgCenterSpin")?.value ?? c.centerSpinRadPerSec);
  c.shockBurstPx = Number($("cfgShockBurst")?.value ?? c.shockBurstPx) * 30;
  $("outGravity").textContent = String(g.gravityAccel);
  $("outMaxSpeed").textContent = String(g.maxSpeedPx);
  $("outRestitution").textContent = g.ballRestitution.toFixed(2);
  $("outShellCount").textContent = String(ARENA_PHYSICS_CFG.shellCount);
  $("outBallFactor").textContent = ARENA_PHYSICS_CFG.ballRadiusFactor.toFixed(3);
  if ($("outRingSpin")) $("outRingSpin").textContent = (c.ringSpinRadPerSec ?? 0.58).toFixed(2);
  if ($("outCenterSpin")) $("outCenterSpin").textContent = (c.centerSpinRadPerSec ?? 2).toFixed(2);
  if ($("outShockBurst")) $("outShockBurst").textContent = String(Math.round((c.shockBurstPx ?? 240) / 30));
}

function slidersFromCfg() {
  const g = ARENA_PHYSICS_CFG.gathering;
  const c = ARENA_PHYSICS_CFG.chaos;
  $("cfgGravity").value = g.gravityAccel;
  $("cfgMaxSpeed").value = g.maxSpeedPx;
  $("cfgRestitution").value = g.ballRestitution;
  $("cfgShellCount").value = ARENA_PHYSICS_CFG.shellCount;
  $("cfgBallFactor").value = ARENA_PHYSICS_CFG.ballRadiusFactor;
  if ($("cfgRingSpin")) $("cfgRingSpin").value = c.ringSpinRadPerSec ?? 0.58;
  if ($("cfgCenterSpin")) $("cfgCenterSpin").value = c.centerSpinRadPerSec ?? 2;
  if ($("cfgShockBurst")) $("cfgShockBurst").value = Math.round((c.shockBurstPx ?? 240) / 30);
  readSlidersIntoCfg();
}

function countLeaks() {
  if (!arena) return 0;
  let n = 0;
  for (const body of arena.bodies.values()) {
    if (body?.plugin?.fallingOut) continue;
    const m = arena._bodyMetrics(body);
    if (m.inGap || arena._mayUseExitGap(body)) continue;
    const limit = arena._ballMaxCenterDist(m.radius);
    if (m.dist > limit + 3) n += 1;
  }
  return n;
}

function countSevereOverlaps() {
  if (!arena) return 0;
  const bodies = [...arena.bodies.values()].filter((b) => !b?.plugin?.fallingOut);
  let n = 0;
  for (let i = 0; i < bodies.length; i++) {
    for (let j = i + 1; j < bodies.length; j++) {
      const dx = bodies[j].position.x - bodies[i].position.x;
      const dy = bodies[j].position.y - bodies[i].position.y;
      const dist = Math.hypot(dx, dy) || 0.001;
      const minD =
        (bodies[i].circleRadius || 10) + (bodies[j].circleRadius || 10) + 0.5;
      if (dist < minD * 0.78) n += 1;
    }
  }
  return n;
}

function updateStats() {
  if (!arena) return;
  const bodies = [...arena.bodies.values()].filter((b) => !b?.plugin?.fallingOut);
  let sum = 0;
  let max = 0;
  let resting = 0;
  let maxY = -Infinity;
  const { cy, r } = arena._bounds;

  for (const b of bodies) {
    const vx = Number(b.velocity?.x);
    const vy = Number(b.velocity?.y);
    const sp = Number.isFinite(vx) && Number.isFinite(vy) ? Math.hypot(vx, vy) : 0;
    sum += sp;
    max = Math.max(max, sp);
    if (sp < 18) resting += 1;
    maxY = Math.max(maxY, b.position.y);
  }

  $("statCount").textContent = String(bodies.length);
  $("statAvgSpd").textContent = bodies.length ? (sum / bodies.length).toFixed(2) : "0";
  $("statMaxSpd").textContent = max.toFixed(2);
  $("statResting").textContent = `${resting}/${bodies.length}`;
  $("statLeaks").textContent = String(countLeaks());
  $("statOverlap").textContent = String(countSevereOverlaps());
  $("statPoolY").textContent =
    bodies.length && maxY > -Infinity
      ? `${maxY.toFixed(0)} (Δ${(maxY - cy).toFixed(0)})`
      : "—";
  syncPhaseUi();
}

async function spawnBall(teamCode = null) {
  const team =
    TEAMS.find((t) => t.code === teamCode) ||
    TEAMS[spawnSeq++ % TEAMS.length];
  const id = `lab-${Date.now()}-${spawnSeq}`;
  await arena.spawn({
    id,
    teamCode: team.code,
    teamName: team.name,
    flagUrl: team.flagUrl,
    displayName: `Test ${spawnSeq}`,
  });
  updateStats();
}

async function spawnMany(n) {
  for (let i = 0; i < n; i++) {
    await spawnBall(TEAMS[i % TEAMS.length].code);
  }
}

function applyConfig() {
  readSlidersIntoCfg();
  arena.syncPhysicsConfig();
  updateStats();
}

function setPhase(phase) {
  const radio = document.querySelector(`input[name="phase"][value="${phase}"]`);
  if (radio) radio.checked = true;
  if (phase === "chaos") {
    if (arena.bodies.size) arena.forceEnterChaos();
    else arena.setRoundPhase("chaos");
    arena._chaosEnteredAt = Date.now() - arena._eliminationGraceMs - 1000;
  } else {
    arena.setRoundPhase("gathering");
    arena.setChaos(false);
  }
  syncPhaseUi();
}

function buildTeamButtons() {
  const root = $("teamButtons");
  if (!root) return;
  root.innerHTML = "";
  for (const t of TEAMS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cl-team";
    btn.title = t.name;
    btn.style.backgroundImage = `url(${t.flagUrl})`;
    btn.addEventListener("click", () => spawnBall(t.code));
    root.appendChild(btn);
  }
}

function wireControls() {
  $("btnRun").addEventListener("click", () => {
    running = true;
    if (!arena.running) arena.start();
  });

  $("btnPause").addEventListener("click", () => {
    running = false;
    arena.stop();
  });

  $("btnStep").addEventListener("click", () => {
    arena.step();
    arena._draw();
    updateStats();
  });

  document.querySelectorAll('input[name="phase"]').forEach((el) => {
    el.addEventListener("change", () => setPhase(el.value));
  });

  $("btnChaosNow").addEventListener("click", () => {
    if (!arena.bodies.size) {
      setLabHint("Önce en az 1 top ekleyin (+1 / +10 / +80).");
      return;
    }
    if (!running) {
      running = true;
      arena.start();
    }
    const radio = document.querySelector('input[name="phase"][value="chaos"]');
    if (radio) radio.checked = true;
    if (!arena.forceEnterChaos()) {
      setLabHint("Kaosa geçilemedi — top yok.");
      return;
    }
    for (let i = 0; i < 3; i++) arena.step();
    setLabHint(`Kaos aktif — ${arena.bodies.size} top, ort. hız kontrol panelinde`);
    syncPhaseUi();
    updateStats();
  });

  $("btnShock").addEventListener("click", () => {
    if (!arena.bodies.size) {
      setLabHint("Şok için önce top ekleyin.");
      return;
    }
    if (arena.roundPhase !== "chaos") arena.forceEnterChaos();
    if (!arena.triggerShockWave()) {
      setLabHint("Şok yalnızca kaos fazında.");
      return;
    }
    setLabHint("Şok dalgası uygulandı.");
    syncPhaseUi();
    updateStats();
  });

  $("btnSpawn1").addEventListener("click", () => spawnBall());
  $("btnSpawn10").addEventListener("click", () => spawnMany(10));
  $("btnSpawn80").addEventListener("click", () => spawnMany(80));

  $("btnClear").addEventListener("click", () => {
    arena.clear();
    arena.layout();
    updateStats();
  });

  $("btnApplyCfg").addEventListener("click", applyConfig);

  $("btnResetCfg").addEventListener("click", () => {
    resetArenaPhysicsConfig();
    slidersFromCfg();
    arena.syncPhysicsConfig();
    updateStats();
  });

  $("btnCopyCfg").addEventListener("click", async () => {
    readSlidersIntoCfg();
    const json = JSON.stringify(ARENA_PHYSICS_CFG, null, 2);
    try {
      await navigator.clipboard.writeText(json);
      $("btnCopyCfg").textContent = "Kopyalandı ✓";
      setTimeout(() => {
        $("btnCopyCfg").textContent = "JSON kopyala";
      }, 1500);
    } catch {
      prompt("Arena CFG:", json);
    }
  });

  for (const id of [
    "cfgGravity",
    "cfgMaxSpeed",
    "cfgRestitution",
    "cfgShellCount",
    "cfgBallFactor",
    "cfgRingSpin",
    "cfgCenterSpin",
    "cfgShockBurst",
  ]) {
    $(id)?.addEventListener("input", readSlidersIntoCfg);
  }

  window.addEventListener("resize", () => {
    arena.layout();
    arena._draw();
  });
}

function init() {
  const canvas = $("arenaCanvas");
  if (!canvas || !window.Matter) {
    document.body.innerHTML = "<p style='color:#fff;padding:2rem'>Matter.js yüklenemedi.</p>";
    return;
  }

  arena = new TeamRaceArena(canvas, {
    showExitLabel: true,
    eliminationGraceMs: 1500,
    onEliminate: (id) => {
      console.log("[circle-lab] eliminate", id);
      updateStats();
    },
  });

  arena.layout();
  arena.setRoundPhase("gathering");
  arena.setChaos(false);
  arena.start();

  slidersFromCfg();
  buildTeamButtons();
  wireControls();
  syncPhaseUi();

  statsTimer = setInterval(() => {
    if (running) updateStats();
  }, 250);

  updateStats();
}

init();
