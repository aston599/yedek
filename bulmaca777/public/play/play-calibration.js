import { PLAY_ARENA_LAYOUT_DEFAULT } from "./arena-layout-default.js?v=1";
import {
  startCalibrationLivePreview,
  stopCalibrationLivePreview,
} from "./play-calibration-preview.js?v=2";

const STORAGE_PREFIX = "play-arena-layout:";
const MAX_UNDO = 50;

/** Bu slotlarda yükseklik % olarak arenaya göre verilir; içerik kesilir — sadece genişlik kullanılır */
const ARENA_SLOTS_NO_FIXED_HEIGHT = new Set(["phaseBanner", "railLeft", "railRight"]);

/** Alt hizalı slotlar — kayıtta bottom % kullanılır */
const BOTTOM_ANCHORED_SLOTS = new Set([
  "winnerCard",
  "arenaCmdBand",
  "arenaPromoAlert",
  "elimFlash",
]);

export const CAL_ARENA_SLOTS = [
  { key: "phaseBanner", label: "Faz HUD", selector: "#phaseBanner", resizable: true, centerX: true },
  { key: "railLeft", label: "Kazananlar", selector: ".play-arena-rail--left", resizable: true },
  { key: "railRight", label: "En çok yazan", selector: ".play-arena-rail--right", resizable: true },
  { key: "arenaBadge", label: "Arenada sayaç", selector: "#arenaBadge" },
  { key: "arenaCmdBand", label: "Komut / kural bandı", selector: "#arenaCmdBand", centerX: true },
  { key: "arenaPromoAlert", label: "Promo bandı", selector: "#arenaPromoAlert", centerX: true },
  { key: "elimFlash", label: "Elenme flaşı", selector: "#elimFlash", centerX: true },
  { key: "winnerCard", label: "Bilgi bandı", selector: "#winnerCard", resizable: true, centerX: true },
];

let layoutState = structuredClone(PLAY_ARENA_LAYOUT_DEFAULT);
let activeOrientation = "vertical";
let roomId = null;
let enabled = false;
let handleLayer = null;
let onLayoutApplied = null;
let getArena = null;
let onPreviewTeardown = null;
const undoStack = [];
const redoStack = [];
let undoBound = false;

function storageKey() {
  return `${STORAGE_PREFIX}${roomId || "global"}`;
}

function pct(v, total) {
  if (!total) return 0;
  return Math.round((v / total) * 1000) / 10;
}

function cloneLayout(src) {
  return structuredClone(src || PLAY_ARENA_LAYOUT_DEFAULT);
}

const CAL_SLOT_KEYS = new Set(CAL_ARENA_SLOTS.map((s) => s.key));

/** Eski export (ctaLike, activityTicker…) ve eksik yatay slotları temizler */
export function sanitizeArenaLayout(layout) {
  const base = cloneLayout(PLAY_ARENA_LAYOUT_DEFAULT);
  const src = layout || {};
  for (const orient of ["vertical", "horizontal"]) {
    const raw = src[orient] || {};
    const out = { ...base[orient] };
    for (const key of CAL_SLOT_KEYS) {
      if (raw[key] != null) out[key] = { ...raw[key] };
    }
    if (orient === "horizontal") {
      if (!raw.arenaCmdBand && src.vertical?.arenaCmdBand) {
        out.arenaCmdBand = { ...src.vertical.arenaCmdBand };
      }
      if (!raw.arenaPromoAlert && src.vertical?.arenaPromoAlert) {
        out.arenaPromoAlert = { ...src.vertical.arenaPromoAlert };
      }
      if (raw.winnerCard == null && src.vertical?.winnerCard) {
        out.winnerCard = { ...src.vertical.winnerCard, width: out.winnerCard?.width ?? 94 };
      }
    }
    base[orient] = out;
  }
  return base;
}

function getArenaEl() {
  return document.getElementById("arena");
}

function getSlotEl(key) {
  const def = CAL_ARENA_SLOTS.find((s) => s.key === key);
  return def ? document.querySelector(def.selector) : null;
}

