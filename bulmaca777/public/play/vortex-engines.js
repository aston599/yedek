/**
 * Girdap test motorları — farklı teknolojiler / stiller.
 * Sadece daire arena + dönen halka + top–top etkileşimi.
 */

const TAU = Math.PI * 2;
const DT = 1 / 60;

export const VORTEX_CATALOG = [
  {
    id: "production",
    name: "Üretim (arena-physics)",
    tech: "Matter.js + ω×r",
    hint: "Canlı oyun = Girdap Lab Yapay ω×r (halka görsel, ortada döner).",
    async: true,
  },
  {
    id: "contact-push",
    name: "Top–top itiş (özel)",
    tech: "Saf JS · Euler · normal itme",
    hint: "game.exe hedefi: yapay ω yok, sadece çarpışma itişi + halka.",
  },
  {
    id: "matter-native",
    name: "Matter tam motor",
    tech: "Matter.Engine.update",
    hint: "Yerçekimi kapalı; Matter çarpışması + dönen duvar segmentleri.",
  },
  {
    id: "omega-target",
    name: "Yapay ω×r",
    tech: "Saf JS · hız hedefi",
    hint: "Ortada ω×r döner; halka sadece görsel — toplar duvara kapılmaz.",
  },
  {
    id: "tangent-force",
    name: "Teğet kuvvet (pymunk)",
    tech: "Matter · applyForce",
    hint: "game.exe backup: küçük sürekli teğet kuvvet + çarpışma.",
  },
  {
    id: "verlet-repulse",
    name: "Verlet + itme",
    tech: "Saf JS · Verlet",
    hint: "Matter yok; konum tabanlı çift itme, halka sınırı.",
  },
  {
    id: "density-vortex",
    name: "Yoğunluk basıncı",
    tech: "Saf JS · SPH-lite",
    hint: "Merkezde sıkışan topa basınç — girdap hissi yoğunluktan.",
  },
  {
    id: "velocity-field",
    name: "Dönen hız alanı",
    tech: "Saf JS · alan + çarpışma",
    hint: "Analitik girdap alanı + top çarpışması (genelde yapay).",
  },
  {
    id: "ring-only",
    name: "Sadece halka",
    tech: "Saf JS · min itiş",
    hint: "Zayıf top–top; hareket çoğunlukla dönen duvardan.",
  },
  {
    id: "hybrid-game",
    name: "Hibrit (itiş + hafif ω)",
    tech: "Saf JS · karma",
    hint: "İtiş + düşük teğet kuvvet — game.exe tahmini karışım.",
  },
];

const HUES = [0, 28, 200, 280, 120, 45, 310, 170];

export function arenaBounds(w, h) {
  const side = Math.min(w, h);
  return { cx: w / 2, cy: h * 0.44, r: side * 0.41, w, h };
}

function ballRadius(bounds) {
  return Math.max(10, Math.min(14, bounds.r * 0.042));
}

function spawnDisk(n, bounds, ringInner) {
  const br = ballRadius(bounds);
  const spread = bounds.r * 0.34;
  const balls = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU + Math.random() * 0.3;
    const d = spread * Math.sqrt(Math.random());
    balls.push({
      x: bounds.cx + Math.cos(a) * d,
      y: bounds.cy + Math.sin(a) * d * 0.88,
      vx: 0,
      vy: 0,
      r: br,
      hue: HUES[i % HUES.length],
      px: 0,
      py: 0,
    });
  }
  return balls;
}

/** Orta girdap testi — sıkı disk (köşeye dağılmaz) */
function spawnCenterCluster(n, bounds) {
  const br = ballRadius(bounds);
  const clusterR = bounds.r * 0.18;
  const balls = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU + (i % 9) * 0.04;
    const d = clusterR * Math.sqrt((i + 0.5) / n);
    balls.push({
      x: bounds.cx + Math.cos(a) * d,
      y: bounds.cy + Math.sin(a) * d,
      vx: 0,
      vy: 0,
      r: br,
      hue: HUES[i % HUES.length],
    });
  }
  for (let pass = 0; pass < 10; pass++) {
    for (let i = 0; i < balls.length; i++) {
      for (let j = i + 1; j < balls.length; j++) {
        const a = balls[i];
        const b = balls[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const minD = a.r + b.r;
        if (dist >= minD) continue;
        const nx = dx / dist;
        const ny = dy / dist;
        const half = (minD - dist) * 0.5;
        a.x -= nx * half;
        a.y -= ny * half;
        b.x += nx * half;
        b.y += ny * half;
      }
    }
  }
  return balls;
}

