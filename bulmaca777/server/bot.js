import { fillTemplate } from "./utils.js";

export function formatBotMessage(botName, text) {
  const name = (botName || "YouTube Bulmacalari").trim() || "YouTube Bulmacalari";
  return `[${name}] ${text}`;
}

export function buildWinMessage(config, vars) {
  const template =
    config.winMessage ||
    "Tebrikler {user}! Dogru cevap: {answer}";
  return fillTemplate(template, { ...vars, bot: config.botName });
}

export function buildWrongMessage(config, vars) {
  const template =
    config.wrongMessage ||
    "{user}, bu cevap dogru degil. Tekrar dene!";
  return fillTemplate(template, { ...vars, bot: config.botName });
}

export function buildPingMessage(config) {
  const name = (config.botName || "YouTube Bulmacalari").trim();
  return `Pong! ${name} aktif ve canlı sohbeti dinliyor.`;
}

export function buildYouTubeConnectedMessages(config, snapshot) {
  const name = (config.botName || "YouTube Bulmacalari").trim();
  const lines = [
    `Merhaba! Ben ${name} — canlı sohbete bağlandım.`,
    "Soruların cevaplarını inceliyorum; yazdığınız cevapları kontrol edeceğim.",
    "Botu test etmek için sohbete !ping yazabilirsiniz.",
  ];
  if (snapshot?.state === "active" && snapshot?.question) {
    lines.push("Bulmaca şu an aktif — cevabınızı yazın!");
  } else if (snapshot?.totalQuestions) {
    lines.push("Yayın panelinden Başlat deyince bulmaca başlar.");
  }
  return lines;
}

export function buildGameStartedChatMessage(config, snapshot) {
  const q = snapshot?.question;
  const hint = q?.hint ? ` (${q.hint})` : "";
  const preview =
    q?.question && q.question.length > 60
      ? `${q.question.slice(0, 57)}…`
      : q?.question || "";
  return `Bulmaca başladı!${hint} Cevabınızı sohbete yazın.${preview ? ` Soru: ${preview}` : ""}`;
}
