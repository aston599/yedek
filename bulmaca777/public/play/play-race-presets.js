/** Sol panel — tek tıkla tur / otomatik mod ön ayarları */
export const PLAY_RACE_PRESETS = {
  standard_auto: {
    label: "Standart otomatik",
    hint: "Dengeli otomatik tur; kaosta kısa kontrollü spawn pencereleri",
    settings: {
      maxRounds: 8,
      audienceSimEnabled: true,
      autopilot: true,
      autoStartOnConnect: true,
      requireYoutubeForAutostart: false,
      autoNextRoundMs: 12_000,
      autoRetryRoundMs: 45_000,
      gatherDurationSec: 300,
      minParticipants: 3,
      minTeams: 2,
      minTotalSpawns: 3,
      chaosMinEntities: 8,
      chaosTrigger: "time_or_count",
      spawnCooldownMs: 25_000,
      chaosSpawnCooldownMs: 5_000,
      chaosSpawnPolicy: "windowed",
      chaosSpawnOpenChancePct: 22,
      chaosSpawnWindowMs: 8_000,
      chaosSpawnWindowCooldownMs: 14_000,
      chaosEliminationGraceMs: 10_000,
      chaosMinDurationMs: 24_000,
    },
  },
  standard_auto_fast: {
    label: "Standart otomatik hızlı",
    hint: "Hızlı tur döngüsü + otomatik sohbet simülasyonu",
    settings: {
      maxRounds: 8,
      audienceSimEnabled: true,
      autopilot: true,
      autoStartOnConnect: true,
      requireYoutubeForAutostart: false,
      autoNextRoundMs: 6_000,
      autoRetryRoundMs: 20_000,
      gatherDurationSec: 75,
      minParticipants: 2,
      minTeams: 2,
      minTotalSpawns: 2,
      chaosMinEntities: 6,
      chaosTrigger: "time_or_count",
      spawnCooldownMs: 8_000,
      chaosSpawnCooldownMs: 3_000,
      chaosSpawnPolicy: "windowed",
      chaosSpawnOpenChancePct: 36,
      chaosSpawnWindowMs: 10_000,
      chaosSpawnWindowCooldownMs: 8_000,
      chaosEliminationGraceMs: 8_000,
      chaosMinDurationMs: 18_000,
      simulateChat: true,
    },
  },
  sim_lab: {
    label: "Sistem simülasyon",
    hint: "Stres testi: sürekli sohbet + yüksek kaos akışı",
    settings: {
      maxRounds: 5,
      audienceSimEnabled: true,
      autopilot: true,
      autoStartOnConnect: true,
      requireYoutubeForAutostart: false,
      autoNextRoundMs: 5_000,
      autoRetryRoundMs: 14_000,
      gatherDurationSec: 50,
      minParticipants: 1,
      minTeams: 2,
      minTotalSpawns: 2,
      chaosMinEntities: 5,
      chaosTrigger: "time_or_count",
      spawnCooldownMs: 4_000,
      chaosSpawnCooldownMs: 2_000,
      chaosSpawnPolicy: "windowed",
      chaosSpawnOpenChancePct: 55,
      chaosSpawnWindowMs: 12_000,
      chaosSpawnWindowCooldownMs: 5_000,
      chaosEliminationGraceMs: 6_000,
      chaosMinDurationMs: 14_000,
      simulateChat: true,
    },
  },
  manual: {
    label: "Manuel",
    hint: "Siz başlatır / kaos dersiniz",
    settings: {
      maxRounds: 8,
      audienceSimEnabled: false,
      autopilot: false,
      autoStartOnConnect: false,
      requireYoutubeForAutostart: false,
      autoNextRoundMs: 15_000,
      autoRetryRoundMs: 45_000,
      gatherDurationSec: 300,
      minParticipants: 2,
      minTeams: 2,
      minTotalSpawns: 2,
      chaosMinEntities: 8,
      chaosTrigger: "manual",
      spawnCooldownMs: 25_000,
      chaosSpawnCooldownMs: 5_000,
      chaosSpawnPolicy: "locked",
      chaosEliminationGraceMs: 10_000,
      chaosMinDurationMs: 22_000,
    },
  },
  chaos: {
    label: "Yoğun kaos",
    hint: "Dolu havuz, kısa toplanma, çok spawn",
    settings: {
      maxRounds: 8,
      audienceSimEnabled: true,
      autopilot: true,
      autoStartOnConnect: true,
      requireYoutubeForAutostart: false,
      autoNextRoundMs: 10_000,
      autoRetryRoundMs: 30_000,
      gatherDurationSec: 90,
      minParticipants: 2,
      minTeams: 2,
      minTotalSpawns: 2,
      chaosMinEntities: 10,
      chaosTrigger: "count",
      spawnCooldownMs: 12_000,
      chaosSpawnCooldownMs: 2_500,
      chaosSpawnPolicy: "windowed",
      chaosSpawnOpenChancePct: 40,
      chaosSpawnWindowMs: 9_000,
      chaosSpawnWindowCooldownMs: 7_000,
      chaosEliminationGraceMs: 8_000,
      chaosMinDurationMs: 20_000,
      maxEntities: 80,
    },
  },
};

