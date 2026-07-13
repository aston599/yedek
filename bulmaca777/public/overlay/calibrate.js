const FRAME_W = 1080;
const FRAME_H = 1920;
const calParams = new URLSearchParams(window.location.search);
const CAL_ROOM_ID = (calParams.get("room") || "").trim();

function layoutStorageKey() {
  return CAL_ROOM_ID
    ? `bulmaca_layout_vertical_${CAL_ROOM_ID}`
    : "bulmaca_layout_vertical";
}

async function publishLayoutToServer(cfg) {
  if (!CAL_ROOM_ID) {
    throw new Error("Oda seçilmedi — URL'de ?room=ODA_KODU gerekli");
  }
  const res = await fetch(
    `/api/rooms/${encodeURIComponent(CAL_ROOM_ID)}/layout/vertical`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(cfg),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || res.statusText || "Kayıt başarısız");
  }
}

async function fetchRoomLayoutFromServer() {
  if (!CAL_ROOM_ID) return null;
  const res = await fetch(
    `/api/rooms/${encodeURIComponent(CAL_ROOM_ID)}/layout/vertical`,
    { cache: "no-store" }
  );
  if (!res.ok) return null;
  return res.json();
}

const DEFAULT = {
  live: { top: 14, left: 50 },
  question: { left: 22, top: 26.4, width: 57.8, height: 16.3 },
  answer: { left: 11, top: 41.8, width: 82, height: 4.2 },
  feed: {
    left: 25.6,
    top: 54.7,
    width: 66.9,
    height: 38.8,
    padTop: 1.1,
    padLeft: 1.2,
    padRight: 5.2,
  },
  counter: { top: 27.1, right: 39 },
  questionMeta: { left: 21.8, top: 26.1, width: 57, height: 4.7 },
  feedGrid: { avatar: 10.5, points: 22, check: 10, gap: 1.1, pointsInset: 5, checkInset: 0 },
  feedSlots: 7,
  scales: {
    live: 2,
    counter: 2,
    questionMeta: 2,
    question: 2,
    answer: 1,
    feedAvatar: 1.1,
    feedName: 2,
    feedPoints: 2,
    feedCheck: 1,
    winnerHint: 1.3,
    winnerName: 1.2,
    winnerAnswer: 1.85,
  },
};

let layout = structuredClone(DEFAULT);

const frame = document.getElementById("layout");
const feedList = document.getElementById("feedList");
const output = document.getElementById("calOutput");

const names = [
  "ZekiBulmaca",
  "HizliCozucu",
  "BulmacaSever",
  "OyuncuMert",
  "MantikliAdam",
  "CevapciKiz",
  "UstaCozum",
];
const demoPoints = [15, 12, 10, 8, 6, 5, 4];

function mergeImportedLayout(parsed) {
  const merged = structuredClone(DEFAULT);
  if (parsed.question) Object.assign(merged.question, parsed.question);
  if (parsed.answer) Object.assign(merged.answer, parsed.answer);
  if (parsed.feed) Object.assign(merged.feed, parsed.feed);
  if (parsed.counter) Object.assign(merged.counter, parsed.counter);
  if (parsed.questionMeta) Object.assign(merged.questionMeta, parsed.questionMeta);
  if (parsed.live) Object.assign(merged.live, parsed.live);
  if (parsed.feedGrid) Object.assign(merged.feedGrid, parsed.feedGrid);
  if (parsed.feedSlots != null) merged.feedSlots = parsed.feedSlots;
  merged.scales = BulmacaLayoutScales.merge(parsed.scales);
  return merged;
}

function pullCurrentToJson() {
  readFromHandles();
  readGridFromControls();
  readScalesFromControls();
  if (output) output.value = JSON.stringify(layout, null, 2);
}

