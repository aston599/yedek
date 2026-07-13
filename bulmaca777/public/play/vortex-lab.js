import { VORTEX_CATALOG, createVortexEngine } from "./vortex-engines.js?v=4";

const $ = (id) => document.getElementById(id);

const PARAM_VISIBILITY = {
  production: ["ringSpin", "contactPush", "restitution"],
  "contact-push": ["ringSpin", "contactPush", "restitution"],
  "matter-native": ["ringSpin", "restitution"],
  "omega-target": ["ringSpin", "omega", "restitution"],
  "tangent-force": ["ringSpin", "tangentForce", "restitution"],
  "verlet-repulse": ["ringSpin", "contactPush", "restitution"],
  "density-vortex": ["ringSpin", "densityK", "restitution"],
  "velocity-field": ["ringSpin", "omega", "fieldStrength", "restitution"],
  "ring-only": ["ringSpin", "restitution"],
  "hybrid-game": ["ringSpin", "contactPush", "omega", "restitution"],
};

let engine = null;
let styleId = "omega-target";
let running = false;
let statsTimer = 0;
let markedBest = null;

function readParams() {
  return {
    ballCount: Number($("cfgBallCount").value),
    ringSpin: Number($("cfgRingSpin").value),
    contactPush: Number($("cfgContactPush").value),
    omega: Number($("cfgOmega").value),
    tangentForce: Number($("cfgTangentForce").value),
    densityK: Number($("cfgDensityK").value),
    fieldStrength: Number($("cfgFieldStrength").value),
    restitution: Number($("cfgRestitution").value),
  };
}

function syncParamOutputs() {
  const p = readParams();
  $("outBallCount").textContent = String(p.ballCount);
  $("outRingSpin").textContent = p.ringSpin.toFixed(2);
  $("outContactPush").textContent = String(p.contactPush);
  $("outOmega").textContent = p.omega.toFixed(1);
  $("outTangentForce").textContent = p.tangentForce.toFixed(5);
  $("outDensityK").textContent = String(p.densityK);
  $("outFieldStrength").textContent = p.fieldStrength.toFixed(1);
  $("outRestitution").textContent = p.restitution.toFixed(2);
}

function updateParamVisibility() {
  const allowed = new Set(PARAM_VISIBILITY[styleId] || ["ringSpin", "contactPush"]);
  document.querySelectorAll("[data-param]").forEach((el) => {
    el.hidden = !allowed.has(el.dataset.param);
  });
}

function buildStyleList() {
  const list = $("styleList");
  list.replaceChildren();
  VORTEX_CATALOG.forEach((item, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vortex-style-btn" + (item.id === styleId ? " is-active" : "");
    btn.dataset.id = item.id;
    btn.dataset.idx = String(idx);
    btn.innerHTML = `<strong>${item.name}</strong><span class="tech">${item.tech}</span><span class="hint">${item.hint}</span>`;
    btn.addEventListener("click", () => selectStyle(item.id));
    list.appendChild(btn);
  });
}

async function destroyEngine() {
  if (!engine) return;
  if (engine.arena) {
    engine.arena.stop();
    await engine.clear?.();
  } else {
    engine.stop?.();
  }
  engine = null;
}

async function selectStyle(id) {
  styleId = id;
  buildStyleList();
  const meta = VORTEX_CATALOG.find((x) => x.id === id);
  $("styleHint").textContent = meta?.hint || "";
  $("techBadge").textContent = meta?.tech || "";
  $("statStyle").textContent = meta?.name || id;
  updateParamVisibility();
  await destroyEngine();
  const canvas = $("vortexCanvas");
  engine = createVortexEngine(id, canvas);
  engine.setParams(readParams());
  await engine.layout?.();
  await engine.spawn?.(readParams().ballCount);
  if (running) engine.start?.();
  else engine.draw?.();
  updateStats();
}

