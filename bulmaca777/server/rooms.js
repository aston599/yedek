import {
  mkdirSync,
  existsSync,
  readFileSync,
  writeFileSync,
  cpSync,
  readdirSync,
  unlinkSync,
  rmSync,
} from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { randomBytes } from "crypto";
import { GameEngine } from "./game.js";
import { MockChatService } from "./youtube.js";
import { InnerYouTubeChatService } from "./innerChat.js";
import { roomRepo, getDb, raceRepo } from "./db.js";
import { createRoomLogger } from "./room-log.js";
import { auditRecord } from "./auditLog.js";
import {
  normalizeGameMode,
  gameModeLabel,
  isTeamRaceMode,
  isPhotoBattleMode,
  isFootballMode,
  roomUsesPuzzleEngine,
  photoRoomRunsCelebrityAge,
} from "./gameModes.js";
import { isCelebrityAgeQuiz } from "./celebrityImport.js";
import { PhotoBattleEngine } from "./photoBattle/engine.js";
import {
  loadPhotoPool,
  addPhotoFromBase64,
  removePhotoFromPool,
  clearPhotoPool,
} from "./photoBattle/poolStore.js";
import { normalizePhotoBattleSettings } from "./photoBattle/settings.js";
import { TeamRaceEngine } from "./teamRace/engine.js";
import {
  canStartRaceRound,
  getRaceSeriesStatus,
  normalizeRaceSettings,
} from "./teamRace/raceModes.js";
import { RaceAutopilot } from "./teamRace/raceAutopilot.js";
import {
  formatBotMessage,
  buildPingMessage,
  buildGameStartedChatMessage,
} from "./bot.js";
import {
  parseYouTubeVideoIds,
  normalizeStreamUrlDraft,
  resolveYoutubeAnnounceGameStart,
  resolveYoutubePollInWinner,
  resolveYoutubeChatStayConnected,
} from "./utils.js";

function isYoutubeRoomChat(chat) {
  return chat instanceof InnerYouTubeChatService;
}

/** Geçici InnerChat debug — panelde ham sohbet satırları */
const INNER_CHAT_TAP_MAX = 100;

function innerChatTapEnabled() {
  const raw = String(process.env.INNER_CHAT_TAP ?? "1").toLowerCase();
  return !["0", "false", "off", "no"].includes(raw);
}

function innerChatDebugEnabled() {
  const raw = String(process.env.INNER_CHAT_DEBUG ?? "0").toLowerCase();
  return ["1", "true", "on", "yes"].includes(raw);
}

const innerChatPollAuditLast = new Map();

function innerChatDebugLog(roomId, ...parts) {
  if (!innerChatDebugEnabled()) return;
  const msg = parts.join(" ");
  const isPollHeartbeat =
    msg.includes("pollingMode=live") && !msg.includes("reconcile");
  if (isPollHeartbeat) {
    const now = Date.now();
    const last = innerChatPollAuditLast.get(roomId) || 0;
    if (now - last < 60_000) {
      return;
    }
    innerChatPollAuditLast.set(roomId, now);
  }
  console.log(`[InnerChat ${roomId}]`, msg);
  auditRecord({
    roomId,
    category: "youtube",
    level: "debug",
    message: msg,
  });
}

function humanizeChatListenHint(hint = "") {
  const h = String(hint || "");
  if (/API Key was not found/i.test(h)) {
    return "Sohbet anahtarı okunamadı — yayın gerçekten CANLI mı? (bekleme odası / henüz başlamadı / VPS sayfa kısıtı)";
  }
  if (/consent page/i.test(h)) {
    return "YouTube onay sayfası — sunucu cookie akışını deniyor; birkaç saniye bekleyin";
  }
  if (/finished live|is finished live|not live|offline/i.test(h)) {
    return "Yayın canlı değil veya sohbet henüz açılmadı";
  }
  if (/Continuation was not found/i.test(h)) {
    return "Canlı sohbet henüz yok — yayını başlatın veya birkaç dakika bekleyin";
  }
  if (/bot or network block|Watch page incomplete/i.test(h)) {
    return "VPS IP YouTube tarafından kısıtlı — .env: YOUTUBE_HTTP_PROXY veya tarayıcı cookie (YOUTUBE_CONSENT_COOKIE)";
  }
  return h.slice(0, 200);
}

