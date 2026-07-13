const appOrigin = window.location.origin;
const params = new URLSearchParams(location.search);
const fetchOpts = { credentials: "include" };

let currentUser = null;

function getRoomId() {
  const fromUrl = new URLSearchParams(location.search).get("room");
  return fromUrl || localStorage.getItem("bulmaca_room") || "";
}

function setRoomId(id) {
  localStorage.setItem("bulmaca_room", id);
  const u = new URL(location.href);
  if (id) u.searchParams.set("room", id);
  else u.searchParams.delete("room");
  history.replaceState(null, "", u);
  if (id) params.set("room", id);
  else params.delete("room");
}

function isDashboardVisible() {
  const dash = document.getElementById("dashboard");
  return Boolean(dash && !dash.classList.contains("hidden"));
}

const RECENT_ROOMS_KEY = "bulmaca_recent_rooms";
const RECENT_ROOMS_MAX = 6;

function roomModeStorageKey(roomId) {
  return `bulmaca_mode_${roomId}`;
}

function roomStreamStorageKey(roomId) {
  return `bulmaca_stream_${roomId}`;
}

function rememberRoomGameMode(roomId, mode) {
  if (!roomId || !mode) return;
  localStorage.setItem(roomModeStorageKey(roomId), normalizeGameMode(mode));
}

function applyCachedRoomGameMode(roomId) {
  if (!roomId) return;
  const cached = localStorage.getItem(roomModeStorageKey(roomId));
  if (cached) applyDashboardGameMode(cached);
}

const STREAM_URL_ROW_MAX = 12;
let streamUrlListUiReady = false;

function parseStreamUrlDraftText(raw = "") {
  return String(raw || "")
    .split(/[\n\r,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function getStreamUrlListHost() {
  return document.getElementById("streamUrlList");
}

function collectStreamUrlsFromDom() {
  const host = getStreamUrlListHost();
  if (!host) return [];
  const seen = new Set();
  const out = [];
  for (const el of host.querySelectorAll(".stream-url-row-input")) {
    const v = normalizeStreamUrlDraftClient(el.value).trim();
    if (!v || v === "[object Object]" || seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out;
}

function getStreamUrlDraftText() {
  return collectStreamUrlsFromDom().join("\n");
}

function isStreamUrlListFocused() {
  const host = getStreamUrlListHost();
  if (!host) return false;
  const ae = document.activeElement;
  return Boolean(ae && host.contains(ae));
}

function createStreamUrlRow(value = "") {
  const row = document.createElement("div");
  row.className = "stream-url-row";
  row.setAttribute("role", "listitem");

  const input = document.createElement("input");
  input.type = "url";
  input.className = "field-input stream-url-row-input";
  input.placeholder = "https://www.youtube.com/watch?v=… veya youtu.be/…";
  input.autocomplete = "off";
  input.value = value;

  const dup = document.createElement("button");
  dup.type = "button";
  dup.className = "btn stream-url-row-dup";
  dup.textContent = "Çoğalt";
  dup.title = "Bu satırı kopyala";

  const rm = document.createElement("button");
  rm.type = "button";
  rm.className = "btn stream-url-row-remove";
  rm.textContent = "×";
  rm.title = "Satırı kaldır";
  rm.setAttribute("aria-label", "Linki kaldır");

  row.append(input, dup, rm);
  return row;
}

function renderStreamUrlRows(urls) {
  const host = getStreamUrlListHost();
  if (!host) return;
  const items = Array.isArray(urls) ? urls.filter(Boolean) : [];
  const rows = items.length ? items.slice(0, STREAM_URL_ROW_MAX) : [""];
  host.replaceChildren();
  for (const url of rows) {
    host.appendChild(createStreamUrlRow(url));
  }
}

function addStreamUrlRow(value = "") {
  const host = getStreamUrlListHost();
  if (!host) return;
  if (host.querySelectorAll(".stream-url-row").length >= STREAM_URL_ROW_MAX) {
    if (typeof setYoutubeActionBanner === "function") {
      setYoutubeActionBanner(`En fazla ${STREAM_URL_ROW_MAX} link ekleyebilirsiniz.`, "warn");
    }
    return;
  }
  host.appendChild(createStreamUrlRow(value));
  host.querySelector(".stream-url-row:last-child .stream-url-row-input")?.focus();
}

function initStreamUrlListUi() {
  if (streamUrlListUiReady) return;
  streamUrlListUiReady = true;
  const host = getStreamUrlListHost();
  if (!host) return;
  if (!host.querySelector(".stream-url-row")) {
    renderStreamUrlRows([""]);
  }
  host.addEventListener("input", () => {
    clearTimeout(streamUrlParseTimer);
    streamUrlParseTimer = setTimeout(updateStreamUrlPreview, 350);
    scheduleStreamUrlDraftSave();
  });
  host.addEventListener("click", (e) => {
    const row = e.target.closest(".stream-url-row");
    if (!row) return;
    if (e.target.closest(".stream-url-row-dup")) {
      const val = row.querySelector(".stream-url-row-input")?.value?.trim() || "";
      addStreamUrlRow(val);
      scheduleStreamUrlDraftSave();
      void updateStreamUrlPreview();
      return;
    }
    if (e.target.closest(".stream-url-row-remove")) {
      const rows = host.querySelectorAll(".stream-url-row");
      if (rows.length <= 1) {
        const inp = row.querySelector(".stream-url-row-input");
        if (inp) inp.value = "";
      } else {
        row.remove();
      }
      scheduleStreamUrlDraftSave();
      void updateStreamUrlPreview();
    }
  });
  host.addEventListener(
    "blur",
    (e) => {
      if (e.target.classList?.contains("stream-url-row-input")) {
        void persistStreamUrlDraft();
      }
    },
    true
  );
  document.getElementById("btnStreamUrlAdd")?.addEventListener("click", () => {
    addStreamUrlRow("");
    scheduleStreamUrlDraftSave();
  });
}

function normalizeStreamUrlDraftClient(value) {
  if (value == null) return "";
  if (typeof value === "string") {
    const s = value.trim();
    return s === "[object Object]" ? "" : s;
  }
  if (Array.isArray(value)) {
    return value.map((v) => String(v || "").trim()).filter(Boolean).join("\n");
  }
  return "";
}

function getStreamUrlDraft(config = {}, roomId = getRoomId()) {
  const fromServer = normalizeStreamUrlDraftClient(config.streamUrlDraft);
  if (fromServer) return fromServer;
  if (!roomId) return "";
  return localStorage.getItem(roomStreamStorageKey(roomId)) || "";
}

let streamDraftSaveTimer = null;

function scheduleStreamUrlDraftSave() {
  clearTimeout(streamDraftSaveTimer);
  streamDraftSaveTimer = setTimeout(() => {
    void persistStreamUrlDraft();
  }, 500);
}

async function persistStreamUrlDraft() {
  const roomId = getRoomId();
  const raw = getStreamUrlDraftText();
  if (!roomId) return;
  localStorage.setItem(roomStreamStorageKey(roomId), raw);
  try {
    sessionStorage.setItem(
      `bulmaca_panel_${roomId}`,
      JSON.stringify({
        streamUrlDraft: raw,
        gameMode: currentRoomGameMode,
        savedAt: Date.now(),
      })
    );
  } catch {
    /* private mode */
  }
  try {
    await api("/config", {
      method: "PATCH",
      body: JSON.stringify({ streamUrlDraft: String(raw || "") }),
    });
  } catch {
    /* çevrimdışı / oturum */
  }
}

function restorePanelDraftFromSession(roomId) {
  if (!roomId) return;
  try {
    const raw = sessionStorage.getItem(`bulmaca_panel_${roomId}`);
    if (!raw) return;
    const d = JSON.parse(raw);
    // Oyun modu sunucudan gelir; session taslağı modu ezmesin (Uygula sonrası bulmacaya dönme)
    if (d.streamUrlDraft && !getStreamUrlDraftText()) {
      renderStreamUrlRows(parseStreamUrlDraftText(d.streamUrlDraft));
      void updateStreamUrlPreview();
    }
  } catch {
    /* yoksay */
  }
}

function flushRoomPanelDraft() {
  const roomId = getRoomId();
  if (!roomId) return;
  const raw = getStreamUrlDraftText();
  localStorage.setItem(roomStreamStorageKey(roomId), raw);
  try {
    sessionStorage.setItem(
      `bulmaca_panel_${roomId}`,
      JSON.stringify({
        streamUrlDraft: raw,
        gameMode: currentRoomGameMode,
        savedAt: Date.now(),
      })
    );
  } catch {
    /* yoksay */
  }
  if (raw) {
    void api("/config", {
      method: "PATCH",
      body: JSON.stringify({ streamUrlDraft: String(raw || "") }),
    }).catch(() => {});
  }
}

function restoreStreamUrlField(config = {}, yt = {}) {
  if (!getStreamUrlListHost() || isStreamUrlListFocused()) return;

  const draft = getStreamUrlDraft(config, getRoomId());
  if (draft) {
    renderStreamUrlRows(parseStreamUrlDraftText(draft));
    void updateStreamUrlPreview();
    return;
  }

  const urls = (
    Array.isArray(yt.streamUrls) && yt.streamUrls.length
      ? yt.streamUrls
      : yt.streamUrl
        ? [yt.streamUrl]
        : []
  )
    .map((u) => normalizeStreamUrlDraftClient(u))
    .filter((u) => u && u !== "[object Object]");
  const vid = yt.videoId || config.videoId;
  const fallback = vid ? `https://www.youtube.com/watch?v=${vid}` : "";
  renderStreamUrlRows(urls.length ? urls : fallback ? [fallback] : [""]);
  if (urls.length || fallback) void updateStreamUrlPreview();
}
let userRoomsList = [];
let roomSwitcherBusy = false;
/** Oda değişince eski /youtube/status yanıtlarını yoksay */
let roomPanelGeneration = 0;

function gameStateLabel(state) {
  if (state === "running" || state === "active") return "Yayında";
  if (state === "idle") return "Hazır";
  return state || "—";
}

function isGameLive(state) {
  return state === "running" || state === "active";
}

function buildRoomStatusPills(r) {
  const yt = r.youtube || {};
  const pills = [];
  pills.push({ text: gameModeLabel(r.gameMode), kind: "mode" });
  if (yt.chatConnected) {
    pills.push({ text: "Sohbet bağlı", kind: "ok" });
  } else {
    pills.push({ text: "Sohbet kapalı", kind: "warn" });
  }
  if (isGameLive(r.gameState)) {
    pills.push({ text: "Oyun yayında", kind: "ok" });
  }
  return pills;
}

function renderRoomStatusPillsHtml(r) {
  return buildRoomStatusPills(r)
    .map(
      (p) =>
        `<span class="room-hub-pill room-hub-pill--${escapeHtml(p.kind)}">${escapeHtml(p.text)}</span>`
    )
    .join("");
}

function renderRoomsHub() {
  const list = document.getElementById("roomList");
  if (!list) return;
  list.innerHTML = "";
  if (!userRoomsList.length) {
    list.className = "rooms-hub-grid rooms-hub-grid--empty";
    list.innerHTML =
      '<p class="rooms-hub-empty">Henüz yayın odası yok. Aşağıdan yeni oda oluşturun, canlı link ile sohbete bağlanın.</p>';
    return;
  }
  list.className = "rooms-hub-grid";

  userRoomsList.forEach((r) => {
    const yt = r.youtube || {};
    const card = document.createElement("article");
    card.className = "room-hub-card";
    card.setAttribute("role", "listitem");

    const displayName = escapeHtml(r.displayName || r.name);
    const avatar = `<div class="room-hub-avatar room-hub-avatar--placeholder" aria-hidden="true">${escapeHtml((displayName || "?").charAt(0))}</div>`;

    card.innerHTML = `
      ${avatar}
      <div class="room-hub-body">
        <header class="room-hub-header">
          <div>
            <h3 class="room-hub-title">${displayName}</h3>
            <code class="room-hub-code">${escapeHtml(r.id)}</code>
          </div>
          <span class="room-hub-game ${isGameLive(r.gameState) ? "room-hub-game--live" : ""}">${escapeHtml(gameStateLabel(r.gameState))}</span>
        </header>
        <div class="room-hub-pills">${renderRoomStatusPillsHtml(r)}</div>
        <div class="room-hub-actions">
          <button type="button" class="btn btn-hub-primary room-hub-open">Panele gir →</button>
          <button type="button" class="btn btn-hub-secondary room-hub-calibrate" title="Bu yayının overlay yerleşimi">Kalibrasyon</button>
          <button type="button" class="btn btn-hub-secondary room-hub-copy" title="Sorular ve bot ayarları kopyalanır; canlı link kopyalanmaz">Odayı kopyala</button>
          <button type="button" class="btn btn-hub-danger room-hub-delete">Odayı sil</button>
        </div>
      </div>
    `;

    const openBtn = card.querySelector(".room-hub-open");
    openBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      void openRoomPanel(r.id, openBtn);
    });
    card.addEventListener("click", (e) => {
      if (e.target.closest("button, a, input, select, textarea")) return;
      void openRoomPanel(r.id, openBtn);
    });
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        void openRoomPanel(r.id, openBtn);
      }
    });
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute(
      "aria-label",
      `${String(displayName).replace(/<[^>]+>/g, "")} — panele gir`
    );

    card.querySelector(".room-hub-calibrate")?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openCalibratePage(r.id);
    });
    card.querySelector(".room-hub-copy")?.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        await copyBroadcastRoom(r.id);
      } catch (err) {
        log("Kopyalanamadı: " + err.message, false, { persist: true });
      } finally {
        btn.disabled = false;
      }
    });
    card.querySelector(".room-hub-delete")?.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        await deleteBroadcastRoom(r.id);
      } catch (err) {
        log("Oda silinemedi: " + err.message, false, { persist: true });
      } finally {
        btn.disabled = false;
      }
    });

    list.appendChild(card);
  });
}

function rememberRecentRoom(roomId) {
  if (!roomId) return;
  let recent = [];
  try {
    recent = JSON.parse(localStorage.getItem(RECENT_ROOMS_KEY) || "[]");
  } catch {
    recent = [];
  }
  recent = [roomId, ...recent.filter((id) => id !== roomId)].slice(0, RECENT_ROOMS_MAX);
  localStorage.setItem(RECENT_ROOMS_KEY, JSON.stringify(recent));
}

function getRecentRoomIds() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_ROOMS_KEY) || "[]");
  } catch {
    return [];
  }
}

async function fetchUserRooms() {
  const res = await fetch("/api/rooms", fetchOpts);
  if (res.status === 401) return null;
  if (!res.ok) throw new Error("Yayınlar yüklenemedi");
  userRoomsList = await res.json();
  return userRoomsList;
}

function forgetRoomLocally(roomId) {
  if (!roomId) return;
  const recent = getRecentRoomIds().filter((id) => id !== roomId);
  localStorage.setItem(RECENT_ROOMS_KEY, JSON.stringify(recent));
  if (localStorage.getItem("bulmaca_room") === roomId) {
    localStorage.removeItem("bulmaca_room");
  }
}

async function copyBroadcastRoom(roomId) {
  const meta = userRoomsList.find((r) => r.id === roomId);
  const label = meta?.displayName || meta?.name || roomId;
  const defaultName = `${(meta?.name || label).replace(/\s*\(kopya\)\s*$/i, "")} (kopya)`.slice(
    0,
    80
  );
  const chosen = window.prompt(
    `«${label}» kopyalanacak.\n\n` +
      "Kopyalanır: sorular, bot adı, kazanma/yanlış mesajları.\n" +
      "Kopyalanmaz: canlı yayın linki, sohbet bağlantısı, oyun durumu.\n\n" +
      "Yeni oda adı:",
    defaultName
  );
  if (chosen === null) return false;

  const res = await fetch(`/api/rooms/${roomId}/copy`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...fetchOpts.headers },
    credentials: fetchOpts.credentials,
    body: JSON.stringify({ name: chosen.trim() || defaultName }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);

  await fetchUserRooms();
  renderRoomsHub();
  renderRoomSwitcher();
  log(`Kopya oluşturuldu: ${data.displayName || data.name || data.id}`, true, {
    persist: false,
  });

  if (window.confirm("Yeni kopya odaya şimdi girilsin mi?")) {
    await openRoomPanel(data.id);
  }
  return true;
}

function openCalibratePage(roomId) {
  const id = roomId || getRoomId();
  if (!id) {
    log("Önce bir yayın odası seçin.", false, { persist: false });
    return;
  }
  window.location.href = `/admin/calibrate.html?room=${encodeURIComponent(id)}`;
}

async function deleteBroadcastRoom(roomId) {
  const meta = userRoomsList.find((r) => r.id === roomId);
  const label = meta?.displayName || meta?.name || roomId;
  if (
    !window.confirm(
      `«${label}» yayın odası kalıcı olarak silinsin mi?\n\nSorular, günlük kayıtları ve oda dosyaları geri alınamaz.`
    )
  ) {
    return false;
  }

  const res = await fetch(`/api/rooms/${roomId}`, { method: "DELETE", ...fetchOpts });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);

  forgetRoomLocally(roomId);

  if (getRoomId() === roomId) {
    await showSetup();
  } else {
    await fetchUserRooms();
    renderRoomsHub();
    renderRoomSwitcher();
  }

  log("Yayın odası silindi.", true, { persist: false });
  return true;
}

function formatRoomOptionLabel(r) {
  const state = gameStateLabel(r.gameState);
  const yt = r.youtube || {};
  const name = r.displayName || yt.channelTitle || r.name;
  let dot = "";
  if (isGameLive(r.gameState)) dot = " ●";
  else if (yt.chatConnected) dot = " ◉";
  else if (yt.authenticated) dot = " ○";
  return `${name} (${state})${dot}`;
}

function makeRoomChip(r, active) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "room-chip" + (active ? " room-chip--active" : "");
  btn.title = `${r.name} · ${gameStateLabel(r.gameState)}`;
  const yt = r.youtube || {};
  const dot = document.createElement("span");
  dot.className = isGameLive(r.gameState)
    ? "room-chip-dot room-chip-dot--run"
    : yt.chatConnected
      ? "room-chip-dot room-chip-dot--live"
      : yt.authenticated
        ? "room-chip-dot room-chip-dot--auth"
        : "room-chip-dot";
  const name = document.createElement("span");
  name.className = "room-chip-name";
  name.textContent = r.displayName || r.youtube?.channelTitle || r.name;
  btn.append(dot, name);
  if (!active) btn.addEventListener("click", () => switchToRoom(r.id));
  return btn;
}

function renderRoomSwitcher() {
  const nav = document.getElementById("roomSwitcher");
  const select = document.getElementById("roomSwitchSelect");
  const recentEl = document.getElementById("roomSwitchRecent");
  const currentId = getRoomId();
  if (!nav || !select) return;

  nav.classList.remove("hidden");

  select.innerHTML = "";
  if (!userRoomsList.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Yayın yok";
    select.appendChild(opt);
    select.disabled = true;
  } else {
    select.disabled = false;
    userRoomsList.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = formatRoomOptionLabel(r);
      if (r.id === currentId) opt.selected = true;
      select.appendChild(opt);
    });
  }

  if (!recentEl) return;
  recentEl.innerHTML = "";
  const recentIds = getRecentRoomIds().filter(
    (id) => id !== currentId && userRoomsList.some((r) => r.id === id)
  );
  const chips = recentIds
    .map((id) => userRoomsList.find((r) => r.id === id))
    .filter(Boolean);

  if (currentId) {
    const current = userRoomsList.find((r) => r.id === currentId);
    if (current) recentEl.appendChild(makeRoomChip(current, true));
  }
  chips.forEach((r) => recentEl.appendChild(makeRoomChip(r, false)));
}

function handleRoomAccessDenied(message) {
  const badId = getRoomId();
  log(
    message ||
      "Bu yayın hesabınıza ait değil. Üst menüden kendi yayınınızı seçin.",
    false,
    { persist: true }
  );
  if (badId) {
    const recent = getRecentRoomIds().filter((id) => id !== badId);
    localStorage.setItem(RECENT_ROOMS_KEY, JSON.stringify(recent));
    localStorage.removeItem("bulmaca_room");
  }
  const u = new URL(location.href);
  u.searchParams.delete("room");
  history.replaceState(null, "", u.pathname + (u.search || ""));
  params.delete("room");
  if (socket) {
    socket.disconnect();
    socket = null;
  }
  showSetup();
}

