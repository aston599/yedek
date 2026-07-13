import { randomBytes } from "crypto";
import { TeamRaceEngine } from "../teamRace/engine.js";
import { normalizeRaceSettings } from "../teamRace/raceModes.js";
import { TEAM_DISPLAY_NAMES, flagUrlForTeam, teamDisplayName } from "../teamRace/teamsMeta.js";
import { resolveTeamFromText } from "../teamRace/aliases.js";

const MAX_SESSIONS = 120;
const SESSION_TTL_MS = 2 * 60 * 60 * 1000;

/** @type {Map<string, SessionRow>} */
const sessions = new Map();

function pruneSessions() {
  const now = Date.now();
  for (const [id, row] of sessions) {
    if (now - row.lastAt > SESSION_TTL_MS) sessions.delete(id);
  }
  if (sessions.size <= MAX_SESSIONS) return;
  const sorted = [...sessions.entries()].sort((a, b) => a[1].lastAt - b[1].lastAt);
  while (sessions.size > MAX_SESSIONS && sorted.length) {
    sessions.delete(sorted.shift()[0]);
  }
}

function touch(row) {
  row.lastAt = Date.now();
}

function recordRoundWinner(row, snap) {
  const w = snap?.lastWinner;
  if (!w?.teamCode) return;
  row.champions[w.teamCode] = (row.champions[w.teamCode] || 0) + 1;
  row.roundHistory.unshift({
    round: snap.round,
    teamCode: w.teamCode,
    teamName: w.teamName,
    flagUrl: w.flagUrl,
    spawnCount: w.spawnCount,
    winReason: w.winReason,
    endKind: snap.endKind,
    at: w.at || new Date().toISOString(),
  });
  if (row.roundHistory.length > 30) row.roundHistory.length = 30;
}

function syncChaosFromEngine(row) {
  row.chaos = row.engine.isChaos();
}

function wireEngine(row) {
  row.engine.onRoundEnd = (snap) => {
    recordRoundWinner(row, snap);
    syncChaosFromEngine(row);
  };
  row.engine.onPhaseChange = () => {
    syncChaosFromEngine(row);
  };
  row.engine.onStateChange = () => {
    syncChaosFromEngine(row);
  };
}

function playgroundSettings(options = {}) {
  return normalizeRaceSettings({
    spawnCooldownMs: Number(options.spawnCooldownMs) || 3_000,
    gatherDurationMs:
      Number(options.gatherDurationMs) ||
      (Number(options.gatherDurationSec) ? Number(options.gatherDurationSec) * 1000 : undefined),
    chaosMinEntities: options.chaosMinEntities,
    chaosTrigger: options.chaosTrigger,
    minParticipants: options.minParticipants,
    minTeams: options.minTeams,
    minTotalSpawns: options.minTotalSpawns,
    gatherExtendMs: options.gatherExtendMs,
    maxEntities: 60,
    maxRecentSpawns: 20,
    maxPerChannel: 8,
    requireYoutubeForAutostart: false,
    autopilot: options.autopilot !== false,
  });
}

export function createPlaygroundSession(options = {}) {
  pruneSessions();
  const id = randomBytes(8).toString("hex");
  const engine = new TeamRaceEngine({
    settings: playgroundSettings(options),
  });
  const row = {
    engine,
    createdAt: Date.now(),
    lastAt: Date.now(),
    champions: {},
    chaos: false,
    roundHistory: [],
  };
  wireEngine(row);
  sessions.set(id, row);
  return {
    sessionId: id,
    snapshot: engine.getSnapshot(),
    champions: {},
    roundHistory: [],
  };
}

export function getPlaygroundSession(sessionId) {
  if (!sessionId || !sessions.has(sessionId)) return null;
  const row = sessions.get(sessionId);
  touch(row);
  return row;
}

export function deletePlaygroundSession(sessionId) {
  sessions.delete(sessionId);
}

export function updatePlaygroundSettings(sessionId, partial) {
  const row = getPlaygroundSession(sessionId);
  if (!row) return { error: "Oturum bulunamadı", status: 404 };
  row.engine.updateSettings(partial);
  syncChaosFromEngine(row);
  return { settings: row.engine.settings, snapshot: row.engine.getSnapshot() };
}

