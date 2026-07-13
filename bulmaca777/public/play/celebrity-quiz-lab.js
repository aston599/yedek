/**
 * Ünlü Yaş Lab — modül yok (import hatası önlenir), örnek liste her zaman yüklenir.
 */
(function () {
  "use strict";

const BUILTIN_CELEBRITY_CSV =
  (document.getElementById("builtinCelebrityCsv")?.textContent || "").trim() ||
  `isim,yaş,doğum_tarihi,foto_link
Hande Erçel,32,24.11.1993,https://upload.wikimedia.org/wikipedia/commons/3/34/Hande_Er%C3%A7el.jpg
Afra Saraçoğlu,28,02.12.1997,https://upload.wikimedia.org/wikipedia/commons/f/f7/Afra_Sara%C3%A7o%C4%9Flu_in_2019.png
Mert Ramazan Demir,28,28.01.1998,https://upload.wikimedia.org/wikipedia/commons/6/6e/Mert_Demir_%282023%29_%28cropped%29.png
Zeynep Bastık,32,08.07.1993,https://upload.wikimedia.org/wikipedia/commons/b/b3/Zeynep_Bast%C4%B1k_%28February_2020%29.png
Kerem Bürsin,38,04.06.1987,https://upload.wikimedia.org/wikipedia/commons/5/53/Festival_de_M%C3%A1laga_2024_-_Kerem_B%C3%BCrsin_%28cropped%29.jpg
Demet Özdemir,34,26.02.1992,https://upload.wikimedia.org/wikipedia/commons/2/2d/Demet_%C3%96zdemir_on_Tolgshow.jpg
Serenay Sarıkaya,33,01.07.1992,https://upload.wikimedia.org/wikipedia/commons/a/ac/Serenay_Sar%C4%B1kaya_2019.png
Aleyna Tilki,26,28.03.2000,https://upload.wikimedia.org/wikipedia/commons/e/e4/Aleyna_Tilki.png
Melike Şahin,37,18.04.1989,https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Melike_%C5%9Eahin_4.jpg/1920px-Melike_%C5%9Eahin_4.jpg
Mabel Matiz,40,31.08.1985,https://upload.wikimedia.org/wikipedia/commons/c/cf/Mabel_Matiz_-_15._Radyo_Bo%C4%9Fazi%C3%A7i_%C3%96d%C3%BClleri_%281%29_-_cropped.jpg
Cem Adrian,45,30.11.1980,https://upload.wikimedia.org/wikipedia/commons/f/fd/Cem_Adrian.jpg
Simge Sağın,44,08.08.1981,https://upload.wikimedia.org/wikipedia/commons/f/f3/Simge_-_14._Radyo_Bo%C4%9Fazi%C3%A7i_%C3%96d%C3%BClleri_%281%29_-_cropped.jpg
Çağatay Ulusoy,35,23.09.1990,https://upload.wikimedia.org/wikipedia/commons/6/6a/Gaddar-act-image-46722eae-6123-4963-a3f9-a5d546308a34.jpg
Can Yaman,36,08.11.1989,https://upload.wikimedia.org/wikipedia/commons/4/41/Can_Yaman_Margherita_di_Savoia_2023-04-27_%281%29.jpg
Kıvanç Tatlıtuğ,42,27.10.1983,https://upload.wikimedia.org/wikipedia/commons/2/2a/Kivanc-viki%2C.jpg
Hazal Kaya,35,01.10.1990,https://upload.wikimedia.org/wikipedia/commons/8/87/Hazal_Kaya.jpg
Burak Özçivit,41,24.12.1984,https://upload.wikimedia.org/wikipedia/commons/4/4c/Burak_%C3%96z%C3%A7ivit_2023.jpg
Fahriye Evcen,39,04.06.1986,https://upload.wikimedia.org/wikipedia/commons/8/8b/Fahriye_Evcen_at_Cannes_2017_%283%29_-_cropped.png
Beren Saat,42,26.02.1984,https://upload.wikimedia.org/wikipedia/commons/5/5f/Beren_Saat_2024_02_%28cropped%29.png
Tuba Büyüküstün,43,05.07.1982,https://upload.wikimedia.org/wikipedia/commons/1/12/Tuba_B%C3%BCy%C3%BCk%C3%BCst%C3%BCn.jpg
Elçin Sangu,40,13.08.1985,https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/El%C3%A7in_Sangu_2017_October_%286%29.jpg/1280px-El%C3%A7in_Sangu_2017_October_%286%29.jpg
Hadise,40,21.10.1985,https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Hadise_2023.jpg/1920px-Hadise_2023.jpg
Murat Boz,46,07.03.1980,https://upload.wikimedia.org/wikipedia/en/5/55/Murat_Boz%2C_October_2012.jpg
Hande Yener,53,12.01.1973,https://upload.wikimedia.org/wikipedia/commons/5/51/Hande_Yener_Harbiye_Konseri_4_%28cropped%29.jpg
Kenan Doğulu,51,31.05.1974,https://upload.wikimedia.org/wikipedia/commons/b/bc/Kenan_Dogulu_1060880_Nevit.jpg
Edis,35,28.11.1990,https://upload.wikimedia.org/wikipedia/commons/b/b1/Edis_-_15._Radyo_Bo%C4%9Fazi%C3%A7i_%C3%96d%C3%BClleri_%281%29_-_cropped.jpg
İrem Derici,39,21.03.1987,https://upload.wikimedia.org/wikipedia/commons/3/34/%C4%B0rem_Derici.jpg
Derya Uluğ,40,21.02.1986,https://upload.wikimedia.org/wikipedia/commons/6/67/Derya_Ulu%C4%9F_%28Mar_2024%29_%28cropped%29.png
Oğuzhan Koç,41,13.05.1985,https://upload.wikimedia.org/wikipedia/commons/3/30/O%C4%9Fuzhan_Ko%C3%A7_%28cropped%29.jpg
Reynmen,30,06.12.1995,https://upload.wikimedia.org/wikipedia/commons/a/a5/Reynmen_M%C3%BCzikonair.jpg`;

const params = new URLSearchParams(location.search);
const roomId = (params.get("room") || localStorage.getItem("bulmaca_room") || "").trim();
const autoDemo = params.get("demo") === "1";
const kindFromUrl = String(params.get("kind") || "").trim().toLowerCase();
const fetchOpts = { credentials: "include" };

const $ = (id) => document.getElementById(id);

/** celebrity | football-club | football-nationality */
let labQuizKind = "celebrity";

const LAB_UI = {
  celebrity: {
    kicker: "Bulmaca777 · Ünlü yaş",
    h1: "Ünlü Yaş Lab",
    subSuffix: " · 30 ünlü listesi",
    quickHelp:
      "Giriş sonrası 30 ünlü yüklenir, <strong>Demo başlat</strong> ile oyun açılır.",
    mockLabel: "Yaş",
    mockPlaceholder: "32",
    mockHelp: "Mock modda test mesajı (yaş yazın).",
    currentTitle: "Aktif ünlü",
    demoDone: "Demo hazır: 30 ünlü, oyun yayında. Sahte sohbetle yaşı deneyin.",
  },
  "football-club": {
    kicker: "Bulmaca777 · Futbol takım",
    h1: "Futbol Takım Lab",
    subSuffix: " · 30 oyuncu paketi",
    quickHelp:
      "Giriş sonrası oyuncu paketi yüklenir, <strong>Demo başlat</strong> ile oyun açılır.",
    mockLabel: "Takım",
    mockPlaceholder: "Galatasaray",
    mockHelp: "Mock modda kulüp adı yazın (GS, Real Madrid…).",
    currentTitle: "Aktif oyuncu",
    demoDone:
      "Demo hazır: 30 oyuncu, oyun yayında. Sahte sohbetle takım adı deneyin.",
  },
  "football-nationality": {
    kicker: "Bulmaca777 · Futbol milliyet",
    h1: "Futbol Milliyet Lab",
    subSuffix: " · 30 oyuncu paketi",
    quickHelp:
      "Giriş sonrası oyuncu paketi yüklenir, <strong>Demo başlat</strong> ile oyun açılır.",
    mockLabel: "Ülke",
    mockPlaceholder: "Türkiye",
    mockHelp: "Mock modda ülke adı yazın (Türkiye, Brezilya…).",
    currentTitle: "Aktif oyuncu",
    demoDone:
      "Demo hazır: 30 oyuncu, oyun yayında. Sahte sohbetle ülke adı deneyin.",
  },
};

const MODE_LABELS = {
  puzzle: "Bulmaca",
  "photo-battle": "Photo Quiz",
  "team-race": "Takım yarışı",
  "football-club": "Futbol — takım ✓",
  "football-nationality": "Futbol — milliyet ✓",
};

function normalizeLabKind(value, footballQuiz) {
  const v = String(value || "").toLowerCase();
  if (v === "football-club" || v === "football_club") return "football-club";
  if (
    v === "football-nationality" ||
    v === "football_nationality"
  ) {
    return "football-nationality";
  }
  if (footballQuiz) return "football-club";
  return "celebrity";
}

function applyLabUi(kind) {
  const k = LAB_UI[kind] ? kind : "celebrity";
  labQuizKind = k;
  document.body.dataset.quizKind = k;
  const ui = LAB_UI[k];
  const isFb = k !== "celebrity";
  if ($("cqlKicker")) $("cqlKicker").textContent = ui.kicker;
  if ($("cqlH1")) $("cqlH1").textContent = ui.h1;
  document.title = `${ui.h1} — test`;
  if ($("roomCode")) $("roomCode").textContent = roomId || "—";
  if ($("cqlSubSuffix")) $("cqlSubSuffix").textContent = ui.subSuffix;
  if ($("cqlQuickHelpText")) $("cqlQuickHelpText").innerHTML = ui.quickHelp;
  $("sectionCelebrity")?.classList.toggle("hidden", isFb);
  $("sectionFootball")?.classList.toggle("hidden", !isFb);
  if ($("mockAnswerLabel")) $("mockAnswerLabel").textContent = ui.mockLabel;
  if ($("mockText")) $("mockText").placeholder = ui.mockPlaceholder;
  if ($("mockHelp")) $("mockHelp").textContent = ui.mockHelp;
  if ($("currentCardTitle")) $("currentCardTitle").textContent = ui.currentTitle;
  if ($("footballListTitle")) {
    $("footballListTitle").textContent =
      k === "football-nationality" ? "Milliyet paketi" : "Takım paketi";
  }
  if ($("footballListHelp")) {
    $("footballListHelp").textContent =
      k === "football-nationality"
        ? "Sohbette ülke adı yazılır. «Paketi odaya yükle» ile 30 soru gelir."
        : "Sohbette kulüp adı yazılır. «Paketi odaya yükle» ile 30 soru gelir.";
  }
  const skipBtn = $("btnSkip");
  if (skipBtn) {
    skipBtn.disabled = isFb;
    skipBtn.title = isFb ? "Futbol modunda soru yalnızca doğru cevapla geçer" : "";
  }
}

function api(path, opts = {}) {
  return fetch(`/api/rooms/${encodeURIComponent(roomId)}${path}`, {
    ...fetchOpts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
}

function setStatus(el, msg, ok = true) {
  if (!el) return;
  el.textContent = msg;
  el.style.color = ok ? "#7adfff" : "#ff8a8a";
}

function parseCsvPreviewRows(text) {
  const rows = [];
  for (const line of String(text || "").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    let parts;
    if (trimmed.includes("\t")) {
      parts = trimmed.split("\t").map((s) => s.trim());
    } else {
      parts = trimmed.split(",").map((s) => s.trim());
      if (parts.length > 4) {
        parts = [parts[0], parts[1], parts[2], parts.slice(3).join(",").trim()];
      }
    }
    if (parts.length < 4) continue;
    const [name, age, birthDate, imageUrl] = parts;
    if (!name || !age || !imageUrl) continue;
    if (/^isim/i.test(name) && /yaş|yas/i.test(age)) continue;
    let url = imageUrl;
    if (url && !/^https?:\/\//i.test(url)) url = `https://${url}`;
    rows.push({ name, age, birthDate, imageUrl: url });
  }
  return rows;
}

function renderSamplePreview(rows) {
  const wrap = $("samplePreview");
  const badge = $("sampleCountBadge");
  const valid = rows.length;
  if (badge) {
    badge.textContent = valid ? `${valid} ünlü` : "0 ünlü";
    badge.classList.toggle("cql-badge--ok", valid >= 30);
    badge.classList.toggle("cql-badge--warn", valid > 0 && valid < 30);
  }
  if (!wrap) return;
  wrap.replaceChildren();
  if (!valid) {
    const p = document.createElement("p");
    p.className = "cql-preview-empty";
    p.textContent = "Geçerli satır yok — format: isim,yaş,doğum,foto_url";
    wrap.appendChild(p);
    return;
  }
  const table = document.createElement("table");
  table.className = "cql-sample-table";
  table.innerHTML =
    "<thead><tr><th>#</th><th></th><th>İsim</th><th>Yaş</th></tr></thead>";
  const tbody = document.createElement("tbody");
  rows.slice(0, 40).forEach((r, i) => {
    const tr = document.createElement("tr");
    const thumb = document.createElement("img");
    thumb.className = "cql-sample-thumb";
    thumb.src = r.imageUrl;
    thumb.alt = r.name;
    thumb.loading = "lazy";
    thumb.referrerPolicy = "no-referrer";
    thumb.onerror = () => {
      thumb.classList.add("cql-sample-thumb--err");
    };
    tr.innerHTML = `<td>${i + 1}</td><td class="cql-sample-thumb-cell"></td><td>${escapeHtml(r.name)}</td><td>${escapeHtml(String(r.age))}</td>`;
    tr.querySelector(".cql-sample-thumb-cell")?.appendChild(thumb);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  if (rows.length > 40) {
    const more = document.createElement("p");
    more.className = "cql-help";
    more.textContent = `+${rows.length - 40} kişi daha (tabloda ilk 40 gösteriliyor)`;
    wrap.appendChild(more);
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function applyCsvToEditor(csv, sourceLabel) {
  const ta = $("csvText");
  if (!ta) return 0;
  ta.value = csv;
  const rows = parseCsvPreviewRows(csv);
  renderSamplePreview(rows);
  setStatus(
    $("importStatus"),
    rows.length
      ? `✓ ${rows.length} ünlü hazır (${sourceLabel}). «Odaya yükle» veya «Demo başlat».`
      : `Liste boş — ${sourceLabel}`,
    rows.length > 0
  );
  return rows.length;
}

/** Örnek liste: önce anında gömülü, sonra API ile güncelle (asla hata mesajı yok). */
function loadSampleCsvInstant() {
  return applyCsvToEditor(BUILTIN_CELEBRITY_CSV, "gömülü 30 ünlü");
}

async function loadSampleCsvFromServer() {
  try {
    const res = await fetch("/api/celebrity-sample/preview", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      if (data.rows?.length) {
        const lines = ["isim,yaş,doğum_tarihi,foto_link"];
        for (const r of data.rows) {
          lines.push(`${r.name},${r.age},${r.birthDate || ""},${r.imageUrl}`);
        }
        return applyCsvToEditor(lines.join("\n"), "sunucu listesi");
      }
    }
  } catch {
    /* gömülü yeterli */
  }
  try {
    const res = await fetch("/api/celebrity-sample.csv", { cache: "no-store" });
    if (res.ok) {
      const csv = await res.text();
      if (csv.trim()) return applyCsvToEditor(csv.trim(), "sunucu CSV");
    }
  } catch {
    /* gömülü yeterli */
  }
  return loadSampleCsvInstant();
}

async function loadSampleCsv() {
  const n = loadSampleCsvInstant();
  void loadSampleCsvFromServer();
  return n > 0;
}

function buildCelebrityChatGptPrompt() {
  return `Sen bir YouTube canlı yayın asistanısın. Türkiye'deki ünlüler için yaş tahmin oyunu listesi üret.

HEDEF: Tam 30 satır. Her satır TEK satır CSV (virgülle), başlık satırı YOK.

FORMAT:
isim,yaş,doğum_tarihi,foto_link

KURALLAR:
1. Gerçek ünlü (oyuncu, şarkıcı, sporcu)
2. yaş = 2025 tam sayı
3. doğum_tarihi = GG.AA.YYYY
4. foto_link = çalışan https Wikipedia/Wikimedia URL
5. Çıktı YALNIZCA 30 satır CSV — açıklama yok

ÖRNEK:
Hande Erçel,32,24.11.1993,https://upload.wikimedia.org/wikipedia/commons/3/34/Hande_Er%C3%A7el.jpg

Şimdi 30 satır üret.`;
}

async function copyCelebrityGptPrompt() {
  const text = buildCelebrityChatGptPrompt();
  try {
    await navigator.clipboard.writeText(text);
    setStatus($("importStatus"), "ChatGPT şablonu panoya kopyalandı — ChatGPT'ye yapıştırın, CSV'yi buraya alın.");
    return true;
  } catch {
    setStatus($("importStatus"), "Kopyalanamadı — metni CSV kutusunun üstündeki şablondan kopyalayın.", false);
    return false;
  }
}

function renderLeaderboard(feed = []) {
  const list = $("leaderboard");
  if (!list) return;
  list.replaceChildren();
  if (!feed.length) {
    const li = document.createElement("li");
    li.className = "cql-leaderboard-empty";
    li.textContent = "Henüz doğru cevap yok";
    list.appendChild(li);
    return;
  }
  feed.slice(0, 7).forEach((row, i) => {
    const li = document.createElement("li");
    const rank = document.createElement("span");
    rank.className = "cql-lb-rank";
    rank.textContent = String(row.rank ?? i + 1);
    const img = document.createElement("img");
    if (row.avatarUrl) {
      img.src = row.avatarUrl;
      img.alt = "";
      img.referrerPolicy = "no-referrer";
    } else {
      img.style.visibility = "hidden";
    }
    const name = document.createElement("span");
    name.className = "cql-lb-name";
    name.textContent = row.displayName || "—";
    const pts = document.createElement("span");
    pts.className = "cql-pts";
    pts.textContent = `${Math.round(Number(row.points) || 0)} p`;
    li.append(rank, img, name, pts);
    list.appendChild(li);
  });
}

function updateCurrentQuestionCard(snap) {
  const card = $("currentQuestionCard");
  if (!card) return;
  const q = snap?.question;
  if (!q || snap.state !== "active") {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  const img = $("currentPhoto");
  const nameEl = $("currentName");
  const ageEl = $("currentAgeHint");
  if (img) {
    img.src = q.imageUrl || "";
    img.alt = q.question || "";
    img.onerror = () => {
      img.style.display = "none";
    };
    img.style.display = q.imageUrl ? "block" : "none";
  }
  const displayName =
    q.meta?.name || String(q.question || "").replace(/\s*kaç\s+yaşında\??\s*$/i, "").trim();
  if (nameEl) nameEl.textContent = displayName || "—";
  const fk = q.meta?.gameKind;
  if (ageEl) {
    if (fk === "football-club") {
      const club = q.meta?.club || q.answers?.[0] || "—";
      ageEl.textContent = `Test için sohbete yazın: ${club} (veya GS, Real Madrid…)`;
    } else if (fk === "football-nationality") {
      const country = q.meta?.country || q.answers?.[0] || "—";
      ageEl.textContent = `Test için sohbete yazın: ${country}`;
    } else {
      const age = q.meta?.age ?? q.answers?.[0];
      ageEl.textContent = age
        ? `Test için sohbete yazın: ${age} veya «${age} yaş»`
        : "Sohbette yaşı yazın";
    }
  }
}

function updateGameUi(snap) {
  if (!snap) return;
  const labels = {
    idle: "Hazır",
    active: "Yayında",
    winner: "Doğru!",
    ended: "Bitti",
  };
  $("statPhase").textContent = labels[snap.state] || snap.state;
  const total = snap.totalQuestions || 0;
  const idx = snap.state === "idle" ? 0 : (snap.currentIndex ?? 0) + 1;
  $("statOrder").textContent = total ? `${idx} / ${total}` : "—";
  $("statTotal").textContent = String(total);
  renderLeaderboard(snap.feed || []);
  updateCurrentQuestionCard(snap);

  const hint = $("previewHint");
  const isFb = labQuizKind !== "celebrity";
  if (hint) {
    if (snap.state === "active") {
      hint.textContent = isFb
        ? "Sağda oyuncu fotoğrafı ve soru görünmeli. Görünmüyorsa «Yenile»."
        : "Sağda ünlü fotoğrafı görünmeli. Görünmüyorsa «Yenile».";
    } else if (snap.state === "idle" && total > 0) {
      hint.textContent = isFb
        ? `${total} soru yüklü — «Başlat» veya «Demo başlat».`
        : `${total} ünlü yüklü — «Başlat» veya «Demo başlat».`;
    } else if (!total) {
      hint.textContent = isFb
        ? "Önce futbol paketini odaya yükleyin."
        : "Önce ünlü listesini odaya yükleyin.";
    } else {
      hint.textContent = "Sağdaki liste = doğru cevap verenler (avatar + puan).";
    }
  }
}

let overlayBust = 0;

function celebrityOverlayUrl() {
  const q = new URLSearchParams({ room: roomId, motion: "1", t: String(Date.now()) });
  return `${location.origin}/celebrity-overlay?${q}`;
}

function wireOverlay() {
  overlayBust += 1;
  $("overlayFrame").src = celebrityOverlayUrl();
}

function initNav() {
  $("roomCode").textContent = roomId || "(oda yok)";
  if (roomId) {
    $("linkAdmin").href = `/admin/?room=${encodeURIComponent(roomId)}`;
    $("linkLogin").href = `/login/?next=${encodeURIComponent(location.pathname + location.search)}`;
    $("linkOverlay").href = celebrityOverlayUrl();
  }
}

async function ensureGameMode(mode) {
  const target =
    mode === "football-nationality" ? "football-nationality" : mode === "football-club" ? "football-club" : "puzzle";
  const res = await api("/config", {
    method: "PATCH",
    body: JSON.stringify({ gameMode: target }),
  });
  if (res.ok) applyLabUi(target === "puzzle" ? "celebrity" : target);
  return res.ok;
}

function renderFootballPreviewRows(rows) {
  const wrap = $("footballPreview");
  const badge = $("footballPackBadge");
  if (badge) {
    badge.textContent = rows.length ? `${rows.length} oyuncu` : "—";
    badge.classList.toggle("cql-badge--ok", rows.length >= 30);
  }
  if (!wrap) return;
  wrap.replaceChildren();
  if (!rows.length) {
    const p = document.createElement("p");
    p.className = "cql-preview-empty";
    p.textContent = "Paket henüz yüklenmedi.";
    wrap.appendChild(p);
    return;
  }
  const table = document.createElement("table");
  table.className = "cql-sample-table";
  const col =
    labQuizKind === "football-nationality" ? "Ülke" : "Takım";
  table.innerHTML = `<thead><tr><th>#</th><th></th><th>Oyuncu</th><th>${col}</th></tr></thead>`;
  const tbody = document.createElement("tbody");
  rows.slice(0, 40).forEach((r, i) => {
    const tr = document.createElement("tr");
    const thumb = document.createElement("img");
    thumb.className = "cql-sample-thumb";
    thumb.src = r.imageUrl || "";
    thumb.alt = r.name;
    thumb.loading = "lazy";
    thumb.referrerPolicy = "no-referrer";
    tr.innerHTML = `<td>${i + 1}</td><td class="cql-sample-thumb-cell"></td><td>${escapeHtml(r.name)}</td><td>${escapeHtml(r.answer)}</td>`;
    tr.querySelector(".cql-sample-thumb-cell")?.appendChild(thumb);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
}

async function loadFootballPackLab() {
  const kind =
    labQuizKind === "football-nationality" ? "nationality" : "club";
  await ensureGameMode(labQuizKind);
  setStatus($("importStatus"), "Futbol paketi yükleniyor…");
  const res = await api("/football/load-pack", {
    method: "POST",
    body: JSON.stringify({ kind }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) {
      setStatus(
        $("importStatus"),
        "Giriş gerekli — Admin ile giriş yapın.",
        false
      );
    } else {
      setStatus($("importStatus"), data.error || "Paket yüklenemedi", false);
    }
    return null;
  }
  const n = data.imported ?? data.count ?? 0;
  setStatus($("importStatus"), `${n} futbol sorusu yüklendi. Şimdi Başlat.`);
  if (data.game) updateGameUi(data.game);
  wireOverlay();
  await refreshFootballQuestionPreview();
  await refreshStatus();
  return data;
}

async function refreshFootballQuestionPreview() {
  const res = await api("/questions");
  if (!res.ok) return;
  const data = await res.json();
  const list = Array.isArray(data?.questions) ? data.questions : data;
  const rows = (Array.isArray(list) ? list : [])
    .filter((q) => /football-/.test(String(q?.meta?.gameKind || "")))
    .map((q) => ({
      name: q.meta?.name || q.meta?.player || "—",
      answer:
        labQuizKind === "football-nationality"
          ? q.meta?.country || q.answers?.[0]
          : q.meta?.club || q.answers?.[0],
      imageUrl: q.imageUrl,
    }));
  renderFootballPreviewRows(rows);
}

async function refreshChatInfo() {
  try {
    const res = await fetch(`${location.origin}/api/app/chat-info`, { cache: "no-store" });
    if (!res.ok) return;
    const info = await res.json();
    const help = $("chatModeHelp");
    if (help) {
      help.textContent = info.readMethodLabel || "";
    }
    const yt = $("ytStatus");
    if (yt) {
      yt.textContent = `Doğru bilenler listesi: en fazla ${info.puzzleFeedMax} kişi (puan sırası). ${info.botPostNote || ""}`;
      yt.style.color = "#9a94b8";
    }
  } catch {
    /* yoksay */
  }
}

async function refreshStatus() {
  const res = await fetch(
    `${location.origin}/api/rooms/${encodeURIComponent(roomId)}/status`,
    fetchOpts
  );
  if (!res.ok) return null;
  const d = await res.json();
  const mode = d.config?.gameMode || "puzzle";
  const resolvedKind = normalizeLabKind(
    kindFromUrl || mode,
    Boolean(d.footballQuiz)
  );
  applyLabUi(resolvedKind);
  const modeEl = $("statMode");
  if (modeEl) {
    const okMode =
      resolvedKind === "celebrity"
        ? mode === "puzzle" || d.celebrityQuiz
        : mode === resolvedKind;
    modeEl.textContent = MODE_LABELS[mode] || mode;
    modeEl.classList.toggle("cql-warn", !okMode);
  }
  const yt = $("ytStatus");
  if (yt && d.youtube) {
    const conn = d.youtube.connected ? "YouTube bağlı ✓" : "YouTube bağlı değil — admin panelden bağlayın";
    const poll = d.youtube.pollingMode === "live" ? " · dinleme: CANLI" : " · dinleme: beklemede (Başlat sonrası canlı)";
    yt.textContent = `${conn}${poll}. Listede ${d.puzzleFeedCount ?? 0}/${d.puzzleFeedMax ?? 7} kişi.`;
    yt.style.color = d.youtube.connected ? "#3dd68c" : "#ffb86c";
  }
  if (d.game) updateGameUi(d.game);
  if (resolvedKind !== "celebrity") {
    void refreshFootballQuestionPreview();
  }
  return d;
}

function initSocket() {
  if (!roomId || !window.io) return null;
  const socket = io({ path: "/socket.io", query: { room: roomId } });
  socket.on("game:state", (s) => {
    updateGameUi(s);
  });
  socket.on("config", () => {
    void refreshStatus();
    wireOverlay();
  });
  socket.on("connect", () => refreshStatus());
  return socket;
}

async function importCsvFromTextarea() {
  const csv = $("csvText").value.trim();
  if (!csv) {
    setStatus($("importStatus"), "CSV yapıştırın veya örnek yükleyin", false);
    return null;
  }
  await ensureGameMode("celebrity");
  const body = JSON.stringify({
    csv,
    hint: $("csvHint").value.trim() || "Ünlülerin Yaşını Tahmin Et",
    mode: "replace",
  });
  let res = await api("/questions/import-celebrities", { method: "POST", body });
  if (res.status === 404) {
    res = await api("/import-celebrities", { method: "POST", body });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) {
      setStatus(
        $("importStatus"),
        "Giriş gerekli — «Admin giriş» ile panele girin, sonra bu sayfaya dönün.",
        false
      );
    } else {
      setStatus($("importStatus"), data.error || "Yüklenemedi", false);
    }
    return null;
  }
  setStatus(
    $("importStatus"),
    `${data.imported ?? data.count} ünlü yüklendi (toplam ${data.count}). Şimdi Başlat.`
  );
  if (data.game) updateGameUi(data.game);
  wireOverlay();
  await refreshStatus();
  return data;
}

async function startGame() {
  const res = await api("/game/start", { method: "POST", body: "{}" });
  const data = await res.json().catch(() => ({}));
  if (res.ok) {
    updateGameUi(data);
    wireOverlay();
    setStatus($("mockStatus"), "Oyun başladı — sağdaki önizlemeye bakın.");
    return data;
  }
  setStatus($("mockStatus"), data.error || "Başlatılamadı (giriş / soru listesi?)", false);
  return null;
}

async function runDemo() {
  $("btnQuickDemo").disabled = true;
  setStatus($("importStatus"), "Demo çalışıyor…");
  if (labQuizKind !== "celebrity") {
    const imported = await loadFootballPackLab();
    if (!imported) {
      $("btnQuickDemo").disabled = false;
      return;
    }
    await startGame();
    $("btnQuickDemo").disabled = false;
    setStatus($("importStatus"), LAB_UI[labQuizKind].demoDone);
    return;
  }
  loadSampleCsvInstant();
  const imported = await importCsvFromTextarea();
  if (!imported) {
    $("btnQuickDemo").disabled = false;
    return;
  }
  await startGame();
  $("btnQuickDemo").disabled = false;
  setStatus($("importStatus"), LAB_UI.celebrity.demoDone);
}

async function main() {
  if (!roomId) {
    setStatus($("importStatus"), "URL'ye ?room=ODA_ID ekleyin", false);
    return;
  }
  localStorage.setItem("bulmaca_room", roomId);
  const initialKind = normalizeLabKind(kindFromUrl, false);
  applyLabUi(initialKind);
  initNav();
  const loginInline = $("linkLoginInline");
  if (loginInline) {
    loginInline.href = `/login/?next=${encodeURIComponent(location.pathname + location.search)}`;
  }
  wireOverlay();
  initSocket();
  loadSampleCsvInstant();
  void loadSampleCsvFromServer();
  await refreshChatInfo();
  const status = await refreshStatus();
  const ytLink = $("linkAdminYt");
  if (ytLink && roomId) ytLink.href = `/admin/?room=${encodeURIComponent(roomId)}`;

  $("csvText")?.addEventListener("input", () => {
    renderSamplePreview(parseCsvPreviewRows($("csvText").value));
    const n = parseCsvPreviewRows($("csvText").value).length;
    const badge = $("sampleCountBadge");
    if (badge) badge.textContent = n ? `${n} ünlü` : "—";
  });

  $("btnLoadSample").addEventListener("click", () => {
    loadSampleCsvInstant();
    void loadSampleCsvFromServer();
  });
  $("btnCopyGpt")?.addEventListener("click", () => copyCelebrityGptPrompt());
  $("btnClearCsv")?.addEventListener("click", () => {
    $("csvText").value = "";
    renderSamplePreview([]);
    setStatus($("importStatus"), "Liste temizlendi.");
  });
  $("btnReloadPreview")?.addEventListener("click", () => wireOverlay());
  $("btnImportCsv").addEventListener("click", () => importCsvFromTextarea());
  $("btnLoadFootballPackLab")?.addEventListener("click", () => {
    loadFootballPackLab().catch(() => {});
  });
  $("btnQuickDemo").addEventListener("click", () => runDemo());
  $("btnStart").addEventListener("click", () => startGame());
  $("btnStop").addEventListener("click", async () => {
    const res = await api("/game/stop", { method: "POST", body: "{}" });
    if (res.ok) updateGameUi(await res.json());
  });
  $("btnSkip").addEventListener("click", async () => {
    const res = await api("/game/skip", { method: "POST", body: "{}" });
    if (res.ok) updateGameUi(await res.json());
  });
  $("btnReset").addEventListener("click", async () => {
    if (!confirm("Puanlar ve sıra sıfırlansın mı?")) return;
    const res = await api("/game/reset", { method: "POST", body: "{}" });
    if (res.ok) updateGameUi(await res.json());
  });

  $("btnMockSend").addEventListener("click", async () => {
    const author = $("mockAuthor").value.trim() || "@test";
    const text = $("mockText").value.trim();
    if (!text) return;
    const res = await api("/chat/test", {
      method: "POST",
      body: JSON.stringify({ author, text }),
    });
    const data = await res.json().catch(() => ({}));
    $("mockText").value = "";
    if (res.ok) {
      setStatus($("mockStatus"), data.note || "Gönderildi");
      if (data.result?.type === "correct") await refreshStatus();
    } else {
      setStatus($("mockStatus"), data.error || "Hata (giriş gerekli olabilir)", false);
    }
  });

  if (autoDemo) {
    void runDemo();
  } else if (status?.game?.totalQuestions >= 30 && status.game.state === "idle") {
    const label = labQuizKind === "celebrity" ? "ünlü" : "soru";
    setStatus(
      $("importStatus"),
      `${status.game.totalQuestions} ${label} hazır — «Demo başlat» veya «Başlat» deyin.`
    );
  }
  if (
    kindFromUrl &&
    (kindFromUrl === "football-club" || kindFromUrl === "football-nationality") &&
    autoDemo
  ) {
    void runDemo();
  }
}

main();
})();