function normalizeActivityTickerBox(box = {}) {
  const h = Number(box.minHeight ?? box.height) || 18;
  const out = {
    bottom: 0,
    left: box.left != null ? box.left : 0,
    minHeight: h,
  };
  if (box.right != null) out.right = box.right;
  else if (box.width != null && box.width > 0 && box.width < 99) {
    out.width = box.width;
  } else {
    out.left = out.left ?? 0;
    out.right = 0;
  }
  return out;
}

function applySlotStyle(key, box) {
  const el = getSlotEl(key);
  const def = CAL_ARENA_SLOTS.find((s) => s.key === key);
  if (!el || !box) return;

  if (key === "activityTicker") {
    box = normalizeActivityTickerBox(box);
  }

  el.style.top = "";
  el.style.bottom = "";
  el.style.left = "";
  el.style.right = "";
  el.style.width = "";
  el.style.height = "";
  el.style.minHeight = "";
  el.style.transform = "";

  if (box.top != null) el.style.top = `${box.top}%`;
  if (box.bottom != null) el.style.bottom = `${box.bottom}%`;
  if (box.left != null) el.style.left = `${box.left}%`;
  if (box.right != null) el.style.right = `${box.right}%`;
  if (box.width != null && box.width > 0) el.style.width = `${box.width}%`;
  if (!ARENA_SLOTS_NO_FIXED_HEIGHT.has(key) && box.height != null && box.height > 0) {
    el.style.height = `${box.height}%`;
  }
  if (box.minHeight != null) el.style.minHeight = `${box.minHeight}%`;

  if (def?.centerX) {
    if (box.left != null) el.style.transform = "translateX(-50%)";
    else if (box.bottom != null) {
      el.style.left = "50%";
      el.style.transform = "translateX(-50%)";
    }
  }

  if (key === "phaseBanner") {
    const arena = getArenaEl();
    if (arena && box.top != null) {
      arena.dataset.calHudTop = "1";
      const arenaH = arena.getBoundingClientRect().height || 600;
      arena.style.setProperty("--arena-hud-top", `${Math.round((box.top / 100) * arenaH)}px`);
    }
  }
}

export function applyPlayArenaLayout(layout = layoutState, orientation = activeOrientation) {
  layoutState = sanitizeArenaLayout(layout);
  activeOrientation = orientation === "horizontal" ? "horizontal" : "vertical";
  const cfg = layoutState[activeOrientation] || layoutState.vertical;
  const arena = getArenaEl();
  if (arena) arena.dataset.calLayout = "1";
  for (const slot of CAL_ARENA_SLOTS) {
    applySlotStyle(slot.key, cfg[slot.key]);
  }
  onLayoutApplied?.(layoutState, activeOrientation);
  if (enabled) requestAnimationFrame(syncHandles);
}

export function getPlayArenaLayout() {
  return cloneLayout(layoutState);
}

export function setCalibrationOrientation(orientation) {
  activeOrientation = orientation === "horizontal" ? "horizontal" : "vertical";
  applyPlayArenaLayout(layoutState, activeOrientation);
}

function readBoxFromElement(el, arenaRect, def) {
  const r = el.getBoundingClientRect();
  const box = {};
  if (def.centerX) {
    box.left = pct(r.left + r.width / 2 - arenaRect.left, arenaRect.width);
  } else {
    box.left = pct(r.left - arenaRect.left, arenaRect.width);
  }
  const hPct = pct(r.height, arenaRect.height);
  if (def.key === "activityTicker") {
    box.bottom = pct(arenaRect.bottom - r.bottom, arenaRect.height);
    box.width = pct(r.width, arenaRect.width);
    box.minHeight = hPct > 1 ? hPct : 18;
    return normalizeActivityTickerBox(box);
  }
  if (BOTTOM_ANCHORED_SLOTS.has(def.key)) {
    box.bottom = pct(arenaRect.bottom - r.bottom, arenaRect.height);
  } else {
    box.top = pct(r.top - arenaRect.top, arenaRect.height);
  }
  box.width = pct(r.width, arenaRect.width);
  if (hPct > 1) box.height = hPct;
  if (ARENA_SLOTS_NO_FIXED_HEIGHT.has(def.key)) {
    delete box.height;
  }
  return box;
}

