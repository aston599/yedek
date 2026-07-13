/**
 * Arena alt orta bölüm — YouTube CTA rozetleri + sohbet kuralları bandı.
 */
import { applyArenaCtasToDom } from "./youtube-ctas-ui.js";

/** @type {{ text: string, tone?: "ban" | "cta" | "rule" }[]} */
export const DEFAULT_CMD_RULES = [
  { text: "Abone ol", tone: "cta" },
  { text: "2× tıkla", tone: "cta" },
  { text: "Takip et", tone: "cta" },
  { text: "67 = ban", tone: "ban" },
  { text: "Spam = ban", tone: "ban" },
  { text: "Kısaltma veya tam ad", tone: "rule" },
  { text: "Mesaj = top", tone: "rule" },
];

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * @param {HTMLElement | null} tickerEl
 * @param {typeof DEFAULT_CMD_RULES} [rules]
 */
export function renderCmdRulesTicker(tickerEl, rules = DEFAULT_CMD_RULES) {
  if (!tickerEl || !rules.length) return;
  const chips = rules
    .map((r) => {
      const tone = r.tone === "ban" ? " play-cmd-chip--ban" : r.tone === "cta" ? " play-cmd-chip--cta" : "";
      return `<li class="play-cmd-chip${tone}">${esc(r.text)}</li>`;
    })
    .join("");
  tickerEl.innerHTML = chips + chips;
}

/**
 * @param {HTMLElement | null} root
 */
export function initArenaCmdBand(root) {
  if (!root) return;
  const ticker = root.querySelector("[data-arena-cmd-ticker]");
  renderCmdRulesTicker(ticker);
}

/**
 * @param {HTMLElement | null} root
 * @param {boolean} on
 */
export function setArenaCmdBandVisible(root, on) {
  if (!root) return;
  root.classList.toggle("hidden", !on);
}

/**
 * @param {HTMLElement | null} root
 * @param {Record<string, { active?: boolean, label?: string, author?: string | null }> | null | undefined} arenaCtas
 */
export function syncArenaCmdBand(root, arenaCtas) {
  if (!root) return;
  const ctasRoot = root.querySelector("[data-arena-cmd-ctas]") || root;
  applyArenaCtasToDom(ctasRoot, arenaCtas);
}
