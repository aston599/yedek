/**
 * Arena bildiri hub — katılma şartları, canlı katılım, kazanan / seçim.
 */
import { formatWinnerLines, teamFlagUrl } from "./team-ui.js";

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const JOIN_RULES = [
  {
    icon: "📋",
    headline: "KATILMA ŞARTLARI",
    sub: "Sohbete kısaltma veya tam ad yaz (gs, Galatasaray, fener…)",
  },
  { icon: "✍️", headline: "MESAJ = KATILIM", sub: "Her geçerli mesaj arenada bayrağınla bir top olur" },
  { icon: "👥", headline: "EN AZ 2 TAKIM", sub: "Yeterli katılım olunca kaos turu başlar" },
  { icon: "❤️", headline: "YAYINI DESTEKLE", sub: "Beğen · abone ol · takip et yazabilirsin" },
];

export const ARENA_INFO_SLIDES = {
  idle: [
    ...JOIN_RULES,
    {
      icon: "🎮",
      headline: "KATIL!",
      sub: "Yayın başlayınca sohbete takımının kısaltmasını veya tam adını yaz",
    },
    {
      icon: "⚽",
      headline: "TAKIMINI SEÇ",
      sub: "Galatasaray · gs · Fenerbahçe · fener · Beşiktaş · trabzon…",
    },
  ],
  gathering: [
    ...JOIN_RULES,
    {
      icon: "⚽",
      headline: "TAKIMINI DESTEKLE!",
      sub: "Sohbete kısaltma veya tam ad yaz — top havuzda birikir",
    },
    { icon: "⏳", headline: "TOPLANMA", sub: "Havuz dolunca kaos başlayacak" },
    { icon: "👥", headline: "ARKADAŞLARINI ÇAĞIR", sub: "Çok katılım = kaos daha erken" },
  ],
  chaos: [
    ...JOIN_RULES,
    { icon: "⚡", headline: "KAOS!", sub: "Alttaki çıkıştan düşen top elenir" },
    { icon: "🏆", headline: "SON KALAN KAZANIR", sub: "Takımına yazmaya devam et!" },
    { icon: "💥", headline: "ÇIKIŞ AÇIK", sub: "Dönen boşluktan düşen elenir" },
  ],
};

const ROTATE_MS = 4800;
const WINNER_MS = 13_000;
const ACTIVITY_MS = 4_200;
const JOIN_STEP_MS = 2600;

/** @param {object} row */
export function formatActivityLines(row) {
  const author = String(row?.author || row?.displayName || "").trim() || "İzleyici";
  const teamName = row?.teamName || row?.teamCode || "";
  if (row?.type === "spawn" && teamName) {
    const count = Number(row?.count) || 0;
    const pick =
      count > 1
        ? `${author}, ${count}. defa ${teamName}'ı seçti!`
        : `${author}, ${teamName}'ı seçti!`;
    return {
      kicker: "CANLI SEÇİM",
      name: teamName,
      badge: pick,
      meta: "",
      teamCode: row.teamCode,
      flagUrl: row.flagUrl,
    };
  }
  if (row?.type === "cta" && row.teamName) {
    return {
      kicker: "CTA",
      name: row.teamName,
      badge: `${author} → ${row.teamName}`,
      meta: "",
      teamCode: row.teamCode,
      flagUrl: row.flagUrl,
    };
  }
  return {
    kicker: "BİLDİRİ",
    name: teamName || author,
    badge: author,
    meta: "",
    teamCode: row?.teamCode,
    flagUrl: row?.flagUrl,
  };
}

export function createArenaInfoTicker(root) {
  if (!root) return null;
  return new ArenaInfoTicker(root);
}

export class ArenaInfoTicker {
  constructor(root) {
    this.root = root;
    this.hubPanel =
      root.querySelector("[data-arena-info-hub]") ||
      root.querySelector(".tr-arena-info__panel--hub");
    this.ctaPanel =
      root.querySelector("[data-arena-info-cta]") ||
      root.querySelector(".tr-arena-hub__promo") ||
      this.hubPanel;
    this.joinListEl = root.querySelector("[data-arena-info-join-list]");
    this.winnerPanel =
      root.querySelector("[data-arena-info-winner]") ||
      root.querySelector(".tr-arena-info__panel--winner");
    this.iconEl = root.querySelector(".tr-arena-info__icon");
    this.headlineEl = root.querySelector(".tr-arena-info__headline");
    this.subEl = root.querySelector(".tr-arena-info__sub");
    this.flagEl = root.querySelector(".tr-winner-card__flag img");
    this.titleEl = root.querySelector(".tr-winner-card__kicker");
    this.nameEl = root.querySelector(".tr-winner-card__name, .play-winner-name, .race-winner-name");
    this.badgeEl = root.querySelector(".tr-winner-card__badge");
    this.metaEl = root.querySelector(".tr-winner-card__meta, .play-winner-meta");

    this._rotateTimer = null;
    this._winnerTimer = null;
    this._activityTimer = null;
    this._joinTimer = null;
    this._slideIdx = 0;
    this._slides = ARENA_INFO_SLIDES.idle;
    this._joinRows = [];
    this._joinHighlight = 0;
    this._mode = "hub";
    this._contextKey = "";
    this._resumeCtx = null;
  }