function snapshotLayout() {
  return cloneLayout(layoutState);
}

function updateUndoUi() {
  const fb = document.getElementById("playCalFeedback");
  const undoBtn = document.getElementById("btnCalUndo");
  if (undoBtn) undoBtn.disabled = undoStack.length === 0;
  const redoBtn = document.getElementById("btnCalRedo");
  if (redoBtn) redoBtn.disabled = redoStack.length === 0;
  if (fb && enabled && (undoStack.length || redoStack.length)) {
    fb.textContent = `Geri al: ${undoStack.length} · Yinele: ${redoStack.length} (Ctrl+Z / Ctrl+Y)`;
  }
}

function pushUndoCheckpoint() {
  undoStack.push(snapshotLayout());
  if (undoStack.length > MAX_UNDO) undoStack.shift();
  redoStack.length = 0;
  updateUndoUi();
}

function applyLayoutSnapshot(snap) {
  layoutState = cloneLayout(snap);
  applyPlayArenaLayout(layoutState, activeOrientation);
  if (enabled) buildHandleLayer();
  updatePanelPreview();
  updateUndoUi();
}

export function undoCalibrationLayout() {
  if (!undoStack.length) return false;
  redoStack.push(snapshotLayout());
  applyLayoutSnapshot(undoStack.pop());
  return true;
}

export function redoCalibrationLayout() {
  if (!redoStack.length) return false;
  undoStack.push(snapshotLayout());
  applyLayoutSnapshot(redoStack.pop());
  return true;
}

function bindUndoKeys() {
  if (undoBound) return;
  undoBound = true;
  window.addEventListener("keydown", (e) => {
    if (!enabled) return;
    const mod = e.ctrlKey || e.metaKey;
    if (!mod) return;
    if (e.key === "z" || e.key === "Z") {
      if (e.shiftKey) {
        if (redoCalibrationLayout()) e.preventDefault();
      } else if (undoCalibrationLayout()) {
        e.preventDefault();
      }
    } else if (e.key === "y" || e.key === "Y") {
      if (redoCalibrationLayout()) e.preventDefault();
    }
  });
}

function readLayoutFromDom() {
  const arena = getArenaEl();
  if (!arena) return;
  const rect = arena.getBoundingClientRect();
  const orient = layoutState[activeOrientation] || {};
  for (const slot of CAL_ARENA_SLOTS) {
    const el = getSlotEl(slot.key);
    if (!el) continue;
    orient[slot.key] = readBoxFromElement(el, rect, slot);
  }
  layoutState[activeOrientation] = orient;
}

function syncHandles() {
  if (!handleLayer) return;
  const arena = getArenaEl();
  if (!arena) return;
  const aRect = arena.getBoundingClientRect();
  for (const h of handleLayer.querySelectorAll(".play-cal-handle")) {
    const el = getSlotEl(h.dataset.calKey);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    h.style.left = `${r.left - aRect.left}px`;
    h.style.top = `${r.top - aRect.top}px`;
    h.style.width = `${r.width}px`;
    h.style.height = `${r.height}px`;
  }
}

