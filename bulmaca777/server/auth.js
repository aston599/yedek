import { randomBytes, scryptSync, timingSafeEqual } from "crypto";
import { getDb } from "./db.js";

const SESSION_DAYS = 30;

function hashPassword(password) {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

function verifyPassword(password, stored) {
  const [salt, hash] = stored.split(":");
  if (!salt || !hash) return false;
  const attempt = scryptSync(password, salt, 64);
  const expected = Buffer.from(hash, "hex");
  if (attempt.length !== expected.length) return false;
  return timingSafeEqual(attempt, expected);
}

function newToken() {
  return randomBytes(32).toString("hex");
}

export function registerUser(username, password) {
  const name = String(username || "").trim();
  if (name.length < 3) {
    const err = new Error("Kullanıcı adı en az 3 karakter");
    err.status = 400;
    throw err;
  }
  if (!password || password.length < 6) {
    const err = new Error("Şifre en az 6 karakter");
    err.status = 400;
    throw err;
  }

  try {
    const result = getDb()
      .prepare("INSERT INTO users (username, password_hash) VALUES (?, ?)")
      .run(name, hashPassword(password));
    const rowId = result.lastInsertRowid;
    return {
      id: typeof rowId === "bigint" ? Number(rowId) : rowId,
      username: name,
    };
  } catch (e) {
    const msg = String(e?.message || "");
    if (e.code === "SQLITE_CONSTRAINT_UNIQUE" || msg.includes("UNIQUE")) {
      const err = new Error("Bu kullanıcı adı alınmış");
      err.status = 409;
      throw err;
    }
    throw e;
  }
}

export function loginUser(username, password) {
  const row = getDb()
    .prepare("SELECT * FROM users WHERE username = ? COLLATE NOCASE")
    .get(String(username || "").trim());
  if (!row || !verifyPassword(password, row.password_hash)) {
    const err = new Error("Kullanıcı adı veya şifre hatalı");
    err.status = 401;
    throw err;
  }
  return createSession(row.id, row.username);
}

export function createSession(userId, username) {
  const token = newToken();
  const expires = new Date();
  expires.setDate(expires.getDate() + SESSION_DAYS);
  getDb()
    .prepare("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)")
    .run(token, userId, expires.toISOString());
  return {
    token,
    expiresAt: expires.toISOString(),
    user: { id: Number(userId), username },
  };
}

export function getSession(token) {
  if (!token) return null;
  const row = getDb()
    .prepare(
      `SELECT s.token, s.expires_at, u.id AS user_id, u.username
       FROM sessions s JOIN users u ON u.id = s.user_id
       WHERE s.token = ?`
    )
    .get(token);
  if (!row) return null;
  if (new Date(row.expires_at) < new Date()) {
    getDb().prepare("DELETE FROM sessions WHERE token = ?").run(token);
    return null;
  }
  return {
    token: row.token,
    user: { id: Number(row.user_id), username: row.username },
  };
}

export function logoutSession(token) {
  if (token) getDb().prepare("DELETE FROM sessions WHERE token = ?").run(token);
}

export function attachSession(req, _res, next) {
  const token =
    req.cookies?.session ||
    (req.headers.authorization?.startsWith("Bearer ")
      ? req.headers.authorization.slice(7)
      : null);
  const session = getSession(token);
  req.user = session?.user ?? null;
  req.sessionToken = session?.token ?? null;
  next();
}

export function requireUser(req, res, next) {
  if (!req.user) {
    return res.status(401).json({ error: "Giriş gerekli" });
  }
  next();
}

export function setSessionCookie(res, token) {
  const maxAge = SESSION_DAYS * 24 * 60 * 60 * 1000;
  const secure =
    process.env.COOKIE_SECURE === "true" ||
    (process.env.COOKIE_SECURE !== "false" &&
      process.env.NODE_ENV === "production");
  res.cookie("session", token, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    maxAge,
    path: "/",
  });
}

export function clearSessionCookie(res) {
  const secure =
    process.env.COOKIE_SECURE === "true" ||
    (process.env.COOKIE_SECURE !== "false" &&
      process.env.NODE_ENV === "production");
  res.clearCookie("session", { path: "/", secure, sameSite: "lax" });
}