function centerHoldR(bounds, params) {
  return bounds.r * (params.centerHoldRadiusFactor ?? 0.22);
}

function centerContainBalls(balls, bounds, params) {
  const { cx, cy } = bounds;
  const holdR = centerHoldR(bounds, params);
  for (const b of balls) {
    const dx = b.x - cx;
    const dy = b.y - cy;
    const dist = Math.hypot(dx, dy) || 1;
    if (dist <= holdR) continue;
    const s = holdR / dist;
    b.x = cx + dx * s;
    b.y = cy + dy * s;
    const nx = dx / dist;
    const ny = dy / dist;
    const vn = b.vx * nx + b.vy * ny;
    if (vn > 0) {
      b.vx -= nx * vn;
      b.vy -= ny * vn;
    }
  }
}

function centerHoldVelocity(balls, bounds, params, dt) {
  const { cx, cy } = bounds;
  const holdR = centerHoldR(bounds, params);
  const pullK = params.centerHoldPullPx ?? 480;
  for (const b of balls) {
    const dx = b.x - cx;
    const dy = b.y - cy;
    const dist = Math.hypot(dx, dy) || 1;
    if (dist <= holdR * 0.9) continue;
    const nx = dx / dist;
    const ny = dy / dist;
    const outward = b.vx * nx + b.vy * ny;
    const pull = (dist - holdR) * pullK * dt;
    b.vx -= nx * (pull + Math.max(0, outward) * 0.5);
    b.vy -= ny * (pull + Math.max(0, outward) * 0.5);
  }
}

function finite(v) {
  return Number.isFinite(v) ? v : 0;
}