function startDrag(e, handleEl) {
  e.preventDefault();
  const pointerId = e.pointerId;
  if (pointerId != null && typeof handleEl.setPointerCapture === "function") {
    try {
      handleEl.setPointerCapture(pointerId);
    } catch {
      /* ignore */
    }
  }
  pushUndoCheckpoint();
  const arena = getArenaEl();
  const target = getSlotEl(handleEl.dataset.calKey);
  if (!arena || !target) return;
  const def = CAL_ARENA_SLOTS.find((s) => s.key === handleEl.dataset.calKey);
  const aRect = arena.getBoundingClientRect();
  const tRect = target.getBoundingClientRect();
  const startPointerX = e.clientX;
  const startPointerY = e.clientY;
  const startLeftPx = tRect.left - aRect.left;
  const startTopPx = tRect.top - aRect.top;
  const boxW = tRect.width;
  const boxH = tRect.height;

  const useBottomAnchor = BOTTOM_ANCHORED_SLOTS.has(handleEl.dataset.calKey);
  if (useBottomAnchor) {
    target.style.top = "auto";
  } else {
    target.style.bottom = "auto";
  }

  const move = (ev) => {
    const arenaRect = arena.getBoundingClientRect();
    const dx = ev.clientX - startPointerX;
    const dy = ev.clientY - startPointerY;
    let leftPx = startLeftPx + dx;
    let topPx = startTopPx + dy;

    if (def?.centerX) {
      const centerPx = leftPx + boxW / 2;
      let minC = boxW / 2;
      let maxC = arenaRect.width - boxW / 2;
      if (minC > maxC) {
        minC = 0;
        maxC = arenaRect.width;
      }
      const clamped = Math.max(minC, Math.min(maxC, centerPx));
      target.style.left = `${pct(clamped, arenaRect.width)}%`;
      target.style.transform = "translateX(-50%)";
    } else {
      const minL = Math.min(0, arenaRect.width - boxW);
      const maxL = Math.max(0, arenaRect.width - boxW);
      leftPx = Math.max(minL, Math.min(maxL, leftPx));
      target.style.left = `${pct(leftPx, arenaRect.width)}%`;
      target.style.transform = "";
    }

    if (useBottomAnchor) {
      const bottomPx = arenaRect.height - (topPx + boxH);
      const minB = 0;
      const maxB = Math.max(0, arenaRect.height - boxH);
      const clampedB = Math.max(minB, Math.min(maxB, bottomPx));
      target.style.bottom = `${pct(clampedB, arenaRect.height)}%`;
      target.style.top = "auto";
    } else {
      const minT = Math.min(0, arenaRect.height - boxH);
      const maxT = Math.max(0, arenaRect.height - boxH);
      topPx = Math.max(minT, Math.min(maxT, topPx));
      target.style.top = `${pct(topPx, arenaRect.height)}%`;
    }

    readLayoutFromDom();
    syncHandles();
    updatePanelPreview();
  };
  const up = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", up);
    window.removeEventListener("pointercancel", up);
    if (pointerId != null && typeof handleEl.releasePointerCapture === "function") {
      try {
        if (handleEl.hasPointerCapture?.(pointerId)) handleEl.releasePointerCapture(pointerId);
      } catch {
        /* ignore */
      }
    }
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up);
  window.addEventListener("pointercancel", up);
}

function startResize(e, handleEl) {
  e.stopPropagation();
  e.preventDefault();
  pushUndoCheckpoint();
  const slotKey = handleEl.dataset.calKey;
  const target = getSlotEl(slotKey);
  const arena = getArenaEl();
  if (!target || !arena) return;
  const aRect = arena.getBoundingClientRect();
  const startX = e.clientX;
  const startY = e.clientY;
  const baseW = target.offsetWidth;
  const baseH = target.offsetHeight;

  const move = (ev) => {
    target.style.width = `${pct(Math.max(40, baseW + ev.clientX - startX), aRect.width)}%`;
    if (!ARENA_SLOTS_NO_FIXED_HEIGHT.has(slotKey)) {
      target.style.height = `${pct(Math.max(24, baseH + ev.clientY - startY), aRect.height)}%`;
    }
    readLayoutFromDom();
    syncHandles();
    updatePanelPreview();
  };
  const up = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", up);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up);
}

function buildHandleLayer() {
  const arena = getArenaEl();
  if (!arena) return;
  if (handleLayer) handleLayer.remove();
  handleLayer = document.createElement("div");
  handleLayer.className = "play-cal-handle-layer";
  handleLayer.style.zIndex = "40";
  for (const slot of CAL_ARENA_SLOTS) {
    const h = document.createElement("div");
    h.className = "play-cal-handle";
    h.dataset.calKey = slot.key;
    h.innerHTML = `<span class="play-cal-handle-label">${slot.label}</span>`;
    if (slot.resizable) {
      const grip = document.createElement("span");
      grip.className = "play-cal-resize";
      grip.addEventListener("pointerdown", (e) => startResize(e, h));
      h.appendChild(grip);
    }
    h.addEventListener("pointerdown", (e) => {
      if (e.target.classList.contains("play-cal-resize")) return;
      startDrag(e, h);
    });
    handleLayer.appendChild(h);
  }
  arena.appendChild(handleLayer);
  syncHandles();
}

