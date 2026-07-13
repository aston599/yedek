/**
 * Arena fizik duman testi
 * node scripts/test-arena-physics.js
 */
import Matter from "matter-js";
import { dirname, join } from "path";
import { fileURLToPath, pathToFileURL } from "url";
import { ARENA_PHYSICS_CFG as CFG } from "../public/team-race/arena-physics-config.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const arenaModuleUrl = pathToFileURL(
  join(__dirname, "../public/team-race/arena-physics.js")
).href;

class MockImage {
  set onload(fn) {
    this._fn = fn;
  }
  set src(_v) {
    queueMicrotask(() => this._fn?.());
  }
}
globalThis.window = { Matter, devicePixelRatio: 1, Image: MockImage };
globalThis.Image = MockImage;
globalThis.requestAnimationFrame = () => {};
globalThis.document = {
  createElement: () => ({
    width: 0,
    height: 0,
    getContext: () => ({ imageSmoothingEnabled: true, drawImage: () => {} }),
  }),
};

class MockCanvas {
  constructor() {
    this.width = 400;
    this.height = 600;
    this.style = { width: "400px", height: "600px" };
    this.parentElement = {
      getBoundingClientRect: () => ({ width: 400, height: 600, left: 0, top: 0 }),
    };
  }
  getContext() {
    const noop = () => {};
    return {
      setTransform: noop,
      clearRect: noop,
      save: noop,
      restore: noop,
      translate: noop,
      rotate: noop,
      beginPath: noop,
      arc: noop,
      stroke: noop,
      fill: noop,
      fillText: noop,
      clip: noop,
      closePath: noop,
      drawImage: noop,
    };
  }
}

const results = [];
function ok(name, cond, detail = "") {
  results.push({ name, pass: !!cond, detail });
  console.log(`[${cond ? "OK" : "FAIL"}] ${name}${detail ? ` — ${detail}` : ""}`);
}

function countRingLeaks(arena) {
  let leaks = 0;
  for (const body of arena.bodies.values()) {
    if (body?.plugin?.fallingOut) continue;
    const m = arena._bodyMetrics(body);
    if (m.inGap || arena._mayUseExitGap(body)) continue;
    const limit = arena._ballMaxCenterDist(m.radius);
    if (m.dist > limit + 2) leaks += 1;
  }
  return leaks;
}

function countSevereOverlaps(arena) {
  const bodies = [...arena.bodies.values()].filter((x) => !x?.plugin?.fallingOut);
  let n = 0;
  for (let i = 0; i < bodies.length; i++) {
    for (let j = i + 1; j < bodies.length; j++) {
      const dx = bodies[j].position.x - bodies[i].position.x;
      const dy = bodies[j].position.y - bodies[i].position.y;
      const dist = Math.hypot(dx, dy) || 0.001;
      const minD = (bodies[i].circleRadius || 10) + (bodies[j].circleRadius || 10);
      if (dist < minD * 0.92) n += 1;
    }
  }
  return n;
}

