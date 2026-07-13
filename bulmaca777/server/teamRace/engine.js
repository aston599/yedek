import { randomBytes } from "crypto";
import { resolveTeamFromText } from "./aliases.js";
import { teamDisplayName, flagUrlForTeam } from "./teamsMeta.js";
import {
  ROUND_PHASE,
  CHAOS_TRIGGER,
  normalizeRaceSettings,
  getEngagementMetrics,
  checkGatherRequirements,
  formatGatherBlockedReason,
} from "./raceModes.js";
import {
  CTA_PULSE_MS,
  detectYoutubeCtas,
  buildArenaCtasSnapshot,
} from "./youtubeCtas.js";

export class TeamRaceEngine {
  constructor(options = {}) {
    this.phase = "idle";
    this.round = 0;
    this.roundPhase = null;
    this.roundStartedAt = null;
    this.chaosStartedAt = null;
    this.chaosTriggerReason = null;
    this.shockWaveAt = null;
    this.settings = normalizeRaceSettings(options.settings);
    this.entities = [];
    this.recentSpawns = [];
    this.teamCounts = {};
    this.stats = { spawns: 0, unmatched: 0, rejected: 0 };
    this.lastWinner = null;
    this._channelLastSpawn = new Map();
    this._processedIds = new Set();
    this._gatherTimer = null;
    this.gatherExtendedMs = 0;
    this.gatherBlockedReason = null;
    this.gatherEverReady = false;
    /** @type {Record<string, { author: string, count: number, lastTeamCode?: string, lastTeamName?: string }>} */
    this.viewerCounts = {};
    /** @type {Array<{ id: string, author: string, teamCode?: string, teamName?: string, text?: string, type: string, at: string }>} */
    this.activityLog = [];
    /** @type {Record<string, { until: number, author: string | null }>} */
    this.ctaPulses = {};
    this.chaosSpawnWindowUntil = 0;
    this.chaosSpawnWindowLastAt = 0;
    this.onStateChange = options.onStateChange ?? (() => {});
    this.onSpawn = options.onSpawn ?? (() => {});
    this.onPersist = options.onPersist ?? (() => {});
    this.onRoundEnd = options.onRoundEnd ?? (() => {});
    this.onPhaseChange = options.onPhaseChange ?? (() => {});
  }

  isRunning() {
    return this.phase === "running";
  }

  isChaos() {
    return this.roundPhase === ROUND_PHASE.CHAOS;
  }

  isGathering() {
    return this.roundPhase === ROUND_PHASE.GATHERING;
  }

  _clearGatherTimer() {
    if (this._gatherTimer) {
      clearTimeout(this._gatherTimer);
      this._gatherTimer = null;
    }
  }

  getEngagement() {
    return getEngagementMetrics(this);
  }

  getGatherReadiness() {
    return checkGatherRequirements(this.settings, this.getEngagement());
  }

  _gatherRequirementsMet() {
    return this.getGatherReadiness().met;
  }

  _markGatherReadyIfMet() {
    if (this._gatherRequirementsMet()) {
      this.gatherEverReady = true;
      this.gatherBlockedReason = null;
    }
  }

  getGatherDeadlineMs() {
    if (!this.roundStartedAt) return Date.now();
    const base = new Date(this.roundStartedAt).getTime();
    const extra = Math.min(this.gatherExtendedMs, this.settings.gatherMaxExtraMs);
    return base + this.settings.gatherDurationMs + extra;
  }

  _scheduleGatherTimer() {
    this._clearGatherTimer();
    const remaining = this.getGatherRemainingMs();
    if (remaining <= 0) {
      this._onGatherTimerFired();
      return;
    }
    this._gatherTimer = setTimeout(() => this._onGatherTimerFired(), remaining);
  }

  _onGatherTimerFired() {
    if (!this.isRunning() || !this.isGathering()) return;
    if (this.checkGatheringProgress()) return;
    if (this._gatherRequirementsMet()) {
      this.forceChaos();
      return;
    }
    const { missing } = this.getGatherReadiness();
    this.gatherBlockedReason = formatGatherBlockedReason(missing);
    const canExtend =
      this.gatherExtendedMs + this.settings.gatherExtendMs <= this.settings.gatherMaxExtraMs;
    if (canExtend) {
      this.gatherExtendedMs += this.settings.gatherExtendMs;
      this._scheduleGatherTimer();
    }
    this._emitState();
    this.onPersist();
  }