async function importJsonFromTextarea() {
  const raw = (output?.value || "").trim();
  if (!raw) {
    alert("Önce JSON yapıştırın.");
    return;
  }
  try {
    layout = mergeImportedLayout(JSON.parse(raw));
    applyLayout(layout);
    const save = document.getElementById("importSaveLocal")?.checked !== false;
    if (save) {
      localStorage.setItem(layoutStorageKey(), JSON.stringify(layout));
      try {
        await publishLayoutToServer(layout);
        alert("JSON uygulandı. OBS ve canlı önizleme güncellendi.");
      } catch (err) {
        alert(`JSON uygulandı (yerel). Sunucu: ${err.message}`);
      }
    } else {
      alert("JSON uygulandı (kaydedilmedi).");
    }
  } catch (err) {
    alert(`Geçersiz JSON: ${err.message}`);
  }
}

async function exportJsonToClipboard() {
  pullCurrentToJson();
  const text = output?.value || JSON.stringify(layout, null, 2);
  try {
    await navigator.clipboard.writeText(text);
    alert("JSON panoya kopyalandı.");
  } catch {
    output?.select();
  }
}

function seedFeed() {
  feedList.innerHTML = "";
  for (let i = 0; i < DEFAULT.feedSlots; i++) {
    const li = document.createElement("li");
    const rank = i + 1;
    li.className = "feed-row" + (rank <= 3 ? ` rank-${rank}` : "");
    const avatar = `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(names[i])}`;
    li.innerHTML = `
      <span class="feed-avatar"><img src="${avatar}" alt="" /></span>
      <span class="feed-name">@${names[i]}</span>
      <span class="feed-points">${demoPoints[i]} Puan</span>
      <span class="feed-check">✓</span>`;
    feedList.appendChild(li);
  }
}

function applyLayout(cfg = layout) {
  layout = cfg;
  const q = cfg.question;
  const a = cfg.answer;
  const f = cfg.feed;
  const c = cfg.counter;
  const qm = cfg.questionMeta;
  const g = cfg.feedGrid || DEFAULT.feedGrid;
  const live = cfg.live || DEFAULT.live;

  if (live.top != null) frame.style.setProperty("--live-top", `${live.top}%`);
  if (live.left != null) frame.style.setProperty("--live-left", `${live.left}%`);

  frame.style.setProperty("--q-left", `${q.left}%`);
  frame.style.setProperty("--q-top", `${q.top}%`);
  frame.style.setProperty("--q-width", `${q.width}%`);
  frame.style.setProperty("--q-height", `${q.height}%`);
  frame.style.setProperty("--a-left", `${a.left}%`);
  frame.style.setProperty("--a-top", `${a.top}%`);
  frame.style.setProperty("--a-width", `${a.width}%`);
  frame.style.setProperty("--a-height", `${a.height}%`);
  frame.style.setProperty("--f-left", `${f.left}%`);
  frame.style.setProperty("--f-top", `${f.top}%`);
  frame.style.setProperty("--f-width", `${f.width}%`);
  frame.style.setProperty("--f-height", `${f.height}%`);
  frame.style.setProperty("--f-pad-top", `${f.padTop ?? 1.1}%`);
  frame.style.setProperty("--feed-pad-left", `${f.padLeft ?? f.padX ?? 1.2}%`);
  frame.style.setProperty("--feed-pad-right", `${f.padRight ?? f.padX ?? 3.2}%`);
  frame.style.setProperty("--c-top", `${c.top}%`);
  frame.style.setProperty("--c-right", `${c.right}%`);
  if (qm) {
    frame.style.setProperty("--qm-left", `${qm.left}%`);
    frame.style.setProperty("--qm-top", `${qm.top}%`);
    frame.style.setProperty("--qm-width", `${qm.width}%`);
    frame.style.setProperty("--qm-height", `${qm.height}%`);
  } else if (q) {
    frame.style.setProperty("--qm-left", `${q.left}%`);
    frame.style.setProperty("--qm-top", `${q.top}%`);
    frame.style.setProperty("--qm-width", `${q.width}%`);
    frame.style.setProperty("--qm-height", `4.5%`);
  }
  frame.style.setProperty("--grid-avatar", `${g.avatar}%`);
  frame.style.setProperty("--grid-points", `${g.points ?? 13.8}%`);
  frame.style.setProperty("--grid-check", `${g.check ?? 5.2}%`);
  frame.style.setProperty("--grid-gap", `${g.gap ?? 1.1}%`);
  frame.style.setProperty("--points-inset", `${g.pointsInset ?? 0}%`);
  frame.style.setProperty("--check-inset", `${g.checkInset ?? 0}%`);
  BulmacaLayoutScales.apply(frame, cfg.scales);

  syncGridControls();
  syncScaleControls();
  syncHandles();
  fitCalibrateQuestionText();
  output.value = JSON.stringify(cfg, null, 2);
}

