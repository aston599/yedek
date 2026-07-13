import { DatabaseSync } from "node:sqlite";
import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "data", "app.db");

let db;

export function getDb() {
  if (!db) {
    mkdirSync(join(__dirname, "..", "data"), { recursive: true });
    db = new DatabaseSync(DB_PATH);
    db.exec("PRAGMA journal_mode = WAL");
    db.exec("PRAGMA foreign_keys = ON");
    migrate(db);
  }
  return db;
}

function migrate(database) {
  database.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE COLLATE NOCASE,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sessions (
      token TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      expires_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rooms (
      id TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      bot_name TEXT NOT NULL DEFAULT 'YouTube Bulmacaları',
      video_id TEXT NOT NULL DEFAULT '',
      live_chat_id TEXT NOT NULL DEFAULT '',
      announce_wrong INTEGER NOT NULL DEFAULT 0,
      win_message TEXT,
      wrong_message TEXT,
      questions_json TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_rooms_user ON rooms(user_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

    CREATE TABLE IF NOT EXISTS room_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
      kind TEXT NOT NULL DEFAULT 'info',
      message TEXT NOT NULL,
      highlight INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_room_events_room ON room_events(room_id, id DESC);

    CREATE TABLE IF NOT EXISTS audit_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      room_id TEXT NOT NULL,
      user_id INTEGER,
      category TEXT NOT NULL DEFAULT 'system',
      level TEXT NOT NULL DEFAULT 'info',
      message TEXT NOT NULL,
      detail_json TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_audit_events_room ON audit_events(room_id, id DESC);
  `);

  try {
    database.exec(`ALTER TABLE rooms ADD COLUMN game_state_json TEXT`);
  } catch {
    /* sütun zaten var */
  }

  try {
    database.exec(
      `ALTER TABLE rooms ADD COLUMN game_mode TEXT NOT NULL DEFAULT 'puzzle'`
    );
  } catch {
    /* sütun zaten var */
  }

  try {
    database.exec(`ALTER TABLE rooms ADD COLUMN race_settings_json TEXT`);
  } catch {
    /* sütun zaten var */
  }

  try {
    database.exec(`ALTER TABLE rooms ADD COLUMN stream_url_draft TEXT NOT NULL DEFAULT ''`);
  } catch {
    /* sütun zaten var */
  }

  try {
    database.exec(`ALTER TABLE rooms ADD COLUMN photo_battle_settings_json TEXT`);
  } catch {
    /* sütun zaten var */
  }

  database.exec(`
    CREATE TABLE IF NOT EXISTS room_race_rounds (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
      round INTEGER NOT NULL,
      team_code TEXT NOT NULL,
      team_name TEXT NOT NULL,
      flag_url TEXT,
      spawn_count INTEGER NOT NULL DEFAULT 0,
      win_reason TEXT,
      end_kind TEXT,
      won_at TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_room_race_rounds_room
      ON room_race_rounds(room_id, id DESC);
  `);

  /* Yanlış cevap sohbet yanıtı API kotası tüketir; varsayılan kapalı */
  database.exec(`UPDATE rooms SET announce_wrong = 0 WHERE announce_wrong != 0`);
}

function insertRowId(result) {
  const id = result?.lastInsertRowid;
  return typeof id === "bigint" ? Number(id) : id;
}

/** node:sqlite INTEGER satırları BigInt dönebilir — JSON/Socket.io için sayıya çevir */
export function normalizeSqlId(value) {
  if (value == null) return value;
  return typeof value === "bigint" ? Number(value) : value;
}

export function normalizeEventRow(row) {
  if (!row) return null;
  return {
    id: normalizeSqlId(row.id),
    roomId: row.roomId,
    kind: row.kind,
    message: row.message,
    highlight: Boolean(row.highlight),
    createdAt: row.createdAt,
  };
}

export const roomRepo = {
  create({ id, userId, name, botName, winMessage, wrongMessage, questionsJson }) {
    getDb()
      .prepare(
        `INSERT INTO rooms (id, user_id, name, bot_name, win_message, wrong_message, questions_json)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        id,
        userId,
        name,
        botName ?? "BulmacaBot",
        winMessage,
        wrongMessage,
        questionsJson ?? "[]"
      );
  },

  findById(id) {
    return getDb().prepare("SELECT * FROM rooms WHERE id = ?").get(id);
  },

  listByUser(userId) {
    return getDb()
      .prepare("SELECT * FROM rooms WHERE user_id = ? ORDER BY created_at DESC")
      .all(userId);
  },

  update(id, patch) {
    const fields = [];
    const values = [];
    const allowed = [
      "name",
      "bot_name",
      "video_id",
      "live_chat_id",
      "announce_wrong",
      "win_message",
      "wrong_message",
      "questions_json",
      "game_mode",
      "stream_url_draft",
      "photo_battle_settings_json",
    ];
    for (const key of allowed) {
      if (patch[key] !== undefined) {
        fields.push(`${key} = ?`);
        values.push(patch[key]);
      }
    }
    if (!fields.length) return;
    values.push(id);
    getDb()
      .prepare(`UPDATE rooms SET ${fields.join(", ")} WHERE id = ?`)
      .run(...values);
  },

  delete(id) {
    getDb().prepare("DELETE FROM rooms WHERE id = ?").run(id);
  },

  updateGameState(id, gameStateJson) {
    getDb()
      .prepare("UPDATE rooms SET game_state_json = ? WHERE id = ?")
      .run(gameStateJson, id);
  },

  updateRaceSettings(id, settingsJson) {
    getDb()
      .prepare("UPDATE rooms SET race_settings_json = ? WHERE id = ?")
      .run(settingsJson, id);
  },
};

export const raceRepo = {
  saveSettings(roomId, settings) {
    roomRepo.updateRaceSettings(roomId, JSON.stringify(settings ?? {}));
  },

  loadSettings(roomId) {
    const row = getDb()
      .prepare("SELECT race_settings_json FROM rooms WHERE id = ?")
      .get(roomId);
    if (!row?.race_settings_json) return null;
    try {
      return JSON.parse(row.race_settings_json);
    } catch {
      return null;
    }
  },

  appendRound(roomId, row) {
    const database = getDb();
    const result = database
      .prepare(
        `INSERT INTO room_race_rounds
          (room_id, round, team_code, team_name, flag_url, spawn_count, win_reason, end_kind, won_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        roomId,
        row.round,
        row.teamCode,
        row.teamName,
        row.flagUrl || null,
        Number(row.spawnCount) || 0,
        row.winReason || null,
        row.endKind || null,
        row.at || new Date().toISOString()
      );

    const id = insertRowId(result);
    database
      .prepare(
        `DELETE FROM room_race_rounds
         WHERE room_id = ?
           AND id NOT IN (
             SELECT id FROM room_race_rounds
             WHERE room_id = ?
             ORDER BY id DESC
             LIMIT 120
           )`
      )
      .run(roomId, roomId);

    return id;
  },

  listRounds(roomId, limit = 30) {
    return getDb()
      .prepare(
        `SELECT round, team_code AS teamCode, team_name AS teamName, flag_url AS flagUrl,
                spawn_count AS spawnCount, win_reason AS winReason, end_kind AS endKind,
                won_at AS at
         FROM room_race_rounds
         WHERE room_id = ?
         ORDER BY id DESC
         LIMIT ?`
      )
      .all(roomId, limit)
      .reverse();
  },

  clearRounds(roomId) {
    getDb().prepare("DELETE FROM room_race_rounds WHERE room_id = ?").run(roomId);
  },
};

export const auditRepo = {
  append({ roomId, userId = null, category, level, message, detail }) {
    const database = getDb();
    const detailJson = detail ? JSON.stringify(detail) : null;
    const result = database
      .prepare(
        `INSERT INTO audit_events (room_id, user_id, category, level, message, detail_json)
         VALUES (?, ?, ?, ?, ?, ?)`
      )
      .run(roomId, userId, category, level, message, detailJson);

    const id = insertRowId(result);
    database
      .prepare(
        `DELETE FROM audit_events
         WHERE room_id = ?
           AND id NOT IN (
             SELECT id FROM audit_events
             WHERE room_id = ?
             ORDER BY id DESC
             LIMIT 500
           )`
      )
      .run(roomId, roomId);

    const row = database
      .prepare(
        `SELECT id, room_id AS roomId, user_id AS userId, category, level, message,
                detail_json AS detailJson, created_at AS createdAt
         FROM audit_events WHERE id = ?`
      )
      .get(id);
    return normalizeAuditRow(row);
  },

  listByRoom(roomId, limit = 150, category = null) {
    const database = getDb();
    const rows = category
      ? database
          .prepare(
            `SELECT id, room_id AS roomId, user_id AS userId, category, level, message,
                    detail_json AS detailJson, created_at AS createdAt
             FROM audit_events
             WHERE room_id = ? AND category = ?
             ORDER BY id DESC
             LIMIT ?`
          )
          .all(roomId, category, limit)
      : database
          .prepare(
            `SELECT id, room_id AS roomId, user_id AS userId, category, level, message,
                    detail_json AS detailJson, created_at AS createdAt
             FROM audit_events
             WHERE room_id = ?
             ORDER BY id DESC
             LIMIT ?`
          )
          .all(roomId, limit);
    return rows.reverse().map(normalizeAuditRow);
  },

  clearRoom(roomId) {
    getDb().prepare("DELETE FROM audit_events WHERE room_id = ?").run(roomId);
  },
};

function normalizeAuditRow(row) {
  if (!row) return null;
  let detail = null;
  if (row.detailJson) {
    try {
      detail = JSON.parse(row.detailJson);
    } catch {
      detail = { raw: row.detailJson };
    }
  }
  return {
    id: row.id,
    at: row.createdAt,
    roomId: row.roomId,
    userId: row.userId,
    category: row.category,
    level: row.level,
    message: row.message,
    detail,
  };
}

export const eventRepo = {
  append({ roomId, message, highlight = false, kind = "info" }) {
    const database = getDb();
    const result = database
      .prepare(
        `INSERT INTO room_events (room_id, kind, message, highlight)
         VALUES (?, ?, ?, ?)`
      )
      .run(roomId, kind, message, highlight ? 1 : 0);

    const id = insertRowId(result);
    database
      .prepare(
        `DELETE FROM room_events
       WHERE room_id = ?
         AND id NOT IN (
           SELECT id FROM room_events
           WHERE room_id = ?
           ORDER BY id DESC
           LIMIT 250
         )`
      )
      .run(roomId, roomId);

    const row = database
      .prepare(
        `SELECT id, room_id AS roomId, kind, message, highlight, created_at AS createdAt
         FROM room_events WHERE id = ?`
      )
      .get(id);
    return normalizeEventRow(row);
  },

  listByRoom(roomId, limit = 100) {
    const rows = getDb()
      .prepare(
        `SELECT id, room_id AS roomId, kind, message, highlight, created_at AS createdAt
         FROM room_events
         WHERE room_id = ?
         ORDER BY id DESC
         LIMIT ?`
      )
      .all(roomId, limit);
    return rows.reverse().map(normalizeEventRow);
  },
};
