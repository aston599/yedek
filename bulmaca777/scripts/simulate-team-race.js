/**
 * Takım yarışı motoru — yerel simülasyon (sunucu/DB gerekmez).
 * Çalıştır: node scripts/simulate-team-race.js
 */
import { TeamRaceEngine } from "../server/teamRace/engine.js";
import { resolveTeamFromText } from "../server/teamRace/aliases.js";
import {
  buildSimulatedChatMessage,
} from "../server/teamRace/audienceSimulator.js";
import {
  canStartRaceRound,
  getRaceSeriesStatus,
  normalizeRaceSettings,
} from "../server/teamRace/raceModes.js";

const results = [];
function ok(name, cond, detail = "") {
  results.push({ name, pass: !!cond, detail });
  const mark = cond ? "OK" : "FAIL";
  console.log(`[${mark}] ${name}${detail ? ` — ${detail}` : ""}`);
}

// Alias
ok("alias gs", resolveTeamFromText("gs") === "gs");
ok("alias fener", resolveTeamFromText("fenerbahce") === "fb");
ok("alias unknown", resolveTeamFromText("xyz123") === null);

const engine = new TeamRaceEngine({
  settings: { minParticipants: 2, minTeams: 2, minTotalSpawns: 2 },
});
const events = { state: 0, spawn: 0 };
engine.onStateChange = () => {
  events.state += 1;
};
engine.onSpawn = () => {
  events.spawn += 1;
};

ok("start idle", engine.getSnapshot().phase === "idle");
engine.start();
ok("start running", engine.getSnapshot().phase === "running" && engine.getSnapshot().round === 1);

engine.handleChatMessage({
  id: "pre",
  author: "X",
  channelId: "pre",
  text: "gs",
});
engine.start();
ok("start clears arena", engine.getSnapshot().entityCount === 0);

const spawn1 = engine.handleChatMessage({
  id: "m1",
  author: "Ali",
  channelId: "ch-ali",
  text: "gs",
});
ok("spawn gs", spawn1.type === "spawn" && spawn1.entity.teamCode === "gs");

const dup = engine.handleChatMessage({
  id: "m1",
  author: "Ali",
  channelId: "ch-ali",
  text: "gs",
});
ok("duplicate ignored", dup.type === "ignored");

const cooldown = engine.handleChatMessage({
  id: "m2",
  author: "Ali",
  channelId: "ch-ali",
  text: "fener",
});
ok("cooldown same channel", cooldown.type === "cooldown");

const spawn2 = engine.handleChatMessage({
  id: "m3",
  author: "Veli",
  channelId: "ch-veli",
  text: "bjk",
});
ok("spawn bjk", spawn2.type === "spawn");

const stopped = engine.stop();
ok("stop idle", stopped.phase === "idle");
ok("winner picked", stopped.lastWinner?.teamCode === "gs" || stopped.lastWinner?.teamCode === "bjk");

const blob = engine.serializeState();
const engine2 = new TeamRaceEngine();
engine2.restoreState(blob);
ok("restore phase", engine2.phase === "idle");
ok("restore winner", engine2.lastWinner?.teamCode === stopped.lastWinner?.teamCode);

engine.reset();
ok("reset clean", engine.getSnapshot().round === 0 && !engine.getSnapshot().lastWinner);

ok("events fired", events.state >= 3 && events.spawn >= 2);

const auto = new TeamRaceEngine();
let roundEndCount = 0;
auto.onRoundEnd = () => {
  roundEndCount += 1;
};
auto.start();
auto.handleChatMessage({ id: "a1", author: "A", channelId: "c1", text: "gs" });
auto.handleChatMessage({ id: "a2", author: "B", channelId: "c2", text: "fener" });
const gsId = auto.entities.find((e) => e.teamCode === "gs")?.id;
ok("auto round has 2 teams", Object.keys(auto.getActiveCountsByTeam()).length === 2);
auto.tryEnterChaos("force");
auto.chaosStartedAt = new Date(Date.now() - 60_000).toISOString();
if (gsId) auto.eliminateEntity(gsId);
ok("auto end after one team left", auto.phase === "idle" && roundEndCount === 1);
ok("auto winner fb", auto.lastWinner?.teamCode === "fb");

