/**
 * Futbol paketi + cevap eşleştirme (sunucu gerekmez)
 * node scripts/test-football-pack.js
 */
import { footballPlayersToQuestions } from "../server/football/footballImport.js";
import {
  matchFootballAnswer,
  getTeamKeywords,
  getCountryKeywords,
} from "../server/football/footballMatch.js";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const clubQs = footballPlayersToQuestions("club");
const natQs = footballPlayersToQuestions("nationality");

assert(clubQs.length === 30, `club soru sayısı 30 olmalı, got ${clubQs.length}`);
assert(natQs.length === 30, `nationality soru sayısı 30 olmalı, got ${natQs.length}`);

const q0 = clubQs.find((q) => q.meta?.name === "Lionel Messi");
assert(q0, "Messi sorusu yok");
assert(matchFootballAnswer("inter miami", q0), "Messi: inter miami");
assert(matchFootballAnswer("IMCF", q0), "Messi: IMCF");
assert(!matchFootballAnswer("barcelona", q0), "Messi: barcelona yanlış");

const arda = clubQs.find((q) => q.meta?.name === "Arda Güler");
assert(matchFootballAnswer("rm", arda), "Arda: rm");
assert(matchFootballAnswer("real madrid", arda), "Arda: real madrid");

const icardi = clubQs.find((q) => q.meta?.name === "Mauro Icardi");
assert(icardi, "Icardi yok");
assert(matchFootballAnswer("gs", icardi), "Icardi: gs");

const modriNat = natQs.find((q) => q.meta?.name === "Luka Modrić");
assert(matchFootballAnswer("hrvatska", modriNat) || matchFootballAnswer("croatia", modriNat), "Modrić milliyet");

const teams = Object.keys(getTeamKeywords()).length;
const countries = Object.keys(getCountryKeywords()).length;
assert(teams >= 20, `takım sözlüğü: ${teams}`);
assert(countries >= 15, `ülke sözlüğü: ${countries}`);

console.log("OK — futbol paketi:", clubQs.length, "oyuncu,", teams, "takım,", countries, "ülke");