  tryEnterChaos(reason = "manual") {
    if (!this.isRunning() || this.isChaos()) return false;
    const { chaosTrigger } = this.settings;
    const force = reason === "manual" || reason === "force";

    if (!force && reason !== "manual" && !this._gatherMinTimeElapsed()) {
      return false;
    }

    if (reason === "time") {
      if (
        chaosTrigger !== CHAOS_TRIGGER.TIME &&
        chaosTrigger !== CHAOS_TRIGGER.TIME_OR_COUNT
      ) {
        return false;
      }
    } else if (reason === "count") {
      const n = this.entities.filter((e) => !e.eliminated).length;
      if (n < this.settings.chaosMinEntities) return false;
    } else if (reason === "ready") {
      if (!this._gatherRequirementsMet()) return false;
    } else if (!force) {
      return false;
    }

    if (!force && !this._gatherRequirementsMet()) {
      const { missing } = this.getGatherReadiness();
      this.gatherBlockedReason = formatGatherBlockedReason(missing);
      this._emitState();
      return false;
    }

    this._clearGatherTimer();
    this.gatherBlockedReason = null;
    this.gatherEverReady = true;
    this.roundPhase = ROUND_PHASE.CHAOS;
    this.chaosStartedAt = new Date().toISOString();
    this.chaosTriggerReason = reason === "ready" ? "auto" : reason;
    this.chaosSpawnWindowUntil = 0;
    this.chaosSpawnWindowLastAt = 0;
    this._emitState();
    this.onPersist();
    this.onPhaseChange(this.getSnapshot());
    return true;
  }

  getChaosElapsedMs() {
    if (!this.chaosStartedAt) return 0;
    return Date.now() - new Date(this.chaosStartedAt).getTime();
  }

  isInChaosEliminationGrace() {
    return this.getChaosElapsedMs() < this.settings.chaosEliminationGraceMs;
  }

  canEndRoundFromChaos() {
    return this.getChaosElapsedMs() >= this.settings.chaosMinDurationMs;
  }

  triggerShockWave(source = "manual") {
    if (!this.isRunning() || !this.isChaos()) return false;
    this.shockWaveAt = new Date().toISOString();
    this._recordActivity({
      author: "Sistem",
      text: source === "manual" ? "Şok dalgası tetiklendi" : "Şok dalgası",
      type: "system",
    });
    this._emitState();
    this.onPersist();
    return true;
  }

  _isChaosSpawnWindowOpen(now = Date.now()) {
    return this.chaosSpawnWindowUntil > now;
  }

  _maybeOpenChaosSpawnWindow() {
    if (!this.isRunning() || !this.isChaos()) return false;
    if (this.settings.chaosSpawnPolicy !== "windowed") return false;
    const now = Date.now();
    if (this._isChaosSpawnWindowOpen(now)) return true;
    if (now - this.chaosSpawnWindowLastAt < this.settings.chaosSpawnWindowCooldownMs) return false;

    const active = this.entities.filter((e) => !e.eliminated).length;
    const target = Math.max(1, this.settings.chaosMinEntities || 1);
    const pressure = active / target;
    const baseChance = (this.settings.chaosSpawnOpenChancePct || 0) / 100;
    const pressureMul = pressure <= 0.75 ? 1.35 : pressure <= 1.05 ? 1 : pressure <= 1.3 ? 0.72 : 0.45;
    const chance = Math.max(0, Math.min(0.95, baseChance * pressureMul));
    if (Math.random() > chance) return false;

    this.chaosSpawnWindowUntil = now + this.settings.chaosSpawnWindowMs;
    this.chaosSpawnWindowLastAt = now;
    this._recordActivity({
      author: "Sistem",
      text: "Kaosta kısa spawn penceresi açıldı",
      type: "system",
    });
    return true;
  }

