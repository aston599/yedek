/**
 * Tüm arena katmanlarını aynı anda göster — yerleşim / kalibrasyon önizlemesi.
 */

export const CAL_SLOT_LABELS = {
  phaseBanner: "Faz HUD (toplanma / kaos)",
  railLeft: "Sol şerit — tur kazananları",
  railRight: "Sağ şerit — en çok yazan",
  arenaBadge: "Arenada top sayısı",
  arenaCmdBand: "Komut / kural bandı",
  arenaPromoAlert: "Promo / uyarı bandı",
  elimFlash: "Elenme flaşı",
  winnerCard: "Alt bilgi kartı (tüm modlar)",
};

const DEMO_TEAMS = [
  { code: "gs", name: "Galatasaray" },
  { code: "fb", name: "Fenerbahçe" },
  { code: "bjk", name: "Beşiktaş" },
  { code: "ts", name: "Trabzonspor" },
];

function $(id) {
  return document.getElementById(id);
}

export function applyCalSlotLabels(root = document) {
  for (const [key, label] of Object.entries(CAL_SLOT_LABELS)) {
    const el = root.querySelector?.(`[data-cal-slot="${key}"]`) ?? document.querySelector(`[data-cal-slot="${key}"]`);
    if (el) el.setAttribute("data-cal-label", label);
  }
  root.querySelectorAll?.("[data-arena-info-hub], [data-arena-info-winner]")?.forEach((el) => {
    el.removeAttribute("data-cal-label");
  });
}

/**
 * @param {object} deps
 * @param {(code: string, size?: string, alt?: string) => string} deps.teamFlagImg
 * @param {(code: string) => string} deps.teamFlagUrl
 * @param {import('../team-race/arena-info-ticker.js').ArenaInfoTicker | null} [deps.arenaInfoTicker]
 * @param {(map: Record<string, string>) => void} [deps.setScenePreviewCtas]
 * @param {(root: Element, ctas: object) => void} [deps.applyArenaCtasToDom]
 * @param {(root: Element | null) => void} [deps.initArenaCmdBand]
 */
