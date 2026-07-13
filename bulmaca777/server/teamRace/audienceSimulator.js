import { randomBytes } from "crypto";
import { resolveTeamFromText } from "./aliases.js";

const SIM_NAMES = [
  "AhmetYilmaz",
  "Zeynep_42",
  "CanKral",
  "ElifLive",
  "MuratGS",
  "SelinFB",
  "EmreBJK",
  "Deniz1907",
  "Burak61",
  "AyseTrabzon",
  "Kaan1905",
  "Merve_izleyici",
  "YusufCanli",
  "EceFener",
  "OzanKartal",
  "SudeAslan",
  "BarisRize",
  "GamzeGoztepe",
  "Tolga1903",
  "IremSam",
  "HakanGSli",
  "CerenFbFan",
  "ArdaChamp",
  "NazliLive",
  "Serkan61",
  "Pelin1907",
  "UmutBJK",
  "DilaraGS",
  "KemalFener",
  "MelisTrabzon",
];

const SIM_PREFIXES = [
  "Ali",
  "Ayse",
  "Can",
  "Deniz",
  "Ece",
  "Emir",
  "Mina",
  "Ozan",
  "Sena",
  "Yigit",
  "Arda",
  "Defne",
  "Kerem",
  "Nehir",
  "Bora",
];

const SIM_TEAM_MSGS = [
  "gs",
  "GS",
  "galatasaray",
  "cimbom",
  "fener",
  "fenerbahce",
  "fb",
  "FB",
  "bjk",
  "besiktas",
  "trabzon",
  "ts",
  "goztepe",
  "samsun",
  "basaksehir",
  "konya",
  "rizespor",
  "antalya",
  "karagumruk",
  "kasimpasa",
];

const SIM_NOISE_MSGS = [
  "geldim",
  "selam",
  "aslanlar",
  "kanarya",
  "kartal",
  "göztepe",
  "hadi",
  "lets go",
];

let profileSeq = 0;
const recentAuthors = [];

export function isSimulatedChannelId(channelId) {
  return String(channelId || "").startsWith("sim:");
}

export function isSimulatedMessage(msg) {
  return Boolean(msg?.simulated) || isSimulatedChannelId(msg?.channelId);
}

export function generateSimAuthor() {
  const useFresh = Math.random() < 0.84;
  let author = "";
  if (useFresh) {
    const prefix = SIM_PREFIXES[Math.floor(Math.random() * SIM_PREFIXES.length)];
    profileSeq += 1;
    author = `${prefix}${100 + (profileSeq % 900)}`;
  } else {
    author = SIM_NAMES[Math.floor(Math.random() * SIM_NAMES.length)];
  }
  let guard = 0;
  while (recentAuthors.includes(author) && guard < 14) {
    profileSeq += 1;
    const prefix = SIM_PREFIXES[Math.floor(Math.random() * SIM_PREFIXES.length)];
    author = `${prefix}${100 + (profileSeq % 900)}`;
    guard += 1;
  }
  recentAuthors.unshift(author);
  if (recentAuthors.length > 28) recentAuthors.length = 28;
  return author;
}

export function generateSimChatText() {
  const roll = Math.random();
  if (roll < 0.92) {
    return SIM_TEAM_MSGS[Math.floor(Math.random() * SIM_TEAM_MSGS.length)];
  }
  return SIM_NOISE_MSGS[Math.floor(Math.random() * SIM_NOISE_MSGS.length)];
}

export function buildSimulatedChatMessage(author = generateSimAuthor(), text = generateSimChatText()) {
  const safeAuthor = String(author || "Izleyici").trim() || "Izleyici";
  const body = String(text || "").trim() || generateSimChatText();
  const key = safeAuthor.toLowerCase().slice(0, 48);
  return {
    id: `sim-${randomBytes(6).toString("hex")}`,
    author: safeAuthor,
    channelId: `sim:${key}`,
    text: body,
    simulated: true,
    publishedAt: new Date().toISOString(),
  };
}

/** Gerçek sohbet yokken veya katılım düşükken sim mesajı üretilmeli mi? */
export function shouldSimulateAudience(engine, settings, lastRealChatAt = 0) {
  if (settings.audienceSimEnabled === false) return false;
  if (!engine?.isRunning?.()) return false;

  const now = Date.now();
  const silentMs = Math.max(4000, Number(settings.audienceSimSilentMs) || 14_000);
  const sinceReal = lastRealChatAt ? now - lastRealChatAt : silentMs + 1;

  const viewerCounts = engine.viewerCounts || {};
  let realParticipants = 0;
  for (const v of Object.values(viewerCounts)) {
    if (!v?.simulated) realParticipants += 1;
  }

  const minP = Math.max(1, Number(settings.minParticipants) || 2);
  const eng = engine.getEngagement?.() || {};
  const spawns = Number(eng.spawns) || 0;
  const minSpawns = Math.max(1, Number(settings.minTotalSpawns) || 2);

  if (realParticipants < minP) return true;
  if (spawns < minSpawns && sinceReal > silentMs * 0.5) return true;
  if (sinceReal >= silentMs) return true;
  return false;
}

export function pickSimIntervalMs(settings) {
  const base = Math.max(2200, Number(settings.audienceSimIntervalMs) || 4200);
  return base + Math.floor(Math.random() * 900);
}