  forceChaos() {
    return this.tryEnterChaos("force");
  }

  /** Toplanma fazı ilerlemesi: min. süre + (isteğe bağlı) havuz dolunca veya süre bitince */
  checkGatheringProgress() {
    if (!this.isGathering()) return false;
    if (!this._gatherMinTimeElapsed()) return false;

    const { chaosTrigger } = this.settings;
    const n = this.entities.filter((e) => !e.eliminated).length;
    const poolTriggers = [CHAOS_TRIGGER.COUNT, CHAOS_TRIGGER.TIME_OR_COUNT];
    if (
      n >= this.settings.chaosMinEntities &&
      poolTriggers.includes(chaosTrigger) &&
      this.tryEnterChaos("count")
    ) {
      return true;
    }

    const remaining = this.getGatherRemainingMs();
    if (remaining > 0) return false;

    if (this._gatherRequirementsMet()) {
      return this.forceChaos();
    }

    return false;
  }

  getGatherRemainingMs() {
    if (!this.isGathering() || !this.roundStartedAt) return 0;
    return Math.max(0, this.getGatherDeadlineMs() - Date.now());
  }

  _getGatherElapsedMs() {
    if (!this.roundStartedAt) return 0;
    return Math.max(0, Date.now() - new Date(this.roundStartedAt).getTime());
  }

  /** Havuz dolsa bile bu süre dolmadan otomatik kaosa geçilmez */
  getGatherMinBeforeChaosMs() {
    return (
      Number(this.settings.gatherMinBeforeChaosMs) ||
      Number(this.settings.gatherDurationMs) ||
      300_000
    );
  }

  getGatherMinRemainingMs() {
    if (!this.isGathering() || !this.roundStartedAt) return 0;
    return Math.max(0, this.getGatherMinBeforeChaosMs() - this._getGatherElapsedMs());
  }

  _gatherMinTimeElapsed() {
    return this._getGatherElapsedMs() >= this.getGatherMinBeforeChaosMs();
  }

  _viewerKey(author) {
    return String(author || "anon")
      .trim()
      .toLowerCase()
      .slice(0, 48);
  }

  _pulseYoutubeCtas(text, author) {
    const hits = detectYoutubeCtas(text);
    if (!hits.length) return [];
    const name = String(author || "İzleyici").trim() || "İzleyici";
    const until = Date.now() + CTA_PULSE_MS;
    for (const key of hits) {
      this.ctaPulses[key] = { until, author: name };
    }
    return hits;
  }

  getArenaCtas() {
    return buildArenaCtasSnapshot(this.ctaPulses);
  }

  _recordActivity(entry) {
    const row = {
      id: randomBytes(4).toString("hex"),
      author: String(entry.author || "İzleyici").trim() || "İzleyici",
      teamCode: entry.teamCode || null,
      teamName: entry.teamName || null,
      text: entry.text || null,
      type: entry.type || "spawn",
      at: new Date().toISOString(),
    };
    this.activityLog.unshift(row);
    if (this.activityLog.length > 40) this.activityLog.length = 40;
    return row;
  }

  _bumpViewer(author, teamCode, teamName, { simulated = false } = {}) {
    const key = this._viewerKey(author);
    const row = this.viewerCounts[key] || {
      author: String(author || "İzleyici").trim() || "İzleyici",
      count: 0,
      simulated: false,
    };
    row.count += 1;
    if (simulated) row.simulated = true;
    if (teamCode) {
      row.lastTeamCode = teamCode;
      row.lastTeamName = teamName || teamDisplayName(teamCode);
    }
    this.viewerCounts[key] = row;
  }

  getTopViewers(limit = 5) {
    const real = [];
    const sim = [];
    for (const v of Object.values(this.viewerCounts)) {
      if (v?.simulated) sim.push(v);
      else real.push(v);
    }
    real.sort((a, b) => b.count - a.count);
    sim.sort((a, b) => b.count - a.count);
    return [...real, ...sim].slice(0, limit).map((v, i) => ({
      rank: i + 1,
      author: v.author,
      count: v.count,
      simulated: Boolean(v.simulated),
      lastTeamCode: v.lastTeamCode || null,
      lastTeamName: v.lastTeamName || null,
      flagUrl: v.lastTeamCode ? flagUrlForTeam(v.lastTeamCode) : null,
    }));
  }