async function verifyRoomAccess(roomId) {
  const res = await fetch(`/api/rooms/${roomId}`, { ...fetchOpts, cache: "no-store" });
  if (res.status === 401) {
    location.href = `/login/?next=${encodeURIComponent(location.pathname + location.search)}`;
    return false;
  }
  if (res.status === 403) {
    const data = await res.json().catch(() => ({}));
    handleRoomAccessDenied(data.error);
    return false;
  }
  if (!res.ok) {
    log("Yayın açılamadı.", false, { persist: true });
    showSetup();
    return false;
  }
  return true;
}

async function openRoomPanel(roomId, triggerBtn) {
  const btn = triggerBtn;
  const label = btn?.textContent || "Panele gir →";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Açılıyor…";
  }
  try {
    await switchToRoom(roomId);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = label;
    }
  }
}

async function switchToRoom(roomId) {
  if (!roomId || roomSwitcherBusy) return;
  if (roomId === getRoomId() && isDashboardVisible()) return;
  const previousRoomId = getRoomId();
  roomSwitcherBusy = true;
  try {
    await fetchUserRooms();
    if (!userRoomsList.some((r) => r.id === roomId)) {
      log(
        "Bu yayın sizin hesabınızda yok. Listeden seçin veya yeni yayın oluşturun.",
        false,
        { persist: true }
      );
      showSetup();
      return;
    }
    if (!(await verifyRoomAccess(roomId))) return;
    rememberRecentRoom(roomId);
    closePreviewModal();
    if (previousRoomId && previousRoomId !== roomId) {
      resetYoutubePanelForRoomSwitch({ clearStream: true });
    }
    document.getElementById("setupScreen")?.classList.add("hidden");
    document.getElementById("dashboard")?.classList.remove("hidden");
    await initDashboard(roomId, { skipAccessCheck: true });
  } catch (err) {
    log("Yayın geçişi hatası: " + err.message, false, { persist: true });
  } finally {
    roomSwitcherBusy = false;
  }
}

function cycleRoom(delta) {
  if (!userRoomsList.length || roomSwitcherBusy) return;
  const currentId = getRoomId();
  let idx = userRoomsList.findIndex((r) => r.id === currentId);
  if (idx < 0) idx = 0;
  const next = userRoomsList[(idx + delta + userRoomsList.length) % userRoomsList.length];
  if (next) switchToRoom(next.id);
}

function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

function api(path, opts = {}) {
  const roomId = getRoomId();
  if (!roomId) throw new Error("Yayın seçilmedi");
  return fetch(`/api/rooms/${roomId}${path}`, {
    cache: "no-store",
    ...fetchOpts,
    ...opts,
    headers: { "Content-Type": "application/json; charset=utf-8", ...opts.headers },
  });
}

const BUNDLED_APP_VERSION =
  document.querySelector('meta[name="app-version"]')?.getAttribute("content") || "";

const seenLogIds = new Set();

const OVERLAY_PARAMS = {
  motion: "1",
  particles: "50",
  ov: "7",
  scale: "cover",
};

/** Panel önizlemesi: küçük iframe’de tam görünsün (OBS linkleri cover kalır) */
const PREVIEW_OVERLAY_PARAMS = {
  ...OVERLAY_PARAMS,
  embed: "1",
  preview: "1",
  scale: "contain",
};

let previewLoadSerial = 0;

function clearPreviewFrame(frame) {
  if (!frame) return;
  frame.removeAttribute("src");
  frame.removeAttribute("srcdoc");
  frame.src = "about:blank";
  frame.classList.add("preview-frame--hidden");
}

function isChromeErrorFrame(frame) {
  if (!frame) return false;
  try {
    const href = frame.contentWindow?.location?.href || "";
    return href.startsWith("chrome-error:") || href.startsWith("chrome://");
  } catch {
    return false;
  }
}

function setPreviewFallback(visible, message = "", openUrl = "") {
  const box = document.getElementById("previewFallback");
  const text = document.getElementById("previewFallbackText");
  const link = document.getElementById("previewFallbackOpen");
  if (!box) return;
  box.classList.toggle("hidden", !visible);
  if (text) text.textContent = message;
  if (link) {
    if (openUrl) {
      link.href = openUrl;
      link.classList.remove("hidden");
    } else {
      link.href = "#";
      link.classList.add("hidden");
    }
  }
}

/** Panel önizlemesi: /overlay (oturum gerekmez; iframe güvenilir) */
function updateFootballOverlayLinks(roomId) {
  const obs = document.getElementById("btnOpenFootballOverlay");
  if (obs) obs.href = roomId ? celebrityOverlayUrl(roomId) : "/celebrity-overlay";
}

function showFootballStatus(message, type = "info") {
  const el = document.getElementById("footballActionStatus");
  if (!el) return;
  el.textContent = message;
  el.className = `celebrity-action-status celebrity-action-status--${type}`;
  el.classList.remove("hidden");
}

function updateFootballQuestionsBadge() {
  const el = document.getElementById("footballQuestionsBadge");
  if (!el || !isFootballGameMode(currentRoomGameMode)) return;
  const n = questions.filter((q) =>
    /football-/.test(String(q?.meta?.gameKind || ""))
  ).length;
  el.textContent = n
    ? `${n} futbol sorusu yüklü`
    : "Henüz paket yüklenmedi — «Oyuncu paketini yükle»";
}

function usesQuizPhotoOverlay(gameMode = currentRoomGameMode) {
  const mode = normalizeGameMode(gameMode);
  if (isFootballGameMode(mode)) return true;
  if (mode === GAME_MODE_PHOTO_BATTLE) {
    return celebrityAgeInPhotoMode();
  }
  return roomHasCelebrityQuestions();
}

function buildPreviewUrls(roomId, gameMode = currentRoomGameMode) {
  const q = (extra) => {
    const p = new URLSearchParams({ room: roomId, ...PREVIEW_OVERLAY_PARAMS });
    if (extra) Object.entries(extra).forEach(([k, v]) => p.set(k, v));
    const mode = normalizeGameMode(gameMode);
    if (mode !== GAME_MODE_PUZZLE) p.set("mode", mode);
    return p.toString();
  };
  const quizScreen = usesQuizPhotoOverlay(gameMode);
  const celebParams = new URLSearchParams({
    room: roomId,
    motion: "1",
    ...PREVIEW_OVERLAY_PARAMS,
  });
  const vertical = quizScreen
    ? `${appOrigin}/celebrity-overlay?${celebParams}`
    : `${appOrigin}/overlay?${q({ layout: "vertical" })}`;
  return {
    horizontal: `${appOrigin}/overlay?${q({ layout: "horizontal" })}`,
    vertical,
    celebrity: `${appOrigin}/celebrity-overlay?${celebParams}`,
  };
}

function previewStartupHint() {
  return "Sunucu yanıt vermiyor veya oturum süresi dolmuş olabilir.";
}

/** Sunucu yanıt veriyorsa iframe src ile yükle (srcdoc Socket.io’yu bozar) */
async function loadPreviewFrame(frame, url) {
  if (!frame || !url) return false;
  const serial = ++previewLoadSerial;
  frame.dataset.previewSerial = String(serial);
  clearPreviewFrame(frame);
  setPreviewFallback(true, "Önizleme yükleniyor…", url);

  try {
    const health = await fetch("/api/health", {
      cache: "no-store",
      credentials: "same-origin",
    });
    if (!health.ok) throw new Error("Sunucu kapalı");

    const res = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (frame.dataset.previewSerial !== String(serial)) return false;

    frame.dataset.previewExpectedUrl = url;
    const loaded = await new Promise((resolve) => {
      const onLoad = () => {
        frame.removeEventListener("load", onLoad);
        if (frame.dataset.previewSerial !== String(serial)) {
          resolve(false);
          return;
        }
        try {
          const href = frame.contentWindow?.location?.href || "";
          if (href === "about:blank" || href === "") return;
        } catch {
          /* çapraz köken — yüklendi say */
        }
        if (isChromeErrorFrame(frame)) {
          clearPreviewFrame(frame);
          delete frame.dataset.previewExpectedUrl;
          resolve(false);
          return;
        }
        frame.classList.remove("preview-frame--hidden");
        setPreviewFallback(false);
        setPreviewLoadMessage("");
        delete frame.dataset.previewExpectedUrl;
        resolve(true);
      };
      frame.addEventListener("load", onLoad, { once: true });
      frame.removeAttribute("srcdoc");
      frame.src = url;
    });
    if (!loaded) throw new Error("Önizleme iframe açılamadı");
    return true;
  } catch (err) {
    if (frame.dataset.previewSerial !== String(serial)) return false;
    clearPreviewFrame(frame);
    const roomId = new URL(url, appOrigin).searchParams.get("room");
    const tabUrl = roomId ? buildUrls(roomId).vertical : url;
    setPreviewLoadMessage(`${err.message}. ${previewStartupHint()}`);
    setPreviewFallback(true, err.message, tabUrl);
    return false;
  }
}

function setObsUrlElement(id, url) {
  const el = document.getElementById(id);
  if (!el) return;
  const text = url || "— (önce yayın seçin)";
  el.textContent = text;
  if (el instanceof HTMLAnchorElement) {
    if (url) {
      el.href = url;
      el.removeAttribute("aria-disabled");
    } else {
      el.href = "#";
      el.setAttribute("aria-disabled", "true");
    }
  }
}

const GAME_MODE_PUZZLE = "puzzle";
const GAME_MODE_TEAM_RACE = "team-race";
const GAME_MODE_PHOTO_BATTLE = "photo-battle";
const GAME_MODE_FOOTBALL_CLUB = "football-club";
const GAME_MODE_FOOTBALL_NATIONALITY = "football-nationality";

const GAME_MODE_LABELS = {
  [GAME_MODE_PUZZLE]: "Bulmaca",
  [GAME_MODE_TEAM_RACE]: "Takım yarışı",
  [GAME_MODE_PHOTO_BATTLE]: "Photo Quiz",
  [GAME_MODE_FOOTBALL_CLUB]: "Futbol — takım",
  [GAME_MODE_FOOTBALL_NATIONALITY]: "Futbol — milliyet",
};

let photoBattleAdmin = null;
/** Photo Quiz modunda ünlü yaş soruları yüklü mü (sunucudan status/import) */
let roomCelebrityQuiz = false;
async function ensurePhotoBattleAdmin() {
  if (photoBattleAdmin) return photoBattleAdmin;
  const mod = await import("./photo-battle-admin.js?v=1");
  photoBattleAdmin = mod.initPhotoBattleAdmin({
    api,
    getRoomId,
    escapeHtml: escapeAdmin,
  });
  return photoBattleAdmin;
}

let currentRoomGameMode = GAME_MODE_PUZZLE;
let syncingGameModeUi = false;

function normalizeGameMode(value) {
  const v = String(value || "").trim().toLowerCase();
  if (v === GAME_MODE_TEAM_RACE || v === "team_race" || v === "teamrace") {
    return GAME_MODE_TEAM_RACE;
  }
  if (
    v === GAME_MODE_PHOTO_BATTLE ||
    v === "photo_battle" ||
    v === "photo-quiz" ||
    v === "photoquiz"
  ) {
    return GAME_MODE_PHOTO_BATTLE;
  }
  if (
    v === GAME_MODE_FOOTBALL_CLUB ||
    v === "football_club" ||
    v === "footballer_current_club_guess"
  ) {
    return GAME_MODE_FOOTBALL_CLUB;
  }
  if (
    v === GAME_MODE_FOOTBALL_NATIONALITY ||
    v === "football_nationality" ||
    v === "football-nationality-guess"
  ) {
    return GAME_MODE_FOOTBALL_NATIONALITY;
  }
  return GAME_MODE_PUZZLE;
}

function isFootballGameMode(mode) {
  const m = normalizeGameMode(mode);
  return m === GAME_MODE_FOOTBALL_CLUB || m === GAME_MODE_FOOTBALL_NATIONALITY;
}

function footballPackKindForMode(mode) {
  return normalizeGameMode(mode) === GAME_MODE_FOOTBALL_NATIONALITY
    ? "nationality"
    : "club";
}

function roomUsesPhotoOverlayScreen() {
  return usesQuizPhotoOverlay(currentRoomGameMode);
}

/** Ünlü / futbol: soru yalnızca doğru cevapla geçer */
function questionLockedUntilCorrect() {
  return (
    isFootballGameMode(currentRoomGameMode) || roomHasCelebrityQuestions()
  );
}

function gameModeLabel(mode) {
  return GAME_MODE_LABELS[normalizeGameMode(mode)] || GAME_MODE_LABELS[GAME_MODE_PUZZLE];
}

function celebrityAgeInPhotoMode() {
  return (
    currentRoomGameMode === GAME_MODE_PHOTO_BATTLE && Boolean(roomCelebrityQuiz)
  );
}

function setRoomCelebrityQuizFlag(value) {
  roomCelebrityQuiz = Boolean(value);
}

function detectLocalCelebrityQuiz() {
  if (isFootballGameMode(currentRoomGameMode)) return false;
  return questions.some((q) => {
    if (/football-/.test(String(q?.meta?.gameKind || ""))) return false;
    return (
      q?.meta?.age != null ||
      /kaç\s+yaşında/i.test(String(q?.question || ""))
    );
  });
}

function getNewRoomGameMode() {
  const checked = document.querySelector('input[name="newRoomGameMode"]:checked');
  return normalizeGameMode(checked?.value);
}

function applyDashboardGameMode(mode) {
  const m = normalizeGameMode(mode);
  syncingGameModeUi = true;
  currentRoomGameMode = m;
  const dash = document.getElementById("dashboard");
  if (dash) dash.dataset.gameMode = m;

  const badge = document.getElementById("gameModeActiveBadge");
  if (badge) {
    badge.textContent = gameModeLabel(m);
    badge.classList.toggle("game-mode-active-badge--race", m === GAME_MODE_TEAM_RACE);
  }

  document.querySelectorAll("#roomGameModePicker input[name=roomGameMode]").forEach((el) => {
    el.checked = el.value === m;
  });

  const isRace = m === GAME_MODE_TEAM_RACE;
  const isPhoto = m === GAME_MODE_PHOTO_BATTLE;
  const isFootball = isFootballGameMode(m);
  document.getElementById("panelCelebrityQuiz")?.classList.toggle(
    "hidden",
    isRace || isFootball
  );
  document.getElementById("panelFootballQuiz")?.classList.toggle("hidden", !isFootball);
  const fbTitle = document.getElementById("footballPanelTitle");
  const fbHelp = document.getElementById("footballPanelHelp");
  if (fbTitle) {
    fbTitle.textContent =
      m === GAME_MODE_FOOTBALL_NATIONALITY
        ? "Futbol — Milliyet"
        : "Futbol — Güncel takım";
  }
  if (fbHelp) {
    fbHelp.innerHTML =
      m === GAME_MODE_FOOTBALL_NATIONALITY
        ? "Gömülü paketi yükleyin. İzleyici sohbette <strong>ülke</strong> yazar (Türkiye, Brezilya…). OBS linki aşağıda."
        : "Gömülü paketi yükleyin. İzleyici sohbette <strong>takım</strong> yazar (GS, Real Madrid…). OBS linki aşağıda.";
  }
  const loadFb = document.getElementById("btnLoadFootballPack");
  if (loadFb) {
    loadFb.textContent =
      m === GAME_MODE_FOOTBALL_NATIONALITY
        ? "30 oyuncu (milliyet) yükle"
        : "30 oyuncu (takım) yükle";
  }
  document.getElementById("celebrityPhotoNote")?.classList.toggle(
    "hidden",
    !isPhoto || !roomCelebrityQuiz
  );
  document.getElementById("panelPhotoBattle")?.classList.toggle(
    "hidden",
    !isPhoto || roomCelebrityQuiz
  );
  document.getElementById("previewPanelPuzzle")?.classList.toggle(
    "hidden",
    isRace || isPhoto
  );
  document.getElementById("previewPanelRace")?.classList.toggle("hidden", !isRace);

  document.querySelectorAll(".panel-puzzle-only").forEach((el) => {
    if (el.classList.contains("panel-photo-battle-shared")) return;
    el.classList.toggle("hidden", isRace || isPhoto || isFootball);
  });

  const guidePuzzle = document.getElementById("guideStepsPuzzle");
  const guideRace = document.getElementById("guideStepsTeamRace");
  const guidePhoto = document.getElementById("guideStepsPhotoBattle");
  const guideFootball = document.getElementById("guideStepsFootball");
  if (guidePuzzle) guidePuzzle.classList.toggle("hidden", isRace || isPhoto || isFootball);
  if (guideRace) guideRace.classList.toggle("hidden", m !== GAME_MODE_TEAM_RACE);
  if (guidePhoto) guidePhoto.classList.toggle("hidden", !isPhoto);
  if (guideFootball) guideFootball.classList.toggle("hidden", !isFootball);

  const fillEx = document.getElementById("btnFillExample");
  if (fillEx) fillEx.disabled = isRace || isPhoto || isFootball;

  updateObsPanelCopy(m);
  updatePreviewPanelCopy(m);

  const lockSkip = questionLockedUntilCorrect();
  const btnSkip = document.getElementById("btnSkip");
  if (btnSkip) {
    btnSkip.disabled = lockSkip;
    btnSkip.title = lockSkip
      ? "Doğru cevap gelene kadar soru değişmez"
      : "";
  }

  const modeHelp = document.getElementById("gameModeHelp");
  if (modeHelp) {
    modeHelp.textContent = isPhoto && roomCelebrityQuiz
      ? "Photo Quiz + ünlü yaş: 30 ünlü yüklü — Başlat, sohbette yaş yazın, OBS ünlü ekranı. Mod değişmez."
      : isPhoto
      ? "Photo Quiz: görsel havuzu yükleyin, OBS overlay açın, sohbette 1/2 ile oylayın. Başlat = eleme turu."
      : m === GAME_MODE_TEAM_RACE
        ? "Bu sayfa yayın ayarları. Arena, Başlat ve sohbet testi için Canlı stüdyoyu açın (/play/). OBS linkleri aşağıda."
        : isFootball
          ? "Futbol modu: paketi yükleyin, OBS quiz ekranı, sohbette takım veya ülke yazılır. Uygula ile mod kaydedilir."
          : "Modu seçin, Uygula ile kaydedin. Mod değişince çalışan oyun durur.";
  }

  if (isPhoto && getRoomId()) {
    ensurePhotoBattleAdmin().then((pb) => pb.onRoomReady({ photoBattleSettings: {} }));
  }

  const roomId = getRoomId();
  updateUrlDisplay(roomId);
  updateRaceStudioLinks(roomId);
  updateQuizLabLinks(roomId);
  updateFootballOverlayLinks(roomId);
  updateFootballQuestionsBadge();
  syncingGameModeUi = false;
  updateGameModeApplyButton();
}

function updateObsPanelCopy(mode) {
  const help = document.getElementById("obsPanelHelp");
  if (!help) return;
  const m = normalizeGameMode(mode);
  if (isFootballGameMode(m)) {
    help.textContent =
      "OBS tarayıcı kaynağı: 1080×1920. Dikey link quiz ekranıdır (fotoğraf + soru).";
    return;
  }
  if (m === GAME_MODE_TEAM_RACE) {
    help.textContent =
      "OBS tarayıcı kaynağı: 1080×1920. Dikey link takım yarışı arenasıdır.";
    return;
  }
  if (m === GAME_MODE_PHOTO_BATTLE) {
    help.textContent =
      "OBS tarayıcı kaynağı: 1080×1920. Photo Quiz veya ünlü yaş için uygun link otomatik seçilir.";
    return;
  }
  if (roomHasCelebrityQuestions()) {
    help.textContent =
      "OBS tarayıcı kaynağı: 1080×1920. Ünlü yaş quiz ekranı — dikey link.";
    return;
  }
  help.textContent =
    "OBS tarayıcı kaynağı: 1080×1920, şeffaf arka plan kapalı. Dikey / yatay linkleri kopyalayın.";
}