function resolveBallBall(balls, rest, iters = 6) {
  for (let pass = 0; pass < iters; pass++) {
    for (let i = 0; i < balls.length; i++) {
      for (let j = i + 1; j < balls.length; j++) {
        const a = balls[i];
        const b = balls[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const minD = a.r + b.r;
        if (dist >= minD) continue;
        const nx = dx / dist;
        const ny = dy / dist;
        const overlap = minD - dist;
        const half = overlap * 0.5;
        a.x -= nx * half;
        a.y -= ny * half;
        b.x += nx * half;
        b.y += ny * half;
        const relN = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny;
        if (relN >= 0) continue;
        const imp = (-(1 + rest) * relN) / 2;
        a.vx -= nx * imp;
        a.vy -= ny * imp;
        b.vx += nx * imp;
        b.vy += ny * imp;
      }
    }
  }
}

function constrainRing(b, bounds, limitR) {
  const dx = b.x - bounds.cx;
  const dy = b.y - bounds.cy;
  const dist = Math.hypot(dx, dy) || 1;
  if (dist <= limitR) return;
  const s = limitR / dist;
  b.x = bounds.cx + dx * s;
  b.y = bounds.cy + dy * s;
  const vn = (b.vx * dx + b.vy * dy) / dist;
  if (vn > 0) {
    const nx = dx / dist;
    const ny = dy / dist;
    b.vx -= nx * vn;
    b.vy -= ny * vn;
  }
}

function shellPositions(bounds, ringR, shellCount, ringAngle, gapRad = 0.95) {
  const gapHalf = gapRad / 2;
  const pts = [];
  for (let i = 0; i < shellCount; i++) {
    const a = ringAngle + (i / shellCount) * TAU;
    let da = a - Math.PI / 2;
    while (da > Math.PI) da -= TAU;
    while (da < -Math.PI) da += TAU;
    if (Math.abs(da) < gapHalf) continue;
    pts.push({
      x: bounds.cx + Math.cos(a) * ringR,
      y: bounds.cy + Math.sin(a) * ringR,
      a,
    });
  }
  return pts;
}

function resolveShells(balls, shells, params, bounds = null) {
  const shellR = params.shellRadius ?? 8;
  const transfer = params.shellTransfer ?? 0.55;
  const extra = params.shellExtra ?? 0.55;
  const rest = params.restitution ?? 0.45;
  const wallSpeed = (params.ringSpin ?? 0.55) * (params.ringR ?? 150);
  const holdR = bounds ? centerHoldR(bounds, params) : Infinity;

  for (const b of balls) {
    let wallMul = 1;
    if (bounds) {
      const dist = Math.hypot(b.x - bounds.cx, b.y - bounds.cy);
      if (dist > holdR * 1.25) wallMul = 0.15;
    }
    for (const sh of shells) {
      const dx = b.x - sh.x;
      const dy = b.y - sh.y;
      const dist = Math.hypot(dx, dy) || 0.001;
      const minD = b.r + shellR;
      if (dist >= minD) continue;
      const nx = dx / dist;
      const ny = dy / dist;
      const push = minD - dist + extra;
      b.x += nx * push;
      b.y += ny * push;
      const vn = b.vx * nx + b.vy * ny;
      if (vn < 0) {
        b.vx -= nx * vn * (1 + rest);
        b.vy -= ny * vn * (1 + rest);
      }
      const tx = -Math.sin(sh.a);
      const ty = Math.cos(sh.a);
      b.vx += tx * wallSpeed * transfer * wallMul;
      b.vy += ty * wallSpeed * transfer * wallMul;
    }
  }
}

function contactPushPass(balls, pushPx, cushion = 1.04, dt = DT) {
  for (let i = 0; i < balls.length; i++) {
    for (let j = i + 1; j < balls.length; j++) {
      const a = balls[i];
      const b = balls[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.hypot(dx, dy) || 0.001;
      const minD = (a.r + b.r) * cushion;
      if (dist >= minD) continue;
      const nx = dx / dist;
      const ny = dy / dist;
      const overlap = minD - dist;
      const half = overlap * 0.52;
      a.x -= nx * half;
      a.y -= ny * half;
      b.x += nx * half;
      b.y += ny * half;
      const relN = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny;
      const sep = pushPx * dt + Math.max(0, -relN) * 1.45;
      const imp = sep * 0.5;
      a.vx -= nx * imp;
      a.vy -= ny * imp;
      b.vx += nx * imp;
      b.vy += ny * imp;
    }
  }
}

function capSpeed(balls, maxPx) {
  for (const b of balls) {
    const sp = Math.hypot(b.vx, b.vy);
    if (sp <= maxPx) continue;
    const s = maxPx / sp;
    b.vx *= s;
    b.vy *= s;
  }
}

function computeStats(balls, bounds, params) {
  const floorY = bounds.cy + bounds.r * (params.floorZone ?? 0.38);
  let sum = 0;
  let max = 0;
  let tang = 0;
  let floor = 0;
  let overlap = 0;
  const dir = 1;
  for (let i = 0; i < balls.length; i++) {
    const b = balls[i];
    const sp = Math.hypot(b.vx, b.vy);
    sum += sp;
    max = Math.max(max, sp);
    if (b.y > floorY) floor += 1;
    const dx = b.x - bounds.cx;
    const dy = b.y - bounds.cy;
    const d = Math.hypot(dx, dy) || 1;
    tang += Math.abs((b.vx * -dy + b.vy * dx) / d) * dir;
    for (let j = i + 1; j < balls.length; j++) {
      const o = balls[j];
      const dist = Math.hypot(o.x - b.x, o.y - b.y);
      if (dist < (b.r + o.r) * 0.88) overlap += 1;
    }
  }
  const n = Math.max(1, balls.length);
  return {
    count: balls.length,
    avgSpeed: sum / n,
    maxSpeed: max,
    avgTangential: tang / n,
    onFloor: floor,
    overlaps: overlap,
  };
}

function drawScene(ctx, bounds, balls, ringAngle, label) {
  const { cx, cy, r } = bounds;
  const ringR = r - 3;
  ctx.clearRect(0, 0, bounds.w, bounds.h);
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, ringR, 0, TAU);
  ctx.strokeStyle = "rgba(255, 120, 200, 0.85)";
  ctx.lineWidth = 6;
  ctx.stroke();
  const gapHalf = 0.95 / 2;
  const ex = ringAngle + Math.PI / 2;
  ctx.setLineDash([10, 8]);
  ctx.beginPath();
  ctx.arc(cx, cy, ringR, ex - gapHalf, ex + gapHalf);
  ctx.strokeStyle = "rgba(120, 255, 180, 0.9)";
  ctx.lineWidth = 4;
  ctx.stroke();
  ctx.setLineDash([]);
  for (const b of balls) {
    ctx.beginPath();
    ctx.arc(b.x, b.y, b.r, 0, TAU);
    ctx.fillStyle = `hsl(${b.hue} 70% 52%)`;
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.35)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(255,255,255,0.75)";
  ctx.font = "600 13px system-ui,sans-serif";
  ctx.fillText(label, 14, 24);
  ctx.restore();
}

/** Ortak saf JS girdap tabanı */
class BaseVortexEngine {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.params = {
      ringSpin: 0.58,
      contactPush: 260,
      omega: 1.6,
      tangentForce: 0.00012,
      densityK: 420,
      fieldStrength: 1.2,
      restitution: 0.48,
      airDrag: 0.14,
      maxSpeed: 360,
      shellCount: 36,
      shellRadius: 8,
      shellTransfer: 0.55,
      shellExtra: 0.55,
      floorZone: 0.38,
      ballCount: 34,
    };
    this.balls = [];
    this.ringAngle = Math.PI;
    this.bounds = arenaBounds(400, 600);
    this._running = false;
    this._raf = 0;
    this.styleId = "base";
    this.styleName = "Base";
  }

  layout() {
    const parent = this.canvas.parentElement;
    const rect = parent?.getBoundingClientRect();
    const w = Math.max(320, Math.floor(rect?.width || 400));
    const h = Math.max(420, Math.floor(rect?.height || 600));
    const dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
    this.canvas.width = Math.floor(w * dpr);
    this.canvas.height = Math.floor(h * dpr);
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.bounds = arenaBounds(w, h);
  }

  setParams(p) {
    Object.assign(this.params, p);
  }

  clear() {
    this.balls = [];
  }

  spawn(n = this.params.ballCount) {
    const inner = this.bounds.r - 6 - ballRadius(this.bounds);
    this.balls = spawnDisk(n, this.bounds, inner);
    this.kickstart();
  }

  kickstart() {
    for (const b of this.balls) {
      const dx = b.x - this.bounds.cx;
      const dy = b.y - this.bounds.cy;
      const dist = Math.hypot(dx, dy) || 1;
      const nx = dx / dist;
      const ny = dy / dist;
      const tx = -ny;
      const ty = nx;
      const k = 80 + Math.random() * 140;
      b.vx = tx * k * 0.45 + nx * (40 + Math.random() * 60);
      b.vy = ty * k * 0.45 + ny * (40 + Math.random() * 60) - 30;
    }
  }

  getStats() {
    return computeStats(this.balls, this.bounds, this.params);
  }

  start() {
    if (this._running) return;
    this._running = true;
    this.layout();
    const loop = () => {
      if (!this._running) return;
      this.step();
      this.draw();
      this._raf = requestAnimationFrame(loop);
    };
    loop();
  }

  stop() {
    this._running = false;
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
  }

  step() {
    this._stepImpl();
  }

  draw() {
    drawScene(this.ctx, this.bounds, this.balls, this.ringAngle, this.styleName);
  }

  _ringStep() {
    this.ringAngle = (this.ringAngle + this.params.ringSpin * DT) % TAU;
  }

  _commonIntegrate(gravityY = 0) {
    const drag = Math.exp(-this.params.airDrag * DT);
    const limit = this.bounds.r - 6 - ballRadius(this.bounds);
    const ringR = this.bounds.r - 3 + (this.params.shellRadius ?? 8) * 0.5;
    const shells = shellPositions(
      this.bounds,
      ringR,
      this.params.shellCount,
      this.ringAngle
    );
    this._ringStep();

    for (const b of this.balls) {
      b.vy += gravityY * DT;
      b.vx *= drag;
      b.vy *= drag;
      b.x += b.vx * DT;
      b.y += b.vy * DT;
      constrainRing(b, this.bounds, limit);
    }
    resolveShells(
      this.balls,
      shells,
      { ...this.params, ringR },
      this.bounds
    );
    capSpeed(this.balls, this.params.maxSpeed);
  }
}

class ContactPushEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "contact-push";
    this.styleName = "Top–top itiş";
  }
  _stepImpl() {
    resolveBallBall(this.balls, this.params.restitution, 7);
    contactPushPass(this.balls, this.params.contactPush);
    this._commonIntegrate(0);
    resolveBallBall(this.balls, this.params.restitution, 5);
    contactPushPass(this.balls, this.params.contactPush * 0.85);
    const floorY = this.bounds.cy + this.bounds.r * this.params.floorZone;
    for (const b of this.balls) {
      if (b.y > floorY) b.vy -= 800 * DT;
    }
  }
}

class OmegaEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "omega-target";
    this.styleName = "Yapay ω×r";
    this.params.omega = 2;
    this.params.restitution = 0.42;
    this.params.airDrag = 0.22;
    this.params.shellTransfer = 0;
    this.params.maxSpeed = 280;
    this.params.centerHoldRadiusFactor = 0.22;
    this.params.centerHoldPullPx = 480;
  }

  spawn(n = this.params.ballCount) {
    this.balls = spawnCenterCluster(n, this.bounds);
    this.kickstart();
  }

  kickstart() {
    const omega = this.params.omega ?? 2;
    const { cx, cy, r } = this.bounds;
    const minR = r * 0.12;
    for (const b of this.balls) {
      const dx = b.x - cx;
      const dy = b.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      const tx = -dy / dist;
      const ty = dx / dist;
      const tang = omega * Math.max(dist * 0.44, minR);
      b.vx = tx * tang;
      b.vy = ty * tang;
    }
  }

  _applyOmegaSpin(preserveRadial = true) {
    const omega = this.params.omega ?? 2;
    const { cx, cy, r } = this.bounds;
    const holdR = centerHoldR(this.bounds, this.params);
    const blend = 0.38;
    const minR = r * 0.12;

    for (const b of this.balls) {
      const dx = b.x - cx;
      const dy = b.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      const rx = dx / dist;
      const ry = dy / dist;
      const tx = -ry;
      const ty = rx;
      const edge = Math.min(1, dist / Math.max(holdR, 1));
      const spinBlend = blend * (1.1 - edge * 0.85);
      const target = omega * Math.max(dist * 0.44, minR);
      const curTang = b.vx * tx + b.vy * ty;
      const tang = curTang + (target - curTang) * spinBlend;

      if (!preserveRadial) {
        b.vx = tx * tang;
        b.vy = ty * tang;
      } else {
        const radial = b.vx * rx + b.vy * ry;
        let outR = radial;
        if (dist > holdR && outR > 0) outR *= 0.2;
        b.vx = rx * outR + tx * tang;
        b.vy = ry * outR + ty * tang;
      }
    }
  }

  _stepImpl() {
    this._applyOmegaSpin(false);
    resolveBallBall(this.balls, this.params.restitution, 7);

    const drag = Math.exp(-this.params.airDrag * DT);
    const limit = this.bounds.r - 6 - ballRadius(this.bounds);
    this._ringStep();
    centerHoldVelocity(this.balls, this.bounds, this.params, DT);

    for (const b of this.balls) {
      b.vx *= drag;
      b.vy *= drag;
      b.x += b.vx * DT;
      b.y += b.vy * DT;
      constrainRing(b, this.bounds, limit);
    }
    resolveBallBall(this.balls, this.params.restitution, 6);
    this._applyOmegaSpin(true);
    centerContainBalls(this.balls, this.bounds, this.params);
    capSpeed(this.balls, this.params.maxSpeed);
  }
}

class VerletEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "verlet-repulse";
    this.styleName = "Verlet + itme";
  }
  kickstart() {
    super.kickstart();
    for (const b of this.balls) {
      b.px = b.x - b.vx * DT;
      b.py = b.y - b.vy * DT;
    }
  }
  spawn(n) {
    super.spawn(n);
    for (const b of this.balls) {
      b.px = b.x - b.vx * DT;
      b.py = b.y - b.vy * DT;
    }
  }
  _stepImpl() {
    const push = this.params.contactPush * 0.9;
    for (let i = 0; i < this.balls.length; i++) {
      for (let j = i + 1; j < this.balls.length; j++) {
        const a = this.balls[i];
        const b = this.balls[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const minD = (a.r + b.r) * 1.02;
        if (dist >= minD) continue;
        const nx = dx / dist;
        const ny = dy / dist;
        const f = ((minD - dist) / minD) * push * DT;
        a.x -= nx * f;
        a.y -= ny * f;
        b.x += nx * f;
        b.y += ny * f;
      }
    }
    this._ringStep();
    const limit = this.bounds.r - 6 - ballRadius(this.bounds);
    const ringR = this.bounds.r - 3 + (this.params.shellRadius ?? 8) * 0.5;
    const shells = shellPositions(
      this.bounds,
      ringR,
      this.params.shellCount,
      this.ringAngle
    );
    for (const b of this.balls) {
      const vx = (b.x - b.px) * (1 - this.params.airDrag * DT);
      const vy = (b.y - b.py) * (1 - this.params.airDrag * DT);
      b.px = b.x;
      b.py = b.y;
      b.x += vx;
      b.y += vy;
      b.vx = vx / DT;
      b.vy = vy / DT;
      constrainRing(b, this.bounds, limit);
    }
    resolveShells(this.balls, shells, this.params);
    capSpeed(this.balls, this.params.maxSpeed);
  }
}

class DensityEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "density-vortex";
    this.styleName = "Yoğunluk basıncı";
  }
  _stepImpl() {
    const k = this.params.densityK;
    const h = 55;
    for (const b of this.balls) {
      let rho = 0;
      let gx = 0;
      let gy = 0;
      for (const o of this.balls) {
        if (o === b) continue;
        const dx = b.x - o.x;
        const dy = b.y - o.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const q = Math.max(0, 1 - dist / h);
        rho += q * q;
        if (dist < h * 0.5) {
          gx += (dx / dist) * q;
          gy += (dy / dist) * q;
        }
      }
      const pr = (rho - 1.2) * k * DT;
      if (pr > 0) {
        const gl = Math.hypot(gx, gy) || 1;
        b.vx += (gx / gl) * pr;
        b.vy += (gy / gl) * pr;
      }
    }
    resolveBallBall(this.balls, this.params.restitution, 6);
    this._commonIntegrate(0);
  }
}

class VelocityFieldEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "velocity-field";
    this.styleName = "Hız alanı";
  }
  _stepImpl() {
    const s = this.params.fieldStrength;
    const omega = this.params.omega;
    const { cx, cy } = this.bounds;
    for (const b of this.balls) {
      const dx = b.x - cx;
      const dy = b.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      const w = Math.max(0, 1 - dist / (this.bounds.r * 0.9));
      b.vx += (-dy / dist) * omega * dist * 0.15 * s * DT;
      b.vy += (dx / dist) * omega * dist * 0.15 * s * DT;
    }
    resolveBallBall(this.balls, this.params.restitution, 5);
    this._commonIntegrate(0);
  }
}

class RingOnlyEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "ring-only";
    this.styleName = "Sadece halka";
  }
  _stepImpl() {
    resolveBallBall(this.balls, this.params.restitution * 0.6, 3);
    const shells = shellPositions(
      this.bounds,
      this.bounds.r - 3 + 8 * 0.5,
      this.params.shellCount,
      this.ringAngle
    );
    this.params.shellTransfer = 0.82;
    this._ringStep();
    const limit = this.bounds.r - 6 - ballRadius(this.bounds);
    for (const b of this.balls) {
      b.vx *= Math.exp(-0.08 * DT);
      b.vy *= Math.exp(-0.08 * DT);
      b.x += b.vx * DT;
      b.y += b.vy * DT;
      constrainRing(b, this.bounds, limit);
    }
    resolveShells(this.balls, shells, this.params);
    capSpeed(this.balls, this.params.maxSpeed);
  }
}

class HybridEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "hybrid-game";
    this.styleName = "Hibrit";
  }
  _stepImpl() {
    const omega = this.params.omega * 0.35;
    const { cx, cy } = this.bounds;
    for (const b of this.balls) {
      const dx = b.x - cx;
      const dy = b.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      b.vx += (-dy / dist) * omega * 40 * DT;
      b.vy += (dx / dist) * omega * 40 * DT;
    }
    resolveBallBall(this.balls, this.params.restitution, 6);
    contactPushPass(this.balls, this.params.contactPush);
    this._commonIntegrate(0);
  }
}

