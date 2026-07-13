import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, "..", "..", "data", "football");

let teamKeywordsCache = null;
let countryKeywordsCache = null;

/** Sıkı eşleşme: boşluk/noktalama yok (yeni_proje.txt) */
export function normalizeAnswerCompact(text) {
  return String(text || "")
    .trim()
    .toLocaleLowerCase("tr-TR")
    .replace(/ı/g, "i")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ş/g, "s")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c")
    .replace(/[^a-z0-9]/g, "");
}

function loadJson(name) {
  const path = join(DATA_DIR, name);
  if (!existsSync(path)) return {};
  return JSON.parse(readFileSync(path, "utf-8"));
}

export function getTeamKeywords() {
  if (!teamKeywordsCache) {
    teamKeywordsCache = loadJson("team-keywords.json");
  }
  return teamKeywordsCache;
}

export function getCountryKeywords() {
  if (!countryKeywordsCache) {
    countryKeywordsCache = loadJson("country-keywords.json");
  }
  return countryKeywordsCache;
}

/** Oyuncu + takım sözlüğünden kabul edilen tüm varyantlar */
export function buildAcceptedAnswers(question) {
  const meta = question?.meta || {};
  const canonical =
    meta.club || meta.country || question.answers?.[0] || "";
  const fromPlayer = Array.isArray(question.answers) ? question.answers : [];
  const dict =
    meta.gameKind === "football-nationality"
      ? getCountryKeywords()
      : getTeamKeywords();
  const fromDict = dict[canonical] || [];
  const merged = new Set(
    [...fromPlayer, canonical, ...fromDict]
      .map((s) => String(s || "").trim())
      .filter(Boolean)
  );
  return [...merged];
}

export function matchFootballAnswer(userText, question) {
  const compact = normalizeAnswerCompact(userText);
  if (!compact) return false;
  const accepted = buildAcceptedAnswers(question);
  return accepted.some((a) => normalizeAnswerCompact(a) === compact);
}

export function isFootballQuizQuestion(question) {
  const kind = question?.meta?.gameKind;
  return kind === "football-club" || kind === "football-nationality";
}

export function isFootballClubQuiz(questions) {
  const list = Array.isArray(questions) ? questions : [];
  if (!list.length) return false;
  return list.every((q) => q?.meta?.gameKind === "football-club");
}

export function isFootballNationalityQuiz(questions) {
  const list = Array.isArray(questions) ? questions : [];
  if (!list.length) return false;
  return list.every((q) => q?.meta?.gameKind === "football-nationality");
}