function updatePreviewPanelCopy(mode) {
  const title = document.getElementById("previewPanelTitle");
  const hint = document.getElementById("previewPanelHint");
  const sub = document.getElementById("previewPanelSub");
  const m = normalizeGameMode(mode);
  const quizPreview =
    isFootballGameMode(m) ||
    roomHasCelebrityQuestions() ||
    (m === GAME_MODE_PHOTO_BATTLE && celebrityAgeInPhotoMode());
  if (title) {
    title.textContent = quizPreview ? "Canlı quiz önizlemesi" : "Canlı önizleme";
  }
  if (hint) {
    hint.textContent = quizPreview
      ? "Yayında görünecek quiz ekranı. Başlat ve paket yükleyince güncellenir."
      : "Yayında görünecek overlay. Başlat ve soru kaydedince güncellenir.";
  }
  if (sub) {
    sub.textContent = "Sağdaki düğmelerle boyut ve yakınlaştırmayı ayarlayın.";
  }
}

function scrollToActiveModePanel() {
  const m = currentRoomGameMode;
  const target = isFootballGameMode(m)
    ? document.getElementById("panelFootballQuiz")
    : m === GAME_MODE_TEAM_RACE
      ? document.getElementById("panelRaceAdmin")
      : m === GAME_MODE_PHOTO_BATTLE
        ? document.getElementById("panelPhotoBattle") ||
          document.getElementById("panelCelebrityQuiz")
        : roomHasCelebrityQuestions()
          ? document.getElementById("panelCelebrityQuiz")
          : document.getElementById("panelGameMode");
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function getSelectedRoomGameMode() {
  const checked = document.querySelector(
    "#roomGameModePicker input[name=roomGameMode]:checked"
  );
  return normalizeGameMode(checked?.value);
}

function syncGameModePickerToSaved() {
  syncingGameModeUi = true;
  document
    .querySelectorAll("#roomGameModePicker input[name=roomGameMode]")
    .forEach((el) => {
      el.checked = el.value === currentRoomGameMode;
    });
  syncingGameModeUi = false;
  updateGameModeApplyButton();
}

function updateGameModeApplyButton() {
  const btn = document.getElementById("btnApplyGameMode");
  const hint = document.getElementById("gameModePendingHint");
  const picker = document.getElementById("roomGameModePicker");
  const pending = getSelectedRoomGameMode();
  const dirty = pending !== currentRoomGameMode;
  const hasRoom = Boolean(getRoomId());

  if (picker) {
    picker.classList.toggle("game-mode-picker--dirty", dirty && hasRoom);
  }
  if (hint) {
    hint.classList.toggle("hidden", !dirty || !hasRoom);
  }
  if (btn) {
    if (!hasRoom) {
      btn.disabled = true;
      btn.textContent = "Uygula";
    } else if (dirty) {
      btn.disabled = false;
      btn.textContent = `Uygula — ${gameModeLabel(pending)}`;
    } else {
      btn.disabled = true;
      btn.textContent = `Kayıtlı: ${gameModeLabel(currentRoomGameMode)}`;
    }
  }
}

async function applySelectedGameMode() {
  const roomId = getRoomId();
  if (!roomId) {
    log("Önce bir yayın odası seçin.", false, { persist: true });
    return;
  }

  const next = getSelectedRoomGameMode();
  if (next === currentRoomGameMode) {
    updateGameModeApplyButton();
    return;
  }

  const btn = document.getElementById("btnApplyGameMode");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Kaydediliyor…";
  }

  try {
    await saveRoomGameMode(next);
    flushRoomPanelDraft();
    syncGameModePickerToSaved();
    await loadQuestions();
    await refreshGameStatusUi();
    await syncPreviewStages(roomId);
    scrollToActiveModePanel();
    if (isFootballGameMode(next)) {
      showFootballStatus(
        `${gameModeLabel(next)} kaydedildi. Oyuncu paketini yükleyin.`,
        "ok"
      );
    }
  } catch (err) {
    syncGameModePickerToSaved();
    log("Oyun modu kaydedilemedi: " + err.message, false, { persist: true });
    alert(err.message || "Mod kaydedilemedi");
  } finally {
    updateGameModeApplyButton();
  }
}

function quizLabUrl(roomId, mode = currentRoomGameMode) {
  if (!roomId) return "/play/celebrity-quiz-lab.html";
  const p = new URLSearchParams({ room: roomId });
  if (isFootballGameMode(mode)) {
    p.set("kind", normalizeGameMode(mode));
  }
  return `/play/celebrity-quiz-lab.html?${p}`;
}

function celebrityLabUrl(roomId) {
  return quizLabUrl(roomId, GAME_MODE_PUZZLE);
}

function celebrityOverlayUrl(roomId) {
  if (!roomId) return "/celebrity-overlay";
  return `/celebrity-overlay?room=${encodeURIComponent(roomId)}&motion=1`;
}

function updateQuizLabLinks(roomId) {
  const mode = currentRoomGameMode;
  const labHref = quizLabUrl(roomId, mode);
  const isFb = isFootballGameMode(mode);
  const labLabel = isFb
    ? mode === GAME_MODE_FOOTBALL_NATIONALITY
      ? "Milliyet Lab (test) →"
      : "Takım Lab (test) →"
    : "Ünlü Yaş Lab (test) →";
  for (const id of ["btnOpenCelebrityLab", "btnOpenCelebrityLabPanel", "btnOpenFootballLab"]) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.href = roomId ? labHref : "/play/celebrity-quiz-lab.html";
    if (id === "btnOpenCelebrityLab" || id === "btnOpenFootballLab") {
      el.textContent = labLabel;
    }
  }
  const headerLab = document.getElementById("btnOpenCelebrityLab");
  if (headerLab) headerLab.classList.toggle("hidden", isFb);
  const obs = document.getElementById("btnOpenCelebrityOverlay");
  if (obs) obs.href = roomId ? celebrityOverlayUrl(roomId) : "/celebrity-overlay";
}

function updateCelebrityLabLinks(roomId) {
  updateQuizLabLinks(roomId);
}

function showCelebrityStatus(message, type = "info") {
  const el = document.getElementById("celebrityActionStatus");
  if (!el) return;
  el.textContent = message;
  el.className = `celebrity-action-status celebrity-action-status--${type}`;
  el.classList.remove("hidden");
  el.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function requireRoomForCelebrity(actionLabel) {
  const roomId = getRoomId();
  if (roomId) return roomId;
  const msg = `${actionLabel} için önce bir yayın odası açın (üstte «Yayın değiştir» → Panele gir).`;
  showCelebrityStatus(msg, "error");
  log(msg, false, { persist: true });
  return null;
}

let celebrityPanelWired = false;
let footballPanelWired = false;

async function loadFootballPackForRoom() {
  const roomId = getRoomId();
  if (!roomId) {
    log("Önce bir yayın odası seçin.", false, { persist: true });
    return;
  }
  if (!isFootballGameMode(currentRoomGameMode)) {
    showFootballStatus("Önce futbol modunu seçip Uygula deyin.", "error");
    return;
  }
  const btn = document.getElementById("btnLoadFootballPack");
  const prevLabel = btn?.textContent;
  if (btn) {
    btn.disabled = true;
    btn.classList.add("is-busy");
    btn.textContent = "Yükleniyor…";
  }
  showFootballStatus("Futbol paketi yükleniyor…", "info");
  try {
    const kind = footballPackKindForMode(currentRoomGameMode);
    const imp = await api("/football/load-pack", {
      method: "POST",
      body: JSON.stringify({ kind, mode: "replace" }),
    });
    const data = await imp.json().catch(() => ({}));
    if (!imp.ok) throw new Error(data.error || `Yüklenemedi (${imp.status})`);
    questions = data.questions || [];
    renderQuestionsEditor();
    updateQuestionsCountBadge();
    updateFootballQuestionsBadge();
    const n = data.imported ?? data.count ?? questions.length;
    showFootballStatus(
      `${n} oyuncu yüklendi. «Başlat» → sohbette ${kind === "nationality" ? "ülke" : "takım"} yazın.`,
      "ok"
    );
    log(`Futbol paketi yüklendi (${n} soru).`, true, { persist: true });
    updateUrlDisplay(roomId);
    void refreshGameStatusUi();
  } catch (err) {
    const msg = err.message || "Paket yüklenemedi";
    showFootballStatus(msg, "error");
    log(msg, false, { persist: true });
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("is-busy");
      if (prevLabel) btn.textContent = prevLabel;
    }
  }
}

function initFootballPanel() {
  if (footballPanelWired) return;
  const panel = document.getElementById("panelFootballQuiz");
  if (!panel) return;
  footballPanelWired = true;
  panel.addEventListener("click", (e) => {
    if (e.target.closest("#btnLoadFootballPack")) {
      e.preventDefault();
      loadFootballPackForRoom().catch(() => {});
      return;
    }
    if (e.target.closest("#btnScrollFootballQuestions")) {
      e.preventDefault();
      document
        .getElementById("panelControl")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
      showFootballStatus("Kontrol bölümüne kaydırıldı.", "info");
    }
  });
}

function initCelebrityPanel() {
  if (celebrityPanelWired) return;
  const panel = document.getElementById("panelCelebrityQuiz");
  if (!panel) return;
  celebrityPanelWired = true;

  const onCelebrityPanelClick = async (e) => {
    const lab = e.target.closest(
      "#btnOpenCelebrityLabPanel, #btnOpenCelebrityLab"
    );
    const obs = e.target.closest("#btnOpenCelebrityOverlay");
    const loadBtn = e.target.closest("#btnLoadCelebrityPack");
    const gptBtn = e.target.closest(
      "#btnCopyCelebrityGpt, #btnCopyCelebrityGptModal"
    );
    const csvBtn = e.target.closest(
      "#btnImportCelebrityCsvPanel, #btnImportCelebrityCsv"
    );
    const scrollBtn = e.target.closest("#btnScrollQuestions");

    if (lab) {
      e.preventDefault();
      const roomId = requireRoomForCelebrity("Test Lab");
      if (!roomId) return;
      const url = celebrityLabUrl(roomId);
      window.open(url, "_blank", "noopener");
      showCelebrityStatus("Test Lab yeni sekmede açıldı.", "ok");
      return;
    }

    if (obs) {
      e.preventDefault();
      const roomId = requireRoomForCelebrity("OBS ekranı");
      if (!roomId) return;
      const url = celebrityOverlayUrl(roomId);
      window.open(url, "_blank", "noopener");
      showCelebrityStatus("Ünlü OBS ekranı yeni sekmede açıldı.", "ok");
      return;
    }

    if (gptBtn) {
      e.preventDefault();
      await copyCelebrityGptPrompt();
      return;
    }

    if (csvBtn) {
      e.preventDefault();
      if (!requireRoomForCelebrity("CSV yükleme")) return;
      openCelebrityImportModal();
      showCelebrityStatus("CSV penceresi açıldı — yapıştırıp «Uygula» deyin.", "info");
      return;
    }

    if (scrollBtn) {
      e.preventDefault();
      const target =
        document.getElementById(
          celebrityAgeInPhotoMode() ? "panelControl" : "panelQuestions"
        ) || document.getElementById("panelControl");
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
      showCelebrityStatus("Kontrol / sorular bölümüne kaydırıldı.", "info");
      return;
    }

    if (!loadBtn || loadBtn.disabled) return;

    const roomId = requireRoomForCelebrity("Ünlü paketi");
    if (!roomId) return;

    const prevLabel = loadBtn.textContent;
    loadBtn.disabled = true;
    loadBtn.classList.add("is-busy");
    loadBtn.textContent = "Yükleniyor…";
    showCelebrityStatus("30 ünlü yükleniyor…", "info");

    try {
      const res = await fetch("/play/celebrity-sample.csv");
      if (!res.ok) throw new Error("Örnek CSV bulunamadı");
      const csv = await res.text();
      const body = JSON.stringify({
        csv,
        hint: "Ünlülerin Yaşını Tahmin Et",
        mode: "replace",
      });
      let imp = await api("/questions/import-celebrities", { method: "POST", body });
      if (imp.status === 404) {
        imp = await api("/import-celebrities", { method: "POST", body });
      }
      const data = await imp.json().catch(() => ({}));
      if (!imp.ok) {
        throw new Error(data.error || `Yüklenemedi (${imp.status})`);
      }
      questions = data.questions || [];
      renderQuestionsEditor();
      updateQuestionsCountBadge();
      setRoomCelebrityQuizFlag(data.celebrityQuiz ?? true);
      applyDashboardGameMode(currentRoomGameMode);
      const n = data.imported ?? data.count ?? questions.length;
      showCelebrityStatus(
        `${n} ünlü yüklendi. «Başlat» deyin, sohbette yaş yazın.`,
        "ok"
      );
      log(
        `${n} ünlü yüklendi — Photo Quiz modu korundu. Başlat → sohbette yaş yazın.`,
        true,
        { persist: true }
      );
    updateUrlDisplay(getRoomId());
    void refreshGameStatusUi();
  } catch (err) {
    const msg = err.message || "Paket yüklenemedi";
      showCelebrityStatus(msg, "error");
      log(msg, false, { persist: true });
      alert(msg);
    } finally {
      loadBtn.disabled = false;
      loadBtn.classList.remove("is-busy");
      loadBtn.textContent = prevLabel;
    }
  };

  panel.addEventListener("click", onCelebrityPanelClick);
  document.getElementById("btnOpenCelebrityLab")?.addEventListener("click", onCelebrityPanelClick);
}

function raceStudioUrl(roomId) {
  if (!roomId) return "/play/";
  return `/play/?room=${encodeURIComponent(roomId)}`;
}

function updateRaceStudioLinks(roomId) {
  const href = raceStudioUrl(roomId);
  for (const id of ["btnOpenRaceStudio", "btnOpenRaceStudioAside"]) {
    const el = document.getElementById(id);
    if (el) {
      el.href = href;
      if (id === "btnOpenRaceStudio") el.target = "_blank";
    }
  }
}

async function hydrateRoomConfigFromServer() {
  const roomId = getRoomId();
  if (!roomId) return;
  try {
    const res = await api("/status");
    if (!res.ok) return;
    const d = await res.json();
    if (d.config?.gameMode) {
      applyDashboardGameMode(d.config.gameMode);
      rememberRoomGameMode(roomId, d.config.gameMode);
    }
    if (d.celebrityQuiz != null) {
      setRoomCelebrityQuizFlag(d.celebrityQuiz);
    } else if (d.config?.celebrityQuiz != null) {
      setRoomCelebrityQuizFlag(d.config.celebrityQuiz);
    }
    updateYoutubeUI(d.youtube || { mode: d.chatMode }, d.config || {}, { roomId });
    restoreStreamUrlField(d.config || {}, d.youtube || {});
  } catch {
    /* sunucu yoksa önbellek mod */
    applyCachedRoomGameMode(roomId);
  }
}