class MatterNativeEngine extends BaseVortexEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "matter-native";
    this.styleName = "Matter tam";
    this.Matter = window.Matter;
    this.bodies = [];
    this.shells = [];
    this.world = null;
    this.engine = null;
  }

  layout() {
    super.layout();
    this._rebuildMatter();
  }

  clear() {
    if (this.world && this.Matter) {
      for (const b of this.bodies) this.Matter.World.remove(this.world, b);
      for (const s of this.shells) this.Matter.World.remove(this.world, s);
    }
    this.bodies = [];
    this.shells = [];
  }

  spawn(n = this.params.ballCount) {
    this.clear();
    const { Matter } = this;
    const br = ballRadius(this.bounds);
    for (let i = 0; i < n; i++) {
      const a = Math.random() * TAU;
      const d = this.bounds.r * 0.34 * Math.sqrt(Math.random());
      const body = Matter.Bodies.circle(
        this.bounds.cx + Math.cos(a) * d,
        this.bounds.cy + Math.sin(a) * d * 0.88,
        br,
        {
          restitution: this.params.restitution,
          friction: 0.02,
          frictionAir: this.params.airDrag * 0.02,
        }
      );
      this.bodies.push(body);
      Matter.World.add(this.world, body);
    }
    this.kickstartMatter();
  }

  kickstartMatter() {
    const { Matter } = this;
    for (const body of this.bodies) {
      const dx = body.position.x - this.bounds.cx;
      const dy = body.position.y - this.bounds.cy;
      const dist = Math.hypot(dx, dy) || 1;
      Matter.Body.setVelocity(body, {
        x: (-dy / dist) * 120 + (dx / dist) * 50,
        y: (dx / dist) * 120 + (dy / dist) * 50,
      });
    }
  }

  kickstart() {
    this.kickstartMatter();
  }

  _rebuildMatter() {
    const { Matter } = this;
    if (this.world) {
      this.clear();
      Matter.World.clear(this.world);
      Matter.Engine.clear(this.engine);
    }
    this.engine = Matter.Engine.create({ gravity: { x: 0, y: 0 } });
    this.engine.positionIterations = 10;
    this.engine.velocityIterations = 8;
    this.world = this.engine.world;
    this._syncShells();
  }

  _syncShells() {
    const { Matter } = this;
    for (const s of this.shells) Matter.World.remove(this.world, s);
    this.shells = [];
    const ringR = this.bounds.r - 3 + (this.params.shellRadius ?? 8);
    const pts = shellPositions(
      this.bounds,
      ringR,
      this.params.shellCount,
      this.ringAngle
    );
    for (const p of pts) {
      const w = Matter.Bodies.circle(p.x, p.y, this.params.shellRadius, {
        isStatic: true,
        restitution: 0.4,
        friction: 0.05,
      });
      w._shellAngle = p.a;
      this.shells.push(w);
      Matter.World.add(this.world, w);
    }
  }

  _stepImpl() {
    const { Matter } = this;
    this.ringAngle = (this.ringAngle + this.params.ringSpin * DT) % TAU;
    this._syncShells();
    Matter.Engine.update(this.engine, 1000 / 60);
    const limit = this.bounds.r - 6 - ballRadius(this.bounds);
    for (const body of this.bodies) {
      const dx = body.position.x - this.bounds.cx;
      const dy = body.position.y - this.bounds.cy;
      const dist = Math.hypot(dx, dy) || 1;
      if (dist > limit) {
        const s = limit / dist;
        Matter.Body.setPosition(body, {
          x: this.bounds.cx + dx * s,
          y: this.bounds.cy + dy * s,
        });
      }
      const sp = Math.hypot(body.velocity.x, body.velocity.y);
      if (sp > this.params.maxSpeed) {
        const sc = this.params.maxSpeed / sp;
        Matter.Body.setVelocity(body, {
          x: body.velocity.x * sc,
          y: body.velocity.y * sc,
        });
      }
    }
    this.balls = this.bodies.map((body, i) => ({
      x: body.position.x,
      y: body.position.y,
      vx: body.velocity.x,
      vy: body.velocity.y,
      r: body.circleRadius,
      hue: HUES[i % HUES.length],
    }));
  }

  getStats() {
    return computeStats(this.balls, this.bounds, this.params);
  }
}

class TangentForceEngine extends MatterNativeEngine {
  constructor(canvas) {
    super(canvas);
    this.styleId = "tangent-force";
    this.styleName = "Teğet kuvvet";
  }
  _stepImpl() {
    const { Matter } = this;
    const f = this.params.tangentForce;
    const { cx, cy } = this.bounds;
    for (const body of this.bodies) {
      const dx = body.position.x - cx;
      const dy = body.position.y - cy;
      const dist = Math.hypot(dx, dy) || 1;
      const tx = -dy / dist;
      const ty = dx / dist;
      Matter.Body.applyForce(body, body.position, {
        x: tx * f * body.mass * 6000,
        y: ty * f * body.mass * 6000,
      });
    }
    this.ringAngle = (this.ringAngle + this.params.ringSpin * DT) % TAU;
    this._syncShells();
    Matter.Engine.update(this.engine, 1000 / 60);
    this.balls = this.bodies.map((body, i) => ({
      x: body.position.x,
      y: body.position.y,
      vx: body.velocity.x,
      vy: body.velocity.y,
      r: body.circleRadius,
      hue: HUES[i % HUES.length],
    }));
  }
}

