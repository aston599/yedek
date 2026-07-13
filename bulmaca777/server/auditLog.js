import { auditRepo } from "./db.js";
import { normalizeStreamUrlDraft } from "./utils.js";

const MAX_MEMORY = 400;
const SENSITIVE_KEYS = /^(password|secret|token|cookie|authorization|google_client_secret)$/i;

let ioRef = null;
const memory = [];
const memoryByRoom = new Map();

export function initAuditLog(io) {
  ioRef = io;
}

export function auditEnabled() {
  return !["0", "false", "off", "no"].includes(
    String(process.env.AUDIT_LOG ?? "1").toLowerCase()
  );
}

function persistEnabled() {
  return (
    auditEnabled() &&
    !["0", "false", "off", "no"].includes(
      String(process.env.AUDIT_LOG_PERSIST ?? "1").toLowerCase()
    )
  );
}

function consoleEnabled() {
  return (
    auditEnabled() &&
    !["0", "false", "off", "no"].includes(
      String(process.env.AUDIT_LOG_CONSOLE ?? "1").toLowerCase()
    )
  );
}

function sanitizeValue(key, value) {
  if (SENSITIVE_KEYS.test(String(key || ""))) return "[redacted]";
  if (value == null) return value;
  const s = String(value);
  if (s.length > 280) return `${s.slice(0, 280)}…`;
  return value;
}

export function sanitizePayload(obj, depth = 0) {
  if (obj == null || depth > 4) return obj;
  if (Array.isArray(obj)) {
    return obj.slice(0, 30).map((v) => sanitizePayload(v, depth + 1));
  }
  if (typeof obj !== "object") return obj;
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    if (SENSITIVE_KEYS.test(k)) {
      out[k] = "[redacted]";
      continue;
    }
    if (k === "streamUrl" || k === "streamUrlDraft" || k === "url") {
      out[k] = sanitizeStreamField(v);
      continue;
    }
    if (typeof v === "object" && v !== null) {
      out[k] = sanitizePayload(v, depth + 1);
    } else {
      out[k] = sanitizeValue(k, v);
    }
  }
  return out;
}

function sanitizeStreamField(v) {
  const s = normalizeStreamUrlDraft(v);
  if (!s.trim()) {
    if (v && typeof v === "object") return { invalid: "object", keys: Object.keys(v).slice(0, 8) };
    return "";
  }
  const ids = s.match(/[a-zA-Z0-9_-]{11}/g) || [];
  if (ids.length) return { videoIds: [...new Set(ids)], len: s.length };
  return { preview: s.slice(0, 120), len: s.length };
}

function pushMemory(entry) {
  memory.unshift(entry);
  if (memory.length > MAX_MEMORY) memory.length = MAX_MEMORY;
  if (entry.roomId) {
    const rid = entry.roomId;
    if (!memoryByRoom.has(rid)) memoryByRoom.set(rid, []);
    const arr = memoryByRoom.get(rid);
    arr.unshift(entry);
    if (arr.length > MAX_MEMORY) arr.length = MAX_MEMORY;
  }
}

function emitSocket(entry) {
  if (!ioRef || !entry.roomId) return;
  ioRef.to(entry.roomId).emit("audit:log", entry);
}

/**
 * @param {object} opts
 * @param {string} [opts.roomId]
 * @param {number|null} [opts.userId]
 * @param {string} opts.category — api|youtube|chat|game|config|persist|room|system
 * @param {string} [opts.level] — debug|info|warn|error
 * @param {string} opts.message
 * @param {object} [opts.detail]
 */
export function auditRecord(opts) {
  if (!auditEnabled()) return null;

  const entry = {
    at: new Date().toISOString(),
    roomId: opts.roomId || null,
    userId: opts.userId ?? null,
    category: String(opts.category || "system").slice(0, 32),
    level: String(opts.level || "info").slice(0, 16),
    message: String(opts.message || "").slice(0, 500),
    detail: opts.detail ? sanitizePayload(opts.detail) : null,
  };

  pushMemory(entry);

  if (persistEnabled() && entry.roomId) {
    try {
      const row = auditRepo.append(entry);
      if (row) Object.assign(entry, { id: row.id });
    } catch (err) {
      console.error("[Audit persist]", err.message);
    }
  }

  if (consoleEnabled()) {
    const detailStr = entry.detail
      ? ` ${JSON.stringify(entry.detail)}`
      : "";
    const rid = entry.roomId ? ` room=${entry.roomId}` : "";
    console.log(
      `[Audit][${entry.level}][${entry.category}]${rid} ${entry.message}${detailStr}`
    );
  }

  emitSocket(entry);
  return entry;
}

export function auditApiRequest(req) {
  const roomId = req.params?.roomId;
  auditRecord({
    roomId,
    userId: req.user?.id ?? null,
    category: "api",
    level: "debug",
    message: `${req.method} ${req.originalUrl || req.url}`,
    detail: {
      query: sanitizePayload(req.query),
      body: sanitizePayload(req.body),
    },
  });
}

export function auditApiResponse(req, res, ms) {
  const roomId = req.params?.roomId;
  const level = res.statusCode >= 500 ? "error" : res.statusCode >= 400 ? "warn" : "info";
  auditRecord({
    roomId,
    userId: req.user?.id ?? null,
    category: "api",
    level,
    message: `${res.statusCode} ${req.method} ${req.originalUrl || req.url} (${ms}ms)`,
  });
}

export function listAuditLog(roomId, { limit = 150, category = null } = {}) {
  const mem = memoryByRoom.get(roomId) || [];
  let items = [...mem];
  if (persistEnabled()) {
    const dbRows = auditRepo.listByRoom(roomId, limit, category);
    const seen = new Set(items.map((e) => e.id).filter(Boolean));
    for (const row of dbRows) {
      if (!row.id || seen.has(row.id)) continue;
      items.push(row);
    }
  }
  items.sort((a, b) => String(b.at).localeCompare(String(a.at)));
  if (category) {
    items = items.filter((e) => e.category === category);
  }
  return items.slice(0, limit);
}

export function clearAuditLog(roomId) {
  memoryByRoom.delete(roomId);
  for (let i = memory.length - 1; i >= 0; i--) {
    if (memory[i].roomId === roomId) memory.splice(i, 1);
  }
  if (persistEnabled()) auditRepo.clearRoom(roomId);
  if (ioRef) ioRef.to(roomId).emit("audit:log:clear");
  return { ok: true };
}
