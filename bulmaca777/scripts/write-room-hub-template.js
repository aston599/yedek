import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const playHtml = fs.readFileSync(
  path.join(__dirname, "../public/play/index.html"),
  "utf8"
).replace(/^\uFEFF/, "");

const main =
  playHtml.match(/<main class="play-body[\s\S]*?<\/main>/i)?.[0] || "";
const body = main.replace('class="play-body hidden"', 'class="play-body"');

const header = `  <header class="play-topbar play-topbar--embed" id="playTopbar">
    <div class="play-topbar-brand">
      <p class="play-kicker">Canlı panel</p>
      <h2 class="play-title">Bayrak yarışı</h2>
    </div>
    <div class="play-topbar-meta">
      <span class="play-phase-pill" id="phaseLabel">Beklemede</span>
      <span class="play-round-pill" id="roundLabel">Tur —</span>
      <span class="play-stat-pill">Arena <strong id="statArena">0</strong></span>
      <span class="play-stat-pill">Spawn <strong id="statSpawns">0</strong></span>
      <span class="play-stat-pill">Eşleşmeyen <strong id="statUnmatched">0</strong></span>
    </div>
    <div class="play-control-group">
      <button type="button" class="btn btn-sm btn-accent" id="btnChaos">Kaos</button>
      <button type="button" class="btn btn-sm btn-warning" id="btnShock">💥 Şok</button>
    </div>
  </header>
  <p id="playBlocked" class="play-blocked hidden" role="alert"></p>
  <p id="playLoading" class="play-loading">Yükleniyor…</p>
  <p class="play-autopilot hidden" id="autopilotBanner" role="status"></p>`;

const out = header + "\n" + body;

const file = `/** Admin onizleme paneline gomulu bayrak yarisi arayuzu. */\nexport const ROOM_HUB_MOUNT_HTML = \`${out}\`;\n`;
const target = path.join(__dirname, "../public/team-race/room-hub-template.js");
fs.writeFileSync(target, "\uFEFF" + file, "utf8");
console.log("OK", target, out.length);