function fitCalibrateQuestionText() {
  const card = document.getElementById("questionCard");
  const body = card?.querySelector(".question-body");
  const hintEl = document.getElementById("hintText");
  const textEl = document.getElementById("questionText");
  if (!body || !textEl || card?.classList.contains("hidden")) return;
  const text = (textEl.textContent || "").trim();
  if (!text) return;

  const scale = Number(
    getComputedStyle(frame).getPropertyValue("--scale-question").trim()
  ) || 1;
  const minPx = Math.max(12, Math.round(13 * scale));
  const maxPx = Math.round(30 * scale);
  const width = Math.max(72, body.clientWidth - 10);
  const hintH =
    hintEl && (hintEl.textContent || "").trim() ? hintEl.offsetHeight + 8 : 0;
  const slot = card.closest(".slot-puzzle");
  const slotRect = slot?.getBoundingClientRect();
  const frameRect = frame.getBoundingClientRect();
  const extraDown =
    slotRect && frameRect
      ? Math.max(0, frameRect.bottom - slotRect.bottom - 20)
      : 0;
  const maxH = Math.max(56, body.clientHeight - hintH + extraDown * 0.9);

  textEl.style.maxWidth = `${width}px`;
  textEl.style.whiteSpace = "normal";
  textEl.style.wordBreak = "break-word";

  let lo = minPx;
  let hi = maxPx;
  let best = minPx;
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2);
    textEl.style.fontSize = `${mid}px`;
    if (
      textEl.scrollWidth <= width + 2 &&
      textEl.scrollHeight <= maxH + 2
    ) {
      best = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  textEl.style.fontSize = `${best}px`;
}

function readScalesFromControls() {
  if (!layout.scales) layout.scales = { ...BulmacaLayoutScales.DEFAULT };
  for (const input of document.querySelectorAll("[data-scale-key]")) {
    layout.scales[input.dataset.scaleKey] = Number(input.value) / 100;
  }
}

function syncScaleControls() {
  const s = BulmacaLayoutScales.merge(layout.scales);
  for (const input of document.querySelectorAll("[data-scale-key]")) {
    const pct = Math.round((s[input.dataset.scaleKey] ?? 1) * 100);
    input.value = String(pct);
    const valEl = input.closest(".cal-scale-item")?.querySelector(".cal-scale-val");
    if (valEl) valEl.textContent = `${pct}%`;
  }
}

function initScaleControls() {
  const host = document.getElementById("scaleControls");
  if (!host) return;
  for (const item of BulmacaLayoutScales.KEYS) {
    const wrap = document.createElement("label");
    wrap.className = "cal-scale-item";
    wrap.title = `${item.label} boyutu`;
    wrap.innerHTML = `<span class="cal-scale-label">${item.label}</span>
      <input type="range" data-scale-key="${item.key}" min="50" max="200" step="5" value="100" />
      <span class="cal-scale-val">100%</span>`;
    host.appendChild(wrap);
    wrap.querySelector("input").addEventListener("input", (e) => {
      const pct = e.target.value;
      wrap.querySelector(".cal-scale-val").textContent = `${pct}%`;
      readScalesFromControls();
      applyLayout(layout);
    });
  }
}

function syncGridControls() {
  const g = layout.feedGrid || DEFAULT.feedGrid;
  const f = layout.feed || DEFAULT.feed;
  const map = {
    gridAvatar: g.avatar,
    gridPoints: g.points,
    gridCheck: g.check,
    gridGap: g.gap,
    gridPointsInset: g.pointsInset ?? 0,
    gridCheckInset: g.checkInset ?? 0,
    feedPadRight: f.padRight ?? 3.2,
  };
  for (const [id, val] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el) el.value = String(val);
  }
}

