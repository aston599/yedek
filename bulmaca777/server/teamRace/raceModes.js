/** Tur içi fazlar: önce toplanma, sonra kaos */
export const ROUND_PHASE = Object.freeze({
  GATHERING: "gathering",
  CHAOS: "chaos",
});

/** Kaos ne zaman başlar */
export const CHAOS_TRIGGER = Object.freeze({
  TIME: "time",
  COUNT: "count",
  TIME_OR_COUNT: "time_or_count",
  MANUAL: "manual",
});

export const DEFAULT_RACE_SETTINGS = Object.freeze({
  spawnCooldownMs: 25_000,
  /** Toplanma fazında aynı izleyicinin tekrar spawn bekleme süresi (ms) */
  gatherRepeatCooldownMs: 10_000,
  /** Kaos fazında aynı izleyici tekrar spawn (ms) */
  chaosSpawnCooldownMs: 5_000,
  /** Kaosta spawn politikası: locked (kapalı) / windowed (kısa aralıklarla açık) */
  chaosSpawnPolicy: "locked",
  /** Kaosta açık pencere tetikleme taban olasılığı (%) */
  chaosSpawnOpenChancePct: 22,
  /** Kaosta spawn penceresi açık kalma süresi (ms) */
  chaosSpawnWindowMs: 8_000,
  /** Kaosta iki açık pencere arası bekleme (ms) */
  chaosSpawnWindowCooldownMs: 14_000,
  maxEntities: 80,
  maxRecentSpawns: 14,
  maxPerChannel: 0,
  /** Toplanma fazı taban süresi (ms) — varsayılan 5 dk */
  gatherDurationMs: 300_000,
  /** Havuz dolunca kaos için min. top (count / time_or_count) */
  chaosMinEntities: 8,
  chaosTrigger: CHAOS_TRIGGER.TIME_OR_COUNT,
  /** Kaosa geçmek için min. farklı izleyici (spawn yapan) */
  minParticipants: 3,
  /** Min. farklı takım (en az bir spawn) */
  minTeams: 2,
  /** Min. toplam spawn (tur içi) */
  minTotalSpawns: 3,
  /** Süre dolunca şartlar yoksa toplanmayı bu kadar uzat (ms) */
  gatherExtendMs: 45_000,
  /** Toplam ek uzatma üst sınırı (ms) — ~15 dk ek */
  gatherMaxExtraMs: 900_000,
  /** Tam otomatik yayın (varsayılan açık) */
  autopilot: true,
  /** YouTube bağlanınca ilk turu otomatik başlat */
  autoStartOnConnect: true,
  /** Başlat sonrası YouTube beklemeden tur (test/play) */
  requireYoutubeForAutostart: true,
  autoStartDelayMs: 3_000,
  /** Kazanan sonrası sonraki tur bekleme */
  autoNextRoundMs: 12_000,
  /** Etkileşimsiz tur sonrası yeniden deneme */
  autoRetryRoundMs: 45_000,
  /** Toplanma analiz aralığı */
  autopilotTickMs: 4_000,
  /** (Yalnızca HUD) süre bitmeden kaos uyarısı — 0 = kapalı */
  earlyChaosRemainingMs: 0,
  /** Kaos başladıktan sonra elenme yok (ms) — toplar dağılsın */
  chaosEliminationGraceMs: 10_000,
  /** Tur bitişi için min. kaos süresi (ms) */
  chaosMinDurationMs: 24_000,
  /** Yayın serisinde kaç tur (kazanan kaydı) oynanacak */
  maxRounds: 8,
  /** Sessiz sohbette gerçekçi izleyici + takım yazısı simülasyonu */
  audienceSimEnabled: true,
  /** İki sim mesajı arası (ms) */
  audienceSimIntervalMs: 4200,
  /** Bu süredir gerçek sohbet yoksa sim devreye girer (ms) */
  audienceSimSilentMs: 14_000,
});