function scanMenuRegion(root, label) {
  if (!root) return null;
  const r = root.getBoundingClientRect();
  const vw = window.innerWidth || 1;
  const vh = window.innerHeight || 1;
  return {
    label,
    id: root.id || null,
    class: root.className || null,
    rect: {
      top: pct(r.top, vh),
      left: pct(r.left, vw),
      width: pct(r.width, vw),
      height: pct(r.height, vh),
    },
  };
}

function scanButtons(root, groupLabel) {
  if (!root) return [];
  const vw = window.innerWidth || 1;
  const vh = window.innerHeight || 1;
  return [...root.querySelectorAll("button, a.btn, a.btn-ghost")].map((el) => {
    const r = el.getBoundingClientRect();
    return {
      group: groupLabel,
      id: el.id || null,
      text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 48),
      title: el.title || null,
      href: el.getAttribute("href") || null,
      rect: {
        top: pct(r.top, vh),
        left: pct(r.left, vw),
        width: pct(r.width, vw),
        height: pct(r.height, vh),
      },
    };
  });
}

export function buildLayoutExportBundle() {
  readLayoutFromDom();
  const orient = activeOrientation;
  const arenaLayout = getPlayArenaLayout();
  const cfg = arenaLayout[orient] || {};

  const cssLines = [`/* Play arena — ${orient} */`];
  for (const slot of CAL_ARENA_SLOTS) {
    const box = cfg[slot.key];
    if (!box) continue;
    const parts = [];
    if (box.top != null) parts.push(`top: ${box.top}%`);
    if (box.bottom != null) parts.push(`bottom: ${box.bottom}%`);
    if (box.left != null) parts.push(`left: ${box.left}%`);
    if (box.right != null) parts.push(`right: ${box.right}%`);
    if (box.width != null) parts.push(`width: ${box.width}%`);
    if (box.height != null) parts.push(`height: ${box.height}%`);
    if (box.minHeight != null) parts.push(`min-height: ${box.minHeight}%`);
    cssLines.push(`[data-cal-slot="${slot.key}"] { ${parts.join("; ")}; }`);
  }

  return {
    version: 1,
    exportedAt: new Date().toISOString(),
    roomId: roomId || null,
    orientation: orient,
    arenaLayout,
    arenaSlots: CAL_ARENA_SLOTS.map((s) => ({
      key: s.key,
      label: s.label,
      selector: s.selector,
      box: cfg[s.key] || null,
    })),
    menu: {
      topbar: scanMenuRegion(document.getElementById("playTopbar"), "Ust bar"),
      topbarBrand: scanMenuRegion(document.querySelector(".play-topbar-brand"), "Marka"),
      topbarMeta: scanMenuRegion(document.querySelector(".play-topbar-meta"), "Durum pillleri"),
      topbarControls: scanMenuRegion(
        document.querySelector(".play-topbar-controls"),
        "Tur kontrolleri"
      ),
      topbarNav: scanMenuRegion(document.getElementById("playTopbarNav"), "Navigasyon"),
      leftDock: scanMenuRegion(document.querySelector(".play-dock--left"), "Sol panel"),
      rightDock: scanMenuRegion(document.querySelector(".play-dock--right"), "Sag panel"),
      stage: scanMenuRegion(document.getElementById("playStage"), "Arena sahnesi"),
    },
    buttons: [
      ...scanButtons(document.querySelector(".play-topbar-controls"), "tur"),
      ...scanButtons(document.getElementById("playTopbarNav"), "nav"),
      ...scanButtons(document.querySelector(".play-dock--left"), "sol"),
      ...scanButtons(document.querySelector(".play-dock--right"), "sag"),
    ],
    css: cssLines.join("\n"),
  };
}

