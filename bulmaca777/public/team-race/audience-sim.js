/** Tarayıcı — sessiz sohbette gerçekçi izleyici simülasyonu (play / playground) */

const SIM_NAMES = [
  "AhmetYilmaz", "Zeynep_42", "CanKral", "ElifLive", "MuratGS", "SelinFB",
  "EmreBJK", "Deniz1907", "Burak61", "AyseTrabzon", "Kaan1905", "Merve_izleyici",
];

const SIM_PREFIXES = ["Ali", "Ayse", "Can", "Deniz", "Ece", "Emir", "Mina", "Ozan"];

const SIM_TEAM_MSGS = [
  "gs", "GS", "galatasaray", "fener", "fb", "bjk", "trabzon", "ts", "goztepe", "samsun",
];

let profileSeq = 0;
const recentAuthors = [];

export function generateSimAuthor() {
  const prefix = SIM_PREFIXES[Math.floor(Math.random() * SIM_PREFIXES.length)];
  profileSeq += 1;
  let author =
    Math.random() < 0.82
      ? `${prefix}${100 + (profileSeq % 900)}`
      : SIM_NAMES[Math.floor(Math.random() * SIM_NAMES.length)];
  let guard = 0;
  while (recentAuthors.includes(author) && guard < 12) {
    profileSeq += 1;
    author = `${prefix}${100 + (profileSeq % 900)}`;
    guard += 1;
  }
  recentAuthors.unshift(author);
  if (recentAuthors.length > 24) recentAuthors.length = 24;
  return author;
}

export function generateSimChatText() {
  return SIM_TEAM_MSGS[Math.floor(Math.random() * SIM_TEAM_MSGS.length)];
}

export function shouldRunClientAudienceSim(
  snap,
  lastRealChatAt,
  { isRoomMode, autopilot, manualBurstOn = false } = {}
) {
  if (!snap || snap.phase !== "running") return false;
  if (snap.settings?.audienceSimEnabled === false) return false;
  if (manualBurstOn) return false;
  if (isRoomMode && autopilot?.enabled && autopilot?.armed) return false;

  const now = Date.now();
  const silentMs = Number(snap.settings?.audienceSimSilentMs) || 14_000;
  const sinceReal = lastRealChatAt ? now - lastRealChatAt : silentMs + 1;
  const realP = snap.engagement?.realParticipants ?? 0;
  const minP = snap.gatherRequirements?.minParticipants ?? 2;

  if (realP < minP) return true;
  if (sinceReal >= silentMs) return true;
  return false;
}

export function pickClientSimIntervalMs(settings = {}) {
  const base = Number(settings.audienceSimIntervalMs) || 4200;
  return Math.max(2000, base + Math.floor(Math.random() * 800));
}