export function normalizeRaceSettings(input = {}) {
  const s = { ...DEFAULT_RACE_SETTINGS, ...input };
  s.spawnCooldownMs = Math.max(1000, Number(s.spawnCooldownMs) || DEFAULT_RACE_SETTINGS.spawnCooldownMs);
  s.chaosSpawnCooldownMs = Math.max(
    1000,
    Number(s.chaosSpawnCooldownMs) ||
      Number(s.spawnCooldownMs) ||
      DEFAULT_RACE_SETTINGS.chaosSpawnCooldownMs
  );
  s.chaosSpawnPolicy = s.chaosSpawnPolicy === "windowed" ? "windowed" : "locked";
  s.chaosSpawnOpenChancePct = Math.max(
    0,
    Math.min(100, Number(s.chaosSpawnOpenChancePct) || DEFAULT_RACE_SETTINGS.chaosSpawnOpenChancePct)
  );
  s.chaosSpawnWindowMs = Math.max(
    1000,
    Math.min(60_000, Number(s.chaosSpawnWindowMs) || DEFAULT_RACE_SETTINGS.chaosSpawnWindowMs)
  );
  s.chaosSpawnWindowCooldownMs = Math.max(
    1000,
    Math.min(
      120_000,
      Number(s.chaosSpawnWindowCooldownMs) || DEFAULT_RACE_SETTINGS.chaosSpawnWindowCooldownMs
    )
  );
  s.gatherRepeatCooldownMs = Math.max(
    10_000,
    Math.min(
      30_000,
      Number(s.gatherRepeatCooldownMs) || DEFAULT_RACE_SETTINGS.gatherRepeatCooldownMs
    )
  );
  s.maxEntities = Math.max(4, Math.min(120, Number(s.maxEntities) || 80));
  s.gatherDurationMs = Math.max(
    15_000,
    Math.min(600_000, Number(s.gatherDurationMs) || DEFAULT_RACE_SETTINGS.gatherDurationMs)
  );
  const gatherMinRaw = Number(input.gatherMinBeforeChaosMs);
  s.gatherMinBeforeChaosMs =
    Number.isFinite(gatherMinRaw) && gatherMinRaw > 0
      ? Math.max(s.gatherDurationMs, Math.min(600_000, gatherMinRaw))
      : s.gatherDurationMs;
  s.chaosMinEntities = Math.max(
    2,
    Math.min(80, Number(s.chaosMinEntities) || DEFAULT_RACE_SETTINGS.chaosMinEntities)
  );
  s.minParticipants = Math.max(
    1,
    Math.min(50, Number(s.minParticipants) || DEFAULT_RACE_SETTINGS.minParticipants)
  );
  s.minTeams = Math.max(2, Math.min(20, Number(s.minTeams) || DEFAULT_RACE_SETTINGS.minTeams));
  s.minTotalSpawns = Math.max(
    1,
    Math.min(80, Number(s.minTotalSpawns) || DEFAULT_RACE_SETTINGS.minTotalSpawns)
  );
  s.gatherExtendMs = Math.max(
    10_000,
    Math.min(180_000, Number(s.gatherExtendMs) || DEFAULT_RACE_SETTINGS.gatherExtendMs)
  );
  s.gatherMaxExtraMs = Math.max(
    0,
    Math.min(1_800_000, Number(s.gatherMaxExtraMs) || DEFAULT_RACE_SETTINGS.gatherMaxExtraMs)
  );
  const trig = String(s.chaosTrigger || CHAOS_TRIGGER.TIME_OR_COUNT);
  s.chaosTrigger = Object.values(CHAOS_TRIGGER).includes(trig)
    ? trig
    : CHAOS_TRIGGER.TIME_OR_COUNT;
  s.autopilot = s.autopilot !== false;
  s.autoStartOnConnect = s.autoStartOnConnect !== false;
  s.requireYoutubeForAutostart = s.requireYoutubeForAutostart !== false;
  s.autoStartDelayMs = Math.max(0, Math.min(60_000, Number(s.autoStartDelayMs) || 3000));
  s.autoNextRoundMs = Math.max(5000, Math.min(300_000, Number(s.autoNextRoundMs) || 20_000));
  s.autoRetryRoundMs = Math.max(10_000, Math.min(600_000, Number(s.autoRetryRoundMs) || 45_000));
  s.autopilotTickMs = Math.max(2000, Math.min(30_000, Number(s.autopilotTickMs) || 4000));
  s.earlyChaosRemainingMs = Math.max(
    0,
    Math.min(120_000, Number(s.earlyChaosRemainingMs) ?? DEFAULT_RACE_SETTINGS.earlyChaosRemainingMs)
  );
  s.chaosEliminationGraceMs = Math.max(
    1000,
    Math.min(30_000, Number(s.chaosEliminationGraceMs) || DEFAULT_RACE_SETTINGS.chaosEliminationGraceMs)
  );
  s.chaosMinDurationMs = Math.max(
    3000,
    Math.min(120_000, Number(s.chaosMinDurationMs) || DEFAULT_RACE_SETTINGS.chaosMinDurationMs)
  );
  s.maxRounds = Math.max(
    1,
    Math.min(50, Number(s.maxRounds) || DEFAULT_RACE_SETTINGS.maxRounds)
  );
  s.audienceSimEnabled = s.audienceSimEnabled !== false;
  s.audienceSimIntervalMs = Math.max(
    1500,
    Math.min(30_000, Number(s.audienceSimIntervalMs) || DEFAULT_RACE_SETTINGS.audienceSimIntervalMs)
  );
  s.audienceSimSilentMs = Math.max(
    3000,
    Math.min(120_000, Number(s.audienceSimSilentMs) || DEFAULT_RACE_SETTINGS.audienceSimSilentMs)
  );
  return s;
}

