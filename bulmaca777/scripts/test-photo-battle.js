import { PhotoBattleEngine } from "../server/photoBattle/engine.js";
import { parsePhotoVote } from "../server/photoBattle/votes.js";

let ok = 0;
let fail = 0;

function assert(name, cond, detail = "") {
  if (cond) {
    ok++;
    console.log(`[OK] ${name}${detail ? ` — ${detail}` : ""}`);
  } else {
    fail++;
    console.log(`[FAIL] ${name}${detail ? ` — ${detail}` : ""}`);
  }
}

assert("parse 1", parsePhotoVote("1") === 1);
assert("parse 2", parsePhotoVote("2") === 2);
assert("parse bir", parsePhotoVote("bir") === 1);
assert("parse iki", parsePhotoVote("iki") === 2);

const eng = new PhotoBattleEngine({ roomId: "test" });
eng.setPool([
  { id: "a", imageUrl: "/a.jpg", label: "A" },
  { id: "b", imageUrl: "/b.jpg", label: "B" },
  { id: "c", imageUrl: "/c.jpg", label: "C" },
  { id: "d", imageUrl: "/d.jpg", label: "D" },
]);
eng.updateSettings({ voteDurationSec: 1, resultHoldSec: 0.1 });

eng.start();
assert("started voting", eng.phase === "voting");
eng.handleChatMessage({ author: "@u1", text: "1", channelId: "c1" });
eng.handleChatMessage({ author: "@u2", text: "2", channelId: "c2" });
assert("votes counted", eng.left.votes >= 1 && eng.right.votes >= 1);

eng.skipVote();
assert("after skip", eng.phase === "voting" || eng.phase === "result" || eng.phase === "champion");

console.log(`\n${ok}/${ok + fail} passed`);
process.exit(fail ? 1 : 0);