function updatePanelPreview() {
  const ta = document.getElementById("playCalOutput");
  if (!ta) return;
  const bundle = buildLayoutExportBundle();
  ta.value = JSON.stringify(bundle, null, 2);
}

/** Dışa aktarılan JSON paketini yükle (arenaLayout veya doğrudan vertical/horizontal) */
export function importPlayLayoutBundle(raw) {
  const data = typeof raw === "string" ? JSON.parse(raw) : raw;
  const next =
    data?.arenaLayout && (data.arenaLayout.vertical || data.arenaLayout.horizontal)
      ? cloneLayout(data.arenaLayout)
      : data?.vertical || data?.horizontal
        ? cloneLayout(data)
        : null;
  if (!next) throw new Error("Gecersiz kalibrasyon JSON — arenaLayout bulunamadi");
  if (data?.orientation === "horizontal" || data?.orientation === "vertical") {
    activeOrientation = data.orientation;
  }
  pushUndoCheckpoint();
  layoutState = sanitizeArenaLayout(next);
  applyPlayArenaLayout(layoutState, activeOrientation);
  if (enabled) buildHandleLayer();
  updatePanelPreview();
  return layoutState;
}

export async function copyPlayLayoutBundle() {
  readLayoutFromDom();
  const bundle = buildLayoutExportBundle();
  const text = JSON.stringify(bundle, null, 2);
  try {
    await navigator.clipboard.writeText(text);
    return { ok: true, message: "Tüm menü ve arena kodları panoya kopyalandı." };
  } catch {
    const ta = document.getElementById("playCalOutput");
    if (ta) {
      ta.value = text;
      ta.select();
    }
    return { ok: false, message: "Panoya kopyalanamadı — metin kutusundan seçin." };
  }
}

export function savePlayArenaLayoutLocal() {
  readLayoutFromDom();
  localStorage.setItem(storageKey(), JSON.stringify(layoutState));
  return layoutState;
}

