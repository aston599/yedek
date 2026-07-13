/**
 * Uzun arena koşusu — toplanma + kaos metrikleri.
 * node scripts/benchmark-arena-physics.js
 */
import { createRequire } from "module";
import { fileURLToPath, pathToFileURL } from "url";
import { dirname, join } from "path";

const require = createRequire(import.meta.url);
const __dirname = dirname(fileURLToPath(import.meta.url));
global.window = {
  Matter: require("matter-js"),
  devicePixelRatio: 1,
  requestAnimationFrame: (fn) => setTimeout(fn, 16),
};
global.Image = class {
  constructor() {
    this.onload = null;
    this.onerror = null;
  }
  set src(_v) {
    setTimeout(() => this.onerror?.(), 0);
  }
};

class MockCanvas {
  constructor() {
    this.width = 800;
    this.height = 1200;
    this.style = {};
    this.parentElement = { getBoundingClientRect: () => ({ width: 800, height: 1200 }) };
  }
  getContext() {
    return {
      setTransform() {},
      clearRect() {},
      save() {},
      restore() {},
      translate() {},
      rotate() {},
      beginPath() {},
      arc() {},
      stroke() {},
      fill() {},
      clip() {},
      drawImage() {},
      fillText() {},
      moveTo() {},
      lineTo() {},
      closePath() {},
      fillStyle: "",
      strokeStyle: "",
      shadowBlur: 0,
      font: "",
      textAlign: "",
      lineWidth: 1,
      lineCap: "",
    };
  }
}

const arenaModuleUrl = pathToFileURL(
  join(__dirname, "../public/team-race/arena-physics.js")
).href;

function runStep(arena) {
  const { Matter, engine } = arena;
  if (arena.roundPhase === "gathering") {
    arena._applyGatheringEngineGravity();
  } else if (arena.roundPhase === "chaos") {
    arena._applyChaosGravity();
    arena._applyChaosForces();
  }
  const spin = arena.roundPhase === "chaos" ? 0.0055 : 0;
  if (spin > 0) {
    arena._ringRotation = (arena._ringRotation + spin) % (Math.PI * 2);
    arena._syncWallsToRotation();
  }
  const crowd = arena.bodies.size >= 20;
  const subSteps =
    arena.roundPhase === "chaos" ? (crowd ? 6 : 4) : crowd ? 3 : 2;
  const dt = 1000 / 60 / subSteps;
  for (let s = 0; s < subSteps; s++) Matter.Engine.update(engine, dt);
  if (arena.roundPhase === "gathering") {
    arena._enforceRingCollider();
    arena._relaxOverlaps(2.1);
    arena._dampGatheringAtRest();
    for (const body of arena.bodies.values()) {
      if (!body?.plugin?.fallingOut) arena._clampInsideRing(body);
    }
  } else if (arena.roundPhase === "chaos") {
    arena._separateBallOverlaps?.(3, 0.9);
    for (const body of arena.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      arena._constrainToRing(body);
      arena._assistExitThroughGap(body);
    }
    arena._clampChaosSpeed?.();
  }
}

function avgSpeed(arena) {
  let sum = 0;
  let n = 0;
  for (const body of arena.bodies.values()) {
    if (body?.plugin?.fallingOut) continue;
    sum += Math.hypot(body.velocity.x, body.velocity.y);
    n += 1;
  }
  return n ? sum / n : 0;
}

async function main() {
  const { TeamRaceArena } = await import(arenaModuleUrl);
  const arena = new TeamRaceArena(new MockCanvas(), {
    showExitLabel: false,
    eliminationGraceMs: 0,
    onEliminate: () => {},
  });
  arena.layout();
  arena.setRoundPhase("gathering");
  for (let i = 0; i < 80; i++) {
    await arena.spawn({
      id: `b${i}`,
      teamCode: ["gs", "fb", "bjk", "ts"][i % 4],
      teamName: "T",
      displayName: `U${i}`,
    });
  }
  let gatherSpeedPeak = 0;
  for (let f = 0; f < 360; f++) {
    runStep(arena);
    gatherSpeedPeak = Math.max(gatherSpeedPeak, avgSpeed(arena));
  }
  arena.setRoundPhase("chaos");
  arena.kickstartChaos();
  let chaosSpeedPeak = 0;
  let chaosSpeedSum = 0;
  let chaosFrames = 0;
  for (let f = 0; f < 300; f++) {
    runStep(arena);
    const v = avgSpeed(arena);
    chaosSpeedPeak = Math.max(chaosSpeedPeak, v);
    chaosSpeedSum += v;
    chaosFrames += 1;
  }
  const chaosAvg = chaosSpeedSum / chaosFrames;
  console.log("=== Arena benchmark (80 top) ===");
  console.log(`Toplanma tepe hız: ${gatherSpeedPeak.toFixed(2)}`);
  console.log(`Kaos ortalama hız:   ${chaosAvg.toFixed(2)}`);
  console.log(`Kaos tepe hız:       ${chaosSpeedPeak.toFixed(2)}`);
  console.log(`Kalan top:           ${arena.bodies.size}`);
  if (chaosAvg < 2.5) {
    console.error("UYARI: Kaos ortalama hız düşük — donma riski.");
    process.exit(1);
  }
  console.log("Benchmark tamam.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