  getSnapshot() {
    const entityCount = this.entities.filter((e) => !e.eliminated).length;
    const engagement = this.getEngagement();
    const readiness = checkGatherRequirements(this.settings, engagement);
    return {
      mode: "team-race",
      phase: this.phase,
      round: this.round,
      roundPhase: this.roundPhase,
      chaos: this.isChaos(),
      roundStartedAt: this.roundStartedAt,
      chaosStartedAt: this.chaosStartedAt,
      chaosTriggerReason: this.chaosTriggerReason,
      shockWaveAt: this.shockWaveAt,
      chaosSpawnWindowOpen: this._isChaosSpawnWindowOpen(),
      chaosSpawnWindowRemainingMs: Math.max(0, this.chaosSpawnWindowUntil - Date.now()),
      gatherRemainingMs: this.getGatherRemainingMs(),
      gatherMinRemainingMs: this.getGatherMinRemainingMs(),
      gatherMinBeforeChaosMs: this.getGatherMinBeforeChaosMs(),
      gatherExtendedMs: this.gatherExtendedMs,
      gatherBlockedReason: this.gatherBlockedReason,
      gatherEverReady: this.gatherEverReady,
      engagement,
      gatherRequirements: {
        met: readiness.met,
        missing: readiness.missing,
        minParticipants: this.settings.minParticipants,
        minTeams: this.settings.minTeams,
        minTotalSpawns: this.settings.minTotalSpawns,
        chaosMinEntities: this.settings.chaosMinEntities,
      },
      poolFillRatio: Math.min(
        1,
        entityCount / Math.max(1, this.settings.chaosMinEntities)
      ),
      settings: { ...this.settings },
      stats: { ...this.stats },
      teamCounts: { ...this.teamCounts },
      recentSpawns: [...this.recentSpawns],
      entityCount,
      totalSpawned: this.entities.length,
      activeByTeam: this.getActiveCountsByTeam(),
      activeEntities: this.entities
        .filter((e) => !e.eliminated)
        .map((e) => ({
          id: e.id,
          teamCode: e.teamCode,
          teamName: e.teamName,
          flagUrl: e.flagUrl,
          displayName: e.displayName,
        })),
      lastWinner: this.lastWinner ? { ...this.lastWinner } : null,
      topViewers: this.getTopViewers(5),
      activityFeed: [...this.activityLog].slice(0, 25),
      arenaCtas: this.getArenaCtas(),
    };
  }

  _clearRoundArena() {
    this.entities = [];
    this.recentSpawns = [];
    this.teamCounts = {};
    this.stats = { spawns: 0, unmatched: 0, rejected: 0 };
    this._channelLastSpawn.clear();
  }

  start() {
    this._clearGatherTimer();
    this._clearRoundArena();
    this.lastWinner = null;
    this.phase = "running";
    this.round += 1;
    this.roundPhase = ROUND_PHASE.GATHERING;
    this.roundStartedAt = new Date().toISOString();
    this.chaosStartedAt = null;
    this.chaosTriggerReason = null;
    this.shockWaveAt = null;
    this.chaosSpawnWindowUntil = 0;
    this.chaosSpawnWindowLastAt = 0;
    this.gatherExtendedMs = 0;
    this.gatherBlockedReason = null;
    this.gatherEverReady = false;
    this._scheduleGatherTimer();
    this._emitState();
    this.onPersist();
    this.onPhaseChange(this.getSnapshot());
    return this.getSnapshot();
  }

  stop() {
    return this._endRound("manual");
  }

  eliminateEntity(entityId, reason = "fallen") {
    if (!this.isChaos()) return false;
    if (this.isInChaosEliminationGrace()) return false;
    const e = this.entities.find((x) => x.id === entityId);
    if (!e || e.eliminated) return false;
    e.eliminated = true;
    e.eliminatedAt = new Date().toISOString();
    e.eliminateReason = reason;
    this._emitState();
    this.onPersist();
    if (this.isRunning()) this._maybeAutoEndRound();
    return true;
  }