export function eliminatePlaygroundEntity(sessionId, entityId) {
  const row = getPlaygroundSession(sessionId);
  if (!row) return { error: "Oturum bulunamadı", status: 404 };
  const wasRunning = row.engine.isRunning();
  const ok = row.engine.eliminateEntity(entityId);
  const snap = row.engine.getSnapshot();
  const roundEnded = wasRunning && snap.phase === "idle";
  return {
    ok,
    roundEnded,
    snapshot: snap,
    entities: row.engine.entities.filter((e) => !e.eliminated),
    champions: { ...row.champions },
    roundHistory: [...row.roundHistory],
    chaos: row.chaos,
  };
}

export function setPlaygroundChaos(sessionId, enabled) {
  const row = getPlaygroundSession(sessionId);
  if (!row) return { error: "Oturum bulunamadı", status: 404 };
  if (enabled) {
    if (!row.engine.isRunning()) row.engine.start();
    if (!row.engine.isChaos()) {
      const ok = row.engine.forceChaos();
      if (!ok) {
        return {
          error: "Kaos başlatılamadı.",
          status: 400,
          snapshot: row.engine.getSnapshot(),
        };
      }
    }
  }
  syncChaosFromEngine(row);
  return { chaos: row.chaos, snapshot: row.engine.getSnapshot() };
}

export function triggerPlaygroundShock(sessionId) {
  const row = getPlaygroundSession(sessionId);
  if (!row) return { error: "Oturum bulunamadı", status: 404 };
  const ok = row.engine.triggerShockWave("manual");
  return { ok, snapshot: row.engine.getSnapshot(), chaos: row.chaos };
}

export function stopPlaygroundRound(sessionId) {
  const row = getPlaygroundSession(sessionId);
  if (!row) return { error: "Oturum bulunamadı", status: 404 };
  const snap = row.engine.stop();
  syncChaosFromEngine(row);
  return {
    snapshot: snap,
    champions: { ...row.champions },
    roundHistory: [...row.roundHistory],
    chaos: row.chaos,
  };
}

export function listTeams() {
  return Object.entries(TEAM_DISPLAY_NAMES).map(([code, name]) => ({
    code,
    name,
    flagUrl: flagUrlForTeam(code),
  }));
}

export function playgroundChat(sessionId, { author, text, simulated = false }) {
  const row = getPlaygroundSession(sessionId);
  if (!row) return { error: "Oturum bulunamadı", status: 404 };

  const body = String(text ?? "").trim();
  if (!body) return { error: "Mesaj gerekli", status: 400 };

  const name = String(author || "Oyuncu").trim() || "Oyuncu";
  const channelId = `play-${name.toLowerCase().replace(/\s+/g, "-").slice(0, 40)}-${Date.now().toString(36).slice(-4)}`;
  const isSim = Boolean(simulated);

  const msg = {
    id: isSim
      ? `sim-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
      : `play-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    author: name,
    channelId: isSim ? `sim:${channelId.replace(/^play-/, "")}` : channelId,
    avatarUrl: null,
    text: body,
    simulated: isSim,
    publishedAt: new Date().toISOString(),
  };

  const result = row.engine.handleChatMessage(msg);
  const preview = resolveTeamFromText(body);
  const snap = row.engine.getSnapshot();

  return {
    result,
    resolvedTeam: preview ? { code: preview, name: teamDisplayName(preview) } : null,
    snapshot: snap,
    entities: row.engine.entities.filter((e) => !e.eliminated),
    lastSpawn: result?.type === "spawn" ? result.entity : null,
    champions: { ...row.champions },
    roundHistory: [...row.roundHistory],
    chaos: row.chaos,
    phaseChanged: snap.roundPhase === "chaos" && snap.chaosTriggerReason === "count",
  };
}

export function getPlaygroundEntities(sessionId) {
  const row = getPlaygroundSession(sessionId);
  if (!row) return null;
  return row.engine.entities.filter((e) => !e.eliminated);
}