async function saveRoomGameMode(mode) {
  const next = normalizeGameMode(mode);
  if (next === currentRoomGameMode) return;
  const res = await api("/config", {
    method: "PATCH",
    body: JSON.stringify({ gameMode: next }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  applyDashboardGameMode(data.gameMode ?? next);
  rememberRoomGameMode(getRoomId(), data.gameMode ?? next);
  flushRoomPanelDraft();
  await fetchUserRooms();
  renderRoomsHub();
  renderRoomSwitcher();
  log(`Oyun modu kaydedildi: ${gameModeLabel(data.gameMode ?? next)}`, true, {
    persist: true,
  });
}

function setupGameModePicker() {
  document
    .querySelectorAll("#roomGameModePicker input[name=roomGameMode]")
    .forEach((input) => {
      if (input.dataset.wired) return;
      input.dataset.wired = "1";
      input.addEventListener("change", () => {
        if (!input.checked || syncingGameModeUi) return;
        const rid = getRoomId();
        if (rid) {
          try {
            sessionStorage.setItem(
              `bulmaca_panel_${rid}`,
              JSON.stringify({
                streamUrlDraft: getStreamUrlDraftText(),
                gameMode: getSelectedRoomGameMode(),
                savedAt: Date.now(),
              })
            );
          } catch {
            /* yoksay */
          }
        }
        updateGameModeApplyButton();
      });
    });

  const applyBtn = document.getElementById("btnApplyGameMode");
  if (applyBtn && !applyBtn.dataset.wired) {
    applyBtn.dataset.wired = "1";
    applyBtn.addEventListener("click", () => {
      applySelectedGameMode().catch((err) => {
        log(err.message || "Mod uygulanamadı", false, { persist: true });
      });
    });
  }

  updateGameModeApplyButton();
}

function roomHasCelebrityQuestions() {
  if (isFootballGameMode(currentRoomGameMode)) return false;
  return (
    roomCelebrityQuiz ||
    detectLocalCelebrityQuiz() ||
    (Array.isArray(questions) &&
      questions.some(
        (x) =>
          !/football-/.test(String(x?.meta?.gameKind || "")) &&
          (x?.meta?.age != null ||
            /kaç\s+yaşında/i.test(String(x?.question || "")))
      ))
  );
}

function buildUrls(roomId, gameMode = currentRoomGameMode) {
  const q = (extra) => {
    const p = new URLSearchParams({ room: roomId, ...OVERLAY_PARAMS });
    if (extra) Object.entries(extra).forEach(([k, v]) => p.set(k, v));
    const mode = normalizeGameMode(gameMode);
    if (mode !== GAME_MODE_PUZZLE) p.set("mode", mode);
    return p.toString();
  };
  const celebParams = new URLSearchParams({ room: roomId, ...OVERLAY_PARAMS });
  const vertical = usesQuizPhotoOverlay(gameMode)
    ? `${appOrigin}/celebrity-overlay?${celebParams}`
    : `${appOrigin}/overlay?${q({ layout: "vertical" })}`;
  return {
    horizontal: `${appOrigin}/overlay?${q({ layout: "horizontal" })}`,
    vertical,
    celebrity: `${appOrigin}/celebrity-overlay?${celebParams}`,
  };
}

let previewLayout = "vertical";
/** null = panele sığdır; sayı = 1080 tabanlı ölçek (0.2–1) */
let previewSidebarZoom = null;
let previewModalZoom = null;
const PREVIEW_ZOOM_STEP = 0.1;
const PREVIEW_ZOOM_MIN = 0.2;
const PREVIEW_ZOOM_MAX = 1;

/** Soru puanı seçenekleri (karışık dağıtım bu havuzdan) */
const QUESTION_POINT_OPTIONS = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100];

function pickRandomQuestionPoints() {
  return QUESTION_POINT_OPTIONS[Math.floor(Math.random() * QUESTION_POINT_OPTIONS.length)];
}

function normalizeQuestionPoints(q) {
  const n = Number(q?.points);
  return Number.isFinite(n) && n > 0 ? Math.round(n) : 10;
}

const SAMPLE_QUESTIONS = [
  {
    id: "1",
    hint: "Harf karmaşası",
    question: "R, A, M, O, Z, Y, K",
    answers: ["yazıcı", "Yazıcı", "YAZICI"],
    points: 10,
  },
  {
    id: "2",
    hint: "Harf karmaşası",
    question: "K, A, H, V, E",
    answers: ["kahve", "Kahve", "KAHVE"],
    points: 15,
  },
  {
    id: "3",
    hint: "Harf karmaşası",
    question: "T, E, L, E, F, O, N",
    answers: ["telefon", "Telefon", "TELEFON"],
    points: 20,
  },
  {
    id: "4",
    hint: "Harf karmaşası",
    question: "D, E, N, İ, Z",
    answers: ["deniz", "Deniz", "DENİZ"],
    points: 25,
  },
  {
    id: "5",
    hint: "Harf karmaşası",
    question: "K, İ, T, A, P",
    answers: ["kitap", "Kitap", "KİTAP"],
    points: 15,
  },
  {
    id: "6",
    hint: "Coğrafya",
    question: "Türkiye'nin başkenti neresidir?",
    answers: ["ankara", "Ankara", "ANKARA"],
    points: 30,
  },
  {
    id: "7",
    hint: "Matematik",
    question: "12 + 8 = ?",
    answers: ["20", "yirmi"],
    points: 10,
  },
  {
    id: "8",
    hint: "Genel kültür",
    question: "Güneş sistemindeki en büyük gezegen hangisidir?",
    answers: ["jüpiter", "jupiter", "Jüpiter"],
    points: 40,
  },
  {
    id: "9",
    hint: "Tarih",
    question: "Türkiye Cumhuriyeti hangi yıl ilan edildi?",
    answers: ["1923"],
    points: 50,
  },
  {
    id: "10",
    hint: "Spor",
    question: "Futbolda bir takımda sahada kaç oyuncu oynar?",
    answers: ["11", "on bir", "onbir"],
    points: 20,
  },
];

function cloneQuestions(list) {
  return (list || []).map((q) => ({
    ...q,
    answers: [...(q.answers || [])],
  }));
}

/** Hazır soru paketleri — Şablon ekle */
const QUESTION_TEMPLATES = [
  {
    id: "mixed-10",
    name: "Karışık örnek (10 soru)",
    description: "Harf karmaşası, coğrafya, tarih, spor — panel örnek seti",
    questions: () => cloneQuestions(SAMPLE_QUESTIONS),
  },
  {
    id: "letters-12",
    name: "Harf karmaşası (12 soru)",
    description: "Karışık harflerden kelime bulma",
    questions: () =>
      cloneQuestions([
        { hint: "Harf karmaşası", question: "M, U, Z, İ, K", answers: ["müzik", "Müzik", "MUZIK"], points: 15 },
        { hint: "Harf karmaşası", question: "O, K, U, L", answers: ["okul", "Okul"], points: 10 },
        { hint: "Harf karmaşası", question: "G, Ü, N, E, Ş", answers: ["güneş", "Güneş", "GUNES"], points: 20 },
        { hint: "Harf karmaşası", question: "B, A, L, I, K", answers: ["balık", "Balık", "BALIK"], points: 15 },
        { hint: "Harf karmaşası", question: "Ç, İ, Ç, E, K", answers: ["çiçek", "Çiçek", "CICEK"], points: 15 },
        { hint: "Harf karmaşası", question: "U, Ç, A, K", answers: ["uçak", "Uçak", "UCAK"], points: 25 },
        { hint: "Harf karmaşası", question: "K, E, M, E, R", answers: ["kemer", "Kemer"], points: 10 },
        { hint: "Harf karmaşası", question: "K, A, L, E, M", answers: ["kalem", "Kalem"], points: 10 },
        { hint: "Harf karmaşası", question: "S, A, B, U, N", answers: ["sabun", "Sabun"], points: 15 },
        { hint: "Harf karmaşası", question: "Y, I, L, D, I, Z", answers: ["yıldız", "Yıldız", "YILDIZ"], points: 20 },
        { hint: "Harf karmaşası", question: "K, A, R, T, A, L", answers: ["kartal", "Kartal"], points: 25 },
        { hint: "Harf karmaşası", question: "M, A, V, I", answers: ["mavi", "Mavi", "MAVI"], points: 20 },
      ]),
  },
  {
    id: "genel-15",
    name: "Genel kültür (15 soru)",
    description: "Coğrafya, bilim, tarih, spor karışık",
    questions: () =>
      cloneQuestions([
        { hint: "Coğrafya", question: "Dünyanın en uzun nehri hangisidir?", answers: ["nil", "Nil", "NİL"], points: 25 },
        { hint: "Coğrafya", question: "Fransa'nın başkenti?", answers: ["paris", "Paris"], points: 15 },
        { hint: "Bilim", question: "Suyun kimyasal formülü?", answers: ["h2o", "H2O"], points: 10 },
        { hint: "Bilim", question: "İnsan vücudunda kaç kemik vardır (yaklaşık)?", answers: ["206", "iki yüz altı"], points: 30 },
        { hint: "Tarih", question: "İlk Türk devleti hangisidir (yaygın cevap)?", answers: ["asya hun", "hun", "Hun"], points: 40 },
        { hint: "Tarih", question: "İstanbul'un fethi hangi yıl?", answers: ["1453"], points: 25 },
        { hint: "Spor", question: "Basketbolda bir sayı kaç puan?", answers: ["2", "iki"], points: 10 },
        { hint: "Spor", question: "Olimpiyat halkalarında kaç renk vardır?", answers: ["5", "beş"], points: 15 },
        { hint: "Sinema", question: "Titanic filminin yönetmeni?", answers: ["james cameron", "cameron"], points: 30 },
        { hint: "Müzik", question: "Beethoven hangi ülkenin bestecisidir?", answers: ["almanya", "Almanya"], points: 20 },
        { hint: "Matematik", question: "7 × 8 = ?", answers: ["56", "elli altı"], points: 10 },
        { hint: "Matematik", question: "Bir üçgenin iç açıları toplamı?", answers: ["180", "yüz seksen"], points: 15 },
        { hint: "Türkçe", question: "«Kitap» kelimesinin eş anlamlısı (yaygın)?", answers: ["eser", "yayın"], points: 20 },
        { hint: "Genel kültür", question: "Dünyanın en küçük kıtası?", answers: ["avustralya", "Avustralya", "okyanusya"], points: 25 },
        { hint: "Genel kültür", question: "Mona Lisa hangi müzede?", answers: ["louvre", "Louvre"], points: 35 },
      ]),
  },
  {
    id: "turkiye-12",
    name: "Türkiye temalı (12 soru)",
    description: "Şehirler, yemekler, kültür",
    questions: () =>
      cloneQuestions([
        { hint: "Türkiye", question: "En kalabalık şehir?", answers: ["istanbul", "İstanbul"], points: 15 },
        { hint: "Türkiye", question: "Pamukkale hangi ilde?", answers: ["denizli", "Denizli"], points: 25 },
        { hint: "Türkiye", question: "Lahmacunun anavatanı olarak bilinen şehir?", answers: ["gaziantep", "Gaziantep", "antep"], points: 30 },
        { hint: "Türkiye", question: "Türkiye'nin en doğusundaki il?", answers: ["ığdır", "Iğdır", "igdir"], points: 40 },
        { hint: "Türkiye", question: "Mevlana'nın şehri?", answers: ["konya", "Konya"], points: 20 },
        { hint: "Türkiye", question: "Türk bayrağındaki ay rengi?", answers: ["beyaz", "Beyaz"], points: 10 },
        { hint: "Türkiye", question: "Çayın başkenti olarak anılan Rize'nin ürünü?", answers: ["çay", "Çay"], points: 15 },
        { hint: "Türkiye", question: "Efes antik kenti hangi ilde?", answers: ["izmir", "İzmir", "selçuk"], points: 25 },
        { hint: "Türkiye", question: "Türk Lirasının simgesi (harf)?", answers: ["₺", "tl", "TL"], points: 10 },
        { hint: "Türkiye", question: "Nemrut Dağı hangi bölgede?", answers: ["adıyaman", "Adıyaman"], points: 35 },
        { hint: "Türkiye", question: "Simit hangi ülkenin sokak lezzeti?", answers: ["türkiye", "Türkiye", "turkiye"], points: 15 },
        { hint: "Türkiye", question: "Boğazlar hangi şehri ikiye böler?", answers: ["istanbul", "İstanbul"], points: 20 },
      ]),
  },
  {
    id: "kolay-8",
    name: "Kolay / aile (8 soru)",
    description: "Kısa ve net cevaplar, düşük-orta puan",
    questions: () =>
      cloneQuestions([
        { hint: "Kolay", question: "Gündüz gökyüzünde parlayan yıldız?", answers: ["güneş", "Güneş", "GUNES"], points: 5 },
        { hint: "Kolay", question: "2 + 2 = ?", answers: ["4", "dört"], points: 5 },
        { hint: "Kolay", question: "Kedinin miyavladığı hayvan türü?", answers: ["kedi", "Kedi"], points: 5 },
        { hint: "Kolay", question: "Kışın yağan beyaz şey?", answers: ["kar", "Kar"], points: 5 },
        { hint: "Kolay", question: "Elma hangi renk olabilir (yaygın)?", answers: ["kırmızı", "Kırmızı", "yeşil", "Yeşil"], points: 10 },
        { hint: "Kolay", question: "Haftada kaç gün var?", answers: ["7", "yedi"], points: 5 },
        { hint: "Kolay", question: "Türkiye'nin para birimi?", answers: ["lira", "Lira", "tl", "TL"], points: 10 },
        { hint: "Kolay", question: "Balığı hangi ortamda yaşar?", answers: ["su", "Su", "deniz", "Deniz"], points: 10 },
      ]),
  },
];

const CHATGPT_QUESTION_COUNT = 28;
const CELEBRITY_CHATGPT_COUNT = 30;

function buildCelebrityChatGptPrompt(count = CELEBRITY_CHATGPT_COUNT) {
  return `Sen bir YouTube canlı yayın asistanısın. Türkiye'deki ünlüler için yaş tahmin oyunu listesi üret.

HEDEF: Tam ${count} satır. Her satır TEK satır CSV (virgülle ayrılmış), başlık satırı YOK.

FORMAT (her satır birebir):
isim,yaş,doğum_tarihi,foto_link

KURALLAR:
1. isim = gerçek ünlü adı (oyuncu, şarkıcı, sporcu, fenomen)
2. yaş = 2025 itibarıyla tam sayı
3. doğum_tarihi = GG.AA.YYYY
4. foto_link = Wikimedia Commons veya resmi Wikipedia görsel URL'si (https ile, çalışan link)
5. Tekrarlayan isim yok; farklı alanlardan dengeli seç
6. Çıktı YALNIZCA ${count} satır CSV — açıklama, markdown, numara, kod bloğu YOK

ÖRNEK (2 satır — format böyle):
Hande Erçel,32,24.11.1993,https://upload.wikimedia.org/wikipedia/commons/3/34/Hande_Er%C3%A7el.jpg
Kerem Bürsin,38,04.06.1987,https://upload.wikimedia.org/wikipedia/commons/5/53/Festival_de_M%C3%A1laga_2024_-_Kerem_B%C3%BCrsin_%28cropped%29.jpg

Şimdi tam ${count} satırlık listeyi üret.`;
}

function buildChatGptQuestionPrompt(count = CHATGPT_QUESTION_COUNT) {
  return `Sen bir YouTube canlı yayın bulmaca editörüsün. Türkçe sorular üret.

HEDEF: Tam ${count} soru. Farklı kategorilerden dengeli dağıt (her kategoriden en az 2 soru).

KATEGORİLER (her sorunun "hint" alanına yaz — ekranda kategori olarak görünür):
- Harf karmaşası (soru metni: harfler virgülle, örn. "K, A, H, V, E")
- Coğrafya
- Tarih
- Bilim
- Spor
- Sinema / dizi
- Müzik
- Matematik
- Türkçe / kelime
- Genel kültür
- Türkiye

KURALLAR:
1. Çıktı YALNIZCA geçerli JSON dizisi olsun — markdown, açıklama, \`\`\` kod bloğu YOK.
2. Her öğe şu alanlara sahip olsun:
   - "id": "1", "2", … (sıralı string)
   - "hint": kategori adı (yukarıdaki listeden)
   - "question": soru metni (kısa, tek satır)
   - "answers": en az 2 kabul edilen cevap (küçük/büyük harf varyantları)
   - "points": 5, 10, 15, 20, 25, 30, 40, 50, 75 veya 100 (zorluğa göre)
3. "category" yazarsan "hint" ile aynı kabul edilir.
4. Cevaplar Türkçe karakter içerebilir; alternatif yazımlar ekle (ı/i, ş/s vb.).
5. Harf karmaşası sorularında doğru cevap tek kelime olsun.
6. Tekrarlayan veya çok benzer soru üretme.

ÖRNEK (tek öğe — format böyle olsun):
[
  {
    "id": "1",
    "hint": "Coğrafya",
    "question": "Türkiye'nin başkenti neresidir?",
    "answers": ["ankara", "Ankara", "ANKARA"],
    "points": 25
  }
]

Şimdi tam ${count} soruluk JSON dizisini üret.`;
}

let selectedQuestionTemplateId = null;

async function copyTextToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  }
}

function openQDialog(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("hidden");
  el.inert = false;
}

function closeQDialog(id) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.contains(document.activeElement)) {
    document.getElementById("btnAddQuestion")?.focus();
  }
  el.classList.add("hidden");
  el.inert = true;
}

function normalizeImportedQuestion(raw, index) {
  if (!raw || typeof raw !== "object") return null;
  const question = String(raw.question ?? "").trim();
  let answers = raw.answers;
  if (typeof answers === "string") {
    answers = answers.split(",").map((a) => a.trim()).filter(Boolean);
  }
  if (!Array.isArray(answers)) answers = [];
  answers = answers.map((a) => String(a).trim()).filter(Boolean);
  if (!question || !answers.length) return null;
  const hint = String(raw.hint ?? raw.category ?? "").trim();
  return {
    id: String(raw.id ?? `${Date.now()}-${index}`),
    question,
    answers,
    hint,
    points: normalizeQuestionPoints(raw),
  };
}

function stripMarkdownJsonFence(text) {
  const raw = String(text || "").trim();
  const m = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  return m ? m[1].trim() : raw;
}

function parseQuestionsJsonText(text) {
  const trimmed = stripMarkdownJsonFence(text);
  if (!trimmed) throw new Error("JSON boş");
  let parsed = JSON.parse(trimmed);
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
    if (Array.isArray(parsed.questions)) parsed = parsed.questions;
    else throw new Error("Dizi veya { questions: [...] } bekleniyor");
  }
  if (!Array.isArray(parsed)) throw new Error("Kök öğe bir dizi olmalı");
  const items = [];
  parsed.forEach((raw, i) => {
    const q = normalizeImportedQuestion(raw, i);
    if (q) items.push(q);
  });
  if (!items.length) throw new Error("Geçerli soru bulunamadı");
  return items;
}

function applyQuestionsList(incoming, mode = "replace") {
  const list = cloneQuestions(incoming);
  if (mode === "append") {
    syncFromEditor();
    questions = [...questions, ...list];
  } else {
    questions = list;
  }
  questions.forEach((q, i) => {
    q.id = String(i + 1);
  });
  renderQuestionsEditor();
}

function getQuestionApplyMode(radioName) {
  const el = document.querySelector(`input[name="${radioName}"]:checked`);
  return el?.value === "append" ? "append" : "replace";
}

function renderQuestionTemplateList() {
  const host = document.getElementById("questionTemplateList");
  if (!host) return;
  host.innerHTML = "";
  selectedQuestionTemplateId = null;
  const applyBtn = document.getElementById("btnApplyQuestionTemplate");
  if (applyBtn) applyBtn.disabled = true;

  for (const tpl of QUESTION_TEMPLATES) {
    const count = tpl.questions().length;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "q-template-card";
    btn.dataset.templateId = tpl.id;
    btn.innerHTML = `<strong>${escapeHtml(tpl.name)}</strong><span>${escapeHtml(tpl.description)} · ${count} soru</span>`;
    btn.addEventListener("click", () => {
      host.querySelectorAll(".q-template-card").forEach((c) => c.classList.remove("is-selected"));
      btn.classList.add("is-selected");
      selectedQuestionTemplateId = tpl.id;
      if (applyBtn) applyBtn.disabled = false;
    });
    host.appendChild(btn);
  }
}

function openQuestionTemplateModal() {
  renderQuestionTemplateList();
  openQDialog("questionsTemplateModal");
}

function openQuestionsImportModal() {
  document.getElementById("questionsImportText")?.focus();
  openQDialog("questionsImportModal");
}

const SAMPLE_CONFIG = {
  botName: "BulmacaBot",
  announceWrong: false,
  winMessage: "Tebrikler {user}! Doğru cevap: {answer}",
  wrongMessage: "{user}, bu sefer olmadı. Bir daha dene!",
};

const BOT_PREVIEW_USER = "ZeynepK";
const BOT_PREVIEW_ANSWER = "ankara";

function formatBotTemplate(tpl, user = BOT_PREVIEW_USER, answer = BOT_PREVIEW_ANSWER) {
  const name = user.startsWith("@") ? user : `@${user}`;
  return String(tpl || "")
    .replace(/\{user\}/gi, name)
    .replace(/\{answer\}/gi, answer);
}

function syncBotWrongUi() {
  const on = document.getElementById("announceWrong")?.checked === true;
  document.getElementById("wrongMessageBlock")?.classList.toggle("hidden", !on);
  document.getElementById("botPreviewWrongWrap")?.classList.toggle("hidden", !on);
}

function updateBotPreview() {
  const botName =
    document.getElementById("botName")?.value.trim() || "BulmacaBot";
  const winTpl =
    document.getElementById("winMessage")?.value.trim() ||
    SAMPLE_CONFIG.winMessage;
  const wrongTpl =
    document.getElementById("wrongMessage")?.value.trim() ||
    SAMPLE_CONFIG.wrongMessage;

  const winText = formatBotTemplate(winTpl);
  const wrongText = formatBotTemplate(wrongTpl);

  for (const id of ["previewBotName", "previewBotName2"]) {
    const el = document.getElementById(id);
    if (el) el.textContent = botName;
  }
  const winEl = document.getElementById("botPreviewWin");
  const wrongEl = document.getElementById("botPreviewWrong");
  if (winEl) winEl.textContent = winText;
  if (wrongEl) wrongEl.textContent = wrongText;
  syncBotWrongUi();
}

function initBotPanelUI() {
  document.getElementById("announceWrong")?.addEventListener("change", () => {
    syncBotWrongUi();
    updateBotPreview();
  });
  for (const id of ["botName", "winMessage", "wrongMessage"]) {
    document.getElementById(id)?.addEventListener("input", updateBotPreview);
  }
  document.querySelectorAll(".chip[data-target]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.target);
      if (target) {
        target.value = btn.textContent;
        updateBotPreview();
      }
    });
  });
  syncBotWrongUi();
  updateBotPreview();
}

initBotPanelUI();

const PREVIEW_BASE = {
  vertical: { w: 1080, h: 1920 },
  horizontal: { w: 1920, h: 1080 },
};

function getPreviewSrc(roomId) {
  const urls = buildPreviewUrls(roomId, currentRoomGameMode);
  return previewLayout === "horizontal" ? urls.horizontal : urls.vertical;
}

function setPreviewLoadMessage(message, isError = true) {
  for (const id of ["previewLoadError", "previewLoadErrorRace"]) {
    const el = document.getElementById(id);
    if (!el) continue;
    if (!message) {
      el.classList.add("hidden");
      el.textContent = "";
      continue;
    }
    el.textContent = message;
    el.classList.toggle("preview-load-error--warn", isError);
    el.classList.remove("hidden");
  }
}

async function isPreviewServerUp() {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    if (!res.ok) return false;
    const data = await res.json();
    return Boolean(data.ok && data.overlayReady);
  } catch {
    return false;
  }
}

function wirePreviewFrame(frame) {
  if (!frame || frame.dataset.previewWired) return;
  frame.dataset.previewWired = "1";
  frame.loading = "eager";
  frame.addEventListener("load", () => {
    try {
      const href = frame.contentWindow?.location?.href || "";
      if (href === "about:blank" || href === "") return;
      if (href.startsWith("chrome-error:") || href.startsWith("chrome://")) {
        setPreviewLoadMessage(`Önizleme açılamadı. ${previewStartupHint()}`);
        return;
      }
      const expected = frame.dataset.previewExpectedUrl || "";
      if (
        expected &&
        !href.includes("/overlay") &&
        !href.includes("/celebrity-overlay") &&
        !href.includes("/admin/preview")
      ) {
        return;
      }
      setPreviewLoadMessage("");
    } catch {
      setPreviewLoadMessage("");
    }
  });
  frame.addEventListener("error", () => {
    setPreviewLoadMessage(
      "Önizleme yüklenemedi. npm start çalışıyor mu? Üstten geçerli bir yayın seçin."
    );
  });
}

