/**
 * Ünlü yaş + API smoke test
 * node scripts/test-celebrity-quiz.js [roomId] [baseUrl]
 */
const roomId = process.argv[2] || "f2493157";
const base = (process.argv[3] || "http://127.0.0.1:3847").replace(/\/$/, "");

async function get(path) {
  const res = await fetch(`${base}${path}`);
  const text = await res.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text.slice(0, 200) };
  }
  return { status: res.status, json };
}

async function main() {
  console.log("=== Ünlü Yaş Sistemi Test ===\n");
  console.log("Oda:", roomId, "| Sunucu:", base, "\n");

  const health = await get("/api/health");
  console.log("1. Health:", health.status, health.json?.ok ? "OK" : health.json);
  if (!health.json?.ok) {
    console.error("Sunucu çalışmıyor. baslat.cmd çalıştırın.");
    process.exit(1);
  }

  const info = await get("/api/app/chat-info");
  console.log("2. Sohbet modu:", info.json?.chatMode);
  console.log("   ", info.json?.readMethodLabel);
  console.log("   Liste limiti:", info.json?.puzzleFeedMax, "kişi");

  const preview = await get("/api/celebrity-sample/preview");
  console.log("3. Örnek ünlü:", preview.status, "→", preview.json?.count, "satır");

  const status = await get(`/api/rooms/${roomId}/status`);
  console.log("4. Oda durumu:", status.status);
  if (status.json?.game) {
    console.log(
      "   Sorular:",
      status.json.game.totalQuestions,
      "| Durum:",
      status.json.game.state,
      "| Listede:",
      status.json.puzzleFeedCount ?? status.json.game.feed?.length,
      "/",
      status.json.puzzleFeedMax
    );
  }
  console.log("   Mod:", status.json?.config?.gameMode, "| Ünlü paketi:", status.json?.celebrityQuiz);
  console.log("   YouTube bağlı:", status.json?.youtube?.connected);

  const imp = await fetch(`${base}/api/rooms/${roomId}/questions/import-celebrities`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ csv: "Test Kişi,40,01.01.1985,https://upload.wikimedia.org/wikipedia/commons/3/34/Hande_Er%C3%A7el.jpg", hint: "Test", mode: "append" }),
  });
  console.log(
    "5. import-celebrities (giriş yok):",
    imp.status,
    imp.status === 401 ? "beklenen — admin giriş gerekli" : await imp.text().then((t) => t.slice(0, 80))
  );

  const overlay = await get(`/celebrity-overlay?room=${roomId}`);
  console.log("6. OBS ekranı HTML:", overlay.status, overlay.status === 200 ? "OK" : "HATA");

  console.log("\n--- Önerilen test URL ---");
  console.log(`${base}/play/celebrity-quiz-lab.html?room=${roomId}`);
  console.log(`${base}/celebrity-overlay?room=${roomId}`);
  console.log(`${base}/admin/?room=${roomId}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
