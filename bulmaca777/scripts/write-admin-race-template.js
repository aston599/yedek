import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const playHtml = fs.readFileSync(
  path.join(__dirname, "../public/play/index.html"),
  "utf8"
).replace(/^\uFEFF/, "");

const header =
  playHtml.match(/<header class="play-topbar"[\s\S]*?<\/header>/i)?.[0] || "";
let main =
  playHtml.match(/<main class="play-body[\s\S]*?<\/main>/i)?.[0] || "";

const headerAdmin = header
  .replace('class="play-topbar"', 'class="play-topbar play-topbar--embed"')
  .replace(/<nav class="play-topbar-nav"[\s\S]*?<\/nav>\s*/i, "");

main = main.replace('class="play-body hidden"', 'class="play-body"');

const out = `  <div class="play-room-hub__inner">
    <p id="playBlocked" class="play-blocked hidden" role="alert"></p>
    <p id="playLoading" class="play-loading">Sunucuya bağlanılıyor…</p>
    <p class="play-autopilot hidden" id="autopilotBanner" role="status"></p>
${headerAdmin}
${main}
  </div>`;

const file = `/** Admin icinde gomulu canli panel — play/index.html ile senkron. */\nexport const ADMIN_RACE_MOUNT_HTML = \`${out}\`;\n`;
const target = path.join(__dirname, "../public/team-race/admin-race-template.js");
fs.writeFileSync(target, "\uFEFF" + file, "utf8");
console.log("OK", target, out.length);