/** @param {object} settings @param {Array<{ round?: number }>} roundHistory */
export function getRaceSeriesStatus(settings, roundHistory = []) {
  const maxRounds = normalizeRaceSettings(settings).maxRounds;
  const completedRounds = Array.isArray(roundHistory) ? roundHistory.length : 0;
  return {
    maxRounds,
    completedRounds,
    remainingRounds: Math.max(0, maxRounds - completedRounds),
    seriesComplete: completedRounds >= maxRounds,
  };
}

export function canStartRaceRound(settings, roundHistory = []) {
  return !getRaceSeriesStatus(settings, roundHistory).seriesComplete;
}

function countViewerBuckets(viewerCounts = {}) {
  let realParticipants = 0;
  let simParticipants = 0;
  for (const v of Object.values(viewerCounts)) {
    if (v?.simulated) simParticipants += 1;
    else realParticipants += 1;
  }
  return { realParticipants, simParticipants };
}

/** @param {{ viewerCounts?: object, teamCounts?: object, stats?: { spawns?: number }, entities?: Array<{ eliminated?: boolean }> }} engineLike */
export function getEngagementMetrics(engineLike) {
  const viewerCounts = engineLike.viewerCounts || {};
  const teamCounts = engineLike.teamCounts || {};
  const stats = engineLike.stats || {};
  const entities = engineLike.entities || [];
  const { realParticipants, simParticipants } = countViewerBuckets(viewerCounts);
  return {
    participants: realParticipants + simParticipants,
    realParticipants,
    simParticipants,
    teams: Object.keys(teamCounts).filter((c) => (teamCounts[c] || 0) > 0).length,
    spawns: Number(stats.spawns) || 0,
    entities: entities.filter((e) => !e.eliminated).length,
  };
}

export function checkGatherRequirements(settings, metrics) {
  const s = normalizeRaceSettings(settings);
  const missing = [];
  if (metrics.participants < s.minParticipants) {
    missing.push({
      key: "participants",
      label: "katılımcı",
      need: s.minParticipants,
      have: metrics.participants,
    });
  }
  if (metrics.teams < s.minTeams) {
    missing.push({
      key: "teams",
      label: "takım",
      need: s.minTeams,
      have: metrics.teams,
    });
  }
  if (metrics.spawns < s.minTotalSpawns) {
    missing.push({
      key: "spawns",
      label: "spawn",
      need: s.minTotalSpawns,
      have: metrics.spawns,
    });
  }
  return { met: missing.length === 0, missing, settings: s };
}

export function formatGatherBlockedReason(missing = []) {
  if (!missing.length) return null;
  const parts = missing.map((m) => `${m.label} ${m.have}/${m.need}`);
  return `Etkileşim yetersiz (${parts.join(", ")}) — toplanma sürüyor`;
}
