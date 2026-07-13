/**
 * Takım yarışı arena — Matter.js (test edilebilir, tek adım simülasyon)
 */
import { ARENA_PHYSICS_CFG as CFG } from "./arena-physics-config.js";

export { ARENA_PHYSICS_CFG } from "./arena-physics-config.js";

export class TeamRaceArena {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onEliminate = options.onEliminate ?? (() => {});
    this.showExitLabel = options.showExitLabel !== false;
    this.flagCache = new Map();
    this.bodies = new Map();
    this._eliminating = new Set();
    this.running = false;
    this.chaos = false;
    this.roundPhase = "gathering";
    this._ringRotation = 0;
    this._lastWallRotation = NaN;
    this._ringShell = [];
    this._pit = null;
    this._size = { w: 400, h: 600 };
    this._bounds = { cx: 200, cy: 300, r: 150 };
    this._exitAngleBase = options.exitAngle ?? Math.PI / 2;
    this.exitGapRad = options.exitGapRad ?? 0.95;
    this._chaosEnteredAt = 0;
    this._eliminationGraceMs = options.eliminationGraceMs ?? 5000;
    this._shockCooldownMs = 60_000;
    this._nextShockAt = 0;
    this._lastShockProfile = "medium";
    this._outsideRingSince = new Map();
    this._rafId = 0;

    const Matter = window.Matter;
    if (!Matter) throw new Error("Matter.js yüklenmedi");
    this.Matter = Matter;

    this.engine = Matter.Engine.create({ gravity: { x: 0, y: 1, scale: 0.001 } });
    this.engine.positionIterations = CFG.positionIterations;
    this.engine.velocityIterations = CFG.velocityIterations;
    this.engine.constraintIterations = 2;
    this.engine.enableSleeping = true;
    this.world = this.engine.world;

    this._onPitCollision = (evt) => {
      if (this.roundPhase !== "chaos") return;
      for (const pair of evt.pairs) {
        const { bodyA, bodyB } = pair;
        const pit =
          bodyA.label === "exit-pit" ? bodyA : bodyB.label === "exit-pit" ? bodyB : null;
        const ball = pit ? (bodyA.label === "exit-pit" ? bodyB : bodyA) : null;
        if (pit && ball?.plugin?.entityId && !ball.plugin.fallingOut) {
          this._eliminateBody(ball.plugin.entityId, ball);
        }
      }
    };
    Matter.Events.on(this.engine, "collisionStart", this._onPitCollision);
    Matter.Events.on(this.engine, "collisionActive", this._onPitCollision);