const gather = new TeamRaceEngine({
  settings: {
    gatherDurationMs: 60_000,
    chaosMinEntities: 2,
    chaosTrigger: "count",
    minParticipants: 2,
    minTeams: 2,
    minTotalSpawns: 2,
  },
});
gather.start();
ok("starts gathering", gather.roundPhase === "gathering");
gather.handleChatMessage({ id: "g1", author: "A", channelId: "c1", text: "gs" });
gather.handleChatMessage({ id: "g2", author: "B", channelId: "c2", text: "fener" });
ok("count chaos blocked before min gather", !gather.isChaos());
gather.roundStartedAt = new Date(Date.now() - 61_000).toISOString();
ok(
  "chaos when pool full after min gather",
  gather.checkGatheringProgress() && gather.isChaos()
);

const timeStrict = new TeamRaceEngine({
  settings: {
    gatherDurationMs: 120_000,
    chaosMinEntities: 2,
    chaosTrigger: "time",
    minParticipants: 2,
    minTeams: 2,
    minTotalSpawns: 2,
  },
});
timeStrict.start();
timeStrict.handleChatMessage({ id: "ts1", author: "A", channelId: "c1", text: "gs" });
timeStrict.handleChatMessage({ id: "ts2", author: "B", channelId: "c2", text: "fener" });
ok("time trigger waits for timer", !timeStrict.isChaos());
timeStrict.roundStartedAt = new Date(Date.now() - 140_000).toISOString();
ok("time trigger enters chaos on timeout", timeStrict.checkGatheringProgress() && timeStrict.isChaos());

const stall = new TeamRaceEngine({
  settings: {
    chaosMinEntities: 2,
    chaosTrigger: "count",
    minParticipants: 3,
    minTeams: 2,
    minTotalSpawns: 3,
  },
});
stall.start();
stall.handleChatMessage({ id: "s1", author: "A", channelId: "c1", text: "gs" });
stall.handleChatMessage({ id: "s2", author: "B", channelId: "c2", text: "fener" });
ok("chaos blocked low engagement", !stall.isChaos() && stall.gatherBlockedReason);
stall.forceChaos();
ok("manual force chaos", stall.isChaos());

const chaosMulti = new TeamRaceEngine({
  settings: {
    chaosSpawnCooldownMs: 5000,
    spawnCooldownMs: 25_000,
    maxPerChannel: 1,
    minParticipants: 1,
    minTeams: 1,
    minTotalSpawns: 1,
  },
});
chaosMulti.start();
chaosMulti.forceChaos();
const m1 = chaosMulti.handleChatMessage({
  id: "m-ch1",
  author: "Ali",
  channelId: "ch-ali",
  text: "gs",
});
ok("chaos spawn locked", m1.type === "chaos_locked");
const m2 = chaosMulti.handleChatMessage({
  id: "m-ch2",
  author: "Ali",
  channelId: "ch-ali",
  text: "gs",
});
ok("chaos repeat stays locked", m2.type === "chaos_locked");
const m3 = chaosMulti.handleChatMessage({
  id: "m-ch3",
  author: "Ali",
  channelId: "ch-ali",
  text: "gs",
});
const aliActive = chaosMulti.entities.filter(
  (e) => e.channelId === "ch-ali" && !e.eliminated
).length;
ok("chaos prevents extra balls while eliminating", m3.type === "chaos_locked" && aliActive === 0);