function setupPreviewResizeObserver() {
  const selector =
    currentRoomGameMode === GAME_MODE_TEAM_RACE
      ? "#previewStageObs .preview-viewport"
      : "#previewStage .preview-viewport";
  const viewport = document.querySelector(selector);
  if (!viewport || viewport.dataset.ro) return;
  const ro = new ResizeObserver(() => layoutPreviewScales());
  ro.observe(viewport);
  viewport.dataset.ro = "1";
}

function getPreviewFitWidth(isModal) {
  const base = PREVIEW_BASE[previewLayout];
  if (isModal) {
    const stage = document.getElementById("previewStageModal");
    const maxW = (stage?.clientWidth || window.innerWidth * 0.88) - 4;
    const maxH = window.innerHeight * 0.72;
    const byHeight = maxH * (base.w / base.h);
    return Math.min(maxW, byHeight, base.w);
  }
  const panel =
    currentRoomGameMode === GAME_MODE_TEAM_RACE
      ? document.getElementById("previewPanelRace")
      : document.getElementById("previewPanelPuzzle");
  return Math.max(160, (panel?.clientWidth || 300) - 28);
}

function resolvePreviewWidth(isModal) {
  const base = PREVIEW_BASE[previewLayout];
  const fitW = getPreviewFitWidth(isModal);
  const zoomFactor = isModal ? previewModalZoom : previewSidebarZoom;
  if (zoomFactor == null) return fitW;
  return Math.min(base.w, Math.max(160, base.w * zoomFactor));
}

function formatZoomLabel(isModal) {
  const z = isModal ? previewModalZoom : previewSidebarZoom;
  if (z == null) return "Sığdır";
  return `${Math.round(z * 100)}%`;
}

function updateZoomLabels() {
  const sl = document.getElementById("sidebarZoomLabel");
  const ml = document.getElementById("modalZoomLabel");
  if (sl) sl.textContent = formatZoomLabel(false);
  if (ml) ml.textContent = formatZoomLabel(true);
}

function applyPreviewScale(viewport, isModal) {
  if (!viewport) return;
  const base = PREVIEW_BASE[previewLayout];
  const iframe = viewport.querySelector("iframe");
  if (!iframe) return;

  const targetW = resolvePreviewWidth(isModal);
  const scale = targetW / base.w;
  const targetH = base.h * scale;

  iframe.style.width = `${base.w}px`;
  iframe.style.height = `${base.h}px`;
  iframe.style.transform = `scale(${scale})`;
  iframe.style.transformOrigin = "0 0";

  viewport.style.width = `${Math.round(targetW)}px`;
  viewport.style.height = `${Math.round(targetH)}px`;
  updateZoomLabels();
}

function nudgePreviewZoom(isModal, delta) {
  const base = PREVIEW_BASE[previewLayout];
  const fitW = getPreviewFitWidth(isModal);
  const fitScale = fitW / base.w;
  let current = isModal ? previewModalZoom : previewSidebarZoom;
  if (current == null) current = fitScale;
  current = Math.min(
    PREVIEW_ZOOM_MAX,
    Math.max(PREVIEW_ZOOM_MIN, Math.round((current + delta) * 100) / 100)
  );
  if (isModal) previewModalZoom = current;
  else previewSidebarZoom = current;
  layoutPreviewScales();
}

function resetPreviewZoom(isModal, fitOnly = false) {
  if (isModal) previewModalZoom = fitOnly ? null : null;
  else previewSidebarZoom = fitOnly ? null : null;
  layoutPreviewScales();
}

function layoutPreviewScales() {
  const stage = document.getElementById("previewStage");
  const stageObs = document.getElementById("previewStageObs");
  const modal = document.getElementById("previewModal");
  if (currentRoomGameMode === GAME_MODE_TEAM_RACE && stageObs) {
    applyPreviewScale(stageObs.querySelector(".preview-viewport"), false);
  } else if (stage) {
    applyPreviewScale(stage.querySelector(".preview-viewport"), false);
  }
  if (modal && !modal.classList.contains("hidden")) {
    const modalStage = document.getElementById("previewStageModal");
    if (modalStage) modalStage.dataset.previewLayout = previewLayout;
    applyPreviewScale(modalStage?.querySelector(".preview-viewport"), true);
  }
}

async function syncPreviewStages(roomId) {
  const stage = document.getElementById("previewStage");
  const stageObs = document.getElementById("previewStageObs");
  const stageModal = document.getElementById("previewStageModal");
  if (stage) stage.dataset.previewLayout = previewLayout;
  if (stageObs) {
    stageObs.dataset.previewLayout = previewLayout;
    stageObs.dataset.previewLabel =
      previewLayout === "horizontal" ? "1920×1080" : "1080×1920";
  }
  if (stageModal) stageModal.dataset.previewLayout = previewLayout;

  for (const id of ["previewFrame", "previewFrameModal", "previewFrameObs"]) {
    wirePreviewFrame(document.getElementById(id));
  }

  if (!roomId) {
    setPreviewLoadMessage("Önizleme için üstten bir yayın seçin.");
    for (const id of ["previewFrame", "previewFrameModal", "previewFrameObs"]) {
      clearPreviewFrame(document.getElementById(id));
    }
    return;
  }

  const urls = buildPreviewUrls(roomId, currentRoomGameMode);
  const src = getPreviewSrc(roomId);
  const obsTabUrl = previewLayout === "horizontal" ? urls.horizontal : urls.vertical;
  const openLink = document.getElementById("previewOpenLink");
  if (openLink) {
    openLink.href = obsTabUrl;
    openLink.classList.remove("hidden");
  }
  const openLinkRace = document.getElementById("previewOpenLinkRace");
  if (openLinkRace) openLinkRace.href = obsTabUrl;

  if (currentRoomGameMode === GAME_MODE_TEAM_RACE) {
    setPreviewLoadMessage("");
    if (!(await isPreviewServerUp())) {
      setPreviewLoadMessage(`Sunucu yanıt vermiyor. ${previewStartupHint()}`);
      clearPreviewFrame(document.getElementById("previewFrameObs"));
      return;
    }
    const frameObs = document.getElementById("previewFrameObs");
    await loadPreviewFrame(frameObs, obsTabUrl);
    clearPreviewFrame(document.getElementById("previewFrame"));
    clearPreviewFrame(document.getElementById("previewFrameModal"));
    requestAnimationFrame(() => {
      layoutPreviewScales();
      setupPreviewResizeObserver();
    });
    return;
  }

  clearPreviewFrame(document.getElementById("previewFrameObs"));

  if (!(await isPreviewServerUp())) {
    setPreviewLoadMessage(`Sunucu yanıt vermiyor. ${previewStartupHint()}`);
    for (const id of ["previewFrame", "previewFrameModal"]) {
      clearPreviewFrame(document.getElementById(id));
    }
    setPreviewFallback(true, "Sunucu kapalı.", obsTabUrl);
    return;
  }

  const sidebar = document.getElementById("previewFrame");
  const modalFrame = document.getElementById("previewFrameModal");
  const modalOpen =
    document.getElementById("previewModal") &&
    !document.getElementById("previewModal").classList.contains("hidden");

  await loadPreviewFrame(sidebar, src);
  if (modalOpen) await loadPreviewFrame(modalFrame, src);
  else clearPreviewFrame(modalFrame);

  requestAnimationFrame(() => {
    layoutPreviewScales();
    setupPreviewResizeObserver();
  });
}

function updateUrlDisplay(roomId) {
  const urls = roomId ? buildUrls(roomId) : { horizontal: "", vertical: "" };
  setObsUrlElement("urlHorizontal", urls.horizontal);
  setObsUrlElement("urlVertical", urls.vertical);
  document.getElementById("roomIdDisplay").textContent = roomId || "—";
  updateFootballOverlayLinks(roomId);
  updatePreview(roomId);
}

function updatePreview(roomId) {
  syncPreviewStages(roomId);
}

function setPreviewLayout(layout) {
  previewLayout = layout === "horizontal" ? "horizontal" : "vertical";
  previewSidebarZoom = null;
  previewModalZoom = null;
  document.querySelectorAll(".preview-layout-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.previewLayout === previewLayout);
  });
  updatePreview(getRoomId());
}

async function openPreviewModal() {
  const roomId = getRoomId();
  if (!roomId) return;
  await syncPreviewStages(roomId);
  const modal = document.getElementById("previewModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.inert = false;
  previewModalZoom = null;
  document.body.classList.add("preview-modal-open");
  requestAnimationFrame(() => {
    layoutPreviewScales();
    requestAnimationFrame(layoutPreviewScales);
    document.getElementById("btnPreviewModalClose")?.focus();
  });
}

function closePreviewModal() {
  const modal = document.getElementById("previewModal");
  if (!modal) return;
  if (modal.contains(document.activeElement)) {
    document.activeElement.blur();
  }
  modal.classList.add("hidden");
  modal.inert = true;
  document.body.classList.remove("preview-modal-open");
  requestAnimationFrame(layoutPreviewScales);
}

async function runDemoPreview() {
  let res = await api("/game/demo-preview", { method: "POST" });
  if (res.status === 404) {
    res = await api("/game/start", {
      method: "POST",
      body: JSON.stringify({ demo: true }),
    });
  }
  return res;
}

function applySampleToForms() {
  questions = SAMPLE_QUESTIONS.map((q) => ({ ...q }));
  renderQuestionsEditor();

  document.getElementById("botName").value = SAMPLE_CONFIG.botName;
  document.getElementById("announceWrong").checked = SAMPLE_CONFIG.announceWrong;
  document.getElementById("winMessage").value = SAMPLE_CONFIG.winMessage;
  document.getElementById("wrongMessage").value = SAMPLE_CONFIG.wrongMessage;
  document.getElementById("mockAuthor").value = "ZeynepK";
  document.getElementById("mockText").value = "ankara";

  const rn = document.getElementById("roomName");
  if (rn) rn.textContent = "Örnek Cumartesi Yayını";
}

async function fillExample() {
  const roomId = getRoomId();
  if (!roomId) {
    document.getElementById("newRoomName").value = "Örnek Cumartesi Yayını";
    return;
  }

  applySampleToForms();

  const qRes = await api("/questions", {
    method: "PUT",
    body: JSON.stringify({ questions }),
  });
  if (!qRes.ok) {
    log(
      "Sorular kaydedilemedi: " + ((await qRes.json()).error || qRes.status),
      false,
      { persist: true }
    );
    return;
  }

  const cRes = await api("/config", {
    method: "PATCH",
    body: JSON.stringify(SAMPLE_CONFIG),
  });
  if (!cRes.ok) {
    log("Ayarlar kaydedilemedi.", false, { persist: true });
    return;
  }

  const dRes = await runDemoPreview();
  if (!dRes.ok) {
    const err = await dRes.json().catch(() => ({}));
    log(
      "Önizleme demosu başarısız (" +
        dRes.status +
        "). Sunucuyu yeniden başlatın (npm start): " +
        (err.error || ""),
      true,
      { persist: true }
    );
    return;
  }

  const snapshot = await dRes.json();
  updateUI(snapshot);
  await loadEventLog();
  updatePreview(roomId);
  openPreviewModal();
}

const logEl = document.getElementById("log");
const auditLogEl = document.getElementById("auditLog");
const AUDIT_LOG_MAX = 200;
const LOG_MAX = 100;

function renderLogEntry(msg, highlight = false, eventId = null) {
  if (!logEl) return;
  if (eventId != null) {
    if (seenLogIds.has(eventId)) return;
    seenLogIds.add(eventId);
  }
  const li = document.createElement("li");
  if (eventId != null) li.dataset.eventId = String(eventId);
  const safe = String(msg ?? "");
  if (highlight && safe.includes("<")) li.innerHTML = safe;
  else li.textContent = safe;
  logEl.prepend(li);
  while (logEl.children.length > LOG_MAX) {
    const removed = logEl.lastChild;
    if (removed?.dataset?.eventId) seenLogIds.delete(Number(removed.dataset.eventId));
    logEl.removeChild(removed);
  }
}

function formatAuditTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}

function buildAuditLogItem(entry) {
  const li = document.createElement("li");
  const level = entry.level || "info";
  li.className = `audit-log-item audit-log-item--${level}`;
  const head = document.createElement("div");
  head.className = "audit-log-head";
  head.innerHTML = `<span>${formatAuditTime(entry.at)}</span><span class="audit-log-cat">${escapeHtml(entry.category || "?")}</span><span>${escapeHtml(level)}</span>`;
  const msg = document.createElement("div");
  msg.className = "audit-log-msg";
  msg.textContent = entry.message || "";
  li.append(head, msg);
  if (entry.detail && Object.keys(entry.detail).length) {
    const det = document.createElement("pre");
    det.className = "audit-log-detail";
    det.textContent = JSON.stringify(entry.detail, null, 2);
    li.appendChild(det);
  }
  return li;
}

function prependAuditEntry(entry) {
  if (!auditLogEl || !entry) return;
  auditLogEl.prepend(buildAuditLogItem(entry));
  while (auditLogEl.children.length > AUDIT_LOG_MAX) {
    auditLogEl.lastElementChild?.remove();
  }
}

function renderAuditLogList(items = []) {
  if (!auditLogEl) return;
  auditLogEl.replaceChildren();
  for (const entry of items) {
    auditLogEl.appendChild(buildAuditLogItem(entry));
  }
}

async function loadAuditLog() {
  const meta = document.getElementById("auditLogMeta");
  const roomId = getRoomId();
  if (!auditLogEl || !roomId) return;
  const category = document.getElementById("auditLogFilter")?.value || "";
  try {
    const q = new URLSearchParams({ limit: "150" });
    if (category) q.set("category", category);
    const res = await api(`/audit-log?${q}`);
    if (!res.ok) {
      if (meta) meta.textContent = "Denetim günlüğü yüklenemedi.";
      return;
    }
    const data = await res.json();
    if (getRoomId() !== roomId) return;
    if (meta) {
      meta.textContent = data.enabled
        ? `${data.items?.length ?? 0} kayıt (AUDIT_LOG açık)`
        : "AUDIT_LOG kapalı — sunucuda AUDIT_LOG=1";
    }
    renderAuditLogList(data.items || []);
  } catch (err) {
    if (meta) meta.textContent = "Hata: " + (err.message || "bilinmiyor");
  }
}

async function clearAuditLogPanel() {
  if (!getRoomId()) return;
  try {
    await api("/audit-log/clear", { method: "POST" });
    renderAuditLogList([]);
    const meta = document.getElementById("auditLogMeta");
    if (meta) meta.textContent = "Denetim günlüğü temizlendi.";
  } catch (err) {
    log("Denetim temizlenemedi: " + err.message, false, { persist: true });
  }
}

async function loadEventLog() {
  if (!logEl || !getRoomId()) return;
  try {
    const res = await api("/events?limit=100");
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 403) {
        handleRoomAccessDenied(err.error);
        return;
      }
      if (logEl.children.length === 0) {
        renderLogEntry(
          `Günlük yüklenemedi (${res.status}${err.error ? ": " + err.error : ""}). Sayfayı yenileyin veya tekrar giriş yapın.`,
          false
        );
      }
      return;
    }
    const events = await res.json();
    seenLogIds.clear();
    const rows = [...events];
    logEl.innerHTML = "";
    for (const e of rows) {
      renderLogEntry(e.message, e.highlight, e.id);
    }
  } catch (err) {
    if (logEl.children.length === 0) {
      renderLogEntry("Günlük bağlantı hatası: " + (err.message || "bilinmiyor"), false);
    }
  }
}

async function log(msg, highlight = false, { persist = false } = {}) {
  renderLogEntry(msg, highlight);
  if (!persist || !getRoomId()) return;
  try {
    await api("/events", {
      method: "POST",
      body: JSON.stringify({ message: String(msg).replace(/<[^>]+>/g, ""), highlight }),
    });
  } catch {
    /* yoksay */
  }
}

const stateLabels = {
  idle: "Beklemede",
  active: "Soru aktif",
  winner: "Kazanan!",
  ended: "Bitti",
};

const racePhaseLabels = {
  idle: "Beklemede",
  running: "Tur aktif",
  gathering: "Toplanma",
  chaos: "Kaos",
};

function updateRaceAdminPanel(race) {
  if (!race || currentRoomGameMode !== GAME_MODE_TEAM_RACE) return;
  const gs = document.getElementById("raceGameState");
  if (gs) {
    const label =
      race.phase === "running"
        ? race.roundPhase === "chaos"
          ? "⚡ Kaos"
          : race.roundPhase === "gathering"
            ? "Toplanma"
            : racePhaseLabels.running
        : racePhaseLabels[race.phase] ?? race.phase;
    gs.textContent = label;
  }

  const roundEl = document.getElementById("raceRound");
  if (roundEl) roundEl.textContent = race.round > 0 ? String(race.round) : "—";

  const stats = race.stats || {};
  const spawnEl = document.getElementById("raceSpawnCount");
  if (spawnEl) spawnEl.textContent = String(stats.spawns ?? 0);
  const unmatchedEl = document.getElementById("raceUnmatched");
  if (unmatchedEl) unmatchedEl.textContent = String(stats.unmatched ?? 0);

  const recentUl = document.getElementById("raceRecentSpawns");
  if (recentUl) {
    const recent = race.recentSpawns || [];
    recentUl.innerHTML = recent.length
      ? recent
          .map(
            (s) =>
              `<li><img class="team-flag team-flag--sm" src="${s.flagUrl || `/team-race/flags/${s.teamCode}.png`}" alt="" loading="lazy" /> <strong>${escapeAdmin(s.displayName)}</strong> → ${escapeAdmin(s.teamName || s.teamCode)}</li>`
          )
          .join("")
      : "<li class=\"race-empty\">Henüz katılım yok</li>";
  }

  const countsUl = document.getElementById("raceTeamCounts");
  if (countsUl) {
    const rows = Object.entries(race.teamCounts || {}).sort((a, b) => b[1] - a[1]);
    countsUl.innerHTML = rows.length
      ? rows
          .map(
            ([code, n]) =>
              `<li><img class="team-flag team-flag--sm" src="/team-race/flags/${escapeAdmin(code)}.png" alt="" loading="lazy" /> <span>${n}</span></li>`
          )
          .join("")
      : "<li class=\"race-empty\">—</li>";
  }

  const apBanner = document.getElementById("raceAutopilotBanner");
  if (apBanner && race.autopilot) {
    const ap = race.autopilot;
    apBanner.textContent = ap.armed
      ? `🤖 Otomatik: ${ap.statusMessage || "aktif"}`
      : "Otomatik mod: Başlat ile açılır";
    apBanner.classList.toggle("is-armed", Boolean(ap.armed));
  }

  const engEl = document.getElementById("raceEngagementStatus");
  if (engEl && race.phase === "running" && race.roundPhase === "gathering") {
    const e = race.engagement || {};
    const req = race.gatherRequirements || {};
    if (race.gatherBlockedReason) {
      engEl.textContent = race.gatherBlockedReason;
    } else if (req.met) {
      engEl.textContent = `Yeterli etkileşim — kaos için hazır (${formatMs(race.gatherRemainingMs)} kaldı)`;
    } else {
      engEl.textContent = `Katılım: ${e.participants ?? 0}/${req.minParticipants} kişi · ${e.teams ?? 0}/${req.minTeams} takım · ${e.spawns ?? 0}/${req.minTotalSpawns} spawn`;
    }
  } else if (engEl) {
    engEl.textContent = "";
  }

}

