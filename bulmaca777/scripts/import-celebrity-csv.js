/**
 * Ünlü CSV → oda questions.json
 * node scripts/import-celebrity-csv.js ROOM_ID [csv-file]
 */
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { parseCelebrityCsv } from "../server/celebrityImport.js";

const roomId = process.argv[2];
const csvPath = process.argv[3];
if (!roomId) {
  console.error("Kullanım: node scripts/import-celebrity-csv.js ROOM_ID [dosya.csv]");
  process.exit(1);
}

const csv = csvPath
  ? readFileSync(csvPath, "utf-8")
  : readFileSync(join(process.cwd(), "scripts", "celebrity-sample.csv"), "utf-8");

const questions = parseCelebrityCsv(csv);
const dir = join(process.cwd(), "data", "rooms", roomId);
mkdirSync(dir, { recursive: true });
writeFileSync(join(dir, "questions.json"), JSON.stringify(questions, null, 2), "utf-8");
console.log(`OK: ${questions.length} soru → data/rooms/${roomId}/questions.json`);
