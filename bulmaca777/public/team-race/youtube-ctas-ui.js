/** Arena / overlay — YouTube CTA rozetleri (sunucu snapshot ile senkron) */

export const CTA_ICONS = {
  like: "👆",
  subscribe: "🔔",
  follow: "➕",
};

/**
 * @param {ParentNode} root
 * @param {Record<string, { active?: boolean, label?: string, author?: string | null }> | null | undefined} arenaCtas
 */
export function applyArenaCtasToDom(root, arenaCtas) {
  if (!root) return;
  root.querySelectorAll("[data-cta]").forEach((el) => {
    const key = el.dataset.cta;
    const slot = arenaCtas?.[key];
    const active = Boolean(slot?.active);
    el.classList.toggle("is-live", active);
    el.classList.toggle("is-dormant", !active);
    const textEl = el.querySelector(".yt-cta__text");
    if (textEl && slot?.label) textEl.textContent = slot.label;
    const who = el.querySelector(".yt-cta__who");
    if (who) {
      who.textContent =
        active && slot.author
          ? `@${String(slot.author).replace(/^@/, "")}`
          : "";
    }
  });
}