const PRESET_MATCH_KEYS = [
  "autopilot",
  "autoStartOnConnect",
  "requireYoutubeForAutostart",
  "autoNextRoundMs",
  "autoRetryRoundMs",
  "gatherDurationSec",
  "minParticipants",
  "minTeams",
  "minTotalSpawns",
  "chaosMinEntities",
  "chaosTrigger",
  "chaosSpawnCooldownMs",
  "chaosSpawnPolicy",
  "chaosSpawnOpenChancePct",
  "chaosSpawnWindowMs",
  "chaosSpawnWindowCooldownMs",
  "chaosEliminationGraceMs",
  "chaosMinDurationMs",
  "maxRounds",
  "audienceSimEnabled",
];

/** UI / sunucu ayarlarını ön ayar karşılaştırması için normalize et */
export function normalizeRaceSettingsForPresetMatch(raw = {}) {
  const gatherSec =
    raw.gatherDurationSec != null
      ? Number(raw.gatherDurationSec)
      : raw.gatherDurationMs != null
        ? Math.round(Number(raw.gatherDurationMs) / 1000)
        : 300;
  const cooldownMs = raw.chaosSpawnCooldownMs ?? raw.spawnCooldownMs ?? 5000;
  return {
    autopilot: raw.autopilot !== false,
    autoStartOnConnect: raw.autoStartOnConnect !== false,
    requireYoutubeForAutostart: Boolean(raw.requireYoutubeForAutostart),
    autoNextRoundMs: Number(raw.autoNextRoundMs) || 0,
    autoRetryRoundMs: Number(raw.autoRetryRoundMs) || 0,
    gatherDurationSec: gatherSec,
    minParticipants: Number(raw.minParticipants) || 0,
    minTeams: Number(raw.minTeams) || 0,
    minTotalSpawns: Number(raw.minTotalSpawns) || 0,
    chaosMinEntities: Number(raw.chaosMinEntities) || 0,
    chaosTrigger: raw.chaosTrigger || "time_or_count",
    chaosSpawnCooldownMs: Number(cooldownMs),
    chaosSpawnPolicy: raw.chaosSpawnPolicy === "windowed" ? "windowed" : "locked",
    chaosSpawnOpenChancePct: Number(raw.chaosSpawnOpenChancePct) || 22,
    chaosSpawnWindowMs: Number(raw.chaosSpawnWindowMs) || 8000,
    chaosSpawnWindowCooldownMs: Number(raw.chaosSpawnWindowCooldownMs) || 14000,
    chaosEliminationGraceMs: Number(raw.chaosEliminationGraceMs) || 0,
    chaosMinDurationMs: Number(raw.chaosMinDurationMs) || 0,
    maxRounds: Number(raw.maxRounds) || 8,
    audienceSimEnabled: raw.audienceSimEnabled !== false,
    simulateChat: Boolean(raw.simulateChat),
  };
}

export function raceSettingsEqualForPreset(a, b) {
  return PRESET_MATCH_KEYS.every((k) => a[k] === b[k]);
}

export function findMatchingRacePresetKey(settingsLike, presets = PLAY_RACE_PRESETS) {
  const norm = normalizeRaceSettingsForPresetMatch(settingsLike);
  for (const key of Object.keys(presets)) {
    if (
      raceSettingsEqualForPreset(norm, normalizeRaceSettingsForPresetMatch(presets[key].settings))
    ) {
      return key;
    }
  }
  return null;
}

/** Ön ayar → sunucu PATCH gövdesi */
export function presetSettingsToServerBody(presetSettings = {}) {
  const s = presetSettings;
  const gatherSec = Number(s.gatherDurationSec) || 300;
  return {
    ...s,
    gatherDurationMs: gatherSec * 1000,
    gatherDurationSec: gatherSec,
    spawnCooldownMs: s.chaosSpawnCooldownMs ?? s.spawnCooldownMs,
  };
}
