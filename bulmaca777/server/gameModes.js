import { isCelebrityAgeQuiz } from "./celebrityImport.js";

/** Oda başına oynatılacak interaktif oyun modu */
export const GAME_MODES = Object.freeze({
  PUZZLE: "puzzle",
  TEAM_RACE: "team-race",
  PHOTO_BATTLE: "photo-battle",
  FOOTBALL_CLUB: "football-club",
  FOOTBALL_NATIONALITY: "football-nationality",
});

const LABELS = {
  [GAME_MODES.PUZZLE]: "Bulmaca (soru & cevap)",
  [GAME_MODES.TEAM_RACE]: "Takım yarışı",
  [GAME_MODES.PHOTO_BATTLE]: "Photo Quiz (1 mi 2 mi)",
  [GAME_MODES.FOOTBALL_CLUB]: "Futbol — Güncel takım",
  [GAME_MODES.FOOTBALL_NATIONALITY]: "Futbol — Milliyet",
};

export function normalizeGameMode(value) {
  const v = String(value || "").trim().toLowerCase();
  if (v === GAME_MODES.TEAM_RACE || v === "team_race" || v === "teamrace") {
    return GAME_MODES.TEAM_RACE;
  }
  if (
    v === GAME_MODES.PHOTO_BATTLE ||
    v === "photo_battle" ||
    v === "photo-quiz" ||
    v === "photoquiz" ||
    v === "quize"
  ) {
    return GAME_MODES.PHOTO_BATTLE;
  }
  if (
    v === GAME_MODES.FOOTBALL_CLUB ||
    v === "football_club" ||
    v === "football-club-guess" ||
    v === "footballer_current_club_guess"
  ) {
    return GAME_MODES.FOOTBALL_CLUB;
  }
  if (
    v === GAME_MODES.FOOTBALL_NATIONALITY ||
    v === "football_nationality" ||
    v === "football-nationality-guess"
  ) {
    return GAME_MODES.FOOTBALL_NATIONALITY;
  }
  return GAME_MODES.PUZZLE;
}

export function gameModeLabel(mode) {
  return LABELS[normalizeGameMode(mode)] || LABELS[GAME_MODES.PUZZLE];
}

export function isTeamRaceMode(mode) {
  return normalizeGameMode(mode) === GAME_MODES.TEAM_RACE;
}

export function isPhotoBattleMode(mode) {
  return normalizeGameMode(mode) === GAME_MODES.PHOTO_BATTLE;
}

export function isFootballClubMode(mode) {
  return normalizeGameMode(mode) === GAME_MODES.FOOTBALL_CLUB;
}

export function isFootballNationalityMode(mode) {
  return normalizeGameMode(mode) === GAME_MODES.FOOTBALL_NATIONALITY;
}

export function isFootballMode(mode) {
  return isFootballClubMode(mode) || isFootballNationalityMode(mode);
}

/** Photo Quiz seçili ama sorular ünlü yaş formatındaysa — 1/2 oylama değil, yaş tahmini motoru */
export function photoRoomRunsCelebrityAge(room) {
  if (!room || !isPhotoBattleMode(room.config?.gameMode)) return false;
  return isCelebrityAgeQuiz(room.game?.questions);
}

/** Fotoğraflı quiz overlay (ünlü yaş veya futbol) */
export function roomUsesPhotoOverlay(room) {
  if (!room) return false;
  if (photoRoomRunsCelebrityAge(room)) return true;
  return isFootballMode(room.config?.gameMode);
}

/** Bulmaca motoru (GameEngine): bulmaca, futbol veya Photo Quiz + ünlü yaş */
export function roomUsesPuzzleEngine(room) {
  if (!room) return false;
  if (isTeamRaceMode(room.config?.gameMode)) return false;
  if (isFootballMode(room.config?.gameMode)) return true;
  if (!isPhotoBattleMode(room.config?.gameMode)) return true;
  return photoRoomRunsCelebrityAge(room);
}
