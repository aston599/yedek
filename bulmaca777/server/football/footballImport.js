import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { getTeamKeywords, getCountryKeywords } from "./footballMatch.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PLAYERS_PATH = join(__dirname, "..", "..", "data", "football", "players.json");

export function loadFootballPlayers() {
  if (!existsSync(PLAYERS_PATH)) return [];
  const parsed = JSON.parse(readFileSync(PLAYERS_PATH, "utf-8"));
  return Array.isArray(parsed) ? parsed : [];
}

function slugId(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

function mergeKeywords(playerKeywords, canonical, dict) {
  const fromDict = dict[canonical] || [];
  const set = new Set(
    [...(playerKeywords || []), canonical, ...fromDict]
      .map((s) => String(s || "").trim())
      .filter(Boolean)
  );
  return [...set];
}

/**
 * @param {"club"|"nationality"} kind
 */
export function footballPlayersToQuestions(kind = "club") {
  const players = loadFootballPlayers();
  const teamKw = getTeamKeywords();
  const countryKw = getCountryKeywords();
  const isClub = kind === "club";
  const hint = isClub
    ? "Futbol — Güncel takım"
    : "Futbol — Milliyet";
  const seen = new Set();
  const out = [];

  for (const p of players) {
    const name = String(p.name || "").trim();
    if (!name) continue;
    let id = slugId(name);
    let n = 0;
    while (seen.has(id)) {
      n += 1;
      id = `${slugId(name)}-${n}`;
    }
    seen.add(id);

    if (isClub) {
      const club = String(p.answer || "").trim();
      const answers = mergeKeywords(p.keywords, club, teamKw);
      out.push({
        id,
        hint,
        question: `${name} hangi takımda oynuyor?`,
        imageUrl: p.photo || "",
        answers,
        points: 10,
        meta: {
          gameKind: "football-club",
          name,
          player: name,
          club,
        },
      });
    } else {
      const country = String(p.country || "").trim();
      const answers = mergeKeywords(
        countryKw[country] || [],
        country,
        countryKw
      );
      out.push({
        id,
        hint,
        question: `${name} hangi ülkenin futbolcusudur?`,
        imageUrl: p.photo || "",
        answers,
        points: 10,
        meta: {
          gameKind: "football-nationality",
          name,
          player: name,
          country,
          club: String(p.answer || "").trim(),
        },
      });
    }
  }

  return out;
}

export function getFootballPackMeta() {
  const players = loadFootballPlayers();
  return {
    playerCount: players.length,
    teamKeywordCount: Object.keys(getTeamKeywords()).length,
    countryKeywordCount: Object.keys(getCountryKeywords()).length,
  };
}
