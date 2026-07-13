import { isTeamRaceMode } from "../gameModes.js";
import {
  buildSimulatedChatMessage,
  pickSimIntervalMs,
  shouldSimulateAudience,
} from "./audienceSimulator.js";
import { canStartRaceRound, getRaceSeriesStatus, normalizeRaceSettings } from "./raceModes.js";

/**
 * Yayın otomasyonu: Başlat sonrası tur döngüsü, kaos geçişi ve yeniden deneme.
 * Kullanıcı yalnızca bir kez "Başlat" der; geri kalanı sohbet + kurallara göre ilerler.
 */
export class RaceAutopilot {
  /**
   * @param {object} room
   * @param {import("../rooms.js").RoomManager} roomManager
   */
  constructor(room, roomManager) {
    this.room = room;
    this.roomManager = roomManager;
    this.tickTimer = null;
    this.scheduledTimer = null;
    this.statusMessage = "Hazır — Başlat ile otomatik yayın açılır";
    this.lastSpawnAt = 0;
    this._lastAudienceSimAt = 0;
    this._nextAudienceSimAt = 0;
  }

  get settings() {
    return normalizeRaceSettings(this.room.config?.raceSettings || {});
  }

  isEnabled() {
    return this.settings.autopilot !== false;
  }

  getPublicStatus() {
    const engine = this.room.teamRace;
    return {
      enabled: this.isEnabled(),
      armed: Boolean(this.room.autopilotArmed),
      statusMessage: this.statusMessage,
      running: engine?.isRunning?.() ?? false,
      phase: engine?.getSnapshot?.()?.phase ?? "idle",
    };
  }

  arm() {
    this.room.autopilotArmed = true;
    if (this.isEnabled()) {
      this.statusMessage = "Otomatik mod aktif — turlar kendi kendine ilerler";
      this.startTick();
    }
  }

  disarm() {
    this.room.autopilotArmed = false;
    this.stopTick();
    this.clearScheduled();
    this.statusMessage = "Otomatik mod kapalı";
  }

  startTick() {
    this.stopTick();
    if (!this.isEnabled() || !this.room.autopilotArmed) return;
    const ms = Math.max(2000, Number(this.settings.autopilotTickMs) || 4000);
    this.tickTimer = setInterval(() => this.tick(), ms);
  }

  stopTick() {
    if (this.tickTimer) {
      clearInterval(this.tickTimer);
      this.tickTimer = null;
    }
  }

  clearScheduled() {
    if (this.scheduledTimer) {
      clearTimeout(this.scheduledTimer);
      this.scheduledTimer = null;
    }
  }

  schedule(fn, delayMs) {
    this.clearScheduled();
    this.scheduledTimer = setTimeout(() => {
      this.scheduledTimer = null;
      fn();
    }, Math.max(1000, delayMs));
  }

  onSpawn(entity) {
    this.lastSpawnAt = Date.now();
    if (entity && !entity.simulated) {
      this.room.lastRealChatAt = Date.now();
    }
  }

  _maybeSimulateAudience() {
    if (!this.isEnabled() || !this.room.autopilotArmed) return;
    const engine = this.room.teamRace;
    if (!engine.isRunning()) return;

    const now = Date.now();
    if (this._nextAudienceSimAt && now < this._nextAudienceSimAt) return;
    if (!shouldSimulateAudience(engine, this.settings, this.room.lastRealChatAt || 0)) {
      return;
    }

    this._lastAudienceSimAt = now;
    this._nextAudienceSimAt = now + pickSimIntervalMs(this.settings);

    const msg = buildSimulatedChatMessage();
    const result = engine.handleChatMessage(msg);
    if (result?.type === "spawn") {
      this.onSpawn(result.entity);
      this.roomManager.io.to(this.room.id).emit("race:spawn", result.entity);
    }
    this.roomManager.io.to(this.room.id).emit("race:state", this.roomManager._raceStatePayload(this.room));

    const eng = engine.getEngagement();
    if ((eng.realParticipants ?? 0) === 0) {
      this.statusMessage = `Sohbet simülasyonu — ${msg.author} yazdı (sessiz yayın)`;
    }
  }

  onYoutubeConnected() {
    if (!this.isEnabled() || !this.settings.autoStartOnConnect) return;
    this.arm();
    this.statusMessage = "YouTube bağlandı — ilk tur hazırlanıyor…";
    const delay = Number(this.settings.autoStartDelayMs) || 3000;
    this.schedule(() => this.tryStartRound("youtube"), delay);
  }

  onRoundEnd(snap) {
    if (!this.isEnabled() || !this.room.autopilotArmed) return;
    const series = getRaceSeriesStatus(this.settings, this.room.raceRoundHistory);
    if (series.seriesComplete) {
      this.statusMessage = `Seri bitti (${series.completedRounds}/${series.maxRounds} tur) — kazananlar solda`;
      return;
    }
    const w = snap?.lastWinner;
    if (w) {
      const nextNo = series.completedRounds + 1;
      this.statusMessage = `${w.teamName} kazandı — tur ${nextNo}/${series.maxRounds} yakında`;
      const delay = Number(this.settings.autoNextRoundMs) || 12_000;
      this.schedule(() => this.tryStartRound("next_round"), delay);
    } else {
      this.statusMessage = "Yeterli etkileşim yok — tur yeniden denenecek";
      const delay = Number(this.settings.autoRetryRoundMs) || 45_000;
      this.schedule(() => this.tryStartRound("retry"), delay);
    }
  }