  setVisible(on) {
    this.root.classList.toggle("hidden", !on);
    if (on) this.root.classList.add("is-visible", "tr-arena-info--on");
    else {
      this.root.classList.remove("is-visible", "tr-arena-info--on");
      this.stop();
    }
  }

  stop() {
    clearInterval(this._rotateTimer);
    clearInterval(this._joinTimer);
    clearTimeout(this._winnerTimer);
    clearTimeout(this._activityTimer);
    this._rotateTimer = null;
    this._joinTimer = null;
    this._winnerTimer = null;
    this._activityTimer = null;
    this._mode = "hub";
    this._resumeCtx = null;
  }

  _contextToSlides(ctx = {}) {
    if (ctx.phase === "running") {
      const rp = ctx.roundPhase === "chaos" || ctx.chaos ? "chaos" : "gathering";
      return ARENA_INFO_SLIDES[rp] || ARENA_INFO_SLIDES.gathering;
    }
    return ARENA_INFO_SLIDES.idle;
  }

  _showHubPanel() {
    this._mode = "hub";
    this.hubPanel?.classList.remove("hidden");
    this.winnerPanel?.classList.add("hidden");
    this.root.classList.remove(
      "tr-arena-info--winner",
      "tr-arena-info--activity",
      "tr-arena-info--cta"
    );
    this.root.classList.add("tr-arena-info--hub");
  }

  _showWinnerPanel(mode = "winner") {
    this._mode = mode;
    this.hubPanel?.classList.add("hidden");
    this.winnerPanel?.classList.remove("hidden");
    this.root.classList.remove("tr-arena-info--hub", "tr-arena-info--cta");
    this.root.classList.add(mode === "activity" ? "tr-arena-info--activity" : "tr-arena-info--winner");
  }

  _renderSlide(slide) {
    if (!slide) return;
    if (this.iconEl) this.iconEl.textContent = slide.icon || "";
    if (this.headlineEl) this.headlineEl.textContent = slide.headline || "";
    if (this.subEl) this.subEl.textContent = slide.sub || "";
    this.root.classList.remove("tr-arena-info--pulse");
    void this.root.offsetWidth;
    this.root.classList.add("tr-arena-info--pulse");
  }

  _tickRotate() {
    if (this._mode !== "hub" || !this._slides.length) return;
    const slide = this._slides[this._slideIdx % this._slides.length];
    this._slideIdx += 1;
    this._renderSlide(slide);
  }

  _startRotation() {
    clearInterval(this._rotateTimer);
    this._tickRotate();
    this._rotateTimer = setInterval(() => this._tickRotate(), ROTATE_MS);
  }

  _normalizeJoinRows(feed = {}) {
    const fromSpawns = (feed.recentSpawns || []).map((s) => ({
      id: s.id || `${s.at}-${s.displayName}`,
      author: s.displayName || s.author || "İzleyici",
      teamCode: s.teamCode,
      teamName: s.teamName || s.teamCode,
      flagUrl: s.flagUrl,
    }));
    if (fromSpawns.length) return fromSpawns.slice(0, 8);
    return (feed.activityFeed || [])
      .filter((r) => r?.type === "spawn")
      .slice(0, 8)
      .map((r) => ({
        id: r.id || `${r.at}-${r.author}`,
        author: r.author || "İzleyici",
        teamCode: r.teamCode,
        teamName: r.teamName || r.teamCode,
        flagUrl: r.flagUrl,
      }));
  }

  _renderJoinList() {
    if (!this.joinListEl) return;
    if (!this._joinRows.length) {
      this.joinListEl.innerHTML =
        '<li class="tr-arena-hub__join-item tr-arena-hub__join-item--empty">Henüz katılım yok — ilk sen ol!</li>';
      return;
    }
    this.joinListEl.innerHTML = this._joinRows
      .map((row, i) => {
        const active = i === this._joinHighlight ? " is-active" : "";
        const flag = row.teamCode
          ? `<img class="team-flag team-flag--xs" src="${esc(teamFlagUrl(row.teamCode, row.flagUrl))}" alt="" width="20" height="20" />`
          : "";
        return `<li class="tr-arena-hub__join-item${active}" data-join-idx="${i}">
          ${flag}
          <span class="tr-arena-hub__join-text"><strong>${esc(row.author)}</strong> → ${esc(row.teamName)}</span>
        </li>`;
      })
      .join("");
  }

  _startJoinCycle() {
    clearInterval(this._joinTimer);
    if (!this._joinRows.length) return;
    this._joinTimer = setInterval(() => {
      if (this._mode !== "hub") return;
      this._joinHighlight = (this._joinHighlight + 1) % this._joinRows.length;
      this._renderJoinList();
    }, JOIN_STEP_MS);
  }