function applyParamsLive() {
  syncParamOutputs();
  if (!engine) return;
  engine.setParams(readParams());
  if (engine.arena) {
    import("/team-race/arena-physics-config.js").then((mod) => {
      const cfg = mod.ARENA_PHYSICS_CFG?.chaos;
      if (!cfg) return;
      const p = readParams();
      cfg.ringSpinRadPerSec = p.ringSpin;
      cfg.centerSpinRadPerSec = p.omega ?? cfg.centerSpinRadPerSec;
      cfg.shellSpinTransfer = 0;
      cfg.contactPushPx = p.contactPush;
      cfg.ballRestitution = p.restitution;
      engine.arena.syncPhysicsConfig?.();
    });
  }
}

function updateStats() {
  if (!engine?.getStats) return;
  const s = engine.getStats();
  $("statCount").textContent = String(s.count);
  $("statAvg").textContent = s.avgSpeed.toFixed(1);
  $("statMax").textContent = s.maxSpeed.toFixed(1);
  $("statTang").textContent = s.avgTangential.toFixed(1);
  $("statFloor").textContent = String(s.onFloor);
  $("statOverlap").textContent = String(s.overlaps);
}

function buildReport() {
  const meta = VORTEX_CATALOG.find((x) => x.id === styleId);
  return {
    at: new Date().toISOString(),
    styleId,
    styleName: meta?.name,
    tech: meta?.tech,
    params: readParams(),
    stats: engine?.getStats?.() ?? null,
    markedBest: markedBest === styleId,
    note: ($("feedbackNote").value || "").trim(),
  };
}

async function copyReport() {
  const text = JSON.stringify(buildReport(), null, 2);
  try {
    await navigator.clipboard.writeText(text);
    $("savedMark").hidden = false;
    $("savedMark").textContent = "Rapor panoya kopyalandı — sohbete yapıştırın.";
  } catch {
    $("savedMark").hidden = false;
    $("savedMark").textContent = text;
  }
}

function wireControls() {
  $("btnRun").addEventListener("click", async () => {
    running = true;
    await engine?.layout?.();
    engine?.start?.();
  });

  $("btnPause").addEventListener("click", () => {
    running = false;
    engine?.stop?.();
  });

  $("btnStep").addEventListener("click", () => {
    engine?.step?.();
    engine?.draw?.();
    updateStats();
  });

  $("btnRespawn").addEventListener("click", async () => {
    await engine?.spawn?.(readParams().ballCount);
    updateStats();
  });

  $("btnMarkBest").addEventListener("click", () => {
    markedBest = styleId;
    const meta = VORTEX_CATALOG.find((x) => x.id === styleId);
    $("savedMark").hidden = false;
    $("savedMark").textContent = `İşaretlendi: ${meta?.name || styleId}`;
    try {
      localStorage.setItem("vortexLabBest", styleId);
    } catch {
      /* yoksay */
    }
  });

  $("btnCopyReport").addEventListener("click", () => copyReport());

  [
    "cfgBallCount",
    "cfgRingSpin",
    "cfgContactPush",
    "cfgOmega",
    "cfgTangentForce",
    "cfgDensityK",
    "cfgFieldStrength",
    "cfgRestitution",
  ].forEach((id) => {
    $(id).addEventListener("input", () => applyParamsLive());
  });

  document.addEventListener("keydown", (e) => {
    if (e.target.matches("textarea, input")) return;
    if (e.code === "Space") {
      e.preventDefault();
      running ? $("btnPause").click() : $("btnRun").click();
    }
    if (e.key === "r" || e.key === "R") $("btnRespawn").click();
    const n = e.key === "0" ? 10 : Number(e.key);
    if (n >= 1 && n <= 10 && VORTEX_CATALOG[n - 1]) {
      selectStyle(VORTEX_CATALOG[n - 1].id);
    }
  });
}

async function init() {
  buildStyleList();
  wireControls();
  syncParamOutputs();
  try {
    const saved = localStorage.getItem("vortexLabBest");
    if (saved) markedBest = saved;
  } catch {
    /* yoksay */
  }
  const saved = (() => {
    try {
      return localStorage.getItem("vortexLabBest");
    } catch {
      return null;
    }
  })();
  const initial =
    VORTEX_CATALOG.some((x) => x.id === saved) ? saved : "omega-target";
  await selectStyle(initial);
  running = true;
  engine?.start?.();
  statsTimer = window.setInterval(updateStats, 250);
}

init();