function readGridFromControls() {
  const num = (id, fallback) => {
    const el = document.getElementById(id);
    if (!el) return fallback;
    const v = Number(el.value);
    return Number.isFinite(v) ? v : fallback;
  };
  layout.feedGrid = {
    avatar: num("gridAvatar", DEFAULT.feedGrid.avatar),
    points: num("gridPoints", DEFAULT.feedGrid.points),
    check: num("gridCheck", DEFAULT.feedGrid.check),
    gap: num("gridGap", DEFAULT.feedGrid.gap),
    pointsInset: num("gridPointsInset", 0),
    checkInset: num("gridCheckInset", 0),
  };
  layout.feed = {
    ...layout.feed,
    padRight: num("feedPadRight", DEFAULT.feed.padRight),
    padLeft: layout.feed?.padLeft ?? DEFAULT.feed.padLeft,
    padTop: layout.feed?.padTop ?? DEFAULT.feed.padTop,
  };
}

function pct(v, total) {
  return Math.round((v / total) * 1000) / 10;
}

function setPreviewScene(scene) {
  const frame = document.getElementById("layout");
  const idle = document.getElementById("idleCard");
  const q = document.getElementById("questionCard");
  const w = document.getElementById("winnerCard");
  if (!frame || !q || !w) return;

  frame.dataset.state = scene === "winner" ? "winner" : scene === "active" ? "active" : "idle";
  idle?.classList.toggle("hidden", scene !== "idle");
  q.classList.toggle("hidden", scene !== "active");
  w.classList.toggle("hidden", scene !== "winner");

  const meta = document.getElementById("questionMeta");
  if (meta) meta.textContent = scene === "active" ? "Soru 4 / 50 · 10p" : "";

  document.querySelectorAll(".cal-scene-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.scene === scene);
  });
}

function syncHandles() {
  for (const h of document.querySelectorAll(".cal-handle")) {
    const key = h.dataset.slot;
    if (key === "question" || key === "feed" || key === "questionMeta") {
      const box = layout[key];
      h.style.left = `${box.left}%`;
      h.style.top = `${box.top}%`;
      h.style.width = `${box.width}%`;
      h.style.height = `${box.height}%`;
      h.style.right = "auto";
    } else if (key === "counter") {
      const c = layout.counter;
      const w = h.offsetWidth || 140;
      const leftPx = FRAME_W * (1 - c.right / 100) - w;
      h.style.top = `${c.top}%`;
      h.style.left = `${Math.max(0, leftPx)}px`;
      h.style.right = "auto";
    } else if (key === "live") {
      const l = layout.live || DEFAULT.live;
      const w = h.offsetWidth || 200;
      const leftPx = (FRAME_W * (l.left ?? 50)) / 100 - w / 2;
      h.style.top = `${l.top ?? 14}%`;
      h.style.left = `${Math.max(0, Math.min(FRAME_W - w, leftPx))}px`;
      h.style.right = "auto";
    }
  }
}