function parseVideoIdsField(value) {
  const raw = String(value || "").trim();
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function videoIdsToField(videoIds = []) {
  return [...new Set((videoIds || []).map((v) => String(v || "").trim()).filter(Boolean))].join(",");
}

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_ROOT = join(__dirname, "..", "data");
const ROOMS_ROOT = join(DATA_ROOT, "rooms");
const DEFAULT_QUESTIONS = join(DATA_ROOT, "questions.json");
const DEFAULT_LAYOUT_VERTICAL = join(
  __dirname,
  "..",
  "public",
  "overlay",
  "layout.vertical.json"
);

function sameUserId(a, b) {
  if (a == null || b == null) return false;
  return Number(a) === Number(b);
}

function parseRaceSettingsJson(raw) {
  if (!raw) return null;
  try {
    return normalizeRaceSettings(JSON.parse(raw));
  } catch {
    return null;
  }
}

function rowToConfig(row) {
  const fromDb = parseRaceSettingsJson(row?.race_settings_json);
  const videoIds = parseVideoIdsField(row.video_id || "");
  let photoBattleSettings = {};
  if (row?.photo_battle_settings_json) {
    try {
      photoBattleSettings = normalizePhotoBattleSettings(
        JSON.parse(row.photo_battle_settings_json)
      );
    } catch {
      photoBattleSettings = {};
    }
  }
  let streamUrlDraft = normalizeStreamUrlDraft(row?.stream_url_draft || "");
  if (!streamUrlDraft && videoIds.length) {
    streamUrlDraft = videoIds
      .map((id) => `https://www.youtube.com/watch?v=${id}`)
      .join("\n");
  }
  return {
    gameMode: normalizeGameMode(row?.game_mode),
    videoId: videoIds[0] || "",
    videoIds,
    liveChatId: row.live_chat_id || "",
    botName: row.bot_name || "YouTube Bulmacalari",
    announceWrong: Boolean(row.announce_wrong),
    winMessage: row.win_message || null,
    wrongMessage: row.wrong_message || null,
    raceSettings: fromDb || {},
    photoBattleSettings,
    streamUrlDraft,
  };
}

function configWithDefaults(partial = {}) {
  const videoIds = Array.isArray(partial.videoIds)
    ? [...new Set(partial.videoIds.map((v) => String(v || "").trim()).filter(Boolean))]
    : parseVideoIdsField(partial.videoId || "");
  return {
    gameMode: normalizeGameMode(partial.gameMode),
    videoId: videoIds[0] || "",
    videoIds,
    liveChatId: partial.liveChatId || "",
    botName: partial.botName || "YouTube Bulmacalari",
    announceWrong: Boolean(partial.announceWrong),
    winMessage: partial.winMessage ?? null,
    wrongMessage: partial.wrongMessage ?? null,
    raceSettings: normalizeRaceSettings(partial.raceSettings || {}),
    photoBattleSettings: normalizePhotoBattleSettings(partial.photoBattleSettings || {}),
    streamUrlDraft: normalizeStreamUrlDraft(partial.streamUrlDraft),
  };
}

export class RoomManager {
  constructor({ io, chatMode, gameDefaults }) {
    this.io = io;
    this.chatMode = chatMode;
    this.gameDefaults = gameDefaults;
    this.rooms = new Map();
    /** Kullanıcı başına tek canlı sohbet poll (çok oda = kota çarpanı önlenir) */
    this._userLivePollRoomId = new Map();
    this.appendRoomLog = createRoomLogger(io);

    mkdirSync(ROOMS_ROOT, { recursive: true });
    getDb();
    this._loadRoomsFromDb();
    this._loadLegacyFileRooms();

    const keepaliveMs = Math.max(
      20_000,
      Number(process.env.YOUTUBE_CHAT_KEEPALIVE_MS) || 45_000
    );
    this._chatKeepaliveTimer = setInterval(() => {
      for (const room of this.rooms.values()) {
        try {
          this._reconcileYoutubeChatListen(room);
        } catch (err) {
          console.warn(`[${room.id} chat keepalive]`, err?.message || err);
        }
      }
    }, keepaliveMs);
    if (this._chatKeepaliveTimer?.unref) {
      this._chatKeepaliveTimer.unref();
    }
  }

  _roomDir(roomId) {
    return join(ROOMS_ROOT, roomId);
  }

  _readJson(path, fallback) {
    if (!existsSync(path)) return fallback;
    try {
      return JSON.parse(readFileSync(path, "utf-8"));
    } catch {
      return fallback;
    }
  }

  _writeJson(path, data) {
    writeFileSync(path, JSON.stringify(data, null, 2), "utf-8");
  }

  _loadRoomsFromDb() {
    const rows = getDb().prepare("SELECT * FROM rooms").all();
    for (const row of rows) {
      this._bootstrapRoom(row.id, {
        id: row.id,
        name: row.name,
        userId: row.user_id,
        createdAt: row.created_at,
        config: rowToConfig(row),
        questionsJson: row.questions_json,
        gameStateJson: row.game_state_json,
      });
    }
  }

  _loadLegacyFileRooms() {
    if (!existsSync(ROOMS_ROOT)) return;
    for (const ent of readdirSync(ROOMS_ROOT, { withFileTypes: true })) {
      if (!ent.isDirectory() || this.rooms.has(ent.name)) continue;
      const meta = this._readJson(join(ROOMS_ROOT, ent.name, "meta.json"), null);
      if (!meta) continue;
      const config = this._readJson(this._configPath(ent.name), {});
      this._bootstrapRoom(ent.name, {
        id: ent.name,
        name: meta.name || ent.name,
        userId: meta.userId ?? null,
        createdAt: meta.createdAt,
        config: configWithDefaults({
          ...config,
          botName: config.botName || "BulmacaBot",
          announceWrong: config.announceWrong === true,
        }),
      });
    }
  }

  listRooms(userId = null) {
    const list = [...this.rooms.values()];
    const filtered = userId
      ? list.filter((r) => r.userId == null || sameUserId(r.userId, userId))
      : list;
    return filtered.map((r) => {
      const snap = r.game.getSnapshot();
      const yt = this._getRoomYouTubeListMeta(r);
      const raceSnap = r.teamRace?.getSnapshot?.();
      return {
        id: r.id,
        name: r.name,
        displayName: r.name,
        userId: r.userId,
        botName: r.config.botName,
        createdAt: r.createdAt,
      videoId: r.config.videoId || null,
      videoIds: r.config.videoIds || (r.config.videoId ? [r.config.videoId] : []),
        gameMode: r.config.gameMode,
        gameModeLabel: gameModeLabel(r.config.gameMode),
        youtubeConnected: yt.chatConnected,
        gameState: isTeamRaceMode(r.config.gameMode)
          ? raceSnap?.phase === "running"
            ? "active"
            : raceSnap?.phase || "idle"
          : isPhotoBattleMode(r.config.gameMode) && !roomUsesPuzzleEngine(r)
            ? r.photoBattle?.isRunning?.()
              ? "active"
              : r.photoBattle?.phase === "champion"
                ? "winner"
                : "idle"
            : snap.state,
        youtube: yt,
        race: raceSnap || null,
      };
    });
  }

  _getRoomYouTubeListMeta(room) {
    return {
      chatConnected: Boolean(room.youtubeChatConnected),
    };
  }

  createRoom(name, userId, options = {}) {
    if (!userId) {
      const err = new Error("Giriş gerekli");
      err.status = 401;
      throw err;
    }

    const id = randomBytes(4).toString("hex");
    let questionsJson = "[]";
    if (existsSync(DEFAULT_QUESTIONS)) {
      questionsJson = readFileSync(DEFAULT_QUESTIONS, "utf-8");
    }

    const botName = "YouTube Bulmacalari";
    const gameMode = normalizeGameMode(options.gameMode);
    roomRepo.create({
      id,
      userId,
      name: name.trim() || "Yayin",
      botName,
      winMessage: this.gameDefaults.winMessageTemplate ?? null,
      wrongMessage: "{user}, bu cevap dogru degil!",
      questionsJson,
    });
    roomRepo.update(id, { game_mode: gameMode });

    const room = this._bootstrapRoom(id, {
      id,
      name: name.trim() || "Yayin",
      userId,
      createdAt: new Date().toISOString(),
      config: configWithDefaults({
        gameMode,
        botName,
        announceWrong: false,
        winMessage: this.gameDefaults.winMessageTemplate ?? null,
        wrongMessage: null,
      }),
      questionsJson,
      isNew: true,
    });
    this._ensureNewRoomYouTubeIsolated(id);
    return room;
  }

  /**
   * Odayı kopyala: sorular + bot ayarları; YouTube OAuth, video/link ve oyun durumu kopyalanmaz.
   */
  copyRoom(sourceRoomId, userId, name) {
    const source = this.assertRoomOwner(sourceRoomId, userId);
    const sourceRow = roomRepo.findById(sourceRoomId);

    let questionsJson = sourceRow?.questions_json;
    if (!questionsJson || questionsJson === "[]") {
      const qPath = this._questionsPath(sourceRoomId);
      if (existsSync(qPath)) {
        questionsJson = readFileSync(qPath, "utf-8");
      }
    }
    if (!questionsJson) {
      questionsJson = source.game.getQuestionsJson?.() || "[]";
    }

    const baseLabel = (source.name || sourceRoomId).trim();
    const newName = (name || `${baseLabel} (kopya)`).trim() || "Yayin kopya";
    const id = randomBytes(4).toString("hex");

    const config = configWithDefaults({
      gameMode: source.config.gameMode,
      videoId: "",
      liveChatId: "",
      botName: source.config.botName || "YouTube Bulmacalari",
      announceWrong: Boolean(source.config.announceWrong),
      winMessage: source.config.winMessage ?? null,
      wrongMessage: source.config.wrongMessage ?? null,
    });

    roomRepo.create({
      id,
      userId,
      name: newName,
      botName: config.botName,
      winMessage: config.winMessage,
      wrongMessage: config.wrongMessage,
      questionsJson,
    });

    roomRepo.update(id, {
      video_id: "",
      live_chat_id: "",
      game_mode: config.gameMode,
      announce_wrong: sourceRow?.announce_wrong ?? (config.announceWrong ? 1 : 0),
    });
    roomRepo.updateGameState(id, null);

    const room = this._bootstrapRoom(id, {
      id,
      name: newName,
      userId,
      createdAt: new Date().toISOString(),
      config,
      questionsJson,
      isNew: false,
    });

    this._ensureNewRoomYouTubeIsolated(id);

    const srcLayout = this._layoutPath(sourceRoomId);
    const dstLayout = this._layoutPath(id);
    if (existsSync(srcLayout)) {
      try {
        cpSync(srcLayout, dstLayout);
      } catch (err) {
        console.error(`[${id} layout copy]`, err.message);
      }
    }

    this.appendRoomLog(
      id,
      `Oda «${baseLabel}» kopyasından oluşturuldu (YouTube bağlantısı yok).`,
      { kind: "system", highlight: true }
    );

    return { room, sourceId: sourceRoomId };
  }

  /** Yeni oda: önceki klasör artıkları veya bellekte kalan YouTube verisi kalmasın */
  _ensureNewRoomYouTubeIsolated(roomId) {
    const room = this.rooms.get(roomId);
    if (!room) return;

    if (room.chat instanceof InnerYouTubeChatService) {
      room.chat.setVideoIds([]);
      room.chat.liveChatId = null;
    }

    room.config.videoId = "";
    room.config.videoIds = [];
    room.config.liveChatId = "";
    room.youtubeChatConnected = false;
    room.chatPolling = false;

    if (room.userId && roomRepo.findById(roomId)) {
      roomRepo.update(roomId, { video_id: "", live_chat_id: "" });
    }

    const cfgPath = this._configPath(roomId);
    if (existsSync(cfgPath)) {
      try {
        unlinkSync(cfgPath);
      } catch {
        /* yoksay */
      }
    }
  }

  _persistRoomOwner(roomId, userId) {
    const row = roomRepo.findById(roomId);
    if (row) {
      getDb().prepare("UPDATE rooms SET user_id = ? WHERE id = ?").run(userId, roomId);
      return;
    }
    const metaPath = join(this._roomDir(roomId), "meta.json");
    const meta = this._readJson(metaPath, { id: roomId, name: roomId });
    meta.userId = userId;
    this._writeJson(metaPath, meta);
  }

  /** Dosyadan yüklenen odalar SQLite'da yoksa günlük INSERT'i FK ile düşer */
  _ensureRoomInDb(room) {
    if (!room?.id || roomRepo.findById(room.id)) return;
    if (!room.userId) return;
    try {
      roomRepo.create({
        id: room.id,
        userId: room.userId,
        name: room.name,
        botName: room.config.botName,
        winMessage: room.config.winMessage,
        wrongMessage: room.config.wrongMessage,
        questionsJson: room.game.getQuestionsJson(),
      });
      roomRepo.update(room.id, {
        video_id: videoIdsToField(room.config.videoIds || (room.config.videoId ? [room.config.videoId] : [])),
        live_chat_id: room.config.liveChatId || "",
      });
    } catch (err) {
      if (!String(err.message).includes("UNIQUE")) throw err;
    }
  }

  /** Giriş yapmış kullanıcı: sahipsiz odayı devralır; başkasının odasına 403 */
  ensureRoomAccess(roomId, userId) {
    if (userId == null) {
      const err = new Error("Giriş gerekli");
      err.status = 401;
      throw err;
    }
    const room = this.getRoomOrThrow(roomId);
    const uid = Number(userId);

    if (room.userId == null) {
      room.userId = uid;
      this._persistRoomOwner(roomId, uid);
      this._ensureRoomInDb(room);
      return room;
    }

    this._ensureRoomInDb(room);

    if (!sameUserId(room.userId, uid)) {
      const err = new Error(
        "Bu yayın başka bir hesaba ait. Üstten kendi yayınınızı seçin veya yeni yayın oluşturun."
      );
      err.status = 403;
      throw err;
    }

    return room;
  }

  assertRoomOwner(roomId, userId) {
    return this.ensureRoomAccess(roomId, userId);
  }

  deleteRoom(roomId, userId) {
    this.assertRoomOwner(roomId, userId);
    const room = this.getRoomOrThrow(roomId);

    room.chat.stopPolling?.();
    room.chatPolling = false;

    if (roomRepo.findById(roomId)) {
      roomRepo.delete(roomId);
    }

    this.rooms.delete(roomId);

    const dir = this._roomDir(roomId);
    if (existsSync(dir)) {
      try {
        rmSync(dir, { recursive: true, force: true });
      } catch (err) {
        console.error(`[${roomId}] oda klasörü silinemedi:`, err.message);
      }
    }

    return { ok: true, id: roomId };
  }

  getRoom(roomId) {
    return this.rooms.get(roomId) ?? null;
  }

  getRoomOrThrow(roomId) {
    const room = this.getRoom(roomId);
    if (!room) {
      const err = new Error("Yayın bulunamadı");
      err.status = 404;
      throw err;
    }
    return room;
  }

  updateConfig(roomId, patch, userId) {
    this.assertRoomOwner(roomId, userId);
    const room = this.getRoomOrThrow(roomId);
    const dbPatch = {};

    if (patch.videoId !== undefined || patch.videoIds !== undefined) {
      const nextIds = patch.videoIds !== undefined
        ? [...new Set((patch.videoIds || []).map((v) => String(v || "").trim()).filter(Boolean))]
        : parseVideoIdsField(String(patch.videoId || "").trim());
      room.config.videoIds = nextIds;
      room.config.videoId = nextIds[0] || "";
      dbPatch.video_id = videoIdsToField(nextIds);
      if (room.chat instanceof InnerYouTubeChatService) {
        room.chat.setVideoIds(nextIds);
        room.chat.liveChatId = null;
        room.config.liveChatId = "";
      }
    }
    if (patch.liveChatId !== undefined) {
      room.config.liveChatId = String(patch.liveChatId).trim();
      dbPatch.live_chat_id = room.config.liveChatId;
    }
    if (patch.streamUrlDraft !== undefined) {
      room.config.streamUrlDraft = normalizeStreamUrlDraft(patch.streamUrlDraft);
      dbPatch.stream_url_draft = room.config.streamUrlDraft;
    }
    if (patch.botName !== undefined) {
      room.config.botName = String(patch.botName).trim() || "YouTube Bulmacalari";
      dbPatch.bot_name = room.config.botName;
      room.game.setBotSettings({ botName: room.config.botName });
    }
    if (patch.announceWrong !== undefined) {
      room.config.announceWrong = Boolean(patch.announceWrong);
      dbPatch.announce_wrong = room.config.announceWrong ? 1 : 0;
      room.game.setBotSettings({ announceWrong: room.config.announceWrong });
    }
    if (patch.winMessage !== undefined) {
      room.config.winMessage = patch.winMessage;
      dbPatch.win_message = patch.winMessage;
      room.game.setBotSettings({ winMessage: patch.winMessage });
    }
    if (patch.wrongMessage !== undefined) {
      room.config.wrongMessage = patch.wrongMessage;
      dbPatch.wrong_message = patch.wrongMessage;
      room.game.setBotSettings({ wrongMessage: patch.wrongMessage });
    }
    if (patch.raceSettings !== undefined) {
      room.config.raceSettings = normalizeRaceSettings({
        ...room.config.raceSettings,
        ...patch.raceSettings,
      });
      room.teamRace.updateSettings(room.config.raceSettings);
      this._writeJson(this._configPath(roomId), room.config);
      if (room.userId) {
        raceRepo.saveSettings(roomId, room.config.raceSettings);
      }
    }
    if (patch.photoBattleSettings !== undefined) {
      room.config.photoBattleSettings = normalizePhotoBattleSettings({
        ...room.config.photoBattleSettings,
        ...patch.photoBattleSettings,
      });
      room.photoBattle.updateSettings(room.config.photoBattleSettings);
      dbPatch.photo_battle_settings_json = JSON.stringify(room.config.photoBattleSettings);
      this._writeJson(this._configPath(roomId), room.config);
    }
    if (patch.gameMode !== undefined) {
      const prev = room.config.gameMode;
      const next = normalizeGameMode(patch.gameMode);
      if (prev !== next) {
        room.config.gameMode = next;
        dbPatch.game_mode = next;

        const gameSnap = room.game.getSnapshot();
        if (gameSnap.state !== "idle") room.game.stop();
        if (room.teamRace.isRunning()) room.teamRace.stop();
        if (room.photoBattle?.isRunning?.()) room.photoBattle.stop();

        const persistGame = room.game.onPersist;
        const persistRace = room.teamRace.onPersist;
        const persistPhoto = room.photoBattle.onPersist;
        room.game.onPersist = () => {};
        room.teamRace.onPersist = () => {};
        room.photoBattle.onPersist = () => {};
        room.game.reset();
        room.teamRace.reset();
        room.photoBattle.reset();
        room.raceRoundHistory = [];
        if (room.userId) raceRepo.clearRounds(roomId);
        room.game.onPersist = persistGame;
        room.teamRace.onPersist = persistRace;
        room.photoBattle.onPersist = persistPhoto;

        if (room.userId) roomRepo.updateGameState(roomId, null);

        this.io.to(roomId).emit("game:state", room.game.getSnapshot());
        this.io.to(roomId).emit("race:state", this._raceStatePayload(room));
        this.io.to(roomId).emit("photo-battle:state", room.photoBattle.getSnapshot());

        this.appendRoomLog(
          roomId,
          `Oyun modu: ${gameModeLabel(next)} (tur ve skor sıfırlandı)`,
          { kind: "system", highlight: true }
        );
      }
    }

    if (room.userId) roomRepo.update(roomId, dbPatch);
    try {
      this._writeJson(this._configPath(roomId), room.config);
    } catch {
      /* disk yedek */
    }

    if (room.chat instanceof InnerYouTubeChatService) {
      room.chat.setVideoIds(room.config.videoIds || (room.config.videoId ? [room.config.videoId] : []));
      if (patch.liveChatId !== undefined) {
        room.chat.liveChatId = room.config.liveChatId || null;
      }
    }
    if (patch.gameMode !== undefined) {
      this._emitRoomConfig(room);
    }
    auditRecord({
      roomId,
      userId,
      category: "config",
      level: "info",
      message: "config güncellendi",
      detail: { keys: Object.keys(patch || {}) },
    });
    return room.config;
  }

  _readQuestionsFile(roomId) {
    const path = this._questionsPath(roomId);
    if (!existsSync(path)) return [];
    try {
      const parsed = JSON.parse(readFileSync(path, "utf-8"));
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  _readQuestionsDb(room) {
    if (!room?.userId) return [];
    const row = roomRepo.findById(room.id);
    if (!row?.questions_json) return [];
    try {
      const parsed = JSON.parse(row.questions_json);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  /** Dosya + SQLite + bellek — tüm kaynakları birleştirir (en uzun / en güncel liste) */
  _mergeQuestionSources(lists) {
    const map = new Map();
    const order = [];
    for (const list of lists) {
      if (!Array.isArray(list)) continue;
      for (const raw of list) {
        if (!raw || typeof raw !== "object") continue;
        const question = String(raw.question ?? "").trim();
        if (!question) continue;
        const key =
          raw.id != null && String(raw.id).trim()
            ? String(raw.id).trim()
            : `q:${question}`;
        if (!map.has(key)) order.push(key);
        const prev = map.get(key);
        map.set(
          key,
          prev
            ? {
                ...prev,
                ...raw,
                answers: Array.isArray(raw.answers) && raw.answers.length
                  ? raw.answers
                  : prev.answers,
              }
            : raw
        );
      }
    }
    return order.map((k) => map.get(k));
  }

  ensureQuestionsSynced(room) {
    if (!room?.game) return room?.game?.questions?.length ?? 0;

    const fromFile = this._readQuestionsFile(room.id);
    const fromDb = this._readQuestionsDb(room);
    const inMemory = room.game.questions || [];
    const merged = this._mergeQuestionSources([fromFile, fromDb, inMemory]);
    const prevLen = inMemory.length;

    if (!merged.length) return 0;

    const prevJson = JSON.stringify(inMemory);
    const nextJson = JSON.stringify(merged);
    if (merged.length !== prevLen || prevJson !== nextJson) {
      room.game.setQuestions(merged);
      try {
        this.persistQuestions(room);
      } catch (err) {
        console.error(`[${room.id} questions persist]`, err.message);
      }
      return merged.length;
    }

    return inMemory.length;
  }

  syncQuestionsFromDb(room) {
    const count = this.ensureQuestionsSynced(room);
    return count > 0;
  }

  persistQuestions(room) {
    const json = room.game.getQuestionsJson();
    try {
      if (room.userId) {
        roomRepo.update(room.id, { questions_json: json });
      }
      room.game.saveQuestions();
      auditRecord({
        roomId: room.id,
        category: "persist",
        level: "info",
        message: "Sorular kaydedildi",
        detail: { count: room.game.questions?.length ?? 0 },
      });
    } catch (err) {
      const msg = err?.message || String(err);
      const wrapped = new Error(
        `Sorular diske yazılamadı (${msg}). Sunucuda: chown -R www-data:www-data /opt/bulmaca777/data`
      );
      wrapped.status = 500;
      throw wrapped;
    }
  }

  persistGameState(room) {
    if (!room.userId) return;
    try {
      const json = isTeamRaceMode(room.config.gameMode)
        ? JSON.stringify(room.teamRace.serializeState())
        : roomUsesPuzzleEngine(room)
          ? JSON.stringify(room.game.serializeState())
          : JSON.stringify(room.photoBattle.serializeState());
      roomRepo.updateGameState(room.id, json);
    } catch (err) {
      console.error(`[${room.id} state]`, err.message);
    }
  }

  getRoomDisplayName(room) {
    return room.name;
  }

  getPublicInfo(roomId) {
    const room = this.getRoomOrThrow(roomId);
    return {
      id: room.id,
      name: room.name,
      displayName: this.getRoomDisplayName(room),
      botName: room.config.botName,
      gameMode: room.config.gameMode,
      gameModeLabel: gameModeLabel(room.config.gameMode),
      config: {
        gameMode: room.config.gameMode,
        videoId: room.config.videoId || "",
        botName: room.config.botName,
        announceWrong: room.config.announceWrong,
      },
    };
  }

  _emitRoomConfig(room) {
    this.io.to(room.id).emit("config", {
      chatMode: this.chatMode,
      gameMode: room.config.gameMode,
      gameModeLabel: gameModeLabel(room.config.gameMode),
      youtubeLinked: Boolean(room.youtubeChatConnected),
      roomId: room.id,
      roomName: this.getRoomDisplayName(room),
      botName: room.config.botName,
    });
  }

  _bootstrapRoom(roomId, meta) {
    if (this.rooms.has(roomId)) return this.rooms.get(roomId);

    const dir = this._roomDir(roomId);
    mkdirSync(dir, { recursive: true });

    if (meta.isNew) {
      if (existsSync(DEFAULT_QUESTIONS) && !existsSync(this._questionsPath(roomId))) {
        cpSync(DEFAULT_QUESTIONS, this._questionsPath(roomId));
      }
    }

    if (meta.questionsJson) {
      writeFileSync(this._questionsPath(roomId), meta.questionsJson, "utf-8");
    }

    const game = new GameEngine({
      ...this.gameDefaults,
      questionsPath: this._questionsPath(roomId),
      botName: meta.config.botName,
      announceWrong: meta.config.announceWrong,
      winMessage: meta.config.winMessage,
      wrongMessage: meta.config.wrongMessage,
    });

    const cfgMode = normalizeGameMode(meta.config?.gameMode);
    const restoreGameState =
      meta.gameStateJson &&
      !isTeamRaceMode(cfgMode) &&
      (isFootballMode(cfgMode) ||
        !isPhotoBattleMode(cfgMode) ||
        isCelebrityAgeQuiz(game.questions));
    if (restoreGameState) {
      try {
        game.restoreState(JSON.parse(meta.gameStateJson));
      } catch {
        /* varsayılan */
      }
    }

    const diskCfg = this._readJson(this._configPath(roomId), {});
    const sqlRaceSettings = meta.userId ? raceRepo.loadSettings(roomId) : null;
    const mergedConfig = configWithDefaults({
      ...(meta.config || {}),
      ...diskCfg,
      gameMode: normalizeGameMode(
        meta.config?.gameMode ?? diskCfg?.gameMode
      ),
      photoBattleSettings: {
        ...(meta.config?.photoBattleSettings || {}),
        ...(diskCfg.photoBattleSettings || {}),
      },
      raceSettings: {
        ...(sqlRaceSettings || {}),
        ...(meta.config?.raceSettings || {}),
        ...(diskCfg.raceSettings || {}),
      },
    });
    try {
      this._writeJson(this._configPath(roomId), mergedConfig);
    } catch {
      /* disk senkron opsiyonel */
    }

    const chat = this._createChat(roomId, mergedConfig);
    const teamRace = new TeamRaceEngine({
      settings: normalizeRaceSettings(mergedConfig.raceSettings || {}),
    });

    const photoBattle = new PhotoBattleEngine({
      roomId,
      settings: mergedConfig.photoBattleSettings || {},
    });
    photoBattle.setPool(loadPhotoPool(roomId));

    const room = {
      id: roomId,
      name: meta.name || roomId,
      userId: meta.userId ?? null,
      createdAt: meta.createdAt,
      config: mergedConfig,
      game,
      teamRace,
      photoBattle,
      raceRoundHistory: [],
      autopilotArmed: false,
      lastRealChatAt: 0,
      chat,
      chatPolling: false,
      youtubeChatConnected: false,
      innerChatTap: [],
      chatListenError: null,
    };

    room.raceAutopilot = new RaceAutopilot(room, this);
    room.raceRoundHistory = room.userId ? raceRepo.listRounds(roomId, 30) : [];

    if (room.userId && isTeamRaceMode(room.config.gameMode)) {
      raceRepo.saveSettings(roomId, mergedConfig.raceSettings);
    }

    if (isTeamRaceMode(room.config.gameMode) && meta.gameStateJson) {
      try {
        teamRace.restoreState(JSON.parse(meta.gameStateJson));
      } catch {
        /* varsayılan */
      }
    }

    if (
      isPhotoBattleMode(room.config.gameMode) &&
      !roomUsesPuzzleEngine(room) &&
      meta.gameStateJson
    ) {
      try {
        photoBattle.restoreState(JSON.parse(meta.gameStateJson));
      } catch {
        /* varsayılan */
      }
    }

    game.onPersist = () => this.persistGameState(room);

    game.onStateChange = (snapshot) => {
      if (roomUsesPuzzleEngine(room)) {
        this.io.to(roomId).emit("game:state", snapshot);
        this._syncYoutubePollingMode(room, snapshot);
      }
    };

    photoBattle.onPersist = () => this.persistGameState(room);
    photoBattle.onStateChange = (snap) => {
      if (!photoRoomRunsCelebrityAge(room)) {
        this.io.to(roomId).emit("photo-battle:state", snap);
        this._syncYoutubePollingMode(room, {
          state: photoBattle.isRunning() ? "active" : "idle",
        });
      }
    };

    teamRace.onPersist = () => this.persistGameState(room);
    teamRace.onStateChange = () => {
      const snap = teamRace.getSnapshot();
      this.io.to(roomId).emit("race:state", this._raceStatePayload(room));
      this._syncYoutubePollingMode(room, {
        state: snap.phase === "running" ? "active" : "idle",
      });
    };
    teamRace.onSpawn = (entity) => {
      room.raceAutopilot?.onSpawn?.(entity);
      this.io.to(roomId).emit("race:spawn", entity);
    };
    teamRace.onRoundEnd = (snap) => {
      if (snap?.lastWinner) {
        const w = snap.lastWinner;
        const row = {
          round: snap.round,
          teamCode: w.teamCode,
          teamName: w.teamName,
          flagUrl: w.flagUrl,
          spawnCount: w.spawnCount,
          winReason: w.winReason,
          endKind: snap.endKind,
          at: w.at || new Date().toISOString(),
        };
        room.raceRoundHistory.unshift(row);
        if (room.raceRoundHistory.length > 30) room.raceRoundHistory.length = 30;
        if (room.userId) {
          try {
            raceRepo.appendRound(roomId, row);
          } catch (err) {
            console.error(`[${roomId} race round]`, err.message);
          }
        }
        const reason =
          w.winReason === "last_standing"
            ? "son kalan"
            : w.winReason === "most_on_arena"
              ? "arenada en çok"
              : "en çok katılım";
        this.appendRoomLog(
          roomId,
          `Tur ${snap.round} bitti — ${w.teamName} kazandı (${reason}, ${w.spawnCount} top)`,
          { highlight: true }
        );
      } else {
        this.appendRoomLog(
          roomId,
          `Tur ${snap.round} — yeterli sohbet etkileşimi olmadı`,
          { kind: "system" }
        );
      }
      this.io.to(roomId).emit("race:state", this._raceStatePayload(room));
      room.raceAutopilot?.onRoundEnd?.(snap);
    };

    game.onBotReply = ({ type, chatText, user }) => {
      const label = type === "wrong" ? "Yanlış" : "Doğru";
      void this.sendBotChat(room, chatText, {
        emitType: type,
        logKind: type === "wrong" ? "bot_wrong" : "bot_correct",
        logLabel: label,
      })
        .then(() => {
          if (type === "correct" && user) {
            this.appendRoomLog(roomId, `${user} doğru cevap verdi!`, {
              highlight: true,
              kind: "winner",
            });
          }
        })
        .catch((err) => {
          console.error(`[${roomId} bot]`, err.message);
          this.io.to(roomId).emit("chat:error", { message: err.message });
          this.appendRoomLog(roomId, `Hata: ${err.message}`, { kind: "error" });
        });
    };

    this.rooms.set(roomId, room);

    if (this.chatMode === "youtube" && meta.config?.videoId) {
      if (room.chat instanceof InnerYouTubeChatService) {
        room.chat.setVideoIds(meta.config.videoIds || (meta.config.videoId ? [meta.config.videoId] : []));
      }
      this._resumeYouTubeChat(room).catch((err) => {
        console.error(`[${roomId} youtube resume]`, err.message);
      });
    }

    return room;
  }

  _sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  async sendBotChat(room, chatText, options = {}) {
    if (!room._botSendChain) room._botSendChain = Promise.resolve();
    const run = room._botSendChain.then(() => this._sendBotChatNow(room, chatText, options));
    room._botSendChain = run.catch(() => {});
    return run;
  }

  async _sendBotChatNow(room, chatText, options = {}) {
    const minGapMs = 400;
    const lastAt = room._lastBotSendAt || 0;
    const wait = minGapMs - (Date.now() - lastAt);
    if (wait > 0) await this._sleep(wait);

    const formatted = formatBotMessage(room.config.botName, chatText);
    await room.chat.sendMessage(formatted);
    room._lastBotSendAt = Date.now();
    const payload = {
      type: options.emitType ?? "info",
      text: formatted,
      at: new Date().toISOString(),
    };
    this.io.to(room.id).emit("bot:reply", payload);
    if (options.log !== false) {
      const label = options.logLabel || "Mesaj";
      this.appendRoomLog(room.id, `[Bot ${label}] ${formatted}`, {
        highlight: Boolean(options.highlight),
        kind: options.logKind || "bot",
      });
    }
    return formatted;
  }

  async _resumeYouTubeChat(room) {
    if (!isYoutubeRoomChat(room.chat)) return;
    if (!(room.config.videoIds?.length || room.config.videoId)) return;

    room.chat.stopPolling?.();
    room.chatPolling = false;
    room.chat.setVideoIds(room.config.videoIds || (room.config.videoId ? [room.config.videoId] : []));

    this.wireChat(room);
    room.youtubeChatConnected = true;
    this._syncYoutubePollingMode(room);
    await this._emitYouTubeStatus(room);
  }

  _releaseUserLivePoll(room) {
    const uid = room?.userId;
    if (uid == null) return;
    if (this._userLivePollRoomId.get(uid) === room.id) {
      this._userLivePollRoomId.delete(uid);
    }
  }

  _claimUserLivePoll(room) {
    const uid = room.userId;
    if (uid == null) return;
    const prevId = this._userLivePollRoomId.get(uid);
    if (prevId && prevId !== room.id) {
      const prev = this.rooms.get(prevId);
      if (isYoutubeRoomChat(prev?.chat)) {
        prev.chat.setPollingMode("idle");
      }
    }
    this._userLivePollRoomId.set(uid, room.id);
  }

  /** Bağlıyken InnerChat dinlemeyi açık tut (oyun idle olsa da). */
  _applyStayConnectedChatListen(room) {
    if (!room.youtubeChatConnected || !isYoutubeRoomChat(room.chat)) return false;
    if (!resolveYoutubeChatStayConnected()) return false;
    if (!(room.config.videoIds?.length || room.config.videoId)) return false;

    this._claimUserLivePoll(room);
    room.chat.setPollingMode("live");
    innerChatDebugLog(
      room.id,
      "pollingMode=live (stay-connected)",
      `videos=${(room.config.videoIds || []).join(",") || "—"}`
    );
    return true;
  }

  /** Kopuk stream varsa yeniden başlat (sessiz keepalive). */
  _reconcileYoutubeChatListen(room) {
    if (!room.youtubeChatConnected || !isYoutubeRoomChat(room.chat)) return;
    if (!resolveYoutubeChatStayConnected()) return;
    if (!room.chat._polling) return;

    const ids = room.config.videoIds?.length
      ? room.config.videoIds
      : room.config.videoId
        ? [room.config.videoId]
        : [];
    if (!ids.length) return;

    const active = new Set(room.chat.getQuotaState?.().activeStreamIds || []);
    const missing = ids.filter(
      (id) => !active.has(id) && !room.chat.isStreamCooling?.(id)
    );
    if (!missing.length && room.chat._pollingMode === "live") return;

    room.chat.setPollingMode("live");
    if (missing.length) {
      innerChatDebugLog(room.id, "reconcile listen", missing.join(","));
      void room.chat._ensureLiveChats?.().catch((err) => {
        console.warn(`[${room.id} chat reconcile]`, err?.message || err);
      });
    }
  }

  /** Oyun aktifken canlı sohbet list; beklemede zamanlayıcı durur (sıfır API). */
  _raceStatePayload(room) {
    const snap = room.teamRace.getSnapshot();
    const roundHistory = room.raceRoundHistory || [];
    const series = getRaceSeriesStatus(snap.settings || room.config?.raceSettings, roundHistory);
    return {
      ...snap,
      roundHistory,
      series,
      autopilot: room.raceAutopilot?.getPublicStatus?.() ?? {
        enabled: false,
        armed: false,
        statusMessage: "",
      },
    };
  }

  _syncYoutubePollingMode(room, snapshot) {
    if (!isYoutubeRoomChat(room.chat)) return;
    if (!room.youtubeChatConnected) {
      room.chat.setPollingMode("idle");
      this._releaseUserLivePoll(room);
      return;
    }

    if (this._applyStayConnectedChatListen(room)) {
      return;
    }

    const snap =
      snapshot ??
      (isTeamRaceMode(room.config.gameMode)
        ? {
            state: room.teamRace.isRunning() ? "active" : "idle",
          }
        : isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)
          ? {
              state: room.photoBattle.isRunning() ? "active" : "idle",
            }
          : room.game.getSnapshot());
    const pollInWinner = resolveYoutubePollInWinner();
    const live =
      snap?.state === "active" ||
      (pollInWinner && snap?.state === "winner");

    if (live) {
      this._claimUserLivePoll(room);
      room.chat.setPollingMode("live");
      innerChatDebugLog(
        room.id,
        "pollingMode=live",
        `game=${snap?.state}`,
        `videos=${(room.config.videoIds || []).join(",") || "—"}`
      );
    } else {
      this._releaseUserLivePoll(room);
      room.chat.setPollingMode("idle");
      innerChatDebugLog(room.id, "pollingMode=idle", `game=${snap?.state}`);
    }
  }

  getYouTubeApiConfig() {
    return {
      mode: this.chatMode,
      apiEnabled: this.chatMode === "youtube",
    };
  }

  async _emitYouTubeStatus(room) {
    const status = await this.getYouTubeStatus(room);
    this.io.to(room.id).emit("youtube:status", status);
    return status;
  }

  async getYouTubeStatus(room) {
    const isYt = isYoutubeRoomChat(room.chat);
    const videoIds = room.config.videoIds?.length
      ? room.config.videoIds
      : room.config.videoId
        ? [room.config.videoId]
        : [];
    const videoId = videoIds[0] || room.chat?.videoId || "";
    const qs = isYt ? room.chat.getQuotaState?.() || {} : {};
    const activeIds = qs.activeStreamIds || [];
    if (activeIds.length) room.chatListenError = null;
    return {
      ...this.getYouTubeApiConfig(),
      roomId: room.id,
      youtubeAvailable: isYt,
      readMode: isYt ? "inner" : null,
      connected: Boolean(room.youtubeChatConnected),
      videoId,
      videoIds,
      streamUrl: videoId ? `https://www.youtube.com/watch?v=${videoId}` : "",
      streamUrls: videoIds.map((id) => `https://www.youtube.com/watch?v=${id}`),
      watchUrl: videoId ? `https://www.youtube.com/watch?v=${videoId}` : "",
      channelHint:
        "Canlı yayın linki = o an yayında olan videonun adresi (YouTube Studio veya paylaş menüsünden).",
      chatPollIntervalMs: qs.pollIntervalMs ?? 2000,
      pollingMode: qs.pollingMode || "idle",
      quotaSavingHint:
        "Sohbet okuma yalnızca video linki ile yapılır; Google hesabı gerekmez.",
      innerChatTapEnabled: innerChatTapEnabled(),
      innerChatTapCount: room.innerChatTap?.length ?? 0,
      listeningLive:
        qs.pollingMode === "live" ||
        (resolveYoutubeChatStayConnected() && Boolean(room.youtubeChatConnected)),
      chatStayConnected: resolveYoutubeChatStayConnected(),
      listenError: room.chatListenError || null,
      liveStreamsActive: qs.activeStreamIds || [],
    };
  }

  _summarizeInnerChatOutcome(result, room) {
    if (!result) return { code: "none", label: "—" };
    if (result.type === "command") return { code: "command", label: `komut ${result.command || ""}` };
    if (result.type === "correct") {
      return { code: "correct", label: `doğru +${result.points ?? "?"} p` };
    }
    if (result.type === "wrong") return { code: "wrong", label: "yanlış" };
    if (result.type === "vote") {
      return { code: "vote", label: `oy ${result.side === 1 ? "1" : "2"}` };
    }
    if (result.type === "spawn") {
      return { code: "spawn", label: result.entity?.teamName || "takım" };
    }
    if (result.type === "unmatched") return { code: "unmatched", label: "eşleşmedi" };
    if (room.game?.state === "idle" && roomUsesPuzzleEngine(room)) {
      return { code: "idle", label: "oyun kapalı" };
    }
    return { code: "other", label: result.type || "—" };
  }

  _recordInnerChatTap(room, msg, outcome) {
    if (!innerChatTapEnabled() || !isYoutubeRoomChat(room.chat)) return;
    if (!Array.isArray(room.innerChatTap)) room.innerChatTap = [];

    const entry = {
      at: new Date().toISOString(),
      author: String(msg?.author || "İzleyici").slice(0, 80),
      text: String(msg?.text || "").slice(0, 500),
      sourceVideoId: msg?.sourceVideoId || null,
      simulated: Boolean(msg?.simulated),
      outcome: outcome?.code || "none",
      outcomeLabel: outcome?.label || "—",
    };

    room.innerChatTap.unshift(entry);
    if (room.innerChatTap.length > INNER_CHAT_TAP_MAX) {
      room.innerChatTap.length = INNER_CHAT_TAP_MAX;
    }

    this.io.to(room.id).emit("inner-chat:tap", entry);
    auditRecord({
      roomId: room.id,
      category: "chat",
      level: outcome?.code === "error" ? "error" : "debug",
      message: `chat: ${entry.author} → ${(entry.text || "").slice(0, 80)}`,
      detail: { outcome: entry.outcome, outcomeLabel: entry.outcomeLabel, video: entry.sourceVideoId },
    });
  }

  getInnerChatTap(room) {
    const qs = isYoutubeRoomChat(room.chat) ? room.chat.getQuotaState?.() || {} : {};
    return {
      enabled: innerChatTapEnabled(),
      max: INNER_CHAT_TAP_MAX,
      count: room.innerChatTap?.length ?? 0,
      connected: Boolean(room.youtubeChatConnected),
      pollingMode: qs.pollingMode || "idle",
      streamCount: qs.streamCount ?? 0,
      activeStreamIds: qs.activeStreamIds || [],
      items: [...(room.innerChatTap || [])],
    };
  }

  getInnerChatDiagnostic(room) {
    const tap = this.getInnerChatTap(room);
    const gameSnap = roomUsesPuzzleEngine(room)
      ? room.game.getSnapshot()
      : isTeamRaceMode(room.config.gameMode)
        ? { state: room.teamRace.isRunning() ? "active" : "idle" }
        : isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)
          ? { state: room.photoBattle.isRunning() ? "active" : "idle" }
          : { state: "unknown" };
    const chatDbg = isYoutubeRoomChat(room.chat)
      ? room.chat.getDebugState?.() || {}
      : null;
    const lastChatAgoSec =
      room.lastRealChatAt > 0
        ? Math.round((Date.now() - room.lastRealChatAt) / 1000)
        : null;
    return {
      serverChatMode: this.chatMode,
      roomId: room.id,
      tap,
      gameState: gameSnap?.state ?? "idle",
      chatPolling: Boolean(room.chatPolling),
      lastRealChatAgoSec,
      videoIds: room.config.videoIds?.length
        ? room.config.videoIds
        : room.config.videoId
          ? [room.config.videoId]
          : [],
      innerChat: chatDbg,
      hints: this._innerChatDiagnosticHints(room, tap, gameSnap, chatDbg, lastChatAgoSec),
    };
  }

  _innerChatDiagnosticHints(room, tap, gameSnap, chatDbg, lastChatAgoSec) {
    const hints = [];
    if (this.chatMode !== "youtube") {
      hints.push("Sunucu CHAT_MODE mock — .env CHAT_MODE=youtube + restart");
    }
    if (!tap.connected) {
      hints.push("Sohbete bağlan yapılmamış");
    }
    if (tap.connected && tap.pollingMode !== "live") {
      hints.push("Bağlı ama dinleme kapalı — Kontrol → Başlat (oyun active olmalı)");
    }
    if (tap.pollingMode === "live" && !(chatDbg?.videoIds?.length || tap.activeStreamIds?.length)) {
      hints.push("live modda ama video ID yok — yeniden Sohbete bağlan");
    }
    if (
      tap.pollingMode === "live" &&
      chatDbg &&
      chatDbg.videoIds?.length > 0 &&
      (chatDbg.activeStreamIds?.length ?? 0) === 0
    ) {
      hints.push(
        "youtube-chat yayına bağlanamadı — yayın canlı mı? journalctl | grep 'Inner chat'"
      );
    }
    if (tap.pollingMode === "live" && lastChatAgoSec == null && (tap.count ?? 0) === 0) {
      hints.push("Henüz ham mesaj yok — canlı sohbette test yazın veya tap listesini izleyin");
    }
    if (tap.pollingMode === "live" && lastChatAgoSec != null && lastChatAgoSec < 120) {
      hints.push(`Son gerçek mesaj ${lastChatAgoSec} sn önce — InnerChat çalışıyor gibi`);
    }
    if (gameSnap?.state === "idle" && tap.connected) {
      hints.push("Oyun idle — mesajlar işlenmeyebilir ama tap yine de dolmalı (live iken)");
    }
    return hints;
  }

  clearInnerChatTap(roomId, userId) {
    this.assertRoomOwner(roomId, userId);
    const room = this.getRoomOrThrow(roomId);
    room.innerChatTap = [];
    this.io.to(roomId).emit("inner-chat:tap:clear");
    return { ok: true, count: 0 };
  }

  assertYouTubeMode() {
    if (this.chatMode !== "youtube") {
      const err = new Error(
        "YouTube sohbeti için .env dosyasında CHAT_MODE=youtube olmalı."
      );
      err.status = 400;
      throw err;
    }
  }

  async connectYouTube(roomId, streamUrl, userId) {
    this.assertYouTubeMode();
    this.assertRoomOwner(roomId, userId);
    const room = this.getRoomOrThrow(roomId);
    if (!isYoutubeRoomChat(room.chat)) {
      throw new Error("YouTube servisi başlatılamadı");
    }

    const videoIds = parseYouTubeVideoIds(streamUrl);
    if (!videoIds.length) {
      const err = new Error(
        "Geçersiz yayın linki. Örnek: https://www.youtube.com/watch?v=VIDEO_ID veya https://youtu.be/VIDEO_ID"
      );
      err.status = 400;
      throw err;
    }
    const videoId = videoIds[0];

    if (
      room.youtubeChatConnected &&
      JSON.stringify(room.config.videoIds || []) === JSON.stringify(videoIds)
    ) {
      return this._emitYouTubeStatus(room);
    }

    this.updateConfig(roomId, {
      videoIds,
      liveChatId: "",
      streamUrlDraft: normalizeStreamUrlDraft(streamUrl),
    }, userId);
    room.chatListenError = null;
    room.chat.setVideoIds(videoIds);
    room.chat.liveChatId = null;

    if (room.userId) {
      roomRepo.update(roomId, { video_id: videoIdsToField(videoIds), live_chat_id: "" });
    }

    room.config.liveChatId = "";
    this.wireChat(room);
    room.youtubeChatConnected = true;
    this._applyStayConnectedChatListen(room);
    innerChatDebugLog(roomId, "connect", videoIds.join(","));
    auditRecord({
      roomId,
      userId,
      category: "youtube",
      level: "info",
      message: `Sohbete bağlandı (${videoIds.length} yayın)`,
      detail: { videoIds },
    });
    this._syncYoutubePollingMode(room);
    if (isTeamRaceMode(room.config.gameMode)) {
      room.raceAutopilot?.onYoutubeConnected?.();
    }

    this.appendRoomLog(
      roomId,
      `YouTube canlı sohbete bağlandı (${videoIds.length} yayın).`,
      { highlight: true, kind: "system" }
    );
    const status = await this._emitYouTubeStatus(room);
    status.statusMessage = `Canlı sohbete bağlandı — ${videoIds.length} yayın merkezi olarak okunuyor.`;
    return status;
  }

  async disconnectYouTube(roomId, userId) {
    this.assertRoomOwner(roomId, userId);
    const room = this.getRoomOrThrow(roomId);
    room.chat.stopPolling?.();
    room.chatPolling = false;
    room.youtubeChatConnected = false;
    this._releaseUserLivePoll(room);
    room.chat.liveChatId = null;
    if (isYoutubeRoomChat(room.chat)) {
      room.chat.liveChatId = null;
      room.chat.onStreamEnded = null;
    }
    this.updateConfig(roomId, { liveChatId: "" }, userId);
    this.appendRoomLog(roomId, "YouTube sohbet dinleme durduruldu.", { kind: "system" });
    auditRecord({
      roomId,
      userId,
      category: "youtube",
      level: "info",
      message: "Sohbet dinleme durduruldu",
    });
    const status = await this._emitYouTubeStatus(room);
    status.statusMessage = "Canlı sohbet dinleme durduruldu. Tekrar bağlamak için «Sohbete bağlan».";
    return status;
  }

  async handleChatCommand(room, result) {
    const { command, author } = result;
    if (command === "ping") {
      const text = buildPingMessage(room.config);
      await this.sendBotChat(room, text, {
        emitType: "command",
        logLabel: "Ping",
        logKind: "command",
        highlight: true,
      });
      this.appendRoomLog(room.id, `${author || "İzleyici"} → !ping`, { kind: "chat" });
      return;
    }

    if (command === "yardim" || command === "help") {
      const name = room.config.botName || "Bot";
      const helpText =
        `${name}: Cevabınızı sohbete yazın. !ping — bot kontrolü. Panelden bulmaca başlatılınca sorular sırayla açılır.`;
      await this.sendBotChat(room, helpText, {
        emitType: "command",
        logLabel: "Yardım",
        logKind: "command",
      });
    }
  }

  async announceGameStarted(room) {
    if (!room.youtubeChatConnected) return;
    if (!resolveYoutubeAnnounceGameStart()) return;
    const snapshot = room.game.getSnapshot();
    const text = buildGameStartedChatMessage(room.config, snapshot);
    await this.sendBotChat(room, text, {
      emitType: "system",
      logLabel: "Başladı",
      logKind: "game",
      highlight: true,
    });
  }

  _configPath(roomId) {
    return join(this._roomDir(roomId), "config.json");
  }

  _questionsPath(roomId) {
    return join(this._roomDir(roomId), "questions.json");
  }

  _layoutPath(roomId) {
    return join(this._roomDir(roomId), "layout.vertical.json");
  }

  _layoutPlayPath(roomId) {
    return join(this._roomDir(roomId), "layout.play.json");
  }

  readRoomLayoutPlay(roomId) {
    const roomPath = this._layoutPlayPath(roomId);
    if (existsSync(roomPath)) {
      return this._readJson(roomPath, null);
    }
    return null;
  }

  saveRoomLayoutPlay(roomId, userId, layout) {
    this.assertRoomOwner(roomId, userId);
    if (!layout || typeof layout !== "object") {
      const err = new Error("Geçersiz play yerleşim verisi");
      err.status = 400;
      throw err;
    }
    const dir = this._roomDir(roomId);
    mkdirSync(dir, { recursive: true });
    writeFileSync(
      this._layoutPlayPath(roomId),
      `${JSON.stringify(layout, null, 2)}\n`,
      "utf-8"
    );
    this.io.to(roomId).emit("play-layout:updated", { roomId });
    return layout;
  }

  /** Oda yerleşimi; yoksa genel varsayılan JSON */
  readRoomLayoutVertical(roomId) {
    const roomPath = this._layoutPath(roomId);
    if (existsSync(roomPath)) {
      return this._readJson(roomPath, null);
    }
    if (existsSync(DEFAULT_LAYOUT_VERTICAL)) {
      return this._readJson(DEFAULT_LAYOUT_VERTICAL, null);
    }
    return null;
  }

  saveRoomLayoutVertical(roomId, userId, layout) {
    this.assertRoomOwner(roomId, userId);
    if (!layout || typeof layout !== "object") {
      const err = new Error("Geçersiz yerleşim verisi");
      err.status = 400;
      throw err;
    }
    const dir = this._roomDir(roomId);
    mkdirSync(dir, { recursive: true });
    writeFileSync(
      this._layoutPath(roomId),
      `${JSON.stringify(layout, null, 2)}\n`,
      "utf-8"
    );
    this.io.to(roomId).emit("layout:updated", { roomId });
    return layout;
  }

  _createChat(roomId, config) {
    if (this.chatMode === "youtube") {
      return new InnerYouTubeChatService({
        videoId: videoIdsToField(config.videoIds || (config.videoId ? [config.videoId] : [])),
      });
    }
    return new MockChatService();
  }

  async _processChatMessage(room, msg) {
    const simulated =
      Boolean(msg?.simulated) || String(msg?.channelId || "").startsWith("sim:");
    if (!simulated) {
      room.lastRealChatAt = Date.now();
    }
    if (isPhotoBattleMode(room.config.gameMode) && !roomUsesPuzzleEngine(room)) {
      const result = room.photoBattle.handleChatMessage(msg);
      if (result?.type === "vote") {
        this.appendRoomLog(
          room.id,
          `${result.author} → ${result.side === 1 ? "1" : "2"}`,
          { kind: "chat", highlight: true }
        );
      }
      return result;
    }

    if (isTeamRaceMode(room.config.gameMode)) {
      const result = room.teamRace.handleChatMessage(msg);
      if (result?.type === "spawn") {
        const e = result.entity;
        this.appendRoomLog(
          room.id,
          `${e.displayName} → ${e.teamName} (${e.teamCode})`,
          { kind: "chat", highlight: true }
        );
      } else if (result?.type === "unmatched" && room.teamRace.isRunning()) {
        const preview = String(result.text || "").slice(0, 40);
        if (preview) {
          this.appendRoomLog(room.id, `Takım tanınmadı: «${preview}»`, { kind: "chat" });
        }
      }
      return result;
    }

    const result = room.game.handleChatMessage(msg);
    if (result?.type === "command") {
      await this.handleChatCommand(room, result);
      return result;
    }
    if (result?.type === "correct") {
      this.io.to(room.id).emit("game:winner", result);
    }
    return result;
  }

  startTeamRace(room) {
    this.wireChat(room);
    if (room.config.raceSettings) {
      room.teamRace.updateSettings(room.config.raceSettings);
    }
    const ap = room.raceAutopilot;
    if (ap?.isEnabled()) {
      ap.arm();
    }
    if (room.teamRace.isRunning()) {
      return room.teamRace.getSnapshot();
    }
    if (!canStartRaceRound(room.config?.raceSettings, room.raceRoundHistory)) {
      const series = getRaceSeriesStatus(room.config?.raceSettings, room.raceRoundHistory);
      const err = new Error(
        `Seri tamamlandı (${series.completedRounds}/${series.maxRounds} tur). Sıfırla ile yeniden başlayın.`
      );
      err.status = 409;
      throw err;
    }
    return room.teamRace.start();
  }

  stopTeamRace(room) {
    room.raceAutopilot?.disarm?.();
    return room.teamRace.stop();
  }

  resetTeamRace(room) {
    room.raceRoundHistory = [];
    if (room.userId) {
      try {
        raceRepo.clearRounds(room.id);
      } catch (err) {
        console.error(`[${room.id} race clear]`, err.message);
      }
    }
    room.raceAutopilot?.disarm?.();
    return room.teamRace.reset();
  }

  eliminateTeamRaceEntity(room, entityId) {
    return room.teamRace.eliminateEntity(entityId);
  }

  triggerTeamRaceShock(room) {
    return room.teamRace.triggerShockWave("manual");
  }

  getPhotoBattlePool(room) {
    const pool = loadPhotoPool(room.id);
    room.photoBattle.setPool(pool);
    return { pool, snapshot: room.photoBattle.getSnapshot() };
  }

  addPhotoBattleImages(room, images) {
    if (!Array.isArray(images) || !images.length) {
      const err = new Error("En az bir görsel gerekli");
      err.status = 400;
      throw err;
    }
    const added = [];
    for (const img of images) {
      added.push(
        addPhotoFromBase64(room.id, {
          name: img.name,
          dataBase64: img.dataBase64,
          label: img.label,
        })
      );
    }
    const pool = loadPhotoPool(room.id);
    room.photoBattle.setPool(pool);
    this.io.to(room.id).emit("photo-battle:state", room.photoBattle.getSnapshot());
    return { added, pool };
  }

  removePhotoBattleImage(room, photoId) {
    const pool = removePhotoFromPool(room.id, photoId);
    room.photoBattle.setPool(pool);
    if (room.photoBattle.isRunning()) room.photoBattle.stop();
    this.io.to(room.id).emit("photo-battle:state", room.photoBattle.getSnapshot());
    return { pool };
  }

  clearPhotoBattlePool(room) {
    const pool = clearPhotoPool(room.id);
    room.photoBattle.setPool(pool);
    room.photoBattle.reset();
    this.io.to(room.id).emit("photo-battle:state", room.photoBattle.getSnapshot());
    return { pool };
  }

  startPhotoBattle(room) {
    this.wireChat(room);
    room.photoBattle.setPool(loadPhotoPool(room.id));
    if (room.config.photoBattleSettings) {
      room.photoBattle.updateSettings(room.config.photoBattleSettings);
    }
    const snap = room.photoBattle.start();
    this.persistGameState(room);
    this._syncYoutubePollingMode(room, {
      state: room.photoBattle.isRunning() ? "active" : "idle",
    });
    this.appendRoomLog(
      room.id,
      `Photo Quiz başladı — havuz ${snap.poolCount}, tur ${snap.matchNumber}`,
      { highlight: true, kind: "game" }
    );
    return snap;
  }

  stopPhotoBattle(room) {
    return room.photoBattle.stop();
  }

  resetPhotoBattle(room) {
    return room.photoBattle.reset();
  }

  skipPhotoBattleVote(room) {
    return room.photoBattle.skipVote();
  }

  async injectTestComment(room, author, text, options = {}) {
    const body = String(text ?? "").trim();
    if (!body) {
      const err = new Error("Cevap metni gerekli");
      err.status = 400;
      throw err;
    }

    this.wireChat(room);

    const name = String(author || "Test").trim() || "Test";

    if (room.chat instanceof MockChatService) {
      room.chat.inject(name, body);
      this.appendRoomLog(room.id, `Panel testi: ${name} → ${body}`, { kind: "chat" });
      return { ok: true, mode: "mock" };
    }

    const simulated = Boolean(options.simulated);
    const msg = {
      id: simulated
        ? `sim-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
        : `panel-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      author: name,
      channelId: simulated
        ? `sim:${name.toLowerCase().replace(/\s+/g, "-").slice(0, 40)}`
        : `panel-${name.toLowerCase().replace(/\s+/g, "-")}`,
      avatarUrl: null,
      text: body,
      simulated,
      publishedAt: new Date().toISOString(),
    };

    const result = await this._processChatMessage(room, msg);
    this._recordInnerChatTap(room, msg, this._summarizeInnerChatOutcome(result, room));
    let note = "Oyun testi işlendi.";
    if (isPhotoBattleMode(room.config.gameMode)) {
      note =
        result?.type === "vote"
          ? `Oy: ${result.side === 1 ? "1 (sol)" : "2 (sağ)"}`
          : "Photo Quiz — sohbette 1 veya 2 yazın (tur açıkken)";
    } else if (isTeamRaceMode(room.config.gameMode)) {
      note =
        result?.type === "spawn"
          ? `Takım spawn: ${result.entity.teamName}`
          : result?.type === "unmatched"
            ? "Takım eşleşmedi"
            : "Takım yarışı (tur kapalıysa spawn olmaz)";
    } else if (result?.type === "correct") {
      note = `Doğru! +${result.points ?? "?"} p — listede en fazla ${room.game.feedMax} kişi`;
    } else if (result?.type === "wrong") {
      note = "Yanlış yaş";
    } else if (room.game.state === "idle") {
      note = "Önce «Başlat» — oyun yayında değil";
    }
    if (this.chatMode === "mock") {
      note += " (CHAT_MODE=mock)";
    } else if (!room.youtubeChatConnected) {
      note += " · YouTube bağlı değil — admin’den «Sohbete bağlan»";
    }
    this.appendRoomLog(room.id, `Panel testi: ${name} → ${body}`, { kind: "chat" });
    return {
      ok: true,
      mode: isPhotoBattleMode(room.config.gameMode)
        ? "photo-battle"
        : isTeamRaceMode(room.config.gameMode)
          ? "team-race"
          : "youtube",
      result,
      note,
    };
  }

  _onYouTubeListenError(room, videoId, hint = "") {
    const friendly = humanizeChatListenHint(hint);
    room.chatListenError = `${videoId}: ${friendly}`;
    this.appendRoomLog(
      room.id,
      `Canlı sohbet henüz açılamadı (${videoId}). ${friendly} Birkaç saniyede yeniden denenecek.`,
      { kind: "system", highlight: true }
    );
    auditRecord({
      roomId: room.id,
      category: "youtube",
      level: "warn",
      message: "Sohbet dinleme bekliyor",
      detail: { videoId, hint: friendly, raw: String(hint || "").slice(0, 120) },
    });
    void this._emitYouTubeStatus(room);
  }

  /** Eski davranış: yayın bitince tam kopma. InnerChat artık end/error ile burayı çağırmaz. */
  _onYouTubeStreamEnded(room, reason = "") {
    if (!room.youtubeChatConnected) return;
    if (resolveYoutubeChatStayConnected()) {
      this._onYouTubeStreamInterrupted(room, reason);
      return;
    }

    const roomId = room.id;
    room.chatListenError = null;
    room.chat.stopPolling?.();
    room.chatPolling = false;
    room.youtubeChatConnected = false;
    this._releaseUserLivePoll(room);

    if (isYoutubeRoomChat(room.chat)) {
      room.chat.onStreamEnded = null;
      room.chat.liveChatId = null;
    }

    room.config.liveChatId = "";
    try {
      if (roomRepo.findById(roomId)) {
        roomRepo.update(roomId, { live_chat_id: "" });
      }
    } catch {
      /* yoksay */
    }

    const detail = reason ? ` (${reason})` : "";
    this.appendRoomLog(
      roomId,
      `Yayın sona erdi — canlı sohbet dinleme durduruldu.${detail}`,
      { highlight: true, kind: "system" }
    );
    auditRecord({
      roomId,
      category: "youtube",
      level: "warn",
      message: "Yayın / sohbet sona erdi",
      detail: { reason },
    });

    void this._emitYouTubeStatus(room).then((status) => {
      status.statusMessage =
        "Yayın bitti; sohbet dinleme durdu. Yeni yayında tekrar «Sohbete bağlan».";
      this.io.to(roomId).emit("youtube:status", status);
    });
  }

  /** Geçici kesinti — bağlantı panelde açık kalır, InnerChat yeniden dener. */
  _onYouTubeStreamInterrupted(room, reason = "") {
    if (!room.youtubeChatConnected) return;

    const detail = reason ? ` (${String(reason).slice(0, 120)})` : "";
    room.chatListenError =
      reason && !/yeniden/i.test(String(reason))
        ? `${String(reason).slice(0, 160)} — yeniden deneniyor`
        : null;

    this._applyStayConnectedChatListen(room);
    this._reconcileYoutubeChatListen(room);

    this.appendRoomLog(
      room.id,
      `Canlı sohbet kısa süre kesildi — otomatik yeniden bağlanılıyor.${detail}`,
      { kind: "system", highlight: true }
    );
    auditRecord({
      roomId: room.id,
      category: "youtube",
      level: "warn",
      message: "Sohbet kesintisi — yeniden bağlanılıyor",
      detail: { reason },
    });

    void this._emitYouTubeStatus(room).then((status) => {
      status.statusMessage =
        "Sohbet dinlemesi açık — geçici kesinti, sunucu yeniden bağlanıyor.";
      this.io.to(room.id).emit("youtube:status", status);
    });
  }

  wireChat(room) {
    if (room.chatPolling) return;
    room.chatPolling = true;
    auditRecord({
      roomId: room.id,
      category: "room",
      level: "info",
      message: "wireChat başlatıldı",
      detail: {
        chatMode: this.chatMode,
        youtubeConnected: room.youtubeChatConnected,
      },
    });

    if (isYoutubeRoomChat(room.chat)) {
      room.chat.onStreamEnded = (reason) => {
        if (resolveYoutubeChatStayConnected()) {
          this._onYouTubeStreamInterrupted(room, reason);
        } else {
          this._onYouTubeStreamEnded(room, reason);
        }
      };
      room.chat.onListenError = (videoId, hint) => {
        this._onYouTubeListenError(room, videoId, hint);
        if (resolveYoutubeChatStayConnected()) {
          this._reconcileYoutubeChatListen(room);
        }
      };
    }

    room.chat.startPolling(async (msg) => {
      let outcome = { code: "error", label: "hata" };
      try {
        const result = await this._processChatMessage(room, msg);
        outcome = this._summarizeInnerChatOutcome(result, room);
      } catch (err) {
        console.error(`[${room.id} chat]`, err.message);
        outcome = { code: "error", label: err.message?.slice(0, 60) || "hata" };
      }
      this._recordInnerChatTap(room, msg, outcome);
    });
    this._syncYoutubePollingMode(room);
  }

  log(roomId, message, options) {
    return this.appendRoomLog(roomId, message, options);
  }
}