  _maybeAutoEndRound() {
    if (!this.isRunning() || !this.isChaos()) return false;
    if (!this.canEndRoundFromChaos()) return false;
    const active = this.entities.filter((e) => !e.eliminated);
    const byTeam = this.getActiveCountsByTeam();
    const teamKeys = Object.keys(byTeam);

    if (active.length === 0) {
      return this._endRound("empty_arena");
    }
    if (teamKeys.length === 1 && active.length > 0) {
      return this._endRound("last_standing");
    }
    return false;
  }

  _endRound(endKind = "manual") {
    if (this.phase !== "running") return this.getSnapshot();
    this._clearGatherTimer();
    if (this.entities.length && (this.gatherEverReady || this._gatherRequirementsMet())) {
      this._pickWinner();
    } else {
      this.lastWinner = null;
    }
    this.phase = "idle";
    this.roundPhase = null;
    this.roundStartedAt = null;
    this.chaosStartedAt = null;
    this.shockWaveAt = null;
    this.chaosSpawnWindowUntil = 0;
    this.chaosSpawnWindowLastAt = 0;
    const snap = this.getSnapshot();
    this._emitState();
    this.onPersist();
    this.onRoundEnd({ ...snap, endKind });
    return snap;
  }

  getActiveCountsByTeam() {
    const counts = {};
    for (const e of this.entities) {
      if (e.eliminated) continue;
      counts[e.teamCode] = (counts[e.teamCode] || 0) + 1;
    }
    return counts;
  }

  reset() {
    this._clearGatherTimer();
    this.phase = "idle";
    this.round = 0;
    this.roundPhase = null;
    this.roundStartedAt = null;
    this.chaosStartedAt = null;
    this.chaosTriggerReason = null;
    this.shockWaveAt = null;
    this.gatherExtendedMs = 0;
    this.gatherBlockedReason = null;
    this.gatherEverReady = false;
    this.entities = [];
    this.recentSpawns = [];
    this.teamCounts = {};
    this.stats = { spawns: 0, unmatched: 0, rejected: 0 };
    this.lastWinner = null;
    this._channelLastSpawn.clear();
    this._processedIds.clear();
    this.viewerCounts = {};
    this.activityLog = [];
    this.ctaPulses = {};
    this.chaosSpawnWindowUntil = 0;
    this.chaosSpawnWindowLastAt = 0;
    this._emitState();
    this.onPersist();
    return this.getSnapshot();
  }

  updateSettings(partial) {
    this.settings = normalizeRaceSettings({ ...this.settings, ...partial });
    if (this.isGathering()) this._scheduleGatherTimer();
    this._emitState();
    this.onPersist();
    return this.settings;
  }

