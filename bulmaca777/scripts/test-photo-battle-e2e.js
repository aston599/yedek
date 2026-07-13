/**
 * Photo Quiz uçtan uca API testi (mock sohbet, yerel sunucu)
 * Kullanım: CHAT_MODE=mock node server/index.js  (ayrı terminal)
 *           node scripts/test-photo-battle-e2e.js
 */
const BASE = process.env.TEST_BASE || "http://127.0.0.1:3847";
const USER = process.env.TEST_USER || `pbtest_${Date.now().toString(36)}`;
const PASS = process.env.TEST_PASS || "test1234";

/** 1x1 kırmızı PNG */
const TINY_PNG =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function req(path, opts = {}, cookie = "") {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (cookie) headers.Cookie = cookie;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text };
  }
  return { res, json };
}

function getCookie(res) {
  const set = res.headers.getSetCookie?.() || [];
  const line = set.find((c) => c.startsWith("session="));
  if (line) return line.split(";")[0];
  const h = res.headers.get("set-cookie");
  if (!h) return "";
  const m = h.match(/session=[^;]+/);
  return m ? m[0] : "";
}

async function main() {
  console.log("Photo Quiz E2E →", BASE);

  let r = await req("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username: USER, password: PASS }),
  });
  if (!r.res.ok && r.res.status !== 409) {
    r = await req("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: USER, password: PASS }),
    });
  }
  if (!r.res.ok) {
    r = await req("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: USER, password: PASS }),
    });
  }
  const cookie = getCookie(r.res);
  if (!cookie) {
    console.error("Giriş başarısız", r.res.status, r.json);
    process.exit(1);
  }
  console.log("[OK] Giriş:", USER);

  r = await req(
    "/api/rooms",
    {
      method: "POST",
      body: JSON.stringify({ name: "Photo Quiz test", gameMode: "photo-battle" }),
    },
    cookie
  );
  if (!r.res.ok) {
    console.error("Oda oluşturulamadı", r.json);
    process.exit(1);
  }
  const roomId = r.json.id;
  console.log("[OK] Oda:", roomId);

  const images = [1, 2, 3, 4].map((n) => ({
    name: `test${n}.png`,
    dataBase64: TINY_PNG,
    label: `Test ${n}`,
  }));

  r = await req(
    `/api/rooms/${roomId}/photo-battle/pool`,
    { method: "POST", body: JSON.stringify({ images }) },
    cookie
  );
  if (!r.res.ok || (r.json.pool?.length || 0) < 2) {
    console.error("Havuz yüklenemedi", r.json);
    process.exit(1);
  }
  console.log("[OK] Havuz:", r.json.pool.length, "görsel");

  r = await req(`/api/rooms/${roomId}/game/start`, { method: "POST", body: "{}" }, cookie);
  const snap = r.json.photoBattle || r.json;
  if (!r.res.ok || snap.phase !== "voting") {
    console.error("Başlatılamadı", r.json);
    process.exit(1);
  }
  console.log("[OK] Tur başladı — kalan süre ms:", snap.voteRemainingMs);

  r = await req(
    `/api/rooms/${roomId}/chat/test`,
    {
      method: "POST",
      body: JSON.stringify({ author: "@ali", text: "1" }),
    },
    cookie
  );
  if (!r.res.ok) {
    console.error("Oy testi", r.json);
    process.exit(1);
  }
  console.log("[OK] Test oy 1:", r.json.result?.type);

  r = await req(`/api/rooms/${roomId}/status`);
  const pb = r.json.photoBattle;
  console.log(
    "[OK] Overlay durumu — sol:",
    pb?.voteBar?.leftVotes,
    "sağ:",
    pb?.voteBar?.rightVotes,
    "bar%:",
    pb?.voteBar?.leftPct?.toFixed(1)
  );

  console.log("\n--- Tarayıcıda aç ---");
  console.log("Panel:  ", `${BASE}/admin/?room=${roomId}`);
  console.log("OBS:    ", `${BASE}/overlay?room=${roomId}&mode=photo-battle&layout=vertical&motion=1`);
  console.log("\nPanelde Başlat / görselleri değiştir; sohbet testine 1 ve 2 yazın.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