async function main() {
  const { TeamRaceArena } = await import(arenaModuleUrl);
  const eliminated = [];
  const arena = new TeamRaceArena(new MockCanvas(), {
    showExitLabel: false,
    eliminationGraceMs: 0,
    onEliminate: (id) => {
      if (!eliminated.includes(id)) eliminated.push(id);
    },
  });

  arena.layout();
  arena.setEliminationGraceMs(0);

  ok("gathering uses custom gravity", CFG.gathering.gravityAccel >= 500);

  arena.setRoundPhase("chaos");
  arena._chaosEnteredAt = Date.now() - 60_000;
  arena._rebuildWalls();
  ok("chaos ring shells", arena._ringShell.length >= 28, `n=${arena._ringShell.length}`);

  await arena.spawn({ id: "b1", teamCode: "gs", teamName: "GS", displayName: "A" });
  await arena.spawn({ id: "b2", teamCode: "fb", teamName: "FB", displayName: "B" });
  ok("chaos runs matter", arena.bodies.get("b1").isStatic === false);
  arena.kickstartChaos();

  let chaosMax = 0;
  for (let i = 0; i < 40; i++) {
    arena.step();
    for (const body of arena.bodies.values()) {
      chaosMax = Math.max(
        chaosMax,
        Math.hypot(body.velocity.x, body.velocity.y)
      );
    }
  }
  ok("chaos: balls move", chaosMax > 40, `max=${chaosMax.toFixed(2)}`);

  const beforeShock = chaosMax;
  arena.triggerShockWave();
  let afterShock = 0;
  for (let i = 0; i < 18; i++) {
    arena.step();
    for (const body of arena.bodies.values()) {
      afterShock = Math.max(
        afterShock,
        Math.hypot(body.velocity.x, body.velocity.y)
      );
    }
  }
  ok(
    "chaos: shock boosts motion",
    afterShock > 45 || afterShock >= beforeShock * 0.3,
    `before=${beforeShock.toFixed(1)} after=${afterShock.toFixed(1)}`
  );

  arena.clear();
  arena.setRoundPhase("gathering");
  arena._rebuildWalls();
  ok("gathering has no shells", arena._ringShell.length === 0);

  for (let i = 0; i < 80; i++) {
    await arena.spawn({
      id: `g${i}`,
      teamCode: "gs",
      teamName: "GS",
      displayName: `U${i}`,
    });
  }

  let maxSpeed = 0;
  let gatherLeaks = 0;
  for (let frame = 0; frame < 900; frame++) {
    arena.step();
    gatherLeaks = Math.max(gatherLeaks, countRingLeaks(arena));
    for (const body of arena.bodies.values()) {
      maxSpeed = Math.max(maxSpeed, Math.hypot(body.velocity.x, body.velocity.y));
    }
  }

  let resting = 0;
  for (const body of arena.bodies.values()) {
    if (Math.hypot(body.velocity.x, body.velocity.y) < 25) resting += 1;
  }

  const { cy, r } = arena._bounds;
  let maxY = -Infinity;
  for (const ball of arena.bodies.values()) maxY = Math.max(maxY, ball.position.y);

  ok(
    "gathering: speed cap",
    maxSpeed <= CFG.gathering.maxSpeedPx + 35,
    `max=${maxSpeed.toFixed(1)} cap=${CFG.gathering.maxSpeedPx}`
  );
  ok("gathering: resting", resting >= 40, `resting=${resting}/80`);
  ok("gathering: pooled low", maxY > cy + r * 0.1, `maxY=${maxY.toFixed(0)}`);
  ok("gathering: ring leaks", gatherLeaks <= 1, `leaks=${gatherLeaks}`);
  ok("gathering: overlap", countSevereOverlaps(arena) <= 3, `severe=${countSevereOverlaps(arena)}`);

  arena.setRoundPhase("chaos");
  arena._chaosEnteredAt = Date.now() - 60_000;
  arena._rebuildWalls();
  let transitionStatic = 0;
  let transitionSpeed = 0;
  for (const body of arena.bodies.values()) {
    if (body.isStatic) transitionStatic += 1;
    transitionSpeed += Math.hypot(body.velocity.x, body.velocity.y);
  }
  transitionSpeed /= Math.max(1, arena.bodies.size);
  ok("gathering→chaos: dynamic", transitionStatic === 0, `static=${transitionStatic}`);
  ok("gathering→chaos: burst speed", transitionSpeed > 8, `avg=${transitionSpeed.toFixed(1)}`);
  ok("gathering→chaos: shells", arena._ringShell.length >= 28, `n=${arena._ringShell.length}`);

  arena.clear();
  arena.setRoundPhase("gathering");
  for (let i = 0; i < 34; i++) {
    await arena.spawn({
      id: `crowd${i}`,
      teamCode: "gs",
      teamName: "GS",
      displayName: `C${i}`,
    });
  }
  for (let f = 0; f < 200; f++) arena.step();
  arena.forceEnterChaos();
  let crowdNaN = 0;
  let crowdMax = 0;
  for (let f = 0; f < 120; f++) {
    arena.step();
    for (const body of arena.bodies.values()) {
      const vx = body.velocity?.x;
      const vy = body.velocity?.y;
      if (!Number.isFinite(vx) || !Number.isFinite(vy)) crowdNaN += 1;
      else crowdMax = Math.max(crowdMax, Math.hypot(vx, vy));
    }
  }
  ok("34 balls chaos: no NaN velocity", crowdNaN === 0, `nan=${crowdNaN}`);
  ok("34 balls chaos: moves", crowdMax > 30, `max=${crowdMax.toFixed(1)}`);

  ok(
    "chaos: omega spin motor",
    typeof arena._applyChaosOmegaSpin === "function",
    ""
  );
  let tangSum = 0;
  let tangN = 0;
  const dir = CFG.chaos.centerSpinDirection ?? 1;
  for (const body of arena.bodies.values()) {
    if (body?.plugin?.fallingOut) continue;
    const dx = body.position.x - arena._bounds.cx;
    const dy = body.position.y - arena._bounds.cy;
    const dist = Math.hypot(dx, dy) || 1;
    const tx = (-dy / dist) * dir;
    const ty = (dx / dist) * dir;
    const v = arena._finiteVel(body);
    tangSum += Math.abs(v.x * tx + v.y * ty);
    tangN += 1;
  }
  ok(
    "chaos: tangential spin",
    tangN > 0 && tangSum / tangN > 25,
    `avgTang=${(tangSum / Math.max(1, tangN)).toFixed(1)}`
  );

  const passed = results.filter((r) => r.pass).length;
  console.log(`\n${passed}/${results.length} passed`);
  if (passed < results.length) process.exit(1);
  console.log("Arena fizik testi tamam.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