function formatMs(ms) {
  const sec = Math.max(0, Math.ceil((ms || 0) / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function fillRaceSettingsForm(raceSettings = {}) {
  const s = raceSettings || {};
  const gatherMin = document.getElementById("raceGatherMin");
  if (gatherMin) gatherMin.value = String(Math.round((s.gatherDurationMs || 300_000) / 60_000));
  const mp = document.getElementById("raceMinParticipants");
  if (mp) mp.value = String(s.minParticipants ?? 3);
  const mt = document.getElementById("raceMinTeams");
  if (mt) mt.value = String(s.minTeams ?? 2);
  const ms = document.getElementById("raceMinSpawns");
  if (ms) ms.value = String(s.minTotalSpawns ?? 3);
  const ce = document.getElementById("raceChaosMinEntities");
  if (ce) ce.value = String(s.chaosMinEntities ?? 8);
}

async function saveRaceSettings() {
  if (currentRoomGameMode !== GAME_MODE_TEAM_RACE) return;
  const gatherMin = Number(document.getElementById("raceGatherMin")?.value) || 5;
  const body = {
    gatherDurationMs: gatherMin * 60_000,
    minParticipants: Number(document.getElementById("raceMinParticipants")?.value) || 3,
    minTeams: Number(document.getElementById("raceMinTeams")?.value) || 2,
    minTotalSpawns: Number(document.getElementById("raceMinSpawns")?.value) || 3,
    chaosMinEntities: Number(document.getElementById("raceChaosMinEntities")?.value) || 8,
  };
  const res = await api("/race/settings", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || res.statusText);
  }
  const data = await res.json();
  fillRaceSettingsForm(data.raceSettings);
  if (data.snapshot) updateRaceAdminPanel(data.snapshot);
  log("Tur algoritması kaydedildi.", true, { persist: true });
}

function escapeAdmin(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getLocalQuestionCount() {
  const root = document.getElementById("questionsEditor");
  if (!root || !root.querySelector(".question-item")) {
    return questions.length;
  }
  syncFromEditor();
  return questions.length;
}

function updateUI(snapshot, config = {}) {
  if (config.celebrityQuiz !== undefined) {
    setRoomCelebrityQuizFlag(config.celebrityQuiz);
  }

  const usePhotoBattleUi =
    currentRoomGameMode === GAME_MODE_PHOTO_BATTLE &&
    !celebrityAgeInPhotoMode() &&
    (snapshot?.phase || snapshot?.photoBattle || snapshot?.left);

  if (usePhotoBattleUi) {
    const pb = snapshot.photoBattle || snapshot;
    ensurePhotoBattleAdmin().then((admin) => admin.onState(pb));
    const gs = document.getElementById("gameState");
    if (gs) {
      const labels = {
        idle: "Hazır",
        voting: "Oylama",
        result: "Sonuç",
        champion: "Kazanan",
      };
      gs.textContent = labels[pb.phase] || pb.phase;
    }
    const qo = document.getElementById("questionOrder");
    if (qo) qo.textContent = `Tur ${pb.matchNumber || 0} · ${pb.activeCount ?? 0} kalan`;
    if (config.roomName) document.getElementById("roomName").textContent = config.roomName;
    return;
  }

  if (
    snapshot?.mode === "team-race" ||
    (currentRoomGameMode === GAME_MODE_TEAM_RACE && snapshot?.phase)
  ) {
    updateRaceAdminPanel(snapshot);
    const chatLabel = document.getElementById("chatModeLabel");
    if (chatLabel) {
      if (config.youtubeConnected) chatLabel.textContent = "YouTube canlı";
      else chatLabel.textContent = config.chatMode === "mock" ? "Panel testi" : config.chatMode || "Panel";
    }
    if (config.roomName) document.getElementById("roomName").textContent = config.roomName;
    if (config.botName) {
      const bn = document.getElementById("botName");
      if (bn && !bn.matches(":focus")) bn.value = config.botName;
    }
    return;
  }

  const gs = document.getElementById("gameState");
  if (gs) gs.textContent = stateLabels[snapshot.state] ?? snapshot.state;

  const qo = document.getElementById("questionOrder");
  if (qo) {
    const serverTotal = Math.max(
      Number(snapshot.totalQuestions) || 0,
      serverQuestionCount || 0
    );
    const localTotal = getLocalQuestionCount();
    const unsavedMore = localTotal > serverTotal;
    const total = unsavedMore ? localTotal : serverTotal;
    if (!total) {
      qo.textContent = "—";
    } else if (snapshot.state === "idle") {
      qo.textContent = unsavedMore
        ? `0 / ${total} (${serverTotal} kayıtlı — kaydedin)`
        : `0 / ${total}`;
    } else if (snapshot.state === "ended") {
      qo.textContent = `${total} / ${total}`;
    } else {
      const idx = Math.max(1, (snapshot.currentIndex ?? -1) + 1);
      const pts = snapshot.question?.points;
      const ptsBit = pts ? ` · ${pts} p` : "";
      qo.textContent = `${idx} / ${total}${ptsBit}`;
    }
  }

  const ia = document.getElementById("interactionActive");
  const il = document.getElementById("interactionLast");
  const inter = snapshot.interaction;
  if (ia) {
    if (snapshot.state === "idle" || !inter) {
      ia.textContent = "—";
    } else {
      const q = inter.questionPlayers ?? 0;
      const a = inter.activePlayers ?? 0;
      ia.textContent = `${a} (${q} bu soru)`;
    }
  }
  if (il) {
    const last = inter?.lastAnswer;
    if (!last?.displayName) {
      il.textContent = "—";
      il.className = "interaction-last-admin";
    } else {
      const mark = last.correct ? "✓" : "✗";
      const ans = String(last.answer || "").slice(0, 32);
      il.textContent = `@${last.displayName.replace(/^@/, "")} · ${ans} ${mark}`;
      il.className = `interaction-last-admin ${last.correct ? "is-ok" : "is-bad"}`;
    }
  }

  const chatLabel = document.getElementById("chatModeLabel");
  if (chatLabel) {
    if (config.youtubeConnected) {
      chatLabel.textContent = "YouTube canlı";
    } else {
      chatLabel.textContent =
        config.chatMode === "mock" ? "Panel testi" : config.chatMode || "Panel";
    }
  }

  if (config.roomName) document.getElementById("roomName").textContent = config.roomName;
  if (config.botName) {
    const bn = document.getElementById("botName");
    if (bn && !bn.matches(":focus")) bn.value = config.botName;
  }
}

let questions = [];
/** Sunucuda kayıtlı soru sayısı (kaydet sonrası güncellenir) */
let serverQuestionCount = 0;
/** Oda paneli soru listesi yüklendikten sonra game:state sıra sayacını günceller */
let questionsHydrated = false;
let socket = null;

function fillBotForm(config) {
  if (!config) return;
  document.getElementById("botName").value =
    config.botName || SAMPLE_CONFIG.botName;
  document.getElementById("announceWrong").checked = config.announceWrong === true;
  document.getElementById("winMessage").value =
    config.winMessage || SAMPLE_CONFIG.winMessage;
  document.getElementById("wrongMessage").value =
    config.wrongMessage || SAMPLE_CONFIG.wrongMessage;
  syncBotWrongUi();
  updateBotPreview();
}

function setYtPill(el, text, tone = "") {
  if (!el) return;
  el.textContent = text;
  el.className = "yt-pill" + (tone ? ` yt-pill--${tone}` : "");
}

function setYoutubeActionBanner(message, tone = "") {
  const el = document.getElementById("youtubeActionBanner");
  if (!el) return;
  const text = String(message || "").trim();
  if (!text) {
    el.classList.add("hidden");
    el.textContent = "";
    el.className = "youtube-action-banner hidden";
    return;
  }
  el.textContent = text;
  el.className =
    "youtube-action-banner" + (tone ? ` youtube-action-banner--${tone}` : "");
  el.classList.remove("hidden");
  el.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function requireRoomForYoutubeAction() {
  const roomId = getRoomId();
  if (roomId) return roomId;
  setYoutubeActionBanner(
    "Önce bir yayın odası açın (listeden «Panele gir» veya yeni oda oluşturun).",
    "error"
  );
  log("Yayın seçilmedi — Sohbet botu işlemi yapılamadı.", false, { persist: true });
  return null;
}

function setYoutubeButtonsBusy(busy, ...buttonIds) {
  for (const id of buttonIds) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.disabled = busy;
    btn.classList.toggle("is-busy", busy);
  }
}

function applyYoutubeActionResult(data, { fallbackOk = "" } = {}) {
  const roomId = getRoomId();
  updateYoutubeUI(data, { videoId: data?.videoId }, { roomId });
  updateUI(
    { state: document.getElementById("gameState")?.textContent || "idle" },
    {
      chatMode: data?.mode,
      youtubeConnected: data?.connected,
    }
  );
  const msg =
    data?.statusMessage ||
    data?.welcomeWarning ||
    (data?.connected ? "Canlı sohbet bağlı — bot yorumları okuyor." : fallbackOk);
  if (msg) {
    setYoutubeActionBanner(
      msg,
      data?.welcomeWarning ? "warn" : data?.connected ? "ok" : "ok"
    );
  }
}

function renderConnectSteps(steps) {
  const ol = document.getElementById("youtubeConnectSteps");
  if (!ol) return;
  ol.innerHTML = steps
    .map(
      (s) =>
        `<li class="connect-step${s.done ? " connect-step--done" : ""}${s.active ? " connect-step--active" : ""}">${s.text}</li>`
    )
    .join("");
}

function syncMockTestPanelVisible(yt = {}) {
  const card = document.querySelector(".bot-card--test");
  if (card) card.classList.toggle("hidden", yt.mode === "mock" ? false : true);
}

function updateBotTestHint(yt = {}) {
  const hint = document.getElementById("botTestHint");
  const badge = document.getElementById("botModeBadge");
  const intro = document.getElementById("botIntro");
  syncMockTestPanelVisible(yt);
  if (badge) {
    if (yt.mode === "mock") badge.textContent = "Test modu";
    else if (yt.connected) badge.textContent = "InnerChat bağlı";
    else badge.textContent = "InnerChat";
  }
  if (intro) {
    intro.textContent =
      yt.mode === "mock"
        ? "Sunucu test modunda (CHAT_MODE=mock): aşağıdan sahte cevap. Canlı sohbet için .env → CHAT_MODE=youtube ve sunucuyu yeniden başlatın."
        : "InnerChat: YouTube hesabı gerekmez. Canlı yayın linkini yapıştırın → Sohbete bağlan → Başlat. İzleyici mesajları okunur.";
  }
  if (!hint) return;
  if (yt.mode === "mock") {
    hint.innerHTML =
      "Oyun <strong>Başlat</strong> iken panelden test cevap gönderin (YouTube’a gitmez).";
    return;
  }
  if (!yt.connected) {
    hint.innerHTML =
      "Canlı <strong>video linki</strong> yapıştırın → <strong>Sohbete bağlan</strong> → Kontrol’den <strong>Başlat</strong>.";
    return;
  }
  hint.innerHTML =
    "Sohbet dinleniyor. Panel testi yalnızca oyun mantığını dener; izleyiciler canlı yayında yazar.";
}

let streamUrlParseTimer = null;

function formatInnerChatTapTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}

function renderInnerChatTapMeta(data = {}) {
  const el = document.getElementById("innerChatTapMeta");
  if (!el) return;
  if (!data.enabled) {
    el.textContent = "Tap kapalı (sunucuda INNER_CHAT_TAP=0).";
    return;
  }
  const stayLive =
    data.connected &&
    (data.pollingMode === "live" || data.listeningLive || data.chatStayConnected);
  const listen = stayLive
    ? "dinleniyor (live)"
    : data.connected
      ? "bağlı, oyun bekliyor (idle)"
      : "bağlı değil";
  const streams = data.streamCount > 0 ? `${data.streamCount} yayın` : "yayın yok";
  el.textContent = `${listen} · ${streams} · ${data.count ?? 0}/${data.max ?? 100} kayıt`;
}

function buildInnerChatTapItemLi(entry) {
  const li = document.createElement("li");
  li.className = "inner-chat-tap-item";
  const code = entry.outcome || "none";
  const time = document.createElement("span");
  time.className = "inner-chat-tap-time";
  time.textContent = formatInnerChatTapTime(entry.at);
  const body = document.createElement("div");
  body.className = "inner-chat-tap-body";
  const author = document.createElement("div");
  author.className = "inner-chat-tap-author";
  author.textContent = entry.author || "—";
  const text = document.createElement("div");
  text.className = "inner-chat-tap-text";
  text.textContent = entry.text || "";
  body.append(author, text);
  if (entry.sourceVideoId) {
    const vid = document.createElement("div");
    vid.className = "inner-chat-tap-vid";
    vid.textContent = `video: ${entry.sourceVideoId}`;
    body.appendChild(vid);
  }
  if (entry.simulated) {
    const sim = document.createElement("div");
    sim.className = "inner-chat-tap-vid";
    sim.textContent = "panel testi";
    body.appendChild(sim);
  }
  const outcome = document.createElement("span");
  outcome.className = `inner-chat-tap-outcome inner-chat-tap-outcome--${code}`;
  outcome.textContent = entry.outcomeLabel || code;
  li.append(time, body, outcome);
  return li;
}

function renderInnerChatTapList(items = []) {
  const list = document.getElementById("innerChatTapList");
  const empty = document.getElementById("innerChatTapEmpty");
  if (!list) return;
  list.replaceChildren();
  if (!items.length) {
    empty?.classList.remove("hidden");
    return;
  }
  empty?.classList.add("hidden");
  for (const entry of items) {
    list.appendChild(buildInnerChatTapItemLi(entry));
  }
}

function prependInnerChatTapEntry(entry) {
  const list = document.getElementById("innerChatTapList");
  const empty = document.getElementById("innerChatTapEmpty");
  if (!list || !entry) return;
  empty?.classList.add("hidden");
  list.prepend(buildInnerChatTapItemLi(entry));
  while (list.children.length > 100) {
    list.lastElementChild?.remove();
  }
}

async function loadInnerChatTap(expectedRoomId) {
  const roomId = expectedRoomId || getRoomId();
  if (!roomId) return;
  try {
    const res = await api("/inner-chat/tap");
    if (!res.ok) return;
    const data = await res.json();
    if (getRoomId() !== roomId) return;
    renderInnerChatTapMeta(data);
    renderInnerChatTapList(data.items || []);
  } catch {
    /* yoksay */
  }
}

async function clearInnerChatTap() {
  if (!requireRoomForYoutubeAction()) return;
  try {
    const res = await api("/inner-chat/tap/clear", { method: "POST" });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.error || res.statusText);
    }
    renderInnerChatTapList([]);
    renderInnerChatTapMeta({ enabled: true, count: 0, max: 100, pollingMode: "idle" });
    log("InnerChat tap listesi temizlendi.", true, { persist: false });
  } catch (err) {
    log("Tap temizlenemedi: " + err.message, false, { persist: true });
  }
}

async function updateStreamUrlPreview() {
  const el = document.getElementById("streamUrlParsed");
  if (!el) return;
  const raw = getStreamUrlDraftText();
  if (!raw) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  try {
    const res = await fetch(
      `/api/utils/parse-youtube?${new URLSearchParams({ url: raw })}`,
      { cache: "no-store" }
    );
    const data = await res.json();
    if (data.ok && Array.isArray(data.videoIds) && data.videoIds.length) {
      el.textContent =
        data.videoIds.length === 1
          ? `Tanınan video ID: ${data.videoIds[0]} — Sohbete bağlan deyince bu yayının sohbeti açılır.`
          : `Toplam ${data.videoIds.length} yayın tanındı — bağlanınca tek merkezden hepsi dinlenecek.`;
      el.classList.remove("hidden");
    } else {
      el.textContent =
        "Link tanınmadı. watch?v=…, youtu.be/…, youtube.com/live/… veya Studio yayın linki deneyin.";
      el.classList.remove("hidden");
    }
  } catch {
    el.classList.add("hidden");
  }
}