  tryStartRound(reason) {
    const room = this.room;
    const rm = this.roomManager;
    if (!this.room.autopilotArmed || !this.isEnabled()) return false;
    if (!isTeamRaceMode(room.config.gameMode)) return false;
    if (room.teamRace.isRunning()) return false;

    if (!canStartRaceRound(this.settings, room.raceRoundHistory)) {
      const series = getRaceSeriesStatus(this.settings, room.raceRoundHistory);
      this.statusMessage = `Seri tamamlandı (${series.completedRounds}/${series.maxRounds} tur)`;
      return false;
    }

    if (this.settings.requireYoutubeForAutostart !== false && !room.youtubeChatConnected) {
      this.statusMessage = "YouTube sohbeti bekleniyor — bağlanınca tur otomatik başlar";
      return false;
    }

    rm.wireChat(room);
    if (room.config.raceSettings) {
      room.teamRace.updateSettings(room.config.raceSettings);
    }
    const snap = room.teamRace.start();
    this.lastSpawnAt = 0;
    this.statusMessage =
      reason === "next_round"
        ? `Tur ${snap.round} — toplanma fazı (otomatik)`
        : reason === "retry"
          ? `Tur ${snap.round} — yeniden deneme (otomatik)`
          : `Tur ${snap.round} başladı (otomatik)`;

    rm.appendRoomLog(
      room.id,
      `🤖 Otomatik tur #${snap.round} başladı${reason ? ` (${reason})` : ""}`,
      { highlight: true, kind: "system" }
    );
    rm.io.to(room.id).emit("race:state", rm._raceStatePayload(room));
    return true;
  }

  tick() {
    const room = this.room;
    if (!this.isEnabled() || !room.autopilotArmed) return;
    if (!isTeamRaceMode(room.config.gameMode)) return;

    const engine = room.teamRace;
    const snap = engine.getSnapshot();

    if (snap.phase === "running") {
      this._maybeSimulateAudience();
    }

    if (snap.phase === "idle") {
      if (this.scheduledTimer) return;
      if (room.youtubeChatConnected || this.settings.requireYoutubeForAutostart === false) {
        this.tryStartRound("watchdog");
      }
      return;
    }

    if (snap.phase !== "running" || snap.roundPhase !== "gathering") return;

    const req = snap.gatherRequirements || {};
    const eng = snap.engagement || {};

    if (!req.met) {
      if (this._gatherExtensionExhausted(snap) && (eng.spawns ?? 0) === 0) {
        this.statusMessage = "Sohbet sessiz — tur iptal, yeniden denenecek";
        engine.stop();
        this.roomManager.io.to(room.id).emit("race:state", this.roomManager._raceStatePayload(room));
        this.onRoundEnd({ ...snap, lastWinner: null, endKind: "no_engagement" });
      } else {
        this.statusMessage =
          snap.gatherBlockedReason ||
          `Toplanma — katılım bekleniyor (${eng.participants ?? 0}/${req.minParticipants} kişi)`;
      }
      return;
    }

    if (engine.checkGatheringProgress()) {
      this.statusMessage = "Kaos başladı (otomatik)";
      this.roomManager.io.to(room.id).emit("race:state", this.roomManager._raceStatePayload(room));
      return;
    }

    const remaining = snap.gatherRemainingMs ?? 0;
    const minRemain = snap.gatherMinRemainingMs ?? remaining;
    const poolFull = (snap.entityCount ?? 0) >= (snap.settings?.chaosMinEntities ?? 8);
    const earlyMs = Number(this.settings.earlyChaosRemainingMs) || 0;
    const timeAlmostUp = earlyMs > 0 && remaining > 0 && remaining <= earlyMs;

    if (req.met) {
      if (remaining <= 0 && minRemain <= 0) {
        this.statusMessage = "Süre doldu — kaosa geçiliyor…";
      } else if (poolFull && minRemain <= 0) {
        this.statusMessage = "Havuz doldu — kaos başlıyor…";
      } else if (poolFull) {
        this.statusMessage = `Havuz doldu — kaos için ${Math.ceil(minRemain / 1000)} sn`;
      } else if (timeAlmostUp) {
        this.statusMessage = "Süre bitiyor — kaos hazırlanıyor…";
      } else {
        const sec = Math.ceil(Math.max(minRemain, remaining) / 1000);
        this.statusMessage = `Toplanma ${sec} sn — katılım tamam`;
      }
    }
  }

  _gatherExtensionExhausted(snap) {
    const extra = Number(snap.gatherExtendedMs) || 0;
    const max = Number(snap.settings?.gatherMaxExtraMs) || 0;
    return max > 0 && extra >= max;
  }
}
