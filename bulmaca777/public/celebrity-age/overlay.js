(function () {
  "use strict";

  const params = new URLSearchParams(location.search);
  const roomId = (params.get("room") || "").trim();
  const origin = location.origin && location.origin !== "null" ? location.origin : "http://127.0.0.1:3847";

  const stage = document.getElementById("caStage");
  const $ = (id) => document.getElementById(id);

  const panels = {
    idle: $("caIdle"),
    active: $("caActive"),
    winner: $("caWinner"),
    ended: $("caEnded"),
  };

  const ENGAGEMENT_PROMOS = [
    "ABONE VE BEĞEN — FAZLADAN PUAN KAZANIRSIN!",
    "BEĞEN + ABONE OL — EKSTRA PUAN!",
    "ABONE OL, DAHA ÇOK PUAN TOPLA!",
    "YORUM AT, PUANINI YÜKSELT!",
    "CANLI BEĞENİ = EKSTRA PUAN!",
  ];

  const PRIZE_PROMOS = [
    "EN YÜKSEK PUANA ÖDÜL VAR!",
    "LİSTENİN ZİRVESİ ÖDÜLÜ ALIR!",
    "PUAN TOPLA — ÖDÜL SENİN OLSUN!",
    "EN ÇOK PUAN = ÖDÜL!",
    "ZİRVEDE KİM VAR? ÖDÜL ONUN!",
  ];

  const PR_ROTATION = [
    ...ENGAGEMENT_PROMOS,
    "HADİ BULABİLİRSİN!",
    "BİLMEYE YAKLAŞTIN — TEKRAR DENE!",
    "ÇOK YAKINSIN — BİR RAKAM DAHA!",
    "SOHBETE YAŞ YAZ — HADİ!",
    "KİM BİLECEK? SEN BİLECEKSİN!",
    "HADİ CEVABI BİLEBİLİRSİN!",
    ...PRIZE_PROMOS,
  ];

  const IDLE_PROMOS = [
    "HADİ CEVABI BİLEBİLİRSİN!",
    "SOHBETE YAŞ YAZ!",
    "İLK DOĞRU BİLEN KAZANIR!",
    "TEK RAKAM YETER — ÖRN. 32",
    "KİM BİLECEK?",
    ...ENGAGEMENT_PROMOS,
    ...PRIZE_PROMOS,
  ];

  let lastState = null;
  let idlePromoIndex = 0;
  /** celebrity | football-club | football-nationality */
  let roomQuizKind = "celebrity";

  const QUIZ_BRAND = {
    celebrity: {
      titleHtml: "ÜNLÜLERİN<br />YAŞINI TAHMİN ET",
      docTitle: "Ünlü yaş — OBS",
      prompt: "Sohbette kaç yaşında olduğunu yazın!",
      idleTagline: "Panelden <strong>Başlat</strong> deyince ilk ünlü ekrana gelir",
      idleStep1: "Sohbete sadece <strong>yaş</strong> yazın",
      idleExample: "32",
      endedSub: "Tüm ünlüler tamamlandı",
      prAge: true,
    },
    "football-club": {
      titleHtml: "FUTBOLCU<br />HANGİ TAKIMDA?",
      docTitle: "Futbol takım — OBS",
      prompt: "Sohbette kulüp adını yazın!",
      idleTagline: "Panelden <strong>Başlat</strong> deyince ilk oyuncu gelir",
      idleStep1: "Sohbete <strong>takım</strong> yazın (GS, Real Madrid…)",
      idleExample: "Galatasaray",
      endedSub: "Tüm oyuncular tamamlandı",
      prAge: false,
    },
    "football-nationality": {
      titleHtml: "HANGİ ÜLKENİN<br />FUTBOLCUSU?",
      docTitle: "Futbol milliyet — OBS",
      prompt: "Sohbette ülke adını yazın!",
      idleTagline: "Panelden <strong>Başlat</strong> deyince ilk oyuncu gelir",
      idleStep1: "Sohbete <strong>ülke</strong> yazın (Türkiye, Brezilya…)",
      idleExample: "Türkiye",
      endedSub: "Tüm oyuncular tamamlandı",
      prAge: false,
    },
  };

  function resolveQuizKind(state, configMode) {
    const fk = state?.question?.meta?.gameKind;
    if (fk === "football-club" || fk === "football-nationality") return fk;
    const m = String(configMode || "").toLowerCase();
    if (m === "football-club" || m === "football-nationality") return m;
    return "celebrity";
  }

  function applyQuizBranding(kind) {
    const k = QUIZ_BRAND[kind] ? kind : "celebrity";
    roomQuizKind = k;
    const b = QUIZ_BRAND[k];
    const title = $("caTitle");
    if (title) title.innerHTML = b.titleHtml;
    document.title = b.docTitle;
    const prompt = $("caPrompt");
    if (prompt) prompt.textContent = b.prompt;
    const tag = $("caIdleTagline");
    if (tag) tag.innerHTML = b.idleTagline;
    const s1 = $("caIdleStep1");
    if (s1) s1.innerHTML = b.idleStep1;
    const ex = $("caIdleExampleVal");
    if (ex) ex.textContent = b.idleExample;
  }
  /** OBS skor listesi — en fazla 5 satır (sunucu daha fazla puan tutabilir) */
  const CA_OVERLAY_FEED_MAX = 5;
  let feedDisplayMax = CA_OVERLAY_FEED_MAX;
  let lastFitW = 0;
  let lastFitH = 0;

  const DESIGN_W = 1080;
  const DESIGN_H = 1920;

  /** OBS tarayıcı kaynağı bazen ilk karede 0×0 verir → scale(0) = siyah ekran */
  function fitStage() {
    const w = Math.max(window.innerWidth || 0, 1);
    const h = Math.max(window.innerHeight || 0, 1);
    const native =
      Math.abs(w - DESIGN_W) <= 12 && Math.abs(h - DESIGN_H) <= 12;

    if (lastFitW > 0 && w === lastFitW && h === lastFitH) return;
    lastFitW = w;
    lastFitH = h;

    if (native) {
      document.documentElement.classList.add("ca-obs-native");
      document.documentElement.style.setProperty("--ca-view-scale", "1");
      if (stage) {
        stage.style.left = "0";
        stage.style.top = "0";
        stage.style.transform = "none";
      }
      return;
    }

    document.documentElement.classList.remove("ca-obs-native");
    let scale = Math.min(w / DESIGN_W, h / DESIGN_H);
    if (!Number.isFinite(scale) || scale < 0.05) scale = 1;
    document.documentElement.style.setProperty("--ca-view-scale", String(scale));
    if (stage) {
      stage.style.left = "50%";
      stage.style.top = "50%";
      stage.style.transform =
        "translate(-50%, -50%) scale(var(--ca-view-scale, 1))";
    }
  }

  function scheduleObsFit() {
    fitStage();
    for (const ms of [0, 50, 150, 400, 800, 1500]) {
      setTimeout(fitStage, ms);
    }
  }

  function showError(msg) {
    const el = $("caError");
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function hideError() {
    $("caError")?.classList.add("hidden");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function formatUser(name) {
    const n = String(name || "İzleyici").trim();
    return n.startsWith("@") ? n : `@${n}`;
  }

  function initial(name) {
    return (String(name || "?").trim()[0] || "?").toLocaleUpperCase("tr-TR");
  }

  function progressText(state) {
    const total = Number(state.totalQuestions) || 0;
    if (!total) return "Soru yok";
    if (state.state === "idle") return `0 / ${total} · hazır`;
    if (state.state === "ended") return `${total} / ${total} · bitti`;
    const idx = Math.max(1, (state.currentIndex ?? 0) + 1);
    const pts = Math.round(Number(state.question?.points) || 0);
    return `${idx} / ${total}${pts > 0 ? ` · ${pts} p` : ""}`;
  }

  function prizeRibbonText(label) {
    const raw = String(label || "EN YÜKSEK PUANA ÖDÜL VAR!").trim();
    if (/^🏆/.test(raw)) return raw;
    const nice = raw.charAt(0) + raw.slice(1).toLocaleLowerCase("tr-TR");
    return `🏆 ${nice}`;
  }

  function applyPrizeCopy(state) {
    const label = state?.prizeLabel || PRIZE_PROMOS[0];
    const ribbon = $("caPrizeRibbon");
    if (ribbon) ribbon.textContent = prizeRibbonText(label);
    const scorersPrize = $("caScorersPrize");
    if (scorersPrize) scorersPrize.textContent = "En yüksek puan → ödül";
    const footer = $("caFooter");
    if (footer) footer.textContent = "Beğen · abone ol · en yüksek puana ödül!";
    const endedPrize = $("caEndedPrize");
    if (endedPrize) endedPrize.textContent = prizeRibbonText(label);
  }

  function renderFeed(feed, gameState) {
    const list = $("caFeed");
    const idleBox = $("caFeedIdle");
    if (!list) return;
    const rows = (feed || []).slice(0, feedDisplayMax);
    const isIdle = gameState === "idle";

    if (!rows.length) {
      if (isIdle && idleBox) {
        list.classList.add("hidden");
        list.replaceChildren();
        idleBox.classList.remove("hidden");
        return;
      }
      if (idleBox) idleBox.classList.add("hidden");
      list.classList.remove("hidden");
      list.replaceChildren();
      const li = document.createElement("li");
      li.className = "ca-feed-empty";
      li.textContent = "İlk doğru cevabı bekliyoruz…";
      list.appendChild(li);
      return;
    }

    if (idleBox) idleBox.classList.add("hidden");
    list.classList.remove("hidden");
    list.replaceChildren();
    rows.forEach((row, i) => {
      const li = document.createElement("li");
      const isLeader = (row.rank ?? i + 1) === 1;
      if (isLeader) li.classList.add("ca-feed-leader");
      const rank = document.createElement("span");
      rank.className = "ca-feed-rank";
      rank.textContent = String(row.rank ?? i + 1);
      let avatarHtml;
      if (row.avatarUrl) {
        avatarHtml = `<img class="ca-feed-avatar" src="${escapeHtml(row.avatarUrl)}" alt="" loading="lazy" referrerpolicy="no-referrer" />`;
      } else {
        avatarHtml = `<span class="ca-feed-avatar" style="display:flex;align-items:center;justify-content:center;font-size:18px">${escapeHtml(initial(row.displayName))}</span>`;
      }
      const ptsLabel = isLeader
        ? `🏆 ${Math.round(Number(row.points) || 0)} p`
        : `${Math.round(Number(row.points) || 0)} p`;
      li.innerHTML = `${rank.outerHTML}${avatarHtml}<span class="ca-feed-name">${escapeHtml(formatUser(row.displayName))}</span><span class="ca-feed-pts">${ptsLabel}</span>`;
      list.appendChild(li);
    });
  }

  function renderPromo(state) {
    const box = $("caPromo");
    const textEl = $("caPromoText");
    if (!textEl) return;

    const b = state?.broadcast;
    const celeb = state?.question?.meta?.name;
    let text = b?.text;
    let kind = b?.kind || "idle";

    if (!text) {
      const mod = idlePromoIndex % 8;
      if (mod === 0 || mod === 4) {
        text =
          ENGAGEMENT_PROMOS[Math.floor(idlePromoIndex / 8) % ENGAGEMENT_PROMOS.length];
        kind = "engage";
      } else if (mod === 1 || mod === 5) {
        const pool = state?.prizeLabel
          ? [state.prizeLabel, ...PRIZE_PROMOS.filter((p) => p !== state.prizeLabel)]
          : PRIZE_PROMOS;
        text = pool[Math.floor(idlePromoIndex / 8) % pool.length];
        kind = "prize";
      } else if (celeb && mod === 2) {
        const fk = state?.question?.meta?.gameKind;
        text =
          fk === "football-club"
            ? `${String(celeb).toUpperCase("tr-TR")} HANGİ TAKIMDA?`
            : fk === "football-nationality"
              ? `${String(celeb).toUpperCase("tr-TR")} HANGİ ÜLKE?`
              : `${String(celeb).toUpperCase("tr-TR")} KAÇ YAŞINDA? HADİ!`;
        kind = "idle";
      } else {
        text = PR_ROTATION[idlePromoIndex % PR_ROTATION.length];
        kind = "promo";
      }
    }

    textEl.textContent = text;
    const badge = box?.querySelector(".ca-promo-badge");
    if (badge) {
      badge.textContent =
        kind === "prize" || kind === "engage"
          ? "PR"
          : kind === "correct"
            ? "✓"
            : kind === "wrong" || kind === "far"
              ? "YANLIŞ"
              : kind === "close" || kind === "warm"
                ? "YAKIN"
                : "CANLI";
    }
    if (box) {
      box.dataset.kind = kind;
      box.classList.toggle(
        "ca-promo--pulse",
        kind === "close" ||
          kind === "warm" ||
          kind === "wrong" ||
          kind === "far" ||
          kind === "prize" ||
          kind === "engage" ||
          kind === "correct"
      );
      box.classList.toggle("hidden", state?.state === "ended");
    }
  }

  function renderHoldWinner(winner, hold) {
    const strip = $("caHoldWinner");
    if (!strip) return;
    const show = hold && winner && winner.displayName;
    strip.classList.toggle("hidden", !show);
    if (!show) return;

    $("caHoldName").textContent = formatUser(winner.displayName);
    $("caHoldMeta").textContent = winner.answer ? `Cevap: ${winner.answer}` : "";

    const av = $("caHoldAvatar");
    if (av) {
      if (winner.avatarUrl) {
        av.innerHTML = `<img src="${escapeHtml(winner.avatarUrl)}" alt="" referrerpolicy="no-referrer" />`;
      } else {
        av.textContent = initial(winner.displayName);
      }
    }
  }

  function renderActiveQuestion(state) {
    const q = state.question || {};
    const name =
      q.meta?.name ||
      q.meta?.player ||
      String(q.question || "")
        .replace(/\s*kaç\s+yaşında\??\s*$/i, "")
        .replace(/\s*hangi takımda oynuyor\??\s*$/i, "")
        .replace(/\s*hangi ülkenin futbolcusudur\??\s*$/i, "")
        .trim() ||
      "—";
    const photo = $("caPhoto");
    if (photo) {
      photo.src = q.imageUrl || "";
      photo.alt = name;
      photo.style.display = q.imageUrl ? "block" : "none";
    }
    $("caName").textContent = name;
    const pts = Math.round(Number(q.points) || 0);
    $("caPoints").textContent = pts > 0 ? `${pts} puan` : "";

    const hold = state.holdWinnerUntilNextCorrect !== false;
    renderHoldWinner(state.winner, hold);
  }

  function renderWinnerPanel(winner) {
    const w = winner || {};
    $("caWinnerName").textContent = formatUser(w.displayName);
    $("caWinnerMeta").textContent = w.answer ? `Cevap: ${w.answer}` : "";
    const av = $("caWinnerAvatar");
    if (av) {
      if (w.avatarUrl) {
        av.innerHTML = `<img src="${escapeHtml(w.avatarUrl)}" alt="" referrerpolicy="no-referrer" />`;
      } else {
        av.textContent = initial(w.displayName);
      }
    }
  }

  function showPanel(name) {
    Object.entries(panels).forEach(([key, el]) => {
      if (!el) return;
      el.classList.toggle("hidden", key !== name);
    });
    stage.dataset.state = name;
  }

  function renderEnded(state) {
    const leader = state.feed?.[0];
    const sub = $("caEndedSub");
    const b = QUIZ_BRAND[roomQuizKind] || QUIZ_BRAND.celebrity;
    if (sub) {
      sub.textContent = leader
        ? `${formatUser(leader.displayName)} lider · ${Math.round(Number(leader.points) || 0)} p`
        : b.endedSub;
    }
  }

  function render(state) {
    if (!state) return;
    const kind = resolveQuizKind(state, roomQuizKind);
    if (kind !== roomQuizKind) applyQuizBranding(kind);
    lastState = state;
    $("caProgress").textContent = progressText(state);
    applyPrizeCopy(state);
    renderFeed(state.feed, state.state);
    renderPromo(state);

    switch (state.state) {
      case "idle":
        showPanel("idle");
        break;
      case "active": {
        showPanel("active");
        renderActiveQuestion(state);
        break;
      }
      case "winner": {
        showPanel("winner");
        renderWinnerPanel(state.winner);
        break;
      }
      case "ended":
        showPanel("ended");
        renderEnded(state);
        break;
      default:
        showPanel("idle");
    }
  }

  if (!roomId) {
    showError("URL'de room= parametresi eksik.");
    return;
  }

  scheduleObsFit();
  window.addEventListener("resize", fitStage);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) fitStage();
  });

  setInterval(() => {
    if (!lastState || lastState.state === "ended") return;
    if (lastState.broadcast) return;
    if (lastState.state !== "active" && lastState.state !== "idle") return;
    idlePromoIndex += 1;
    renderPromo(lastState);
  }, 9000);

  if (typeof io !== "function") {
    showError("Socket.io yüklenemedi. Sunucuyu yeniden başlatın.");
    return;
  }

  const socket = io(origin, { path: "/socket.io", query: { room: roomId } });

  socket.on("game:state", (s) => {
    hideError();
    render(s);
  });

  socket.on("connect_error", () => {
    showError("Sunucuya bağlanılamadı. Yayın sunucusu çalışıyor mu?");
  });

  socket.on("error", (d) => {
    showError(d?.message || "Bağlantı hatası");
  });

  fetch(`${origin}/api/rooms/${encodeURIComponent(roomId)}/status`)
    .then((r) => {
      if (!r.ok) throw new Error("Oda bulunamadı");
      return r.json();
    })
    .then((d) => {
      hideError();
      feedDisplayMax = Math.min(
        CA_OVERLAY_FEED_MAX,
        Number(d.puzzleFeedMax) > 0 ? Number(d.puzzleFeedMax) : CA_OVERLAY_FEED_MAX
      );
      const title = $("caScorersTitle");
      if (title) {
        title.textContent = `DOĞRU BİLENLER (en fazla ${feedDisplayMax})`;
      }
      applyQuizBranding(
        resolveQuizKind(d.game, d.config?.gameMode || (d.footballQuiz ? "football-club" : "celebrity"))
      );
      if (d.game) render(d.game);
    })
    .catch((err) => showError(err.message || "Durum alınamadı"));
})();
