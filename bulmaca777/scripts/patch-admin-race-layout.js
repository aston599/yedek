import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const p = path.join(__dirname, "../public/admin/index.html");
let h = fs.readFileSync(p, "utf8");

const lines = [
  '    <aside class="panel preview-panel hidden" id="previewPanelRace" aria-label="OBS önizleme">',
  "      <h2>OBS önizleme</h2>",
  '      <p class="help">Yayında görünecek overlay. Canlı arena ve Başlat için <a href="#" id="btnOpenRaceStudioAside">canlı stüdyoyu</a> açın.</p>',
  '      <div class="preview-toolbar">',
  '        <button type="button" class="btn preview-layout-btn active" data-preview-layout="vertical">1080×1920</button>',
  '        <button type="button" class="btn preview-layout-btn" data-preview-layout="horizontal">1920×1080</button>',
  '        <a class="btn secondary" id="previewOpenLinkRace" href="#" target="_blank" rel="noopener">Yeni sekme</a>',
  '        <button type="button" class="btn" id="btnPreviewRefreshRace">Yenile</button>',
  "      </div>",
  '      <div class="preview-stage preview-stage--obs" id="previewStageObs" data-preview-layout="vertical">',
  '        <p class="preview-load-error hidden" id="previewLoadErrorRace" role="status"></p>',
  '        <div class="preview-viewport">',
  '          <iframe id="previewFrameObs" class="preview-frame--hidden" title="OBS overlay önizleme"></iframe>',
  "        </div>",
  "      </div>",
  "    </aside>",
  "",
];
const replacement = lines.join("\n");

if (!h.includes('id="raceWorkspace"')) {
  console.error("raceWorkspace not found");
  process.exit(1);
}

h = h.replace(/    <section id="raceWorkspace"[\s\S]*?    <\/section>\n/, replacement);

fs.writeFileSync(p, h);
console.log("patched", p);