class ProductionEngine {
  constructor(canvas) {
    this.canvas = canvas;
    this.arena = null;
    this.styleId = "production";
    this.styleName = "Üretim";
    this.params = { ballCount: 34, ringSpin: 0.58, contactPush: 260 };
    this._ready = null;
  }

  async _ensure() {
    if (this.arena) return this.arena;
    if (!this._ready) {
      this._ready = import("/team-race/arena-physics.js?v=81").then((m) => {
        this.arena = new m.TeamRaceArena(this.canvas, { showExitLabel: false });
        this.arena.layout();
        this.arena.setRoundPhase("chaos");
        this.arena._chaosEnteredAt = Date.now() - 60_000;
        this.arena.start();
        return this.arena;
      });
    }
    return this._ready;
  }

  layout() {
    return this._ensure().then((a) => a.layout());
  }

  setParams(p) {
    Object.assign(this.params, p);
    return this._ensure().then((a) => {
      const c = a.constructor?.ARENA_PHYSICS_CFG?.chaos;
      if (!c && window.ARENA_PHYSICS_CFG) {
        /* cfg from module export on arena */
      }
      import("/team-race/arena-physics-config.js").then((mod) => {
        const cfg = mod.ARENA_PHYSICS_CFG?.chaos || mod.DEFAULT_ARENA_PHYSICS_CFG?.chaos;
        if (!cfg) return;
        if (p.ringSpin != null) cfg.ringSpinRadPerSec = p.ringSpin;
        if (p.contactPush != null) cfg.centerSpinRadPerSec = p.omega ?? p.contactPush / 160;
        if (p.omega != null) cfg.centerSpinRadPerSec = p.omega;
        a.syncPhysicsConfig?.();
      });
    });
  }

  clear() {
    return this._ensure().then((a) => a.clear());
  }

  spawn(n = this.params.ballCount) {
    const teams = ["gs", "fb", "bjk", "ts"];
    return this._ensure().then(async (a) => {
      a.clear();
      a.setRoundPhase("chaos");
      for (let i = 0; i < n; i++) {
        await a.spawn({
          id: `v${i}`,
          teamCode: teams[i % teams.length],
          teamName: teams[i % teams.length].toUpperCase(),
          displayName: `T${i}`,
        });
      }
      a.forceEnterChaos();
    });
  }

  kickstart() {
    return this._ensure().then((a) => a.kickstartChaos());
  }

  start() {
    return this._ensure().then((a) => a.start());
  }

  stop() {
    if (this.arena) this.arena.stop();
  }

  step() {
    if (this.arena) {
      this.arena.step();
      this.arena._draw();
    }
  }

  draw() {
    if (this.arena) this.arena._draw();
  }

  getStats() {
    if (!this.arena) {
      return { count: 0, avgSpeed: 0, maxSpeed: 0, avgTangential: 0, onFloor: 0, overlaps: 0 };
    }
    const bounds = this.arena._bounds;
    const balls = [...this.arena.bodies.values()]
      .filter((b) => !b?.plugin?.fallingOut)
      .map((b) => ({
        x: b.position.x,
        y: b.position.y,
        vx: b.velocity.x,
        vy: b.velocity.y,
        r: b.circleRadius || 10,
      }));
    return computeStats(balls, { ...bounds, w: this.arena._size.w, h: this.arena._size.h }, {
      floorZone: 0.38,
    });
  }
}

const ENGINE_MAP = {
  "contact-push": ContactPushEngine,
  "omega-target": OmegaEngine,
  "verlet-repulse": VerletEngine,
  "density-vortex": DensityEngine,
  "velocity-field": VelocityFieldEngine,
  "ring-only": RingOnlyEngine,
  "hybrid-game": HybridEngine,
  "matter-native": MatterNativeEngine,
  "tangent-force": TangentForceEngine,
  production: ProductionEngine,
};

export function createVortexEngine(styleId, canvas) {
  const C = ENGINE_MAP[styleId] || ContactPushEngine;
  return new C(canvas);
}
