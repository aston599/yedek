import { eventRepo } from "./db.js";

/**
 * Oda günlüğü — SQLite + isteğe bağlı Socket.io yayını.
 * @param {import('socket.io').Server} io
 */
export function createRoomLogger(io) {
  return function appendRoomLog(roomId, message, options = {}) {
    const { highlight = false, kind = "info" } = options;
    const text = String(message || "").trim();
    if (!text) return null;

    const row = eventRepo.append({
      roomId,
      message: text,
      highlight: Boolean(highlight),
      kind,
    });

    const payload = row;

    io?.to(roomId).emit("room:log", payload);
    return payload;
  };
}
