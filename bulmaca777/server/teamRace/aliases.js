import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DEFAULT_ALIASES_PATH = join(__dirname, "..", "..", "data", "team-race", "aliases.json");

let cachedMap = null;

function normalizeText(input) {
  return String(input || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/ı/g, "i")
    .replace(/İ/g, "i");
}

export function loadAliasMap(path = DEFAULT_ALIASES_PATH) {
  if (!existsSync(path)) {
    return new Map();
  }
  const raw = JSON.parse(readFileSync(path, "utf-8"));
  const map = new Map();
  for (const [alias, code] of Object.entries(raw)) {
    const key = normalizeText(alias);
    if (key) map.set(key, String(code).toLowerCase());
  }
  return map;
}

export function getAliasMap() {
  if (!cachedMap) cachedMap = loadAliasMap();
  return cachedMap;
}

/**
 * Sohbet metninden takım eşleşmesi (kısaltma veya tam ad: gs, Galatasaray, …) veya null.
 * Önce tam metin, sonra kelime kelime dener.
 */
export function resolveTeamFromText(text, aliasMap = getAliasMap()) {
  const norm = normalizeText(text);
  if (!norm) return null;

  if (aliasMap.has(norm)) return aliasMap.get(norm);

  const tokens = norm.split(/[\s,;|/]+/).filter(Boolean);
  for (const token of tokens) {
    if (aliasMap.has(token)) return aliasMap.get(token);
  }

  for (const [alias, code] of aliasMap) {
    if (alias.length >= 4 && norm.includes(alias)) return code;
  }

  return null;
}