  /**
   * @param {{ recentSpawns?: object[], activityFeed?: object[] }} feed
   */
  syncFeed(feed = {}) {
    const prevHead = this._joinRows[0]?.id;
    this._joinRows = this._normalizeJoinRows(feed);
    if (this._joinRows.length && this._joinRows[0].id !== prevHead) {
      this._joinHighlight = 0;
    } else if (this._joinHighlight >= this._joinRows.length) {
      this._joinHighlight = 0;
    }
    this._renderJoinList();
    if (this._mode === "hub") this._startJoinCycle();
  }

  /** Yeni katılım — listeyi başa al, kısa vurgula */
  pingNewJoin(row, ctx = null) {
    if (!row || this._mode === "winner") return;
    if (ctx) this._resumeCtx = ctx;
    const lines = formatActivityLines(row);
    const entry = {
      id: row.id || `ping-${Date.now()}`,
      author: row.author || row.displayName || lines.name,
      teamCode: lines.teamCode,
      teamName: lines.name || lines.teamCode,
      flagUrl: lines.flagUrl,
    };
    const rest = this._joinRows.filter((r) => r.id !== entry.id);
    this._joinRows = [entry, ...rest].slice(0, 8);
    this._joinHighlight = 0;
    if (this._mode === "hub") {
      this._renderJoinList();
      this.joinListEl?.classList.add("tr-arena-hub__stream-list--ping");
      setTimeout(() => this.joinListEl?.classList.remove("tr-arena-hub__stream-list--ping"), 500);
      return;
    }
    this.showActivity(row, ctx, ACTIVITY_MS);
  }

  /**
   * @param {{ phase?: string, roundPhase?: string, chaos?: boolean }} ctx
   */
  setContext(ctx = {}) {
    const key = `${ctx.phase}|${ctx.roundPhase}|${ctx.chaos}`;
    this._resumeCtx = ctx;
    if (this._mode === "winner" || this._mode === "activity") return;
    if (key === this._contextKey && this._mode === "hub" && this._rotateTimer) return;
    this._contextKey = key;

    this._slides = this._contextToSlides(ctx);
    this._slideIdx = 0;
    this._showHubPanel();
    this._startRotation();
    this._startJoinCycle();
  }

  showActivity(row, ctx = null, durationMs = ACTIVITY_MS) {
    if (!row || this._mode === "winner") return;
    if (ctx) this._resumeCtx = ctx;

    clearInterval(this._rotateTimer);
    clearInterval(this._joinTimer);
    clearTimeout(this._activityTimer);
    this._rotateTimer = null;
    this._joinTimer = null;

    const lines = formatActivityLines(row);
    if (this.flagEl) {
      if (lines.teamCode) {
        this.flagEl.src = teamFlagUrl(lines.teamCode, lines.flagUrl);
        this.flagEl.alt = lines.name || lines.teamCode;
        this.flagEl.parentElement?.classList.remove("hidden");
      } else {
        this.flagEl.removeAttribute("src");
        this.flagEl.parentElement?.classList.add("hidden");
      }
    }
    if (this.titleEl) this.titleEl.textContent = lines.kicker;
    if (this.nameEl) this.nameEl.textContent = lines.name;
    if (this.badgeEl) this.badgeEl.textContent = lines.badge;
    if (this.metaEl) this.metaEl.textContent = lines.meta;

    this._showWinnerPanel("activity");
    this.root.classList.remove("tr-arena-info--pulse");
    void this.root.offsetWidth;
    this.root.classList.add("tr-arena-info--pulse");

    this._activityTimer = setTimeout(() => {
      this._activityTimer = null;
      this._mode = "hub";
      this._contextKey = "";
      if (this._resumeCtx) this.setContext(this._resumeCtx);
      else this._showHubPanel();
    }, durationMs);
  }

  showWinner(winner, round = 0, durationMs = WINNER_MS) {
    if (!winner) return;
    clearInterval(this._rotateTimer);
    clearInterval(this._joinTimer);
    clearTimeout(this._winnerTimer);
    clearTimeout(this._activityTimer);
    this._rotateTimer = null;
    this._joinTimer = null;
    this._activityTimer = null;

    const lines = formatWinnerLines(winner, round);
    if (this.flagEl) {
      this.flagEl.parentElement?.classList.remove("hidden");
      this.flagEl.src = teamFlagUrl(winner.teamCode, winner.flagUrl);
      this.flagEl.alt = winner.teamName || winner.teamCode || "";
    }
    if (this.titleEl) this.titleEl.textContent = lines.title;
    if (this.nameEl) this.nameEl.textContent = lines.name;
    if (this.badgeEl) this.badgeEl.textContent = lines.badge;
    if (this.metaEl) this.metaEl.textContent = lines.meta;

    this._showWinnerPanel("winner");
    this.root.classList.remove("tr-arena-info--pulse");
    void this.root.offsetWidth;
    this.root.classList.add("tr-arena-info--pulse");

    this._winnerTimer = setTimeout(() => {
      this._winnerTimer = null;
      this._contextKey = "";
      this.setContext(this._resumeCtx || { phase: "idle" });
    }, durationMs);
  }
}
