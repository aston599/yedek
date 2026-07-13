const fetchOpts = { credentials: "include" };

function getQueryRoom() {
  return new URLSearchParams(window.location.search).get("room")?.trim() || "";
}

function setQueryRoom(roomId) {
  const url = new URL(window.location.href);
  if (roomId) url.searchParams.set("room", roomId);
  else url.searchParams.delete("room");
  window.history.replaceState({}, "", url);
}

function calibrateFrameSrc(roomId) {
  if (!roomId) return "about:blank";
  return `/overlay/calibrate.html?embed=1&room=${encodeURIComponent(roomId)}&_=${Date.now()}`;
}

function updateShell(roomId) {
  const frame = document.getElementById("calibrateShellFrame");
  const select = document.getElementById("calibrateRoomSelect");
  const back = document.getElementById("btnBackPanel");
  const full = document.getElementById("btnCalibrateFullscreen");

  if (select && roomId) select.value = roomId;
  if (back && roomId) back.href = `/admin/?room=${encodeURIComponent(roomId)}`;
  if (full) {
    full.href = roomId
      ? `/overlay/calibrate.html?room=${encodeURIComponent(roomId)}`
      : "#";
    full.classList.toggle("hidden", !roomId);
  }
  if (frame) {
    frame.src = roomId ? calibrateFrameSrc(roomId) : "about:blank";
  }
}

async function loadRooms() {
  const res = await fetch("/api/rooms", fetchOpts);
  if (res.status === 401) {
    window.location.href = "/login/?next=" + encodeURIComponent(window.location.pathname + window.location.search);
    return [];
  }
  if (!res.ok) throw new Error("Yayınlar yüklenemedi");
  return res.json();
}

async function init() {
  const select = document.getElementById("calibrateRoomSelect");
  let roomId = getQueryRoom();

  let rooms = [];
  try {
    rooms = await loadRooms();
  } catch (err) {
    alert(err.message);
    return;
  }

  if (!select) return;

  select.innerHTML = "";
  if (!rooms.length) {
    select.innerHTML = '<option value="">Yayın yok — önce oda oluşturun</option>';
    updateShell("");
    return;
  }

  for (const r of rooms) {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = r.displayName || r.name || r.id;
    select.appendChild(opt);
  }

  if (!roomId || !rooms.some((r) => r.id === roomId)) {
    roomId = rooms[0].id;
  }

  setQueryRoom(roomId);
  updateShell(roomId);

  select.addEventListener("change", () => {
    const id = select.value;
    setQueryRoom(id);
    updateShell(id);
  });
}

init();
