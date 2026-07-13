/**
 * Play arayüzü HTML + admin/hub şablonlarını UTF-8 olarak yeniden üretir.
 * baslat.cmd başında çalıştırın.
 */
import { spawnSync } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

const steps = [
  "write-play-index.js",
  "write-admin-race-template.js",
  "write-room-hub-template.js",
];

for (const name of steps) {
  const r = spawnSync(process.execPath, [path.join(__dirname, name)], {
    cwd: root,
    stdio: "inherit",
    encoding: "utf8",
  });
  if (r.status !== 0) {
    process.exit(r.status ?? 1);
  }
}

console.log("UI sablonlari guncellendi (UTF-8).");