export function fillLayoutOverviewDemo(deps = {}) {
  const {
    teamFlagImg,
    teamFlagUrl,
    arenaInfoTicker = null,
    setScenePreviewCtas,
    applyArenaCtasToDom,
    initArenaCmdBand,
  } = deps;

  applyCalSlotLabels();
  initArenaCmdBand?.($("arenaCmdBand"));

  const banner = $("phaseBanner");
  if (banner) {
    banner.classList.remove("hidden");
    banner.classList.add("is-cal-preview", "is-chaos");
  }
  if ($("phaseBannerTitle")) $("phaseBannerTitle").textContent = "Kaos";
  if ($("phaseBannerTimer")) $("phaseBannerTimer").textContent = "Elenme açık";
  if ($("poolFill")) $("poolFill").style.width = "72%";
  if ($("hudSub")) {
    $("hudSub").textContent = "Önizleme — tüm bölümler açık (canlıda faz başına tek mod)";
  }

  const badge = $("arenaBadge");
  if (badge) {
    badge.textContent = "Arenada: 8";
    badge.classList.add("is-running");
  }

  const cmdBand = $("arenaCmdBand");
  if (cmdBand) {
    cmdBand.classList.remove("hidden");
    cmdBand.classList.add("is-cal-preview");
  }

  const promo = $("arenaPromoAlert");
  if (promo) {
    promo.classList.remove("hidden");
    promo.textContent = "Promo alanı — duyuru / kampanya metni";
    promo.classList.add("is-cal-preview");
  }

  const winners = $("arenaRoundWinners");
  if (winners && teamFlagImg && teamFlagUrl) {
    winners.innerHTML = DEMO_TEAMS.slice(0, 3)
      .map(
        (t, i) =>
          `<li><span class="play-win-round">TUR ${3 - i}</span>${teamFlagImg(teamFlagUrl(t.code), "sm", t.name)}<span>${t.name}</span></li>`
      )
      .join("");
  }

  const top5 = $("arenaTopViewers");
  if (top5 && teamFlagImg && teamFlagUrl) {
    top5.innerHTML = ["Ali", "Ayşe", "Can", "Deniz", "Ece"]
      .map(
        (name, i) =>
          `<li><span class="play-top-rank">${i + 1}</span>${teamFlagImg(teamFlagUrl(DEMO_TEAMS[i % 4].code), "xs", name)}<span class="play-top-name">${name}</span><strong class="play-top-count">${12 - i * 2}</strong></li>`
      )
      .join("");
  }

  const card = $("winnerCard");
  if (card) {
    card.classList.remove("hidden");
    card.classList.add("is-cal-preview", "is-visible", "tr-arena-info--overview");
    const hubPanel = card.querySelector("[data-arena-info-hub]");
    const winnerPanel = card.querySelector("[data-arena-info-winner]");
    hubPanel?.classList.remove("hidden");
    winnerPanel?.classList.remove("hidden");
    if ($("arenaInfoHeadline")) $("arenaInfoHeadline").textContent = "KATILMA ŞARTLARI";
    if ($("arenaInfoSub")) {
      $("arenaInfoSub").textContent = "Kısaltma veya tam ad yaz · her mesaj = bir top";
    }
    const joinList = card.querySelector("[data-arena-info-join-list]");
    if (joinList && teamFlagImg && teamFlagUrl) {
      joinList.innerHTML = [
        { author: "Ahmet", team: "Galatasaray", code: "gs" },
        { author: "Ece", team: "Fenerbahçe", code: "fb" },
        { author: "Can", team: "Beşiktaş", code: "bjk" },
      ]
        .map(
          (r, i) =>
            `<li class="tr-arena-hub__join-item${i === 0 ? " is-active" : ""}">${teamFlagImg(teamFlagUrl(r.code), "xs", r.team)}<span class="tr-arena-hub__join-text"><strong>${r.author}</strong> → ${r.team}</span></li>`
        )
        .join("");
    }
    if ($("winnerTitle")) $("winnerTitle").textContent = "TUR 1 KAZANANI";
    if ($("winnerName")) $("winnerName").textContent = "Galatasaray";
    if ($("winnerBadge")) $("winnerBadge").textContent = "Son kalan takım";
    if ($("winnerMeta")) $("winnerMeta").textContent = "12 top · Son kalan takım";
    const flag = $("winnerFlag");
    if (flag && teamFlagUrl) {
      flag.src = teamFlagUrl("gs");
      flag.parentElement?.classList.remove("hidden");
    }
  }

  arenaInfoTicker?.stop?.();

  const flash = $("elimFlash");
  if (flash) {
    flash.textContent = "Fenerbahçe elendi!";
    flash.classList.add("is-visible", "is-cal-preview");
  }

  document.querySelectorAll("[data-cta]").forEach((el) => {
    el.classList.add("is-live", "is-cal-preview");
    const who = el.querySelector(".yt-cta__who");
    if (who) who.textContent = "@izleyici";
  });

  setScenePreviewCtas?.({ like: "Ali", subscribe: "Ayşe", follow: "Can", comment: "Can" });
  const arenaEl = document.getElementById("arena");
  if (arenaEl && applyArenaCtasToDom) {
    applyArenaCtasToDom(arenaEl, {
      like: { label: "Beğen", active: true, lastUser: "Ali" },
      subscribe: { label: "Abone ol", active: true, lastUser: "Ayşe" },
      follow: { label: "Takip et", active: true, lastUser: "Can" },
    });
  }
}

export function clearLayoutOverviewDemo() {
  document.body.classList.remove("play-layout-overview", "play-scene-preview--all");
  $("arenaCmdBand")?.classList.add("hidden");
  $("arenaPromoAlert")?.classList.add("hidden");
  $("winnerCard")?.classList.remove("tr-arena-info--overview");
  const hub = document.querySelector("[data-arena-info-hub]");
  const win = document.querySelector("[data-arena-info-winner]");
  hub?.classList.remove("hidden");
  win?.classList.add("hidden");
}
