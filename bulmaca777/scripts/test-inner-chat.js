#!/usr/bin/env node
/**
 * InnerChat (youtube-chat) — Ubuntu / VPS tanı testi
 *
 *   node scripts/test-inner-chat.js "https://www.youtube.com/watch?v=VIDEO_ID"
 *   node scripts/test-inner-chat.js VIDEO_ID --diagnose
 *   node scripts/test-inner-chat.js VIDEO_ID --seconds=30
 */

import {
  applyYoutubeAxiosDefaults,
  diagnoseYoutubeWatchPage,
  patchYoutubeChatFetch,
} from "../server/youtubePageFetch.js";
import { parseYouTubeVideoIds } from "../server/utils.js";

applyYoutubeAxiosDefaults();
patchYoutubeChatFetch();
const { LiveChat } = await import("youtube-chat");

const argv = process.argv.slice(2);
const diagnoseOnly = argv.includes("--diagnose");
const args = argv.filter((a) => !a.startsWith("-"));
const maxSec = Number(
  argv.find((f) => f.startsWith("--seconds="))?.split("=")[1] ||
    process.env.INNER_CHAT_TEST_SECONDS ||
    0
);
const limit = Number(process.env.INNER_CHAT_TEST_LIMIT || 50);

const input = args.join(" ").trim() || process.env.STREAM_URL || "";
const videoIds = parseYouTubeVideoIds(input);

if (!videoIds.length) {
  console.error("Kullanım: node scripts/test-inner-chat.js <watch URL veya video ID> [--diagnose]");
  process.exit(1);
}

const videoId = videoIds[0];
const pollMs = 2000;

async function runDiagnose() {
  console.log("=== YouTube watch sayfası tanısı (VPS) ===\n");
  const d = await diagnoseYoutubeWatchPage(videoId);
  console.log(JSON.stringify(d, null, 2));
  console.log("\nİpuçları:");
  for (const h of d.hints) console.log(" •", h);
  return d.parse?.innerChatWouldWork ? 0 : 3;
}

if (diagnoseOnly) {
  process.exit(await runDiagnose());
}

console.log("=== InnerChat test (youtube-chat) ===");
console.log("Node:", process.version);
console.log("Video ID:", videoId);
console.log("URL:", `https://www.youtube.com/watch?v=${videoId}`);
console.log("Poll:", pollMs, "ms");
if (maxSec > 0) console.log("Süre limiti:", maxSec, "sn");
console.log("—".repeat(50));

const liveChat = new LiveChat({ liveId: videoId }, pollMs);
let count = 0;
let started = false;
let stopping = false;

function formatChat(item) {
  const author = item?.author?.name || "Anonim";
  const text =
    typeof item?.message === "string"
      ? item.message
      : Array.isArray(item?.message)
        ? item.message
            .map((p) => (typeof p === "string" ? p : p?.text || p?.emojiText || ""))
            .join("")
            .trim()
        : String(item?.message || "");
  const ts = item?.timestamp instanceof Date ? item.timestamp.toISOString() : "";
  return { author, text, ts };
}

liveChat.on("chat", (item) => {
  const { author, text, ts } = formatChat(item);
  if (!text) return;
  count += 1;
  const line = ts ? `[${ts}] ` : "";
  console.log(`${line}@${author}: ${text}`);
  if (count >= limit) {
    console.log(`\n--- ${limit} mesaj (limit) ---`);
    shutdown(0);
  }
});

liveChat.on("end", (reason) => {
  console.warn("\n[end]", reason || "Yayın sona erdi");
  shutdown(count > 0 ? 0 : 1);
});

liveChat.on("error", (err) => {
  console.warn("\n[error]", err?.message || err);
});

async function main() {
  console.log("Önce sayfa tanısı…\n");
  const d = await diagnoseYoutubeWatchPage(videoId);
  const p = d.parse;
  console.log(
    `HTTP ${d.httpStatus} | HTML ${p?.htmlBytes ?? "?"} bayt | istenen=${p?.requestedVideoId ?? videoId} | sayfa canonical=${p?.pageCanonicalId ?? "—"} | dinlenen=${p?.canonicalVideoId ?? "—"} | innerChatOK=${p?.innerChatWouldWork}${d.innertubeFallback ? " (innertube)" : ""}`
  );
  if (d.strategies) console.log("Stratejiler:", d.strategies);
  if ((p?.blockKind === "bot" || p?.botHint) && !p?.innerChatWouldWork) {
    console.log(
      "\nVPS bot duvari: .env dosyasina YOUTUBE_HTTP_PROXY veya tarayicidan YOUTUBE_CONSENT_COOKIE ekleyin."
    );
    console.log("Detay: docs/INNERCHAT-TANI.md\n");
  }
  if (
    p?.pageCanonicalId &&
    p?.requestedVideoId &&
    p.pageCanonicalId !== p.requestedVideoId
  ) {
    console.log(
      " ! Sayfada farklı video görünüyor; dinleme yine de istenen ID ile yapılır."
    );
  }
  if (!d.parse?.innerChatWouldWork) {
    for (const h of d.hints) console.log(" !", h);
    console.log("\n--diagnose ile tam JSON: node scripts/test-inner-chat.js", videoId, "--diagnose");
  }
  console.log("\nBağlanılıyor (youtube-chat)…\n");

  const ok = await liveChat.start();
  if (!ok) {
    console.error("\n[start FAILED]");
    console.error("  Tanı ve ipuçları için:");
    console.error(`  node scripts/test-inner-chat.js ${videoId} --diagnose`);
    process.exit(2);
  }
  started = true;
  console.log("[start OK] Sohbet dinleniyor. Ctrl+C ile çık.\n");
}

function shutdown(code = 0) {
  if (stopping) return;
  stopping = true;
  try {
    liveChat.stop();
  } catch {
    /* yoksay */
  }
  if (count > 0) console.log(`\nToplam ${count} mesaj.`);
  process.exit(code);
}

process.on("SIGINT", () => {
  console.log("\nCtrl+C");
  shutdown(0);
});

if (maxSec > 0) {
  setTimeout(() => {
    console.log(`\n--- ${maxSec} sn ---`);
    shutdown(0);
  }, maxSec * 1000);
}

main().catch((err) => {
  console.error("[fatal]", err.message);
  process.exit(1);
});
