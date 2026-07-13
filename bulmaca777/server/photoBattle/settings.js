export const DEFAULT_PHOTO_BATTLE_SETTINGS = Object.freeze({
  title: "Hangisi daha iyi?",
  voteDurationSec: 120,
  maxVotersListed: 16,
  resultHoldSec: 4,
});

export function normalizePhotoBattleSettings(raw = {}) {
  const s = { ...DEFAULT_PHOTO_BATTLE_SETTINGS, ...(raw || {}) };
  s.title = String(s.title || DEFAULT_PHOTO_BATTLE_SETTINGS.title).trim().slice(0, 120);
  s.voteDurationSec = Math.max(
    15,
    Math.min(600, Number(s.voteDurationSec) || DEFAULT_PHOTO_BATTLE_SETTINGS.voteDurationSec)
  );
  s.maxVotersListed = Math.max(
    4,
    Math.min(40, Number(s.maxVotersListed) || DEFAULT_PHOTO_BATTLE_SETTINGS.maxVotersListed)
  );
  s.resultHoldSec = Math.max(
    2,
    Math.min(15, Number(s.resultHoldSec) || DEFAULT_PHOTO_BATTLE_SETTINGS.resultHoldSec)
  );
  return s;
}