    this._resize();
    this._applyPhaseGravity();
    this._rebuildWalls();
  }

  get exitAngle() {
    return this._exitAngleBase + this._ringRotation;
  }

  /** Test ve debug: tek fizik karesi */
  step() {
    this._simulateFrame();
  }

  _resize() {
    const parent = this.canvas.parentElement;
    const rect = parent?.getBoundingClientRect();
    const w = Math.max(320, Math.floor(rect?.width || 400));
    const h = Math.max(420, Math.floor(rect?.height || 600));
    const dpr = Math.min(3, Math.max(1, window.devicePixelRatio || 1));
    this._dpr = dpr;
    this.canvas.width = Math.floor(w * dpr);
    this.canvas.height = Math.floor(h * dpr);
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this._size = { w, h };
    const side = Math.min(w, h);
    this._bounds = { cx: w / 2, cy: h * 0.44, r: side * 0.41 };
  }

  _ringLineWidth() {
    return this.roundPhase === "chaos" ? CFG.ringLineChaos : CFG.ringLineGathering;
  }

  _ringInnerRadius() {
    return this._bounds.r - this._ringLineWidth() * 0.5;
  }

  _ringShellCenterRadius() {
    return this._ringInnerRadius() + CFG.shellRadius;
  }

  _ballRadius(bounds = this._bounds) {
    const r = bounds.r;
    return Math.max(
      CFG.ballRadiusMin,
      Math.min(CFG.ballRadiusMax, r * CFG.ballRadiusFactor)
    );
  }

  _ballMaxCenterDist(radius) {
    return this._ringInnerRadius() - radius;
  }

  _normAngle(a) {
    let x = a;
    while (x > Math.PI) x -= Math.PI * 2;
    while (x < -Math.PI) x += Math.PI * 2;
    return x;
  }

  _angleInExitGap(angle) {
    return Math.abs(this._normAngle(angle - this.exitAngle)) <= this.exitGapRad / 2;
  }

  _bodyNearExitGap(body) {
    const m = this._bodyMetrics(body);
    return Math.abs(this._normAngle(m.angle - this.exitAngle)) <= this.exitGapRad / 2 + 0.14;
  }

  _mayUseExitGap(body) {
    if (this.roundPhase !== "chaos" || body?.plugin?.fallingOut) return false;
    const m = this._bodyMetrics(body);
    if (!m.inGap && !this._bodyNearExitGap(body)) return false;
    const minR = this._bounds.r * (CFG.chaos.exitGapMinDistFactor ?? 0.48);
    return m.pastRim || m.dist > minR;
  }

  _bodyMetrics(body) {
    const b = this._bounds;
    const dx = body.position.x - b.cx;
    const dy = body.position.y - b.cy;
    const dist = Math.hypot(dx, dy) || 1;
    const angle = Math.atan2(dy, dx);
    const { ex, ey } = this._exitDir();
    const radius = body.circleRadius || CFG.ballRadiusMin;
    return {
      dx,
      dy,
      dist,
      angle,
      ex,
      ey,
      radius,
      inGap: this._angleInExitGap(angle),
      outwardVel: (body.velocity?.x || 0) * ex + (body.velocity?.y || 0) * ey,
      pastRim: dist + radius > this._ringInnerRadius() + 1,
      deepOutside: dist + radius > b.r + radius * 0.25,
    };
  }

  _exitDir() {
    return { ex: Math.cos(this.exitAngle), ey: Math.sin(this.exitAngle) };
  }

  _applyPhaseGravity() {
    const { engine } = this;
    engine.gravity.x = 0;
    engine.gravity.y = 1;
    if (this.roundPhase === "chaos") {
      engine.gravity.scale = CFG.chaos.gravityScale ?? 0;
    } else {
      engine.gravity.scale = 0;
    }
  }

  _finiteVel(body) {
    const vx = Number(body?.velocity?.x);
    const vy = Number(body?.velocity?.y);
    return {
      x: Number.isFinite(vx) ? vx : 0,
      y: Number.isFinite(vy) ? vy : 0,
    };
  }

  _sanitizeBodyState(body) {
    const { Matter } = this;
    if (!body) return;
    const b = this._bounds;
    let { x, y } = body.position;
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      x = b.cx;
      y = b.cy;
      Matter.Body.setPosition(body, { x, y });
    }
    const v = this._finiteVel(body);
    Matter.Body.setVelocity(body, v);
    if (!Number.isFinite(body.angularVelocity)) {
      Matter.Body.setAngularVelocity(body, 0);
    }
  }

  _sanitizeAllBodies() {
    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      this._sanitizeBodyState(body);
    }
  }

  /** Kaosa geçiş: topları arena ortasına (köşe / alt yığın kalmaz) */
  _unpackChaosPile() {
    const { Matter } = this;
    const bodies = [...this.bodies.values()].filter((b) => !b?.plugin?.fallingOut);
    const n = bodies.length;
    if (!n) return;
    const { cx, cy, r } = this._bounds;
    const c = CFG.chaos;
    const clusterR = r * (c.unpackRadiusFactor ?? 0.18);

    for (let i = 0; i < n; i++) {
      const body = bodies[i];
      const angle = (i / n) * Math.PI * 2 + (i % 11) * 0.03;
      const dist = clusterR * Math.sqrt((i + 0.5) / n);
      Matter.Body.setPosition(body, {
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
      });
      body.isStatic = false;
      Matter.Sleeping.set(body, false);
      this._applyChaosMaterial(body);
      Matter.Body.setVelocity(body, { x: 0, y: 0 });
    }

    for (let pass = 0; pass < 12; pass++) this._chaosOverlapPass(true);
    this._chaosCenterContain(bodies);
    for (const body of bodies) {
      Matter.Body.setVelocity(body, { x: 0, y: 0 });
      this._sanitizeBodyState(body);
    }
  }

  _chaosCenterHoldRadius() {
    const c = CFG.chaos;
    return this._bounds.r * (c.centerHoldRadiusFactor ?? 0.22);
  }

  /** Topları orta girdap bölgesinde tut */
  _chaosCenterContain(bodies) {
    const { Matter } = this;
    const { cx, cy } = this._bounds;
    const holdR = this._chaosCenterHoldRadius();

    for (const body of bodies) {
      if (body?.plugin?.fallingOut) continue;
      if (this._mayUseExitGap(body)) continue;
      const dx = body.position.x - cx;
      const dy = body.position.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      if (dist <= holdR) continue;
      const s = holdR / dist;
      Matter.Body.setPosition(body, { x: cx + dx * s, y: cy + dy * s });
      const v = this._finiteVel(body);
      const nx = dx / dist;
      const ny = dy / dist;
      const vn = v.x * nx + v.y * ny;
      if (vn > 0) {
        Matter.Body.setVelocity(body, { x: v.x - nx * vn, y: v.y - ny * vn });
      }
    }
  }

  _applyChaosCenterHold(dtSec, bodies) {
    const { Matter } = this;
    const c = CFG.chaos;
    const { cx, cy } = this._bounds;
    const holdR = this._chaosCenterHoldRadius();
    const pullK = c.centerHoldPullPx ?? 520;
    const dt = Math.max(0.001, dtSec);

    for (const body of bodies) {
      if (body?.plugin?.fallingOut) continue;
      if (this._mayUseExitGap(body)) continue;
      const dx = body.position.x - cx;
      const dy = body.position.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      if (dist <= holdR * 0.85) continue;
      const nx = dx / dist;
      const ny = dy / dist;
      const v = this._finiteVel(body);
      const outward = v.x * nx + v.y * ny;
      const pull = (dist - holdR) * pullK * dt;
      Matter.Body.setVelocity(body, {
        x: v.x - nx * (pull + Math.max(0, outward) * 0.55),
        y: v.y - ny * (pull + Math.max(0, outward) * 0.55),
      });
    }
  }

  _chaosWarmActive() {
    const c = CFG.chaos;
    const ms = c.chaosWarmupMs ?? 2800;
    return this._chaosEnteredAt && Date.now() - this._chaosEnteredAt < ms;
  }

  _chaosEffectiveRestitution() {
    const c = CFG.chaos;
    return this._chaosWarmActive() ? (c.chaosWarmRestitution ?? 0.34) : (c.ballRestitution ?? 0.52);
  }

  _chaosEffectiveMaxSpeed() {
    const c = CFG.chaos;
    return this._chaosWarmActive() ? (c.chaosWarmMaxSpeedPx ?? 200) : (c.maxSpeedPx ?? 340);
  }

  _phaseCfg(phase = this.roundPhase) {
    return phase === "chaos" ? CFG.chaos : CFG.gathering;
  }

  _setGatheringKinematic(body) {
    const { Matter } = this;
    body.isStatic = true;
    body.isSensor = false;
    Matter.Body.setAngularVelocity(body, 0);
    Matter.Sleeping.set(body, true);
  }

  _applyChaosMaterial(body) {
    const { Matter } = this;
    body.isStatic = false;
    body.isSensor = false;
    body.sleepThreshold = Infinity;
    Matter.Sleeping.set(body, false);
  }

  _capSpeedPx(maxPx) {
    const { Matter } = this;
    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      const v = this._finiteVel(body);
      const sp = Math.hypot(v.x, v.y);
      if (sp <= maxPx) continue;
      const s = maxPx / sp;
      Matter.Body.setVelocity(body, { x: v.x * s, y: v.y * s });
    }
  }

  _capSpeed(max) {
    this._capSpeedPx(max);
  }

  _pickGatheringSpawn(bounds, radius, index) {
    const g = CFG.gathering;
    const spread = (index % 14) / 14;
    const x =
      bounds.cx + (spread - 0.5) * bounds.r * 0.28 + (Math.random() - 0.5) * radius * 0.8;
    const y = bounds.cy - bounds.r * g.spawnDropYFactor + (Math.random() - 0.5) * radius * 0.4;
    return {
      x,
      y,
      vx: (Math.random() - 0.5) * g.spawnVxPx,
      vy: g.spawnVyPx * (0.4 + Math.random() * 0.6),
    };
  }

  _constrainBallToRing(body, phase = this.roundPhase) {
    if (phase === "chaos") {
      if (this._mayUseExitGap(body)) return;
      const m = this._bodyMetrics(body);
      if (m.inGap) return;
    }
    const { Matter } = this;
    const b = this._bounds;
    const radius = body.circleRadius || CFG.ballRadiusMin;
    const limit = this._ballMaxCenterDist(radius);
    const dx = body.position.x - b.cx;
    const dy = body.position.y - b.cy;
    const dist = Math.hypot(dx, dy) || 1;
    if (dist <= limit) return;
    const s = limit / dist;
    const nx = dx / dist;
    const ny = dy / dist;
    Matter.Body.setPosition(body, { x: b.cx + dx * s, y: b.cy + dy * s });
    const v = this._finiteVel(body);
    const vn = v.x * nx + v.y * ny;
    if (vn > 0) {
      Matter.Body.setVelocity(body, { x: v.x - nx * vn, y: v.y - ny * vn });
    }
  }

  /** Girdap Lab — Yapay ω×r (preserveRadial=false: saf teğet; true: çarpışma radyali korunur) */
  _applyChaosOmegaSpin(opts = {}) {
    const preserveRadial = opts.preserveRadial !== false;
    const { Matter } = this;
    const c = CFG.chaos;
    const omega = c.centerSpinRadPerSec ?? 2;
    const dir = c.centerSpinDirection ?? 1;
    const rf = c.centerSpinRadiusFactor ?? 0.44;
    const blend = c.centerSpinBlend ?? 0.38;
    const { cx, cy } = this._bounds;

    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      if (this._mayUseExitGap(body)) continue;
      const dx = body.position.x - cx;
      const dy = body.position.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      const rx = dx / dist;
      const ry = dy / dist;
      const tx = -ry * dir;
      const ty = rx * dir;
      const ringR = this._bounds.r;
      const holdR = this._chaosCenterHoldRadius();
      const minR = ringR * (c.centerSpinMinRadiusFactor ?? 0.12);
      const target = omega * Math.max(dist * rf, minR);
      const edge = Math.min(1, dist / Math.max(holdR, 1));
      const spinBlend = blend * (1.1 - edge * 0.85);
      const v = this._finiteVel(body);
      const curTang = v.x * tx + v.y * ty;
      const tang = curTang + (target - curTang) * spinBlend;

      if (!preserveRadial) {
        Matter.Body.setVelocity(body, { x: tx * tang, y: ty * tang });
      } else {
        const radial = v.x * rx + v.y * ry;
        let outR = radial;
        if (dist > holdR && outR > 0) outR *= 0.2;
        Matter.Body.setVelocity(body, {
          x: rx * outR + tx * tang,
          y: ry * outR + ty * tang,
        });
      }
      Matter.Body.setAngularVelocity(body, 0);
    }
  }

  _chaosUsesShellCollisions() {
    return (CFG.chaos.shellSpinTransfer ?? 0) > 0;
  }

  _chaosExitPull(dtSec) {
    const { Matter } = this;
    const c = CFG.chaos;
    const b = this._bounds;
    const dt = Math.max(0.001, dtSec);
    const pastGrace =
      this._chaosEnteredAt && Date.now() - this._chaosEnteredAt >= this._eliminationGraceMs;
    const exitPull = pastGrace ? (c.exitAccelPx ?? 130) * dt : 0;
    if (exitPull <= 0) return;
    const { ex, ey } = this._exitDir();
    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      const m = this._bodyMetrics(body);
      if (!this._bodyNearExitGap(body) || m.dist < b.r * 0.32) continue;
      const v = this._finiteVel(body);
      Matter.Body.setVelocity(body, { x: v.x + ex * exitPull, y: v.y + ey * exitPull });
    }
  }

  /**
   * Kaos = Girdap Lab Yapay ω×r:
   * ω (saf) → top–top → sürtünme/hareket/sınır → top–top → ω (radyal koru) → merkez
   */
  _chaosOmegaCircleStep(dtSec) {
    const { Matter } = this;
    const g = CFG.chaos;
    const bodies = [...this.bodies.values()].filter((b) => !b?.plugin?.fallingOut);
    if (!bodies.length) return;

    const dt = Math.min(0.05, Math.max(0.001, dtSec));
    const damp = Math.exp(-(g.airDragPerSec ?? 0.22) * dt);
    const rest = this._chaosEffectiveRestitution();
    const iters = g.collisionIterations ?? 7;
    const shellHits = this._chaosUsesShellCollisions();

    this._chaosExitPull(dt);
    this._applyChaosOmegaSpin({ preserveRadial: false });

    for (let pass = 0; pass < Math.min(7, iters); pass++) {
      this._resolveBallBallCollisions(bodies, rest, "chaos");
    }

    this._applyChaosCenterHold(dt, bodies);

    for (const body of bodies) {
      const v = this._finiteVel(body);
      Matter.Body.setVelocity(body, { x: v.x * damp, y: v.y * damp });
    }

    for (const body of bodies) {
      const v = this._finiteVel(body);
      Matter.Body.setPosition(body, {
        x: body.position.x + v.x * dt,
        y: body.position.y + v.y * dt,
      });
      this._constrainBallToRing(body, "chaos");
    }

    if (shellHits) this._resolveChaosShellCollisions();

    for (let pass = 0; pass < Math.min(6, iters); pass++) {
      this._resolveBallBallCollisions(bodies, rest, "chaos");
      if (shellHits) this._resolveChaosShellCollisions();
    }

    this._applyChaosOmegaSpin({ preserveRadial: true });
    this._chaosCenterContain(bodies);
    this._capSpeedPx(this._chaosEffectiveMaxSpeed());
    this._sanitizeAllBodies();

    for (const body of bodies) {
      Matter.Body.setAngularVelocity(body, 0);
      body.isStatic = false;
    }
  }

  _stepFallingBodies(dtSec) {
    const { Matter } = this;
    const dt = Math.min(0.05, Math.max(0.001, dtSec));
    const g = 720;
    const { ex, ey } = this._exitDir();
    for (const body of this.bodies.values()) {
      if (!body?.plugin?.fallingOut) continue;
      const v = this._finiteVel(body);
      Matter.Body.setVelocity(body, {
        x: v.x + ex * 40 * dt,
        y: v.y + g * dt + ey * 50 * dt,
      });
      Matter.Body.setPosition(body, {
        x: body.position.x + body.velocity.x * dt,
        y: body.position.y + body.velocity.y * dt,
      });
    }
  }

  _resolveBallBallCollisions(bodies, rest, phase) {
    const { Matter } = this;
    for (let i = 0; i < bodies.length; i++) {
      for (let j = i + 1; j < bodies.length; j++) {
        const a = bodies[i];
        const c = bodies[j];
        const ra = a.circleRadius || 10;
        const rc = c.circleRadius || 10;
        const dx = c.position.x - a.position.x;
        const dy = c.position.y - a.position.y;
        const dist = Math.hypot(dx, dy) || 0.0001;
        const minDist = ra + rc;
        if (dist >= minDist) continue;

        const nx = dx / dist;
        const ny = dy / dist;
        const overlap = minDist - dist;
        const half = overlap * 0.5;
        Matter.Body.setPosition(a, {
          x: a.position.x - nx * half,
          y: a.position.y - ny * half,
        });
        Matter.Body.setPosition(c, {
          x: c.position.x + nx * half,
          y: c.position.y + ny * half,
        });

        const va = this._finiteVel(a);
        const vc = this._finiteVel(c);
        const relN = (vc.x - va.x) * nx + (vc.y - va.y) * ny;
        if (relN >= 0) continue;
        const impulse = (-(1 + rest) * relN) / 2;
        Matter.Body.setVelocity(a, {
          x: va.x - nx * impulse,
          y: va.y - ny * impulse,
        });
        Matter.Body.setVelocity(c, {
          x: vc.x + nx * impulse,
          y: vc.y + ny * impulse,
        });
      }
    }
    for (const body of bodies) this._constrainBallToRing(body, phase);
  }

  /**
   * Toplanma + kaos: aynı özel daire fiziği (px/s).
   * Kaos: dönen segment duvar + çıkış boşluğu.
   */
  _customCircleStep(dtSec, phase = this.roundPhase) {
    if (phase === "chaos") {
      this._chaosOmegaCircleStep(dtSec);
      return;
    }

    const { Matter } = this;
    const g = this._phaseCfg(phase);
    const bodies = [...this.bodies.values()].filter((b) => !b?.plugin?.fallingOut);
    if (!bodies.length) return;

    const dt = Math.min(0.05, Math.max(0.001, dtSec));
    const damp = Math.exp(-(g.airDragPerSec ?? 0.5) * dt);
    const grav = g.gravityAccel ?? 600;

    for (const body of bodies) {
      const v = this._finiteVel(body);
      Matter.Body.setVelocity(body, {
        x: v.x * damp,
        y: (v.y + grav * dt) * damp,
      });
    }

    for (const body of bodies) {
      const v = this._finiteVel(body);
      Matter.Body.setPosition(body, {
        x: body.position.x + v.x * dt,
        y: body.position.y + v.y * dt,
      });
      this._constrainBallToRing(body, phase);
    }

    const rest = g.ballRestitution ?? 0.1;
    const iters = g.collisionIterations ?? 5;
    for (let pass = 0; pass < iters; pass++) {
      this._resolveBallBallCollisions(bodies, rest, phase);
    }

    this._capSpeedPx(g.maxSpeedPx ?? 300);
    this._sanitizeAllBodies();

    {
      for (const body of bodies) {
        const v = this._finiteVel(body);
        const sp = Math.hypot(v.x, v.y);
        if (sp < 45) {
          const s = sp < (g.sleepSpeedPx ?? 8) ? 0 : 0.82;
          Matter.Body.setVelocity(body, { x: v.x * s, y: v.y * s });
        }
        Matter.Body.setAngularVelocity(body, 0);
        this._setGatheringKinematic(body);
      }
    }
  }

  _rebuildWalls() {
    const { Matter, world } = this;
    for (const w of this._ringShell) Matter.World.remove(world, w);
    if (this._pit) Matter.World.remove(world, this._pit);
    this._ringShell = [];
    this._pit = null;

    const { cx, cy, r } = this._bounds;
    const exitOpen = this.roundPhase === "chaos";
    const ringR = this._ringShellCenterRadius();
    if (exitOpen) {
      for (let i = 0; i < CFG.shellCount; i++) {
        const angle = this._ringRotation + (i / CFG.shellCount) * Math.PI * 2;
        if (this._angleInExitGap(angle)) continue;
        this._ringShell.push(
          Matter.Bodies.circle(cx + Math.cos(angle) * ringR, cy + Math.sin(angle) * ringR, CFG.shellRadius, {
            isStatic: true,
            isSensor: true,
            label: "ring-shell",
          })
        );
      }
    }

    if (exitOpen) {
      const mouthR = Math.max(18, r * 0.2);
      const mouthDist = r + mouthR * 0.5;
      this._pit = Matter.Bodies.circle(
        cx + Math.cos(this.exitAngle) * mouthDist,
        cy + Math.sin(this.exitAngle) * mouthDist,
        mouthR,
        { isStatic: true, isSensor: true, label: "exit-pit", friction: 0, slop: 0.01 }
      );
      Matter.World.add(world, [...this._ringShell, this._pit]);
    }
  }

  _syncRotatingWalls() {
    if (this.roundPhase !== "chaos") return;
    const { Matter } = this;
    const { cx, cy } = this._bounds;
    const ringR = this._ringShellCenterRadius();
    let si = 0;
    for (let i = 0; i < CFG.shellCount; i++) {
      const angle = this._ringRotation + (i / CFG.shellCount) * Math.PI * 2;
      if (this._angleInExitGap(angle)) continue;
      const w = this._ringShell[si++];
      if (!w) break;
      Matter.Body.setPosition(w, {
        x: cx + Math.cos(angle) * ringR,
        y: cy + Math.sin(angle) * ringR,
      });
    }
    if (this._pit) {
      const mouthR = Math.max(18, this._bounds.r * 0.2);
      const mouthDist = this._bounds.r + mouthR * 0.65;
      Matter.Body.setPosition(this._pit, {
        x: cx + Math.cos(this.exitAngle) * mouthDist,
        y: cy + Math.sin(this.exitAngle) * mouthDist,
      });
    }
    this._lastWallRotation = this._ringRotation;
  }

  _enterChaosMotion() {
    const { Matter } = this;
    const b = this._bounds;
    const c = CFG.chaos;
    const omega = c.centerSpinRadPerSec ?? 2;
    const rf = c.centerSpinRadiusFactor ?? 0.44;
    const dir = c.centerSpinDirection ?? 1;
    const blend = c.enterSpinBlend ?? 1;
    const minR = b.r * (c.centerSpinMinRadiusFactor ?? 0.12);

    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      body.isStatic = false;
      Matter.Sleeping.set(body, false);
      this._applyChaosMaterial(body);
      const dx = body.position.x - b.cx;
      const dy = body.position.y - b.cy;
      const dist = Math.hypot(dx, dy) || 1;
      const tx = (-dy / dist) * dir;
      const ty = (dx / dist) * dir;
      const targetTang = omega * Math.max(dist * rf, minR);
      Matter.Body.setVelocity(body, {
        x: tx * targetTang * blend,
        y: ty * targetTang * blend,
      });
      Matter.Body.setAngularVelocity(body, 0);
    }
  }

  _resolveChaosShellCollisions() {
    const { Matter } = this;
    if (!this._ringShell.length) return;
    const c = CFG.chaos;
    const shellR = CFG.shellRadius;
    const { cx, cy } = this._bounds;
    const ringR = this._ringShellCenterRadius();
    const spin = c.ringSpinRadPerSec ?? (c.ringSpin ?? 0.0065) * 60;
    const wallSpeed = spin * ringR;
    const transfer = c.shellSpinTransfer ?? 0.38;
    const extra = c.shellPushExtra ?? 0.35;
    const rest = c.ballRestitution ?? 0.28;
    const bodies = [...this.bodies.values()].filter((b) => !b?.plugin?.fallingOut);

    for (const body of bodies) {
      const br = body.circleRadius || CFG.ballRadiusMin;
      const m = this._bodyMetrics(body);
      if (this._mayUseExitGap(body)) continue;
      for (const shell of this._ringShell) {
        const dx = body.position.x - shell.position.x;
        const dy = body.position.y - shell.position.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const minD = br + shellR;
        if (dist >= minD) continue;
        const nx = dx / dist;
        const ny = dy / dist;
        const push = minD - dist + extra;
        Matter.Body.setPosition(body, {
          x: body.position.x + nx * push,
          y: body.position.y + ny * push,
        });
        const sa = Math.atan2(shell.position.y - cy, shell.position.x - cx);
        const tx = -Math.sin(sa);
        const ty = Math.cos(sa);
        const v = this._finiteVel(body);
        const vn = v.x * nx + v.y * ny;
        let vx = v.x;
        let vy = v.y;
        if (vn < 0) {
          vx -= nx * vn * (1 + rest);
          vy -= ny * vn * (1 + rest);
        }
        const holdR = this._chaosCenterHoldRadius();
        const m = this._bodyMetrics(body);
        const wallMul = m.dist > holdR * 1.35 ? 0.35 : 1;
        vx += tx * wallSpeed * transfer * wallMul;
        vy += ty * wallSpeed * transfer * wallMul;
        Matter.Body.setVelocity(body, { x: vx, y: vy });
      }
      this._constrainBallToRing(body, "chaos");
    }
  }

  _assistExitThroughGap(body) {
    if (!this._mayUseExitGap(body)) return;
    const { Matter } = this;
    const m = this._bodyMetrics(body);
    const { ex, ey } = this._exitDir();
    const c = CFG.chaos;
    const v = this._finiteVel(body);
    const sp = Math.hypot(v.x, v.y);
    const boost = c.exitRimBoostPx ?? 95;
    if (m.pastRim && m.outwardVel < boost * 0.6) {
      Matter.Body.setVelocity(body, { x: v.x + ex * boost, y: v.y + ey * (boost + 25) });
    } else if (sp < 55 && m.dist > this._bounds.r * 0.48) {
      Matter.Body.setVelocity(body, { x: v.x + ex * boost * 0.65, y: v.y + ey * boost * 0.8 });
    }
  }

  /** Kaos: periyodik şok (sunucu tetiklemezse yerel geri sayım) */
  _maybeAutoChaosShock() {
    const c = CFG.chaos;
    const interval = c.autoShockIntervalMs ?? 20_000;
    if (!interval || interval < 5000) return;
    if (!this._nextShockAt || Date.now() < this._nextShockAt) return;
    this._triggerShockWave();
    this._nextShockAt = Date.now() + interval;
  }

  _triggerShockWave(intensity = null) {
    if (this.roundPhase !== "chaos") return;
    const { Matter } = this;
    const b = this._bounds;
    const c = CFG.chaos;
    const add = intensity === "add";
    const burstBase = c.shockBurstPx ?? c.shockBurst ?? 200;
    const burst =
      intensity === "heavy"
        ? burstBase * 1.35
        : intensity === "add"
          ? burstBase * 0.55
          : burstBase;
    const exitBoost = c.shockExitBoostPx ?? c.shockExitBoost ?? 100;
    const { ex, ey } = this._exitDir();
    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      const dx = body.position.x - b.cx;
      const dy = body.position.y - b.cy;
      const dist = Math.hypot(dx, dy) || 1;
      const nx = dx / dist;
      const ny = dy / dist;
      const tx = -ny;
      const ty = nx;
      const swirl = (Math.random() - 0.5) * burst * 0.65;
      const ix = nx * burst * 0.38 + tx * swirl + ex * exitBoost;
      const iy = ny * burst * 0.38 + ty * swirl + ey * (exitBoost + 40);
      const v = this._finiteVel(body);
      Matter.Body.setVelocity(body, {
        x: add ? v.x + ix : ix,
        y: add ? v.y + iy : iy,
      });
      Matter.Body.setAngularVelocity(body, (Math.random() - 0.5) * 0.5);
    }
  }

  /** Kaos: çakışma düzeltmesi */
  _chaosOverlapPass(strong = false) {
    const { Matter } = this;
    const bodies = [...this.bodies.values()].filter((b) => !b?.plugin?.fallingOut);
    const n = bodies.length;
    if (n < 2) return;

    const cap = strong ? 6 : 2.2;
    const gain = strong ? 0.62 : 0.5;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = bodies[i];
        const c = bodies[j];
        const ra = a.circleRadius || 10;
        const rc = c.circleRadius || 10;
        const dx = c.position.x - a.position.x;
        const dy = c.position.y - a.position.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const minDist = ra + rc + (strong ? 1.2 : 0.15);
        if (dist >= minDist) continue;
        const push = Math.min(cap, (minDist - dist) * gain);
        const nx = dx / dist;
        const ny = dy / dist;
        Matter.Body.setPosition(a, { x: a.position.x - nx * push * 0.5, y: a.position.y - ny * push * 0.5 });
        Matter.Body.setPosition(c, { x: c.position.x + nx * push * 0.5, y: c.position.y + ny * push * 0.5 });
      }
    }
  }

  _clampGlitchOutsideRing() {
    if (this.roundPhase !== "chaos") return;
    for (const [id, body] of this.bodies) {
      if (!body || body.plugin?.fallingOut || this._mayUseExitGap(body)) continue;
      const m = this._bodyMetrics(body);
      if (m.deepOutside && !m.inGap) this._eliminateBody(id, body);
    }
  }

  _checkEliminations() {
    if (this.roundPhase !== "chaos") return;
    if (this._chaosEnteredAt && Date.now() - this._chaosEnteredAt < this._eliminationGraceMs) return;
    const now = Date.now();
    for (const [id, body] of this.bodies) {
      if (!body || body.plugin?.fallingOut) continue;
      const m = this._bodyMetrics(body);
      if (this._bodyNearExitGap(body) && m.pastRim) {
        this._eliminateBody(id, body);
        continue;
      }
      if (this._pit && m.inGap) {
        const pdx = body.position.x - this._pit.position.x;
        const pdy = body.position.y - this._pit.position.y;
        const pr = this._pit.circleRadius || 18;
        if (Math.hypot(pdx, pdy) < m.radius + pr * 0.85) {
          this._eliminateBody(id, body);
          continue;
        }
      }
      if (!m.inGap && m.deepOutside) {
        if (!this._outsideRingSince.has(id)) this._outsideRingSince.set(id, now);
        else if (now - (this._outsideRingSince.get(id) || now) > 120) {
          this._eliminateBody(id, body);
        }
      } else {
        this._outsideRingSince.delete(id);
      }
    }
  }

  _eliminateBody(id, body) {
    if (this.roundPhase !== "chaos" || this._eliminating.has(id)) return;
    this._eliminating.add(id);
    if (body && this.bodies.has(id)) {
      body.plugin = body.plugin || {};
      body.plugin.fallingOut = true;
      const { ex, ey } = this._exitDir();
      body.collisionFilter = { mask: 0, group: -1, category: body.collisionFilter?.category ?? 2 };
      this.Matter.Body.setVelocity(body, {
        x: ex * 5.5 + (Math.random() - 0.5) * 1.2,
        y: ey * 6.5 + 2,
      });
    }
    this.onEliminate(id);
    this._outsideRingSince.delete(id);
    setTimeout(() => this._eliminating.delete(id), 400);
  }

  _cleanupFallingOut() {
    const { Matter } = this;
    const b = this._bounds;
    for (const [id, body] of this.bodies) {
      if (!body?.plugin?.fallingOut) continue;
      if (
        body.position.y > this._size.h + 80 ||
        Math.hypot(body.position.x - b.cx, body.position.y - b.cy) > b.r * 1.6
      ) {
        Matter.World.remove(this.world, body);
        this.bodies.delete(id);
      }
    }
  }

  _simulateFrame() {
    const { Matter, engine } = this;

    const dtSec = CFG.stepMs / 1000;

    if (this.roundPhase === "gathering") {
      this._customCircleStep(dtSec, "gathering");
      return;
    }

    const c = CFG.chaos;
    this._applyPhaseGravity();
    const spin = c.ringSpinRadPerSec ?? (c.ringSpin ?? 0.0065) * 60;
    this._ringRotation = (this._ringRotation + spin * dtSec) % (Math.PI * 2);
    this._syncRotatingWalls();
    this._customCircleStep(dtSec, "chaos");
    this._maybeAutoChaosShock();

    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      this._assistExitThroughGap(body);
    }
    this._stepFallingBodies(dtSec);
    this._checkEliminations();
    this._clampGlitchOutsideRing();
    this._cleanupFallingOut();
  }

  /** circle-lab: CFG değişince motor + duvar + topları güncelle */
  syncPhysicsConfig() {
    const { engine } = this;
    engine.positionIterations = CFG.positionIterations;
    engine.velocityIterations = CFG.velocityIterations;
    this._applyPhaseGravity();
    for (const body of this.bodies.values()) {
      if (body?.plugin?.fallingOut) continue;
      if (this.roundPhase === "gathering") this._setGatheringKinematic(body);
      else this._applyChaosMaterial(body);
    }
    this._lastWallRotation = NaN;
    this._rebuildWalls();
  }

  layout() {
    this._resize();
    this._rebuildWalls();
    this._lastWallRotation = this._ringRotation;
  }

  start() {
    if (this.running && this._rafId) return;
    this.running = true;
    this.layout();
    this._tick();
  }

  stop() {
    this.running = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = 0;
    }
  }

  _tick() {
    if (!this.running) return;
    this._simulateFrame();
    this._draw();
    this._rafId = requestAnimationFrame(() => this._tick());
  }

  setChaos(on) {
    this.chaos = Boolean(on);
  }

  setEliminationGraceMs(ms) {
    this._eliminationGraceMs = Math.max(1000, Number(ms) || 5000);
  }

  getShockCountdownSec() {
    if (this.roundPhase !== "chaos" || !this._nextShockAt) return null;
    return Math.max(0, Math.ceil((this._nextShockAt - Date.now()) / 1000));
  }

  triggerShockWave() {
    if (this.roundPhase !== "chaos") return false;
    this._triggerShockWave();
    const interval = CFG.chaos.autoShockIntervalMs ?? 20_000;
    this._nextShockAt = Date.now() + interval;
    return true;
  }

  /** UI / test: kaosa geç — ani dağılma/şok yok, girdap devam */
  forceEnterChaos() {
    if (this.bodies.size === 0) return false;
    if (!this.running && typeof this.ctx?.clip === "function") this.start();
    const wasChaos = this.roundPhase === "chaos";
    this.setRoundPhase("chaos", { force: wasChaos });
    return true;
  }

  setRoundPhase(phase, opts = {}) {
    const force = Boolean(opts.force);
    const next = phase === "chaos" ? "chaos" : "gathering";
    if (this.roundPhase === next && !force) return;
    const wasGathering = this.roundPhase === "gathering";
    const enteringChaos =
      next === "chaos" && (wasGathering || (force && this.roundPhase === "chaos"));
    this.roundPhase = next;
    this.chaos = next === "chaos";
    this.engine.enableSleeping = next === "gathering";

    for (const body of this.bodies.values()) {
      if (next === "chaos") {
        body.isStatic = false;
        this.Matter.Sleeping.set(body, false);
        this._applyChaosMaterial(body);
      } else {
        this._setGatheringKinematic(body);
      }
    }

    if (enteringChaos) {
      const c = CFG.chaos;
      this._chaosEnteredAt = Date.now();
      if (!force || wasGathering) this._ringRotation = Math.PI;
      const shockIn = c.autoShockIntervalMs ?? 20_000;
      this._nextShockAt = Date.now() + shockIn;
      this._unpackChaosPile();
      this._enterChaosMotion();
      this._sanitizeAllBodies();
    } else {
      this._chaosEnteredAt = 0;
      this._nextShockAt = 0;
      this._outsideRingSince.clear();
    }

    this._applyPhaseGravity();
    this._lastWallRotation = NaN;
    this._rebuildWalls();
  }

  kickstartChaos() {
    if (this.roundPhase !== "chaos") return;
    this._enterChaosMotion();
  }

  clear() {
    const { Matter, world } = this;
    for (const body of this.bodies.values()) Matter.World.remove(world, body);
    this.bodies.clear();
    this._eliminating.clear();
    this._outsideRingSince.clear();
  }

  async spawn(entity) {
    const { Matter, world } = this;
    const bounds = this._bounds;
    const radius = this._ballRadius(bounds);
    let x;
    let y;
    let vx;
    let vy;

    if (this.roundPhase === "gathering") {
      ({ x, y, vx, vy } = this._pickGatheringSpawn(bounds, radius, this.bodies.size));
    } else {
      const c = CFG.chaos;
      const angle = Math.random() * Math.PI * 2;
      const dist = bounds.r * (0.25 + Math.random() * 0.35);
      x = bounds.cx + Math.cos(angle) * dist;
      y = bounds.cy + Math.sin(angle) * dist;
      vx = (Math.random() - 0.5) * (c.spawnVxPx ?? 40);
      vy = (Math.random() - 0.5) * (c.spawnVyPx ?? 38);
    }

    const gathering = this.roundPhase === "gathering";
    const body = Matter.Bodies.circle(x, y, radius, {
      restitution: 0.1,
      friction: 0.2,
      frictionStatic: 0.25,
      frictionAir: 0.02,
      density: 0.002,
      slop: 0.01,
      label: entity.id,
      isStatic: gathering,
      sleepThreshold: gathering ? 60 : Infinity,
      collisionFilter: { category: 0x0002, mask: 0xffffffff, group: 0 },
    });

    Matter.Body.setVelocity(body, { x: vx, y: vy });
    body.plugin = {
      entityId: entity.id,
      teamCode: entity.teamCode,
      teamName: entity.teamName || entity.teamCode,
      flagUrl: entity.flagUrl || `/team-race/flags/${entity.teamCode}.png`,
      displayName: entity.displayName,
    };

    Matter.World.add(world, body);
    this.bodies.set(entity.id, body);
    if (gathering) this._setGatheringKinematic(body);
    else this._applyChaosMaterial(body);
    await this._loadFlag(body.plugin.flagUrl);
  }

  async _loadFlag(url) {
    if (this.flagCache.has(url)) return this.flagCache.get(url);
    const img = new Image();
    const p = new Promise((resolve) => {
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
    });
    img.decoding = "async";
    img.src = url;
    const entry = { img: await p, spritePx: 0, sprite: null };
    this.flagCache.set(url, entry);
    return entry;
  }

  _flagSprite(entry, cssRadius) {
    if (!entry?.img) return null;
    const dpr = this._dpr || 1;
    const px = Math.max(48, Math.ceil(cssRadius * 2.05 * dpr));
    if (entry.sprite && entry.spritePx === px) return entry.sprite;
    const { img } = entry;
    const iw = img.naturalWidth || img.width || 1;
    const ih = img.naturalHeight || img.height || 1;
    const ar = iw / ih;
    let dw = px;
    let dh = px;
    if (ar > 1) dh = Math.round(px / ar);
    else if (ar < 1) dw = Math.round(px * ar);
    const canvas = document.createElement("canvas");
    canvas.width = px;
    canvas.height = px;
    const sctx = canvas.getContext("2d");
    sctx.imageSmoothingEnabled = true;
    sctx.drawImage(img, (px - dw) / 2, (px - dh) / 2, dw, dh);
    entry.spritePx = px;
    entry.sprite = canvas;
    return canvas;
  }

  _drawArenaRing(ctx, bounds) {
    const { cx, cy, r } = bounds;
    const chaos = this.roundPhase === "chaos";
    const gapHalf = this.exitGapRad / 2;
    ctx.save();
    ctx.translate(cx, cy);
    if (chaos) ctx.rotate(this._ringRotation);
    ctx.strokeStyle = chaos ? "rgba(255, 107, 138, 0.95)" : "rgba(125, 255, 192, 0.9)";
    ctx.lineWidth = this._ringLineWidth();
    ctx.lineCap = "round";
    ctx.beginPath();
    if (chaos) {
      ctx.arc(0, 0, r, this._exitAngleBase + gapHalf, this._exitAngleBase - gapHalf + Math.PI * 2);
    } else {
      ctx.arc(0, 0, r, 0, Math.PI * 2);
    }
    ctx.stroke();
    if (chaos) {
      const swirlR = r * 0.38;
      ctx.strokeStyle = "rgba(255, 107, 138, 0.22)";
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 14]);
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.arc(0, 0, swirlR, i * 0.9, i * 0.9 + Math.PI * 0.85);
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    ctx.restore();
  }

  _draw() {
    const { ctx } = this;
    const bounds = this._bounds;
    ctx.clearRect(0, 0, this._size.w, this._size.h);
    this._drawArenaRing(ctx, bounds);

    if (this.showExitLabel || this.roundPhase === "chaos") {
      ctx.textAlign = "center";
      ctx.font = "800 13px Segoe UI, sans-serif";
      ctx.fillStyle = this.roundPhase === "chaos" ? "#ff6b8a" : "#7dffc0";
      ctx.fillText(
        this.roundPhase === "chaos" ? "KAOS — çıkış açık" : "TOPLANMA",
        bounds.cx,
        bounds.cy + bounds.r + 40
      );
      if (this.roundPhase === "chaos") {
        const { ex, ey } = this._exitDir();
        const tipX = bounds.cx + ex * (bounds.r + 28);
        const tipY = bounds.cy + ey * (bounds.r + 28);
        ctx.fillStyle = "rgba(255, 107, 138, 0.9)";
        ctx.font = "700 11px Segoe UI, sans-serif";
        ctx.fillText("▼ ÇIKIŞ", tipX, tipY);
      }
    }

    for (const body of this.bodies.values()) {
      const { x, y } = body.position;
      const drawR = body.circleRadius;
      const entry = this.flagCache.get(body.plugin.flagUrl);
      ctx.save();
      ctx.translate(x, y);
      if (this.roundPhase === "chaos") ctx.rotate(body.angle);
      ctx.beginPath();
      ctx.arc(0, 0, drawR + 1, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(0, 0, drawR - 0.5, 0, Math.PI * 2);
      ctx.clip();
      const sprite = entry ? this._flagSprite(entry, drawR) : null;
      if (sprite) ctx.drawImage(sprite, -drawR, -drawR, drawR * 2, drawR * 2);
      else {
        ctx.fillStyle = "#7c5cff";
        ctx.arc(0, 0, drawR * 0.9, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(0, 0, drawR, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }
  }

  countByTeam() {
    const counts = {};
    for (const body of this.bodies.values()) {
      const c = body.plugin.teamCode;
      counts[c] = (counts[c] || 0) + 1;
    }
    return counts;
  }
}
