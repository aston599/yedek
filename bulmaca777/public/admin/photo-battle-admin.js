/**
 * Photo Quiz admin panel — görsel havuzu + tur ayarları
 */
export function initPhotoBattleAdmin({ api, getRoomId, escapeHtml }) {
  const $ = (id) => document.getElementById(id);

  let pool = [];
  let snapshot = null;

  function renderPool() {
    const grid = $("pbPoolGrid");
    const count = $("pbPoolCount");
    if (count) count.textContent = String(pool.length);
    if (!grid) return;
    if (!pool.length) {
      grid.innerHTML =
        '<p class="help">Henüz görsel yok. Aşağıdan dosya seçin veya sürükleyip bırakın (en az 2).</p>';
      return;
    }
    grid.innerHTML = pool
      .map(
        (p) => `
      <figure class="pb-pool-card" data-id="${escapeHtml(p.id)}">
        <img src="${escapeHtml(p.imageUrl)}" alt="" loading="lazy" />
        <figcaption>${escapeHtml(p.label || p.id)}</figcaption>
        <button type="button" class="btn btn--sm pb-pool-del" data-del="${escapeHtml(p.id)}">Sil</button>
      </figure>`
      )
      .join("");
    grid.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.del;
        await api(`/photo-battle/pool/${encodeURIComponent(id)}`, { method: "DELETE" });
        await refreshPool();
      });
    });
  }

  function renderStats() {
    const s = snapshot;
    $("pbPhase") && ($("pbPhase").textContent = s?.phase || "idle");
    $("pbMatch") && ($("pbMatch").textContent = String(s?.matchNumber ?? 0));
    $("pbVotesLeft") &&
      ($("pbVotesLeft").textContent = String(s?.left?.votes ?? 0));
    $("pbVotesRight") &&
      ($("pbVotesRight").textContent = String(s?.right?.votes ?? 0));
    const rem = s?.voteRemainingMs ?? 0;
    $("pbRemain") &&
      ($("pbRemain").textContent =
        rem > 0 ? `${Math.ceil(rem / 1000)} sn` : "—");
  }

  async function refreshPool() {
    const roomId = getRoomId();
    if (!roomId) return;
    const data = await api("/photo-battle/pool");
    pool = data.pool || [];
    snapshot = data.snapshot || snapshot;
    renderPool();
    renderStats();
  }

  async function saveSettings() {
    const roomId = getRoomId();
    if (!roomId) return;
    await api("/config", {
      method: "PATCH",
      body: JSON.stringify({
        photoBattleSettings: {
          title: $("pbTitle")?.value?.trim() || "Hangisi daha iyi?",
          voteDurationSec: Number($("pbVoteSec")?.value) || 120,
        },
      }),
    });
  }

  async function uploadFiles(fileList) {
    const files = [...fileList].filter((f) => f.type.startsWith("image/"));
    if (!files.length) return;
    const images = await Promise.all(
      files.map(
        (file) =>
          new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () =>
              resolve({
                name: file.name,
                dataBase64: reader.result,
                label: file.name.replace(/\.[^.]+$/, ""),
              });
            reader.onerror = reject;
            reader.readAsDataURL(file);
          })
      )
    );
    await api("/photo-battle/pool", {
      method: "POST",
      body: JSON.stringify({ images }),
    });
    await refreshPool();
  }

  $("pbSaveSettings")?.addEventListener("click", () => saveSettings().catch(alert));

  $("pbUploadInput")?.addEventListener("change", (e) => {
    uploadFiles(e.target.files || []).catch((err) => alert(err.message));
    e.target.value = "";
  });

  const drop = $("pbDropZone");
  if (drop) {
    drop.addEventListener("dragover", (e) => {
      e.preventDefault();
      drop.classList.add("is-drag");
    });
    drop.addEventListener("dragleave", () => drop.classList.remove("is-drag"));
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      drop.classList.remove("is-drag");
      uploadFiles(e.dataTransfer?.files || []).catch((err) => alert(err.message));
    });
  }

  $("pbClearPool")?.addEventListener("click", async () => {
    if (!confirm("Tüm görsel havuzu silinsin mi?")) return;
    await api("/photo-battle/pool", { method: "DELETE" });
    await refreshPool();
  });

  return {
    onRoomReady(config) {
      const s = config?.photoBattleSettings || {};
      if ($("pbTitle")) $("pbTitle").value = s.title || "Hangisi daha iyi?";
      if ($("pbVoteSec")) $("pbVoteSec").value = String(s.voteDurationSec ?? 120);
      return refreshPool();
    },
    onState(state) {
      snapshot = state;
      renderStats();
    },
    refreshPool,
  };
}
