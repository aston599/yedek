import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  unlinkSync,
  readdirSync,
} from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { newPhotoId } from "./engine.js";

const DATA_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "data");

function poolDir(roomId) {
  return join(DATA_ROOT, "rooms", roomId, "photo-pool");
}

function imagesDir(roomId) {
  return join(poolDir(roomId), "images");
}

function manifestPath(roomId) {
  return join(poolDir(roomId), "manifest.json");
}

function mediaUrl(roomId, filename) {
  return `/media/rooms/${roomId}/photo-pool/images/${filename}`;
}

export function loadPhotoPool(roomId) {
  const dir = imagesDir(roomId);
  const mp = manifestPath(roomId);
  if (!existsSync(mp)) return [];
  try {
    const list = JSON.parse(readFileSync(mp, "utf-8"));
    if (!Array.isArray(list)) return [];
    return list
      .filter((e) => e?.id && e?.filename)
      .map((e) => ({
        id: e.id,
        filename: e.filename,
        label: e.label || "",
        imageUrl: mediaUrl(roomId, e.filename),
        eliminated: false,
      }))
      .filter((e) => existsSync(join(dir, e.filename)));
  } catch {
    return [];
  }
}

export function savePhotoManifest(roomId, entries) {
  const dir = poolDir(roomId);
  mkdirSync(imagesDir(roomId), { recursive: true });
  const manifest = entries.map(({ id, filename, label }) => ({
    id,
    filename,
    label: label || "",
  }));
  writeFileSync(manifestPath(roomId), JSON.stringify(manifest, null, 2), "utf-8");
}

export function addPhotoFromBase64(roomId, { name, dataBase64, label }) {
  const match = String(dataBase64 || "").match(/^data:image\/(\w+);base64,(.+)$/);
  const ext = match ? (match[1] === "jpeg" ? "jpg" : match[1].replace(/[^a-z]/gi, "")) : "jpg";
  const b64 = match ? match[2] : String(dataBase64 || "").replace(/\s/g, "");
  if (!b64) {
    const err = new Error("Geçersiz görsel verisi");
    err.status = 400;
    throw err;
  }
  const buf = Buffer.from(b64, "base64");
  if (buf.length > 8 * 1024 * 1024) {
    const err = new Error("Görsel en fazla 8 MB olabilir");
    err.status = 400;
    throw err;
  }
  const id = newPhotoId();
  const filename = `${id}.${ext === "png" ? "png" : "jpg"}`;
  mkdirSync(imagesDir(roomId), { recursive: true });
  writeFileSync(join(imagesDir(roomId), filename), buf);
  const safeLabel =
    String(label || name || "")
      .trim()
      .slice(0, 80) || `Görsel ${id.slice(0, 4)}`;
  const pool = loadPhotoPool(roomId);
  pool.push({
    id,
    filename,
    label: safeLabel,
    imageUrl: mediaUrl(roomId, filename),
    eliminated: false,
  });
  savePhotoManifest(
    roomId,
    pool.map((p) => ({ id: p.id, filename: p.filename, label: p.label }))
  );
  return pool[pool.length - 1];
}

export function removePhotoFromPool(roomId, photoId) {
  const pool = loadPhotoPool(roomId);
  const item = pool.find((p) => p.id === photoId);
  if (!item) return pool;
  const next = pool.filter((p) => p.id !== photoId);
  try {
    unlinkSync(join(imagesDir(roomId), item.filename));
  } catch {
    /* yoksay */
  }
  savePhotoManifest(
    roomId,
    next.map((p) => ({ id: p.id, filename: p.filename, label: p.label }))
  );
  return next;
}

export function clearPhotoPool(roomId) {
  const dir = imagesDir(roomId);
  if (existsSync(dir)) {
    for (const f of readdirSync(dir)) {
      try {
        unlinkSync(join(dir, f));
      } catch {
        /* yoksay */
      }
    }
  }
  savePhotoManifest(roomId, []);
  return [];
}