function readFromHandles() {
  const qEl = document.querySelector('.cal-handle[data-slot="question"]');
  const qmEl = document.querySelector('.cal-handle[data-slot="questionMeta"]');
  const fEl = document.querySelector('.cal-handle[data-slot="feed"]');
  const cEl = document.querySelector('.cal-handle[data-slot="counter"]');
  const liveEl = document.querySelector('.cal-handle[data-slot="live"]');

  const live =
    liveEl && liveEl.offsetWidth
      ? {
          left: pct(liveEl.offsetLeft + liveEl.offsetWidth / 2, FRAME_W),
          top: pct(liveEl.offsetTop, FRAME_H),
        }
      : layout.live || { ...DEFAULT.live };

  layout = {
    live,
    question: {
      left: pct(qEl.offsetLeft, FRAME_W),
      top: pct(qEl.offsetTop, FRAME_H),
      width: pct(qEl.offsetWidth, FRAME_W),
      height: pct(qEl.offsetHeight, FRAME_H),
    },
    answer: layout.answer || { ...DEFAULT.answer },
    questionMeta: qmEl?.offsetWidth
      ? {
          left: pct(qmEl.offsetLeft, FRAME_W),
          top: pct(qmEl.offsetTop, FRAME_H),
          width: pct(qmEl.offsetWidth, FRAME_W),
          height: pct(qmEl.offsetHeight, FRAME_H),
        }
      : layout.questionMeta || { ...DEFAULT.questionMeta },
    feed: {
      left: pct(fEl.offsetLeft, FRAME_W),
      top: pct(fEl.offsetTop, FRAME_H),
      width: pct(fEl.offsetWidth, FRAME_W),
      height: pct(fEl.offsetHeight, FRAME_H),
      padTop: layout.feed?.padTop ?? DEFAULT.feed.padTop,
      padLeft: layout.feed?.padLeft ?? DEFAULT.feed.padLeft,
      padRight: layout.feed?.padRight ?? DEFAULT.feed.padRight,
    },
    counter: {
      top: pct(cEl.offsetTop, FRAME_H),
      right: pct(FRAME_W - cEl.offsetLeft - cEl.offsetWidth, FRAME_W),
    },
    feedGrid: layout.feedGrid || DEFAULT.feedGrid,
    feedSlots: layout.feedSlots || 7,
    scales: BulmacaLayoutScales.merge(layout.scales),
  };
  applyLayout(layout);
}

function makeHandle(slot, label, resizable) {
  const el = document.createElement("div");
  el.className = `cal-handle ${slot}`;
  el.dataset.slot = slot;
  el.innerHTML = `<span class="label">${label}</span>`;
  if (resizable) {
    const grip = document.createElement("span");
    grip.style.cssText =
      "position:absolute;right:0;bottom:0;width:14px;height:14px;cursor:nwse-resize;background:rgba(255,255,255,0.5)";
    el.appendChild(grip);
    grip.addEventListener("pointerdown", (e) => startResize(e, el));
  }
  el.addEventListener("pointerdown", (e) => {
    if (e.target.tagName === "SPAN" && !e.target.classList.contains("label")) return;
    startDrag(e, el);
  });
  frame.appendChild(el);
  return el;
}

function startDrag(e, el) {
  e.preventDefault();
  const startX = e.clientX;
  const startY = e.clientY;
  const baseL = el.offsetLeft;
  const baseT = el.offsetTop;
  const scale = Number(document.getElementById("zoomRange").value) / 100;

  const move = (ev) => {
    const dx = (ev.clientX - startX) / scale;
    const dy = (ev.clientY - startY) / scale;
    el.style.right = "auto";
    el.style.left = `${Math.max(0, Math.min(FRAME_W - el.offsetWidth, baseL + dx))}px`;
    el.style.top = `${Math.max(0, Math.min(FRAME_H - el.offsetHeight, baseT + dy))}px`;
    readFromHandles();
  };
  const up = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", up);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up);
}

function startResize(e, el) {
  e.stopPropagation();
  e.preventDefault();
  const startX = e.clientX;
  const startY = e.clientY;
  const baseW = el.offsetWidth;
  const baseH = el.offsetHeight;
  const scale = Number(document.getElementById("zoomRange").value) / 100;

  const move = (ev) => {
    const dw = (ev.clientX - startX) / scale;
    const dh = (ev.clientY - startY) / scale;
    el.style.width = `${Math.max(40, baseW + dw)}px`;
    el.style.height = `${Math.max(24, baseH + dh)}px`;
    readFromHandles();
  };
  const up = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", up);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up);
}