  handleChatMessage(msg) {
    if (msg?.id && this._processedIds.has(msg.id)) {
      return { type: "ignored", reason: "duplicate" };
    }
    if (msg?.id) {
      this._processedIds.add(msg.id);
      if (this._processedIds.size > 12_000) {
        this._processedIds = new Set([...this._processedIds].slice(-6000));
      }
    }

    const author = String(msg.author || "İzleyici").trim() || "İzleyici";
    const simulated =
      Boolean(msg.simulated) ||
      String(msg.channelId || "").startsWith("sim:");
    const ctaHits = this._pulseYoutubeCtas(msg.text, author);
    if (ctaHits.length) {
      for (const key of ctaHits) {
        this._recordActivity({
          author,
          text: msg.text,
          type: "cta",
          teamCode: key,
          teamName: this.getArenaCtas()[key]?.label || key,
        });
      }
      this._emitState();
    }

    if (!this.isRunning()) {
      if (ctaHits.length) return { type: "cta", hits: ctaHits };
      return { type: "ignored", reason: "not_running" };
    }

    const teamCode = resolveTeamFromText(msg.text);
    // Top 5: tur boyunca her sohbet satırı (takım yazsa da yazmasa da) sayılır.
    if (teamCode) {
      this._bumpViewer(author, teamCode, teamDisplayName(teamCode), { simulated });
    } else {
      this._bumpViewer(author, null, null, { simulated });
    }

    if (!teamCode) {
      this.stats.unmatched += 1;
      this._recordActivity({
        author,
        text: String(msg.text || "").slice(0, 80),
        type: "unmatched",
      });
      this._emitState();
      return { type: "unmatched", text: msg.text };
    }
    const teamName = teamDisplayName(teamCode);
    // Kaosta varsayılan kilit; windowed politikada kısa süreli kontrollü açılır.
    if (this.isChaos()) {
      const open = this._maybeOpenChaosSpawnWindow();
      if (!open && !this._isChaosSpawnWindowOpen()) {
        this._emitState();
        return { type: "chaos_locked", teamCode };
      }
      this._emitState();
    }

    const channelId = msg.channelId || msg.author || "anon";
    const now = Date.now();
    const lastAt = this._channelLastSpawn.get(channelId) || 0;
    const cooldownMs = this.isChaos()
      ? this.settings.chaosSpawnCooldownMs
      : this.isGathering()
        ? Math.max(10_000, this.settings.gatherRepeatCooldownMs || 0)
        : this.settings.spawnCooldownMs;
    if (now - lastAt < cooldownMs) {
      this.stats.rejected += 1;
      this._emitState();
      return { type: "cooldown", teamCode, channelId };
    }

    if (this.entities.length >= this.settings.maxEntities) {
      this.stats.rejected += 1;
      this._emitState();
      return { type: "limit", teamCode };
    }

    if (this.isGathering() && this.settings.maxPerChannel > 0) {
      const activeForChannel = this.entities.filter(
        (e) => e.channelId === channelId && !e.eliminated
      ).length;
      if (activeForChannel >= this.settings.maxPerChannel) {
        this.stats.rejected += 1;
        this._emitState();
        return { type: "channel_limit", teamCode };
      }
    }

    const entity = {
      id: randomBytes(6).toString("hex"),
      teamCode,
      teamName: teamDisplayName(teamCode),
      flagUrl: flagUrlForTeam(teamCode),
      channelId,
      simulated,
      displayName: String(msg.author || "İzleyici").trim() || "İzleyici",
      avatarUrl: msg.avatarUrl || null,
      text: String(msg.text || "").trim(),
      spawnedAt: new Date().toISOString(),
      eliminated: false,
    };

    this.entities.push(entity);
    this.teamCounts[teamCode] = (this.teamCounts[teamCode] || 0) + 1;
    this.stats.spawns += 1;
    this._channelLastSpawn.set(channelId, now);

    this.recentSpawns.unshift({
      id: entity.id,
      teamCode,
      teamName: entity.teamName,
      flagUrl: entity.flagUrl,
      displayName: entity.displayName,
      avatarUrl: entity.avatarUrl,
      at: entity.spawnedAt,
    });
    if (this.recentSpawns.length > this.settings.maxRecentSpawns) {
      this.recentSpawns.length = this.settings.maxRecentSpawns;
    }

    this._recordActivity({
      author: entity.displayName,
      teamCode,
      teamName: entity.teamName,
      type: "spawn",
    });

    this._markGatherReadyIfMet();

    this._emitState();
    this.onSpawn(entity);
    this.onPersist();

    if (this.isGathering()) {
      if (!this._gatherRequirementsMet()) {
        const { missing } = this.getGatherReadiness();
        this.gatherBlockedReason = formatGatherBlockedReason(missing);
      }
      this.checkGatheringProgress();
    }

    return { type: "spawn", entity };
  }

  _pickWinner() {
    const active = this.getActiveCountsByTeam();
    const teams = Object.keys(active);
    if (teams.length === 1) {
      const code = teams[0];
      this.lastWinner = {
        teamCode: code,
        teamName: teamDisplayName(code),
        flagUrl: flagUrlForTeam(code),
        round: this.round,
        spawnCount: active[code],
        winReason: "last_standing",
        at: new Date().toISOString(),
      };
      return;
    }
    if (teams.length > 1) {
      let bestCode = null;
      let best = 0;
      for (const [code, n] of Object.entries(active)) {
        if (n > best) {
          best = n;
          bestCode = code;
        }
      }
      if (bestCode) {
        this.lastWinner = {
          teamCode: bestCode,
          teamName: teamDisplayName(bestCode),
          flagUrl: flagUrlForTeam(bestCode),
          round: this.round,
          spawnCount: best,
          winReason: "most_on_arena",
          at: new Date().toISOString(),
        };
        return;
      }
    }
    this._pickWinnerFromCounts();
  }