const timeUp = new TeamRaceEngine({
  settings: {
    gatherDurationMs: 60_000,
    chaosTrigger: "manual",
    minParticipants: 1,
    minTeams: 1,
    minTotalSpawns: 1,
  },
});
timeUp.start();
timeUp.handleChatMessage({ id: "t1", author: "A", channelId: "c1", text: "gs" });
timeUp._channelLastSpawn.set("c2", 0);
timeUp.handleChatMessage({ id: "t2", author: "B", channelId: "c2", text: "fener" });
timeUp.roundStartedAt = new Date(Date.now() - 120_000).toISOString();
ok("chaos when gather timer ends", timeUp.checkGatheringProgress() && timeUp.isChaos());

const manualStrict = new TeamRaceEngine({
  settings: {
    gatherDurationMs: 120_000,
    chaosMinEntities: 2,
    chaosTrigger: "manual",
    minParticipants: 2,
    minTeams: 2,
    minTotalSpawns: 2,
  },
});
manualStrict.start();
manualStrict.handleChatMessage({ id: "mns1", author: "A", channelId: "c1", text: "gs" });
manualStrict.handleChatMessage({ id: "mns2", author: "B", channelId: "c2", text: "fener" });
ok("manual trigger does not auto-chaos on pool", !manualStrict.isChaos());

const grace = new TeamRaceEngine({
  settings: { chaosEliminationGraceMs: 5000, chaosMinDurationMs: 60_000, minTeams: 1, minParticipants: 1, minTotalSpawns: 1 },
});
grace.start();
grace.handleChatMessage({ id: "g1", author: "A", channelId: "c1", text: "gs" });
grace.forceChaos();
const elimDuringGrace = grace.eliminateEntity(grace.entities[0].id);
ok("chaos grace blocks elimination", !elimDuringGrace && grace.isRunning());

const lowEngStop = new TeamRaceEngine({
  settings: { minParticipants: 5, minTeams: 2, minTotalSpawns: 5 },
});
lowEngStop.start();
lowEngStop.handleChatMessage({ id: "l1", author: "A", channelId: "c1", text: "gs" });
const stoppedLow = lowEngStop.stop();
ok("no winner without engagement", !stoppedLow.lastWinner);

const ctaEng = new TeamRaceEngine();
ctaEng.handleChatMessage({ id: "c1", author: "Ali", text: "abone ol" });
ok("cta subscribe from chat", ctaEng.getArenaCtas().subscribe.active);
ctaEng.handleChatMessage({ id: "c2", author: "Veli", text: "2 kere tıkla" });
ok("cta like from chat", ctaEng.getArenaCtas().like.active);

ok("maxRounds default 8", normalizeRaceSettings({}).maxRounds === 8);
const eightWins = Array.from({ length: 8 }, (_, i) => ({ round: i + 1, teamCode: "gs" }));
const seriesDone = getRaceSeriesStatus({ maxRounds: 8 }, eightWins);
ok("series complete at 8", seriesDone.seriesComplete && seriesDone.completedRounds === 8);
ok("block start after series", !canStartRaceRound({ maxRounds: 8 }, eightWins));
ok("can start mid series", canStartRaceRound({ maxRounds: 8 }, eightWins.slice(0, 3)));

const top = new TeamRaceEngine();
top.start();
top.handleChatMessage({ id: "r1", author: "Ali", channelId: "yt-ali", text: "gs" });
top.handleChatMessage({ id: "r2", author: "Veli", channelId: "yt-veli", text: "gs" });
for (let i = 0; i < 8; i++) {
  const m = buildSimulatedChatMessage(`Bot${i}`, "fb");
  top.handleChatMessage(m);
}
const leaders = top.getTopViewers(5);
ok(
  "top viewers real first",
  leaders[0].author === "Ali" && leaders[1].author === "Veli" && leaders[0].simulated === false
);
ok("top viewers sim tagged", leaders.some((v) => v.simulated));

const failed = results.filter((r) => !r.pass);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
if (failed.length) {
  console.error("Failed:", failed.map((f) => f.name).join(", "));
  process.exit(1);
}
console.log("Simülasyon tamam — takım yarışı motoru hazır.");