function renderYoutubeConnectionMeta(yt = {}) {
  const box = document.getElementById("youtubeConnectionMeta");
  const videoEl = document.getElementById("youtubeLiveVideoLabel");
  if (!box || !videoEl) return;

  const ids = Array.isArray(yt.videoIds) && yt.videoIds.length
    ? yt.videoIds
    : yt.videoId
      ? [yt.videoId]
      : [];
  if (!ids.length) {
    box.classList.add("hidden");
    return;
  }

  box.classList.remove("hidden");
  const rows = ids.slice(0, 4).map((id) => {
    const url = `https://www.youtube.com/watch?v=${id}`;
    return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(id)}</a>`;
  });
  if (ids.length > 4) rows.push(`+${ids.length - 4} yayın daha`);
  videoEl.innerHTML = rows.join(" · ");
}

function beginRoomPanelSession() {
  roomPanelGeneration += 1;
  return roomPanelGeneration;
}

function isCurrentRoomPanelSession(token) {
  return token === roomPanelGeneration;
}

function resetYoutubePanelForRoomSwitch({ clearStream = false } = {}) {
  const parsed = document.getElementById("streamUrlParsed");
  if (clearStream) renderStreamUrlRows([""]);
  if (parsed) {
    parsed.textContent = "";
    parsed.classList.add("hidden");
  }
  document.getElementById("youtubeVideoLinked")?.classList.add("hidden");
  document.getElementById("youtubeConnectionMeta")?.classList.add("hidden");
  renderYoutubeConnectionMeta({});
  setYtPill(document.getElementById("ytPillMode"), "—", "");
  setYtPill(document.getElementById("ytPillChat"), "—", "");
}

function updateYoutubeUI(yt = {}, config = {}, uiOpts = {}) {
  if (uiOpts.roomId && uiOpts.roomId !== getRoomId()) return;

  const help = document.getElementById("youtubeModeHelp");
  const envPre = document.getElementById("envHelpPre");
  const videoLinked = document.getElementById("youtubeVideoLinked");
  const connectBtn = document.getElementById("btnYoutubeConnect");
  const disconnectBtn = document.getElementById("btnYoutubeDisconnect");

  if (envPre) {
    envPre.textContent =
      yt.mode === "mock"
        ? "CHAT_MODE=mock (test)"
        : "CHAT_MODE=youtube · InnerChat (youtube-chat)";
  }

  updateBotTestHint(yt);

  if (yt.mode === "mock") {
    setYtPill(document.getElementById("ytPillMode"), "Test modu (mock)", "warn");
    setYtPill(document.getElementById("ytPillChat"), "Panel sohbeti", "warn");
    if (help) {
      help.textContent =
        "Gerçek YouTube için .env dosyasında CHAT_MODE=youtube yapın ve sunucuyu yeniden başlatın.";
    }
    renderConnectSteps([
      { text: ".env → CHAT_MODE=youtube", done: false, active: true },
      { text: "Sunucuyu yeniden başlat", done: false },
      { text: "Canlı yayın linki + Sohbete bağlan", done: false },
    ]);
    connectBtn?.removeAttribute("disabled");
    disconnectBtn?.setAttribute("disabled", "disabled");
    if (videoLinked) videoLinked.classList.add("hidden");
    setYoutubeActionBanner(
      "Test modu (mock): gerçek YouTube sohbeti kapalı. Aşağıdan «Gönder» ile deneyin veya .env içinde CHAT_MODE=youtube yapıp sunucuyu yeniden başlatın.",
      "warn"
    );
    return;
  }

  connectBtn?.removeAttribute("disabled");
  disconnectBtn?.removeAttribute("disabled");

  setYtPill(document.getElementById("ytPillMode"), "YouTube modu", "ok");
  setYtPill(
    document.getElementById("ytPillChat"),
    yt.connected ? "Sohbet bağlı" : "Sohbet kapalı",
    yt.connected ? "ok" : "warn"
  );

  renderYoutubeConnectionMeta(yt);
  renderInnerChatTapMeta({
    enabled: yt.innerChatTapEnabled !== false,
    pollingMode: yt.pollingMode,
    connected: yt.connected,
    streamCount: (yt.videoIds && yt.videoIds.length) || (yt.videoId ? 1 : 0),
    count: yt.innerChatTapCount ?? 0,
    max: 100,
  });

  if (help) {
    const pollSec = yt.chatPollIntervalMs
      ? Math.round(Number(yt.chatPollIntervalMs) / 1000)
      : 2;
    if (yt.listenError && yt.connected) {
      help.textContent = `Bağlı; canlı sohbet henüz açılamadı: ${yt.listenError}. Yayın CANLI olmalı (watch?v=). Otomatik yeniden deneniyor.`;
    } else if (yt.listeningLive || yt.chatStayConnected) {
      help.textContent = `Canlı sohbet dinleniyor (~${pollSec} sn). Mesajlar oyuna işlenir.`;
    } else if (yt.connected) {
      help.textContent = `Sohbet bağlı. Oyunu «Başlat» deyince canlı dinleme açılır (~${pollSec} sn).`;
    } else {
      help.textContent =
        "Canlı yayın linkini yapıştırın → Sohbete bağlan → Kontrol’den Başlat.";
    }
  }

  renderConnectSteps([
    { text: "Sunucu YouTube modunda (.env)", done: true },
    {
      text: "Canlı yayın video linki (watch / youtu.be / studio)",
      done: Boolean((yt.videoIds && yt.videoIds.length) || yt.videoId),
      active: !((yt.videoIds && yt.videoIds.length) || yt.videoId),
    },
    {
      text: "Sohbete bağlan",
      done: yt.connected,
      active: Boolean((yt.videoIds && yt.videoIds.length) || yt.videoId) && !yt.connected,
    },
    { text: "Kontrol → Başlat", done: false, active: yt.connected },
  ]);

  if (!isStreamUrlListFocused()) {
    restoreStreamUrlField(config, yt);
  }

  if (videoLinked) {
    const urls = Array.isArray(yt.streamUrls) && yt.streamUrls.length
      ? yt.streamUrls
      : yt.videoId
        ? [`https://www.youtube.com/watch?v=${yt.videoId}`]
        : [];
    if (urls.length) {
      videoLinked.innerHTML = `Bağlı yayınlar (${urls.length}): ` +
        urls
          .slice(0, 3)
          .map((url) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(url)}</a>`)
          .join(" · ") +
        (urls.length > 3 ? ` · +${urls.length - 3} daha` : "");
      videoLinked.classList.remove("hidden");
    } else {
      videoLinked.classList.add("hidden");
    }
  }
}

async function refreshYoutubeStatus(expectedRoomId) {
  const roomId = expectedRoomId || getRoomId();
  if (!roomId) return;
  const panelToken = roomPanelGeneration;
  try {
    const res = await fetch(`/api/rooms/${roomId}/youtube/status`, fetchOpts);
    if (!res.ok) return;
    const yt = await res.json();
    if (!isCurrentRoomPanelSession(panelToken) || getRoomId() !== roomId) return;
    updateYoutubeUI(yt, { videoId: yt.videoId }, { roomId });
    updateUI({ state: document.getElementById("gameState")?.textContent || "idle" }, {
      chatMode: yt.mode,
      youtubeConnected: yt.connected,
    });
    void loadInnerChatTap(roomId);
  } catch {
    /* yoksay */
  }
}

async function initDashboard(roomId, { skipAccessCheck = false } = {}) {
  if (!skipAccessCheck && !(await verifyRoomAccess(roomId))) return;

  const panelToken = beginRoomPanelSession();

  document.getElementById("setupScreen")?.classList.add("hidden");
  document.getElementById("dashboard")?.classList.remove("hidden");
  setRoomId(roomId);
  rememberRecentRoom(roomId);
  updateUrlDisplay(roomId);
  const ytRoomEl = document.getElementById("youtubeRoomId");
  if (ytRoomEl) ytRoomEl.textContent = roomId;
  applyCachedRoomGameMode(roomId);
  restorePanelDraftFromSession(roomId);
  resetYoutubePanelForRoomSwitch({ clearStream: false });

  questionsHydrated = false;

  await hydrateRoomConfigFromServer();

  if (socket) {
    socket.disconnect();
    socket = null;
  }

  await loadEventLog();
  await loadQuestions();
  questionsHydrated = true;

  socket = io({ query: { room: roomId } });
  socket.on("game:state", (s) => {
    if (!questionsHydrated) return;
    if (
      currentRoomGameMode !== GAME_MODE_TEAM_RACE &&
      (currentRoomGameMode !== GAME_MODE_PHOTO_BATTLE || celebrityAgeInPhotoMode())
    ) {
      updateUI(s);
    }
  });
  socket.on("race:state", (s) => {
    if (!questionsHydrated) return;
    if (currentRoomGameMode === GAME_MODE_TEAM_RACE) updateUI(s);
  });
  socket.on("race:spawn", () => {
    if (!questionsHydrated || currentRoomGameMode !== GAME_MODE_TEAM_RACE) return;
    void refreshGameStatusUi();
  });
  socket.on("photo-battle:state", (s) => {
    if (!questionsHydrated || currentRoomGameMode !== GAME_MODE_PHOTO_BATTLE) return;
    if (celebrityAgeInPhotoMode()) return;
    updateUI(s);
  });
  socket.on("config", (c) => {
    if (!questionsHydrated) return;
    if (c.gameMode) applyDashboardGameMode(c.gameMode);
    if (c.celebrityQuiz != null) setRoomCelebrityQuizFlag(c.celebrityQuiz);
    updateUI({ state: "idle" }, c);
  });
  socket.on("room:log", (e) => renderLogEntry(e.message, e.highlight, e.id));
  socket.on("youtube:status", (yt) => {
    if (!isCurrentRoomPanelSession(panelToken) || yt.roomId !== roomId) return;
    updateYoutubeUI(yt, { videoId: yt.videoId }, { roomId });
    void refreshGameStatusUi();
  });
  socket.on("inner-chat:tap", (entry) => {
    if (!isCurrentRoomPanelSession(panelToken) || getRoomId() !== roomId) return;
    prependInnerChatTapEntry(entry);
    const meta = document.getElementById("innerChatTapMeta");
    if (meta) {
      const n = document.getElementById("innerChatTapList")?.children.length ?? 0;
      const prev = meta.textContent || "";
      if (prev.includes("kayıt")) {
        meta.textContent = prev.replace(/\d+\/\d+ kayıt/, `${n}/100 kayıt`);
      }
    }
  });
  socket.on("inner-chat:tap:clear", () => {
    if (!isCurrentRoomPanelSession(panelToken) || getRoomId() !== roomId) return;
    renderInnerChatTapList([]);
  });
  socket.on("audit:log", (entry) => {
    if (!isCurrentRoomPanelSession(panelToken) || getRoomId() !== roomId) return;
    prependAuditEntry(entry);
  });
  socket.on("audit:log:clear", () => {
    if (!isCurrentRoomPanelSession(panelToken) || getRoomId() !== roomId) return;
    renderAuditLogList([]);
  });
  socket.on("layout:updated", () => {
    if (!isCurrentRoomPanelSession(panelToken)) return;
    void refreshOverlayAfterLayout();
  });

  try {
    const res = await api("/status");
    if (!isCurrentRoomPanelSession(panelToken) || getRoomId() !== roomId) return;
    if (res.ok) {
      const d = await res.json();
      setRoomCelebrityQuizFlag(d.celebrityQuiz);
      const snap = d.game || d.photoBattle || d.race;
      updateUI(snap, {
        chatMode: d.chatMode,
        roomName: d.roomName,
        botName: d.botName,
        youtubeConnected: d.youtube?.connected,
        celebrityQuiz: d.celebrityQuiz,
      });
      fillBotForm(d.config);
      fillRaceSettingsForm(d.config?.raceSettings || d.race?.settings);
      if (d.config?.gameMode) {
        applyDashboardGameMode(d.config.gameMode);
        rememberRoomGameMode(roomId, d.config.gameMode);
      }
      setupGameModePicker();
      updateYoutubeUI(d.youtube || { mode: d.chatMode }, d.config || {}, {
        roomId,
      });
      restoreStreamUrlField(d.config || {}, d.youtube || {});
      void loadInnerChatTap(roomId);
      void loadAuditLog();
    } else {
      await refreshYoutubeStatus(roomId);
    }
  } catch {
    if (isCurrentRoomPanelSession(panelToken) && getRoomId() === roomId) {
      await refreshYoutubeStatus(roomId);
    }
  }

  await fetchUserRooms();
  renderRoomSwitcher();
  const hubRoom = userRoomsList.find((r) => r.id === roomId);
  if (hubRoom) {
    const rn = document.getElementById("roomName");
    if (rn) rn.textContent = hubRoom.displayName || hubRoom.name;
  }
  setupPreviewResizeObserver();
  setupGameModePicker();
  initCelebrityPanel();
  initFootballPanel();
  updateCelebrityLabLinks(roomId);
  updateFootballOverlayLinks(roomId);
  requestAnimationFrame(layoutPreviewScales);
}

window.addEventListener("pagehide", flushRoomPanelDraft);
window.addEventListener("beforeunload", flushRoomPanelDraft);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") flushRoomPanelDraft();
});

document.getElementById("btnInnerChatTapClear")?.addEventListener("click", () => {
  void clearInnerChatTap();
});

document.getElementById("btnAuditRefresh")?.addEventListener("click", () => {
  void loadAuditLog();
});
document.getElementById("btnAuditClear")?.addEventListener("click", () => {
  void clearAuditLogPanel();
});
document.getElementById("auditLogFilter")?.addEventListener("change", () => {
  void loadAuditLog();
});

document.getElementById("btnYoutubeConnect")?.addEventListener("click", async () => {
  if (!requireRoomForYoutubeAction()) return;

  let chatMode = "youtube";
  try {
    const infoRes = await fetch("/api/app/chat-info", { cache: "no-store" });
    if (infoRes.ok) {
      const info = await infoRes.json();
      chatMode = info.chatMode || chatMode;
    }
  } catch {
    /* devam */
  }
  if (chatMode === "mock") {
    const msg =
      "Sohbet test modu (mock) açık. Canlı yayın için CHAT_MODE=youtube ayarlayıp sunucuyu yeniden başlatın.";
    setYoutubeActionBanner(msg, "warn");
    log(msg, false, { persist: true });
    alert(msg);
    return;
  }

  const streamUrls = collectStreamUrlsFromDom();
  const streamUrl = normalizeStreamUrlDraftClient(streamUrls.join("\n"));
  if (!streamUrl) {
    setYoutubeActionBanner("En az bir canlı yayın linki girin.", "error");
    log("Yayın linki girin.", false, { persist: true });
    return;
  }
  const statusRes = await api("/youtube/status").catch(() => null);
  const prev = statusRes?.ok ? await statusRes.json() : null;
  if (
    prev?.connected &&
    !window.confirm(
      "Sohbet zaten bağlı görünüyor. Yeniden bağlanmak dinlemeyi yeniler. Devam?"
    )
  ) {
    return;
  }
  setYoutubeButtonsBusy(true, "btnYoutubeConnect");
  setYoutubeActionBanner("Canlı sohbete bağlanılıyor…", "loading");
  try {
    const res = await api("/youtube/connect", {
      method: "POST",
      body: JSON.stringify({ streamUrls }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    const n = streamUrls.length;
    applyYoutubeActionResult(data, {
      fallbackOk:
        n > 1
          ? `YouTube canlı sohbete bağlandı (${n} yayın dinleniyor).`
          : "YouTube canlı sohbete bağlandı.",
    });
    void persistStreamUrlDraft();
    await loadEventLog();
    log("YouTube canlı sohbete bağlandı.", true, { persist: false });
  } catch (err) {
    setYoutubeActionBanner(err.message, "error");
    log("Bağlantı hatası: " + err.message, false, { persist: true });
    await refreshYoutubeStatus();
  } finally {
    setYoutubeButtonsBusy(false, "btnYoutubeConnect");
  }
});

document.getElementById("btnYoutubeDisconnect")?.addEventListener("click", async () => {
  if (!requireRoomForYoutubeAction()) return;
  setYoutubeButtonsBusy(true, "btnYoutubeDisconnect");
  setYoutubeActionBanner("Sohbet dinleme durduruluyor…", "loading");
  try {
    const res = await api("/youtube/disconnect", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    applyYoutubeActionResult(data, {
      fallbackOk: "Canlı sohbet dinleme durduruldu.",
    });
    await loadEventLog();
    log("YouTube sohbet dinleme durduruldu.", true, { persist: false });
  } catch (err) {
    setYoutubeActionBanner(err.message, "error");
    log("Hata: " + err.message, false, { persist: true });
  } finally {
    setYoutubeButtonsBusy(false, "btnYoutubeDisconnect");
  }
});

async function showSetup() {
  beginRoomPanelSession();
  if (socket) {
    socket.disconnect();
    socket = null;
  }
  closePreviewModal();
  document.getElementById("setupScreen")?.classList.remove("hidden");
  document.getElementById("dashboard")?.classList.add("hidden");
  document.getElementById("currentUser").textContent = currentUser?.username || "-";

  const rooms = await fetchUserRooms();
  if (rooms === null) {
    location.href = `/login/?next=${encodeURIComponent("/admin/")}`;
    return;
  }
  renderRoomSwitcher();

  renderRoomsHub();
}

document.getElementById("btnLogout")?.addEventListener("click", async (e) => {
  e.preventDefault();
  await fetch("/api/auth/logout", { method: "POST", ...fetchOpts });
  location.href = "/login/";
});

document.getElementById("btnCreateRoom")?.addEventListener("click", async () => {
  const name = document.getElementById("newRoomName")?.value?.trim() || "Yayın";
  const res = await fetch("/api/rooms", {
    method: "POST",
    ...fetchOpts,
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ name, gameMode: getNewRoomGameMode() }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "Yayın oluşturulamadı");
    return;
  }
  await switchToRoom(data.id);
});

document.querySelectorAll(".preview-layout-btn").forEach((btn) => {
  btn.addEventListener("click", () => setPreviewLayout(btn.dataset.previewLayout));
});

document.getElementById("btnPreviewRefresh")?.addEventListener("click", async () => {
  const roomId = getRoomId();
  if (!roomId) return;
  await syncPreviewStages(roomId);
  log("Önizleme yenilendi.", false, { persist: true });
});

document.getElementById("btnPreviewRefreshRace")?.addEventListener("click", async () => {
  const roomId = getRoomId();
  if (!roomId) return;
  await syncPreviewStages(roomId);
  log("Takım yarışı önizlemesi yenilendi.", false, { persist: true });
});

document.getElementById("btnPreviewEnlarge")?.addEventListener("click", openPreviewModal);
document.getElementById("btnPreviewModalClose")?.addEventListener("click", closePreviewModal);
document.getElementById("previewModalBackdrop")?.addEventListener("click", closePreviewModal);
document.getElementById("btnModalZoomIn")?.addEventListener("click", () => nudgePreviewZoom(true, PREVIEW_ZOOM_STEP));
document.getElementById("btnModalZoomOut")?.addEventListener("click", () => nudgePreviewZoom(true, -PREVIEW_ZOOM_STEP));
document.getElementById("btnModalZoomFit")?.addEventListener("click", () => resetPreviewZoom(true, true));
document.getElementById("btnSidebarZoomIn")?.addEventListener("click", () => nudgePreviewZoom(false, PREVIEW_ZOOM_STEP));
document.getElementById("btnSidebarZoomOut")?.addEventListener("click", () => nudgePreviewZoom(false, -PREVIEW_ZOOM_STEP));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closePreviewModal();
  const modal = document.getElementById("previewModal");
  if (!modal || modal.classList.contains("hidden")) return;
  if (e.key === "+" || e.key === "=") nudgePreviewZoom(true, PREVIEW_ZOOM_STEP);
  if (e.key === "-") nudgePreviewZoom(true, -PREVIEW_ZOOM_STEP);
});

window.addEventListener("resize", () => layoutPreviewScales());

async function refreshOverlayAfterLayout() {
  const roomId = getRoomId();
  if (roomId) await syncPreviewStages(roomId);
  layoutPreviewScales();
}

document.getElementById("btnOpenCalibrate")?.addEventListener("click", () => {
  openCalibratePage(getRoomId());
});

document.getElementById("btnFillExample")?.addEventListener("click", () => {
  fillExample().catch((err) => log("Hata: " + err.message, false, { persist: true }));
});
document.getElementById("btnFillExampleSetup")?.addEventListener("click", () => {
  document.getElementById("newRoomName").value = "Örnek Cumartesi Yayını";
});

document.querySelectorAll(".copy").forEach((btn) => {
  btn.addEventListener("click", () => {
    const text = document.getElementById(btn.dataset.target)?.textContent?.trim();
    if (!text || !text.startsWith("http")) return;
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = "Kopyalandı!";
      setTimeout(() => {
        btn.textContent = "Kopyala";
      }, 1500);
    });
  });
});

async function refreshGameStatusUi() {
  try {
    const res = await api("/status");
    if (!res.ok) return;
    const d = await res.json();
    if (d.config?.gameMode) {
      applyDashboardGameMode(d.config.gameMode);
      rememberRoomGameMode(getRoomId(), d.config.gameMode);
    }
    updateYoutubeUI(d.youtube || { mode: d.chatMode }, d.config || {}, {
      roomId: getRoomId(),
    });
    restoreStreamUrlField(d.config || {}, d.youtube || {});
    setRoomCelebrityQuizFlag(d.celebrityQuiz);
    updateUI(d.game || d.race || d.photoBattle, {
      chatMode: d.chatMode,
      roomName: d.roomName,
      botName: d.botName,
      youtubeConnected: d.youtube?.connected,
      celebrityQuiz: d.celebrityQuiz,
    });
  } catch {
    /* yoksay */
  }
}

async function loadQuestions() {
  const badge = document.getElementById("questionsCountBadge");
  try {
    const res = await api("/questions");
    if (res.status === 401) {
      location.href = `/login/?next=${encodeURIComponent(location.pathname + location.search)}`;
      return;
    }
    const data = await res.json();
    if (!res.ok) {
      if (res.status === 403) handleRoomAccessDenied(data.error);
      if (badge) {
        badge.textContent = "Sorular yüklenemedi — yeniden giriş veya sayfayı yenileyin";
        badge.className = "questions-count-badge questions-count-badge--empty";
      }
      return;
    }
    const list = Array.isArray(data)
      ? data
      : Array.isArray(data?.questions)
        ? data.questions
        : [];
    questions = list.map((q) => ({ ...q, points: normalizeQuestionPoints(q) }));
    serverQuestionCount =
      Number(data?.count) > 0 ? Number(data.count) : questions.length;
    renderQuestionsEditor();
    if (data?.config?.gameMode) {
      applyDashboardGameMode(data.config.gameMode);
      rememberRoomGameMode(getRoomId(), data.config.gameMode);
    }
    if (data?.celebrityQuiz != null) {
      setRoomCelebrityQuizFlag(data.celebrityQuiz);
    }
    const snap = data?.game || data?.photoBattle;
    if (snap) {
      updateUI(snap, {
        chatMode: "youtube",
        celebrityQuiz: data.celebrityQuiz,
      });
    }
    await refreshGameStatusUi();
  } catch (err) {
    if (badge) {
      badge.textContent = `Sorular yüklenemedi: ${err.message || "ağ hatası"}`;
      badge.className = "questions-count-badge questions-count-badge--empty";
    }
  } finally {
    updateQuestionsCountBadge();
  }
}

function updateQuestionsCountBadge() {
  const celeb = document.getElementById("celebrityQuestionsBadge");
  const el = document.getElementById("questionsCountBadge");
  if (!el) return;
  const editorItems = document.querySelectorAll(".question-item");
  if (editorItems.length) syncFromEditor();
  const local = questions.length;
  if (!local) {
    el.textContent = "Henüz soru yok";
    el.className = "questions-count-badge questions-count-badge--empty";
    if (celeb) celeb.textContent = "Henüz ünlü sorusu yok — Test Lab veya CSV ile yükleyin";
    refreshQuestionOrderFromEditor();
    return;
  }
  if (local !== serverQuestionCount) {
    el.textContent = `${local} soru panelde · sunucuda ${serverQuestionCount} — «Soruları kaydet» ile önizlemeyi güncelleyin`;
    el.className = "questions-count-badge questions-count-badge--dirty";
  } else {
    el.textContent = `${local} soru kayıtlı · Kontrol ve OBS sayacı ${local} soru`;
    el.className = "questions-count-badge";
  }
  if (celeb) {
    const withPhoto = questions.filter((q) => q.imageUrl).length;
    celeb.textContent = withPhoto
      ? `${withPhoto} ünlü sorusu (fotoğraflı) · toplam ${local} soru`
      : `${local} soru — ünlü fotoğrafı için CSV kullanın`;
  }
  updateFootballQuestionsBadge();
  if (detectLocalCelebrityQuiz()) {
    setRoomCelebrityQuizFlag(true);
    if (currentRoomGameMode === GAME_MODE_PHOTO_BATTLE) {
      applyDashboardGameMode(currentRoomGameMode);
    }
  }
  refreshQuestionOrderFromEditor();
}

/** Kaydedilmemiş soru sayısını Kontrol → Sıra satırında göster */
function refreshQuestionOrderFromEditor() {
  const qo = document.getElementById("questionOrder");
  const gs = document.getElementById("gameState");
  if (!qo || !gs) return;
  if (gs.textContent !== stateLabels.idle) return;
  const local = getLocalQuestionCount();
  if (!local) return;
  if (local === serverQuestionCount) {
    qo.textContent = `0 / ${local}`;
    return;
  }
  qo.textContent = `0 / ${local} (${serverQuestionCount} kayıtlı — kaydedin)`;
}

function renderPointOptions(selected) {
  const pts = normalizeQuestionPoints({ points: selected });
  return QUESTION_POINT_OPTIONS.map(
    (p) => `<option value="${p}"${p === pts ? " selected" : ""}>${p} puan</option>`
  ).join("");
}

function renderQuestionsEditor() {
  const root = document.getElementById("questionsEditor");
  if (!root) return;
  if (!Array.isArray(questions)) questions = [];
  root.innerHTML = "";
  questions.forEach((q, i) => {
    const el = document.createElement("div");
    el.className = "question-item";
    const pts = normalizeQuestionPoints(q);
    el.innerHTML = `
      <div class="question-item-head">
        <span class="question-item-num">Soru ${i + 1}</span>
        <label class="question-points-label">Puan
          <select data-field="points">${renderPointOptions(pts)}</select>
        </label>
      </div>
      <label>Soru metni</label>
      <textarea data-field="question">${escapeHtml(q.question)}</textarea>
      <label>Kabul edilen cevaplar (virgülle)</label>
      <input data-field="answers" value="${escapeHtml((q.answers || []).join(", "))}" />
      <label>Kategori / ipucu (ekranda)</label>
      <input data-field="hint" value="${escapeHtml(q.hint || "")}" placeholder="örn. Coğrafya, Harf karmaşası" />
      <button type="button" class="remove" data-remove="${i}">Sil</button>
    `;
    root.appendChild(el);
  });
  root.querySelectorAll("[data-field]").forEach((i) => {
    i.addEventListener("input", () => {
      syncFromEditor();
      updateQuestionsCountBadge();
    });
    i.addEventListener("change", () => {
      syncFromEditor();
      updateQuestionsCountBadge();
    });
  });
  root.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      questions.splice(Number(btn.dataset.remove), 1);
      renderQuestionsEditor();
      updateQuestionsCountBadge();
    });
  });
  updateQuestionsCountBadge();
}

function syncFromEditor() {
  const items = document.querySelectorAll(".question-item");
  if (!items.length) return;

  const next = [];
  items.forEach((item, i) => {
    const pointsEl = item.querySelector('[data-field="points"]');
    next.push({
      id: questions[i]?.id ?? String(i + 1),
      question: item.querySelector('[data-field="question"]')?.value ?? "",
      answers: (item.querySelector('[data-field="answers"]')?.value ?? "")
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean),
      hint: item.querySelector('[data-field="hint"]')?.value ?? "",
      points: normalizeQuestionPoints({
        points: pointsEl ? Number(pointsEl.value) : 10,
      }),
    });
  });
  questions = next;
}

/** Paneldeki soruları sunucuya yazar */
async function saveQuestionsToServer() {
  syncFromEditor();
  if (!questions.length) {
    log("Kaydedilecek soru yok.", false, { persist: true });
    return { ok: false };
  }
  const roomId = getRoomId();
  if (!roomId) {
    log("Önce «Panele gir» ile bir yayın odası açın, sonra kaydedin.", false, {
      persist: true,
    });
    return { ok: false };
  }
  const res = await api("/questions", {
    method: "PUT",
    body: JSON.stringify({ questions }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    log(
      "Sorular kaydedilemedi: " + (data.error || res.statusText || res.status),
      false,
      { persist: true }
    );
    return { ok: false, error: data.error };
  }
  serverQuestionCount = data.count ?? data.questions?.length ?? questions.length;
  if (data.game) {
    updateUI(data.game);
  } else {
    await refreshGameStatusUi();
  }
  updateQuestionsCountBadge();
  return { ok: true, count: serverQuestionCount };
}

async function autoSaveQuestionsAfterImport(importedCount) {
  const roomId = getRoomId();
  if (!roomId) {
    log(
      `${importedCount} soru yüklendi. Kaydetmek için bu odada «Panele gir» → «Soruları kaydet».`,
      false,
      { persist: true }
    );
    return;
  }
  const result = await saveQuestionsToServer();
  if (result.ok) {
    log(`${result.count} soru sunucuya kaydedildi.`, true, { persist: true });
    await loadEventLog();
  }
}

function shuffleQuestionPoints() {
  syncFromEditor();
  questions.forEach((q) => {
    q.points = pickRandomQuestionPoints();
  });
  renderQuestionsEditor();
  log("Sorulara karışık puan atandı — kaydetmeyi unutmayın.", false, { persist: true });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

document.getElementById("btnAddQuestion")?.addEventListener("click", () => {
  questions.push({
    id: String(Date.now()),
    question: "Yeni soru?",
    answers: ["cevap"],
    hint: "",
    points: pickRandomQuestionPoints(),
  });
  renderQuestionsEditor();
});

document.getElementById("btnQuestionTemplate")?.addEventListener("click", openQuestionTemplateModal);

document.getElementById("btnApplyQuestionTemplate")?.addEventListener("click", () => {
  const tpl = QUESTION_TEMPLATES.find((t) => t.id === selectedQuestionTemplateId);
  if (!tpl) {
    alert("Önce bir şablon seçin.");
    return;
  }
  const mode = getQuestionApplyMode("templateApplyMode");
  if (mode === "replace" && questions.length > 0) {
    if (!window.confirm(`Mevcut ${questions.length} soru silinip şablon yüklensin mi?`)) return;
  }
  const count = tpl.questions().length;
  applyQuestionsList(tpl.questions(), mode);
  closeQDialog("questionsTemplateModal");
  void autoSaveQuestionsAfterImport(count);
});

document.getElementById("btnCopyGptPrompt")?.addEventListener("click", async () => {
  const text = buildChatGptQuestionPrompt(CHATGPT_QUESTION_COUNT);
  const ok = await copyTextToClipboard(text);
  log(
    ok
      ? `ChatGPT promptu panoya kopyalandı (${CHATGPT_QUESTION_COUNT} soru). ChatGPT'ye yapıştırın, JSON'u «JSON yapıştır» ile alın.`
      : "Kopyalama başarısız — tarayıcı izni verin.",
    false,
    { persist: true }
  );
});

document.getElementById("btnImportQuestionsJson")?.addEventListener("click", openQuestionsImportModal);

async function loadCelebritySampleIntoModal() {
  const ta = document.getElementById("celebrityImportText");
  if (!ta) return;
  try {
    const res = await fetch("/play/celebrity-sample.csv");
    if (!res.ok) throw new Error("örnek dosya yok");
    ta.value = await res.text();
    log("30 ünlülük örnek CSV yüklendi.", true, { persist: true });
  } catch {
    log("Örnek CSV yüklenemedi.", false, { persist: true });
  }
}

function openCelebrityImportModal() {
  openQDialog("celebrityImportModal");
  document.getElementById("celebrityImportText")?.focus();
}

async function copyCelebrityGptPrompt() {
  const text = buildCelebrityChatGptPrompt(CELEBRITY_CHATGPT_COUNT);
  const ok = await copyTextToClipboard(text);
  const msg = ok
    ? `ChatGPT şablonu kopyalandı (${CELEBRITY_CHATGPT_COUNT} satır). «CSV yapıştır» ile yükleyin.`
    : "Kopyalama başarısız — tarayıcı izni verin.";
  showCelebrityStatus(msg, ok ? "ok" : "error");
  log(msg, ok, { persist: true });
}

document.getElementById("btnCelebrityLoadSample")?.addEventListener("click", loadCelebritySampleIntoModal);

document.getElementById("btnApplyCelebrityImport")?.addEventListener("click", async () => {
  if (!requireRoomForCelebrity("CSV yükleme")) return;
  const ta = document.getElementById("celebrityImportText");
  const hint = document.getElementById("celebrityImportHint")?.value?.trim();
  const mode = getQuestionApplyMode("celebrityApplyMode");
  showCelebrityStatus("CSV kaydediliyor…", "info");
  try {
    const body = JSON.stringify({
      csv: ta?.value || "",
      hint: hint || "Ünlülerin Yaşını Tahmin Et",
      mode,
    });
    let res = await api("/questions/import-celebrities", { method: "POST", body });
    if (res.status === 404) {
      res = await api("/import-celebrities", { method: "POST", body });
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      alert(data.error || "CSV yüklenemedi");
      return;
    }
    questions = data.questions || [];
    renderQuestionsEditor();
    updateQuestionsCountBadge();
    closeQDialog("celebrityImportModal");
    setRoomCelebrityQuizFlag(data.celebrityQuiz ?? true);
    applyDashboardGameMode(currentRoomGameMode);
    const n = data.imported ?? data.count ?? questions.length;
    showCelebrityStatus(`${n} ünlü kaydedildi. «Başlat» ile başlayın.`, "ok");
    log(
      `${n} ünlü yüklendi (toplam ${data.count ?? questions.length}). Mod değişmedi.`,
      true,
      { persist: true }
    );
    updateUrlDisplay(getRoomId());
    if (currentRoomGameMode !== GAME_MODE_TEAM_RACE) {
      void refreshGameStatusUi();
    }
  } catch (err) {
    const msg = err.message || "CSV hatası";
    showCelebrityStatus(msg, "error");
    alert(msg);
  }
});

initCelebrityPanel();
initFootballPanel();

document.getElementById("btnApplyQuestionsImport")?.addEventListener("click", () => {
  const ta = document.getElementById("questionsImportText");
  try {
    const items = parseQuestionsJsonText(ta?.value || "");
    const mode = getQuestionApplyMode("importApplyMode");
    if (mode === "replace" && questions.length > 0) {
      if (!window.confirm(`Mevcut ${questions.length} soru silinip ${items.length} soru yüklensin mi?`)) {
        return;
      }
    }
    applyQuestionsList(items, mode);
    closeQDialog("questionsImportModal");
    void autoSaveQuestionsAfterImport(items.length);
  } catch (err) {
    alert(`JSON hatası: ${err.message}`);
  }
});

document.querySelectorAll("[data-close]").forEach((el) => {
  el.addEventListener("click", () => closeQDialog(el.dataset.close));
});

document.getElementById("btnShufflePoints")?.addEventListener("click", shuffleQuestionPoints);

document.getElementById("btnSaveQuestions")?.addEventListener("click", async () => {
  const result = await saveQuestionsToServer();
  if (result.ok) {
    log(`${result.count} soru kaydedildi — önizleme güncellendi.`, true, {
      persist: true,
    });
    await loadEventLog();
  }
});

document.getElementById("btnSaveBot")?.addEventListener("click", async () => {
  const res = await api("/config", {
    method: "PATCH",
    body: JSON.stringify({
      botName: document.getElementById("botName").value.trim(),
      announceWrong: document.getElementById("announceWrong").checked,
      winMessage: document.getElementById("winMessage").value.trim() || null,
      wrongMessage: document.getElementById("wrongMessage").value.trim() || null,
    }),
  });
  if (res.ok) await loadEventLog();
  else log("Bot ayarları kaydedilemedi.", false, { persist: true });
});

document.getElementById("btnStart")?.addEventListener("click", async () => {
  const res = await api("/game/start", { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (res.ok) {
    updateUI(data.game || data.photoBattle || data, { celebrityQuiz: roomCelebrityQuiz });
    await loadEventLog();
  } else {
    log("Hata: " + (data.error || res.status), false, { persist: true });
  }
});

document.getElementById("btnStop")?.addEventListener("click", async () => {
  const res = await api("/game/stop", { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (res.ok) {
    updateUI(data.game || data.photoBattle || data, { celebrityQuiz: roomCelebrityQuiz });
    await loadEventLog();
  }
});

document.getElementById("btnRaceChaos")?.addEventListener("click", async () => {
  if (currentRoomGameMode !== GAME_MODE_TEAM_RACE) return;
  const res = await api("/race/chaos", { method: "POST", body: {} });
  const data = await res.json().catch(() => ({}));
  if (res.ok) {
    updateUI(data);
    await loadEventLog();
    log("Kaos modu başlatıldı.", true, { persist: true });
  } else {
    log("Kaos: " + (data.error || res.status), false, { persist: true });
  }
});

document.getElementById("btnReset")?.addEventListener("click", async () => {
  const msg =
    celebrityAgeInPhotoMode()
      ? "Ünlü yaş oyunu sıfırlansın mı? Puanlar ve sıra silinir (soru listesi kalır)."
      : isFootballGameMode(currentRoomGameMode)
        ? "Futbol quiz sıfırlansın mı? Puanlar ve sıra silinir (oyuncu listesi kalır)."
        : currentRoomGameMode === GAME_MODE_PHOTO_BATTLE
          ? "Photo Quiz sıfırlansın mı? Tur ve oylar sıfırlanır (görseller kalır)."
          : currentRoomGameMode === GAME_MODE_TEAM_RACE
            ? "Takım yarışı sıfırlansın mı? Spawn sayıları ve tur silinir."
            : "Oyun sıfırlansın mı? Puanlar silinir, sıra başa döner (Başlat ile yeniden başlarsınız).";
  if (!window.confirm(msg)) {
    return;
  }
  const res = await api("/game/reset", { method: "POST" });
  if (res.ok) {
    const data = await res.json();
    updateUI(data.game || data.photoBattle || data, { celebrityQuiz: roomCelebrityQuiz });
    await loadEventLog();
  } else {
    log("Sıfırlama hatası: " + ((await res.json()).error || res.status), false, {
      persist: true,
    });
  }
});

document.getElementById("btnSkip")?.addEventListener("click", async () => {
  if (questionLockedUntilCorrect()) {
    log("Bu modda soru doğru bilinene kadar atlanamaz.", false, {
      persist: true,
    });
    return;
  }
  const res = await api("/game/skip", { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (res.ok) {
    updateUI(data.game || data.photoBattle || data, { celebrityQuiz: roomCelebrityQuiz });
    await loadEventLog();
  }
});

document.getElementById("btnMockSend")?.addEventListener("click", async () => {
  const author = document.getElementById("mockAuthor")?.value?.trim() || "Test";
  const text = document.getElementById("mockText")?.value?.trim();
  if (!text) {
    log("Cevap metni yazın.", false, { persist: true });
    return;
  }
  const res = await api("/chat/test", {
    method: "POST",
    body: JSON.stringify({ author, text }),
  });
  const data = await res.json().catch(() => ({}));
  document.getElementById("mockText").value = "";
  if (!res.ok) {
    log("Test mesajı: " + (data.error || res.status), false, { persist: true });
    return;
  }
  if (data.note) log(data.note, false, { persist: true });
  await loadEventLog();
});

function ensureUpdateBanner() {
  let bar = document.getElementById("appUpdateBanner");
  if (bar) return bar;
  bar = document.createElement("div");
  bar.id = "appUpdateBanner";
  bar.className = "app-update-banner hidden";
  bar.innerHTML =
    '<span>Yeni panel sürümü hazır.</span><button type="button" class="btn primary" id="btnAppReload">Yenile</button>';
  document.body.prepend(bar);
  bar.querySelector("#btnAppReload")?.addEventListener("click", () => {
    const u = new URL(location.href);
    u.searchParams.set("_v", Date.now());
    location.href = u.toString();
  });
  return bar;
}

async function checkAppVersion() {
  if (!BUNDLED_APP_VERSION) return;
  try {
    const res = await fetch("/api/app/version", { cache: "no-store" });
    if (!res.ok) return;
    const { version } = await res.json();
    if (version && version !== BUNDLED_APP_VERSION) {
      ensureUpdateBanner().classList.remove("hidden");
    }
  } catch {
    /* yoksay */
  }
}

function warnIfEmbeddedPreviewHost() {
  const proto = location.protocol;
  const embedded =
    proto === "vscode-webview:" ||
    proto === "cursor:" ||
    /vscode-cdn\.net/i.test(location.href) ||
    typeof window.acquireVsCodeApi === "function";
  if (embedded || proto === "file:") {
    setPreviewLoadMessage(
      "Önizleme bu pencerede çalışmayabilir. Paneli normal tarayıcıda açın.",
      true
    );
    return true;
  }
  return false;
}

async function boot() {
  initStreamUrlListUi();
  warnIfEmbeddedPreviewHost();
  const me = await fetch("/api/auth/me", { ...fetchOpts, cache: "no-store" }).then((r) =>
    r.json()
  );
  if (!me.user) {
    location.href = `/login/?next=${encodeURIComponent(location.pathname + location.search)}`;
    return;
  }
  currentUser = me.user;

  checkAppVersion();
  setInterval(checkAppVersion, 45_000);
  setInterval(async () => {
    const roomId = getRoomId();
    if (
      !roomId ||
      document.getElementById("dashboard")?.classList.contains("hidden")
    ) {
      return;
    }
    const frame = document.getElementById("previewFrame");
    if (!frame?.classList.contains("preview-frame--hidden") && !isChromeErrorFrame(frame)) {
      return;
    }
    if (await isPreviewServerUp()) await syncPreviewStages(roomId);
  }, 15_000);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    checkAppVersion();
    if (getRoomId() && document.getElementById("dashboard") && !document.getElementById("dashboard").classList.contains("hidden")) {
      loadEventLog();
    }
  });

  try {
    await fetchUserRooms();
  } catch {
    /* yoksay */
  }
  renderRoomSwitcher();

  try {
    const infoRes = await fetch("/api/app/chat-info", { cache: "no-store" });
    if (infoRes.ok) {
      const info = await infoRes.json();
      updateYoutubeUI({ mode: info.chatMode }, {}, {});
      updateBotTestHint({ mode: info.chatMode });
    }
  } catch {
    /* yoksay */
  }

  const roomId = getRoomId();
  if (roomId) {
    const inList = userRoomsList.some((r) => r.id === roomId);
    if (!inList) {
      handleRoomAccessDenied(
        "Kayıtlı yayın kodu hesabınızda yok. Lütfen listeden bir yayın seçin."
      );
    } else {
      applyCachedRoomGameMode(roomId);
      await initDashboard(roomId);
    }
  } else {
    showSetup();
  }
}

document.getElementById("roomSwitchSelect")?.addEventListener("change", (e) => {
  const id = e.target.value;
  if (id) switchToRoom(id);
});

document.getElementById("btnAllRooms")?.addEventListener("click", () => showSetup());

document.getElementById("btnNewRoomQuick")?.addEventListener("click", () => {
  showSetup();
  document.getElementById("newRoomName")?.focus();
});

document.getElementById("btnChangeRoom")?.addEventListener("click", (e) => {
  e.preventDefault();
  showSetup();
});

document.getElementById("btnDeleteRoom")?.addEventListener("click", async (e) => {
  e.preventDefault();
  const roomId = getRoomId();
  if (!roomId) {
    log("Silinecek yayın seçili değil.", false, { persist: true });
    return;
  }
  const link = e.currentTarget;
  link.setAttribute("aria-disabled", "true");
  try {
    await deleteBroadcastRoom(roomId);
  } catch (err) {
    log("Oda silinemedi: " + err.message, false, { persist: true });
  } finally {
    link.removeAttribute("aria-disabled");
  }
});

document.addEventListener("keydown", (e) => {
  if (!e.altKey || e.ctrlKey || e.metaKey) return;
  if (isTypingTarget(document.activeElement)) return;
  if (!document.getElementById("dashboard") || document.getElementById("dashboard").classList.contains("hidden")) {
    return;
  }
  if (e.key === "ArrowUp") {
    e.preventDefault();
    cycleRoom(-1);
  }
  if (e.key === "ArrowDown") {
    e.preventDefault();
    cycleRoom(1);
  }
});

document.getElementById("btnSaveRaceSettings")?.addEventListener("click", () => {
  saveRaceSettings().catch((e) => log(e.message, false, { persist: true }));
});

boot();