export async function loadPlayArenaLayout(options = {}) {
  roomId = options.roomId ?? roomId;
  activeOrientation = options.orientation === "horizontal" ? "horizontal" : "vertical";

  let fromServer = null;
  let fromLocal = null;

  if (roomId) {
    try {
      const res = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/layout/play`, {
        cache: "no-store",
      });
      if (res.ok) fromServer = await res.json();
    } catch {
      /* yoksay */
    }
  }

  try {
    const raw = localStorage.getItem(storageKey());
    if (raw) fromLocal = JSON.parse(raw);
  } catch {
    fromLocal = null;
  }

  // Oda modunda sunucu (Odaya kaydet) öncelikli — eski localStorage canlıyı bozmasın
  const loaded = fromServer || fromLocal || null;
  layoutState = sanitizeArenaLayout(loaded || PLAY_ARENA_LAYOUT_DEFAULT);

  if (fromServer && roomId) {
    try {
      localStorage.setItem(storageKey(), JSON.stringify(layoutState));
    } catch {
      /* yoksay */
    }
  }

  applyPlayArenaLayout(layoutState, activeOrientation);
  return layoutState;
}

export async function savePlayArenaLayoutServer() {
  if (!roomId) {
    savePlayArenaLayoutLocal();
    return { ok: true, local: true };
  }
  readLayoutFromDom();
  const res = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/layout/play`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(layoutState),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Kayit basarisiz");
  }
  savePlayArenaLayoutLocal();
  return { ok: true };
}

export function setCalibrationEnabled(on) {
  enabled = Boolean(on);
  document.body.classList.toggle("play-calibration-on", enabled);
  const panel = document.getElementById("playCalPanel");
  if (panel) panel.classList.toggle("hidden", !enabled);
  const btn = document.getElementById("btnToggleCalibration");
  if (btn) btn.classList.toggle("active", enabled);

  if (enabled) {
    undoStack.length = 0;
    redoStack.length = 0;
    const banner = document.getElementById("phaseBanner");
    if (banner) banner.classList.remove("hidden");
    buildHandleLayer();
    updatePanelPreview();
    updateUndoUi();
    const list = document.getElementById("playCalSlotList");
    if (list) {
      list.innerHTML = CAL_ARENA_SLOTS.map(
        (s) => `<li>${s.key} → ${s.selector}</li>`
      ).join("");
    }
    startCalibrationLivePreview({
      getArena: () => getArena?.() || null,
      onTeardown: () => onPreviewTeardown?.(),
    });
    requestAnimationFrame(() => {
      applyPlayArenaLayout(layoutState, activeOrientation);
      buildHandleLayer();
      syncHandles();
    });
  } else {
    stopCalibrationLivePreview();
    if (handleLayer) {
      handleLayer.remove();
      handleLayer = null;
    }
    undoStack.length = 0;
    redoStack.length = 0;
    applyPlayArenaLayout(layoutState, activeOrientation);
  }
}

export function initPlayCalibration(options = {}) {
  roomId = options.roomId || null;
  onLayoutApplied = options.onLayoutApplied || null;
  getArena = options.getArena || null;
  onPreviewTeardown = options.onPreviewTeardown || null;
  activeOrientation = options.orientation === "horizontal" ? "horizontal" : "vertical";
  bindUndoKeys();

  document.getElementById("btnToggleCalibration")?.addEventListener("click", () => {
    setCalibrationEnabled(!enabled);
  });
  document.getElementById("btnCalCopyAll")?.addEventListener("click", async () => {
    const r = await copyPlayLayoutBundle();
    const fb = document.getElementById("playCalFeedback");
    if (fb) fb.textContent = r.message;
  });
  document.getElementById("btnCalImport")?.addEventListener("click", () => {
    const fb = document.getElementById("playCalFeedback");
    const ta = document.getElementById("playCalOutput");
    try {
      importPlayLayoutBundle(ta?.value?.trim() || "");
      if (fb) fb.textContent = "JSON yuklendi — gerekirse «Odaya kaydet».";
    } catch (e) {
      if (fb) fb.textContent = e.message || "JSON okunamadi";
    }
  });
  document.getElementById("btnCalSaveLocal")?.addEventListener("click", () => {
    savePlayArenaLayoutLocal();
    const fb = document.getElementById("playCalFeedback");
    if (fb) fb.textContent = "Yerel tarayiciya kaydedildi.";
    updatePanelPreview();
  });
  document.getElementById("btnCalSaveServer")?.addEventListener("click", async () => {
    const fb = document.getElementById("playCalFeedback");
    try {
      await savePlayArenaLayoutServer();
      if (fb) fb.textContent = roomId ? "Odaya kaydedildi." : "Yerel kayit yapildi.";
    } catch (e) {
      if (fb) fb.textContent = e.message || "Kaydedilemedi";
    }
  });
  document.getElementById("btnCalUndo")?.addEventListener("click", () => {
    if (undoCalibrationLayout()) {
      const fb = document.getElementById("playCalFeedback");
      if (fb) fb.textContent = "Geri alındı (Ctrl+Z).";
    }
  });
  document.getElementById("btnCalRedo")?.addEventListener("click", () => {
    if (redoCalibrationLayout()) {
      const fb = document.getElementById("playCalFeedback");
      if (fb) fb.textContent = "Yinelendi (Ctrl+Y).";
    }
  });
  document.getElementById("btnCalReset")?.addEventListener("click", () => {
    pushUndoCheckpoint();
    layoutState = cloneLayout(PLAY_ARENA_LAYOUT_DEFAULT);
    applyPlayArenaLayout(layoutState, activeOrientation);
    if (enabled) buildHandleLayer();
    updatePanelPreview();
    const fb = document.getElementById("playCalFeedback");
    if (fb) fb.textContent = "Varsayilan yerlesim yuklendi.";
  });

  window.addEventListener("resize", () => {
    if (enabled) syncHandles();
  });

  return {
    applyPlayArenaLayout,
    loadPlayArenaLayout,
    setCalibrationOrientation,
    getPlayArenaLayout,
    isEnabled: () => enabled,
  };
}

export function shouldSkipAutoHudPosition() {
  const arena = getArenaEl();
  return Boolean(enabled || arena?.dataset?.calHudTop === "1");
}