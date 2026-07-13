/**
 * Ön ayar ↔ sunucu normalize uyumu
 * node scripts/test-play-presets.js
 */
import { dirname, join } from "path";
import { fileURLToPath, pathToFileURL } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const presetsUrl = pathToFileURL(join(__dirname, "../public/play/play-race-presets.js")).href;
const raceModesUrl = pathToFileURL(join(__dirname, "../server/teamRace/raceModes.js")).href;

const { PLAY_RACE_PRESETS, findMatchingRacePresetKey, normalizeRaceSettingsForPresetMatch } =
  await import(presetsUrl);
const { normalizeRaceSettings } = await import(raceModesUrl);

const results = [];
function ok(name, cond, detail = "") {
  results.push({ name, pass: !!cond, detail });
  console.log(`[${cond ? "OK" : "FAIL"}] ${name}${detail ? ` — ${detail}` : ""}`);
}

for (const key of Object.keys(PLAY_RACE_PRESETS)) {
  const preset = PLAY_RACE_PRESETS[key].settings;
  const server = normalizeRaceSettings({
    ...preset,
    gatherDurationMs: (preset.gatherDurationSec || 300) * 1000,
  });
  const matched = findMatchingRacePresetKey(server);
  ok(`preset ${key} matches after server normalize`, matched === key, `got=${matched}`);
}

const fast = normalizeRaceSettingsForPresetMatch(PLAY_RACE_PRESETS.standard_auto_fast.settings);
ok("fast gather 75s", fast.gatherDurationSec === 75);
ok("fast autopilot on", fast.autopilot === true);

const failed = results.filter((r) => !r.pass);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
if (failed.length) process.exit(1);
console.log("Ön ayar testi tamam.");