async function init() {
  const embed = new URLSearchParams(window.location.search).get("embed") === "1";
  if (embed) document.body.classList.add("cal-embed");

  seedFeed();
  document.getElementById("hintText").textContent = "HARF KARMAŞASI";
  document.getElementById("questionText").textContent =
    "Kurtuluş Savaşı'nın başlatıldığı kabul edilen tarih hangi gündür?";
  const meta = document.getElementById("questionMeta");
  if (meta) meta.textContent = "Soru 4 / 50 · 10p";

  try {
    const key = layoutStorageKey();
    const saved = localStorage.getItem(key);
    if (saved) {
      layout = JSON.parse(saved);
    } else {
      const fromRoom = await fetchRoomLayoutFromServer();
      if (fromRoom) layout = fromRoom;
      else {
        const res = await fetch("/overlay/layout.vertical.json");
        if (res.ok) layout = await res.json();
      }
    }
  } catch {
    layout = structuredClone(DEFAULT);
  }

  const roomBadge = document.getElementById("calRoomBadge");
  if (roomBadge) {
    if (CAL_ROOM_ID) {
      roomBadge.textContent = `Oda: ${CAL_ROOM_ID}`;
      roomBadge.classList.remove("hidden");
    } else {
      roomBadge.textContent = "Oda seçilmedi";
      roomBadge.classList.add("hidden");
    }
  }

  if (!layout.scales) layout.scales = { ...BulmacaLayoutScales.DEFAULT };

  initScaleControls();
  applyLayout(layout);
  makeHandle("live", "Canlı yayın", false);
  makeHandle("questionMeta", "Soru sayacı (4/50)", true);
  makeHandle("question", "Bulmaca metni", true);
  makeHandle("feed", "Puan listesi", true);
  makeHandle("counter", "Sayaç (boşta)", false);

  document.querySelectorAll(".cal-scene-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      setPreviewScene(btn.dataset.scene || "active");
      requestAnimationFrame(fitCalibrateQuestionText);
    });
  });
  setPreviewScene("active");
  requestAnimationFrame(fitCalibrateQuestionText);

  const defaultZoom = embed ? 45 : 55;
  const zoomRange = document.getElementById("zoomRange");
  if (zoomRange) zoomRange.value = String(defaultZoom);
  document.getElementById("zoomLabel").textContent = `${defaultZoom}%`;
  document.getElementById("calStage").style.transform = `scale(${defaultZoom / 100})`;

  zoomRange?.addEventListener("input", (e) => {
    const z = Number(e.target.value);
    document.getElementById("zoomLabel").textContent = `${z}%`;
    document.getElementById("calStage").style.transform = `scale(${z / 100})`;
  });

  for (const id of [
    "gridAvatar",
    "gridPoints",
    "gridCheck",
    "gridGap",
    "gridPointsInset",
    "gridCheckInset",
    "feedPadRight",
  ]) {
    document.getElementById(id)?.addEventListener("input", () => {
      readGridFromControls();
      applyLayout(layout);
    });
  }

  document.getElementById("btnReset").addEventListener("click", () => {
    localStorage.removeItem(layoutStorageKey());
    layout = structuredClone(DEFAULT);
    applyLayout(layout);
  });

  document.getElementById("btnApply").addEventListener("click", async () => {
    if (!CAL_ROOM_ID) {
      alert("Bu yayın için oda kodu gerekli. Panelden Kalibrasyon sayfasını açın.");
      return;
    }
    readFromHandles();
    readGridFromControls();
    readScalesFromControls();
    localStorage.setItem(layoutStorageKey(), JSON.stringify(layout));
    try {
      await publishLayoutToServer(layout);
      alert(`Kaydedildi (oda ${CAL_ROOM_ID}). OBS bu yayının overlay linkini kullanmalı.`);
    } catch (err) {
      alert(`Kayıt başarısız: ${err.message}`);
    }
  });

  document.getElementById("btnImportJson")?.addEventListener("click", importJsonFromTextarea);
  document.getElementById("btnImportJsonBottom")?.addEventListener("click", importJsonFromTextarea);
  document.getElementById("btnPullJson")?.addEventListener("click", pullCurrentToJson);
  document.getElementById("btnExport")?.addEventListener("click", exportJsonToClipboard);
  document.getElementById("btnExportBottom")?.addEventListener("click", exportJsonToClipboard);
}

init();