  _pickWinnerFromCounts() {
    let bestCode = null;
    let bestCount = 0;
    for (const [code, count] of Object.entries(this.teamCounts)) {
      if (count > bestCount) {
        bestCount = count;
        bestCode = code;
      }
    }
    if (!bestCode || bestCount === 0) return;
    this.lastWinner = {
      teamCode: bestCode,
      teamName: teamDisplayName(bestCode),
      flagUrl: flagUrlForTeam(bestCode),
      round: this.round,
      spawnCount: bestCount,
      winReason: "most_spawns",
      at: new Date().toISOString(),
    };
  }

  _emitState() {
    this.onStateChange(this.getSnapshot());
  }

  serializeState() {
    return {
      phase: this.phase,
      round: this.round,
      roundPhase: this.roundPhase,
      roundStartedAt: this.roundStartedAt,
      chaosStartedAt: this.chaosStartedAt,
      chaosTriggerReason: this.chaosTriggerReason,
      shockWaveAt: this.shockWaveAt,
      chaosSpawnWindowUntil: this.chaosSpawnWindowUntil,
      chaosSpawnWindowLastAt: this.chaosSpawnWindowLastAt,
      gatherExtendedMs: this.gatherExtendedMs,
      gatherBlockedReason: this.gatherBlockedReason,
      gatherEverReady: this.gatherEverReady,
      settings: this.settings,
      entities: this.entities,
      recentSpawns: this.recentSpawns,
      teamCounts: this.teamCounts,
      stats: this.stats,
      lastWinner: this.lastWinner,
      channelLastSpawn: [...this._channelLastSpawn.entries()],
      viewerCounts: this.viewerCounts,
      activityLog: this.activityLog,
      ctaPulses: this.ctaPulses,
    };
  }

  restoreState(data) {
    if (!data || typeof data !== "object") return;
    this._clearGatherTimer();
    this.phase = data.phase || "idle";
    this.round = Number(data.round) || 0;
    this.roundPhase = data.roundPhase || null;
    this.roundStartedAt = data.roundStartedAt || null;
    this.chaosStartedAt = data.chaosStartedAt || null;
    this.chaosTriggerReason = data.chaosTriggerReason || null;
    this.shockWaveAt = data.shockWaveAt || null;
    this.chaosSpawnWindowUntil = Number(data.chaosSpawnWindowUntil) || 0;
    this.chaosSpawnWindowLastAt = Number(data.chaosSpawnWindowLastAt) || 0;
    this.gatherExtendedMs = Number(data.gatherExtendedMs) || 0;
    this.gatherBlockedReason = data.gatherBlockedReason || null;
    this.gatherEverReady = Boolean(data.gatherEverReady);
    this.settings = normalizeRaceSettings(data.settings);
    this.entities = Array.isArray(data.entities) ? data.entities : [];
    this.recentSpawns = Array.isArray(data.recentSpawns) ? data.recentSpawns : [];
    this.teamCounts =
      data.teamCounts && typeof data.teamCounts === "object" ? data.teamCounts : {};
    this.stats = { ...this.stats, ...data.stats };
    this.lastWinner = data.lastWinner || null;
    this._channelLastSpawn = new Map(data.channelLastSpawn || []);
    this.viewerCounts =
      data.viewerCounts && typeof data.viewerCounts === "object" ? data.viewerCounts : {};
    this.activityLog = Array.isArray(data.activityLog) ? data.activityLog : [];
    this.ctaPulses =
      data.ctaPulses && typeof data.ctaPulses === "object" ? data.ctaPulses : {};
    if (this.isGathering()) this._scheduleGatherTimer();
  }
}
