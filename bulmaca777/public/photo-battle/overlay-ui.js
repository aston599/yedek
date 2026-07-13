function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatTime(ms) {
  const sec = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function renderVotersList(ul, voters) {
  if (!ul) return;
  ul.replaceChildren();
  for (const v of voters || []) {
    const li = document.createElement("li");
    li.textContent = v.author || "İzleyici";
    ul.appendChild(li);
  }
}

export function renderPhotoBattleOverlay(state, els) {
  if (!els?.root || els.root.classList.contains("hidden")) return;
  const phase = state?.phase || "idle";

  els.root.dataset.pbPhase = phase;

  if (els.title) els.title.textContent = state?.title || "Hangisi daha iyi?";
  if (els.meta) {
    const active = state?.activeCount ?? 0;
    const match = state?.matchNumber ?? 0;
    els.meta.textContent =
      phase === "champion"
        ? "Kazanan belli oldu!"
        : `Tur ${match} · Kalan ${active} görsel · Sohbete 1 veya 2 yazın`;
  }

  const showDuel = phase === "voting" || phase === "result";
  els.duel?.classList.toggle("hidden", !showDuel);
  els.idle?.classList.toggle("hidden", phase !== "idle");
  els.champion?.classList.toggle("hidden", phase !== "champion");

  if (phase === "idle") {
    if (els.timer) els.timer.textContent = "";
    return;
  }

  if (phase === "champion" && state.champion) {
    if (els.championImg) {
      els.championImg.src = state.champion.imageUrl;
      els.championImg.alt = state.champion.label || "Kazanan";
    }
    if (els.championName) {
      els.championName.textContent = state.champion.label || "Kazanan";
    }
    return;
  }

  const bar = state.voteBar || {};
  const leftPct = Math.max(8, Math.min(92, bar.leftPct ?? 50));
  if (els.barFill) els.barFill.style.width = `${leftPct}%`;
  if (els.barLeftLabel) els.barLeftLabel.textContent = `1 · ${bar.leftVotes ?? 0}`;
  if (els.barRightLabel) els.barRightLabel.textContent = `${bar.rightVotes ?? 0} · 2`;

  if (els.timer) {
    const rem =
      phase === "voting"
        ? state.voteRemainingMs
        : phase === "result"
          ? state.resultRemainingMs
          : 0;
    els.timer.textContent = rem > 0 ? formatTime(rem) : "";
  }

  const left = state.left;
  const right = state.right;
  const winSide = state.resultWinnerSide;

  if (left && els.leftImg) {
    els.leftImg.src = left.imageUrl;
    els.leftImg.alt = left.label || "1";
  }
  if (right && els.rightImg) {
    els.rightImg.src = right.imageUrl;
    els.rightImg.alt = right.label || "2";
  }
  if (els.leftLabel) els.leftLabel.textContent = left?.label || "Seçenek 1";
  if (els.rightLabel) els.rightLabel.textContent = right?.label || "Seçenek 2";
  if (els.leftVotes) els.leftVotes.textContent = `${left?.votes ?? 0} oy`;
  if (els.rightVotes) els.rightVotes.textContent = `${right?.votes ?? 0} oy`;

  renderVotersList(els.leftVoters, left?.voters);
  renderVotersList(els.rightVoters, right?.voters);

  els.sideLeft?.classList.toggle("pb-side--winner-flash", phase === "result" && winSide === 1);
  els.sideRight?.classList.toggle("pb-side--winner-flash", phase === "result" && winSide === 2);
}

export function bindPhotoBattleOverlayDom(root) {
  return {
    root,
    title: root.querySelector("#pbTitle"),
    meta: root.querySelector("#pbMeta"),
    timer: root.querySelector("#pbTimer"),
    barFill: root.querySelector("#pbBarFillLeft"),
    barLeftLabel: root.querySelector("#pbBarLeftLbl"),
    barRightLabel: root.querySelector("#pbBarRightLbl"),
    duel: root.querySelector("#pbDuel"),
    idle: root.querySelector("#pbIdle"),
    champion: root.querySelector("#pbChampion"),
    championImg: root.querySelector("#pbChampionImg"),
    championName: root.querySelector("#pbChampionName"),
    leftImg: root.querySelector("#pbLeftImg"),
    rightImg: root.querySelector("#pbRightImg"),
    leftLabel: root.querySelector("#pbLeftLabel"),
    rightLabel: root.querySelector("#pbRightLabel"),
    leftVotes: root.querySelector("#pbLeftVotes"),
    rightVotes: root.querySelector("#pbRightVotes"),
    leftVoters: root.querySelector("#pbLeftVoters"),
    rightVoters: root.querySelector("#pbRightVoters"),
    sideLeft: root.querySelector("#pbSideLeft"),
    sideRight: root.querySelector("#pbSideRight"),
  };
}
