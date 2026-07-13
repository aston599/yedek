/**
 * Oyun alanı API uçtan uca testi
 * node scripts/test-playground-api.js [port]
 */
const PORT = Number(process.argv[2]) || 3847;
const BASE = `http://127.0.0.1:${PORT}`;

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`${path} ${res.status}: ${data.error || res.statusText}`);
  return data;
}

async function main() {
  const health = await req("/api/health");
  if (!health.playgroundEnabled) throw new Error("PLAYGROUND kapalı");

  const { sessionId } = await req("/api/playground/team-race/session", {
    method: "POST",
    body: {
      spawnCooldownMs: 1000,
      gatherRepeatCooldownMs: 300,
      chaosEliminationGraceMs: 1000,
      chaosMinDurationMs: 3000,
    },
  });

  const started = await req("/api/playground/team-race/start", {
    method: "POST",
    body: { sessionId },
  });
  if (started.snapshot.phase !== "running") throw new Error("start phase");
  if (started.snapshot.round !== 1) throw new Error("round");

  const c1 = await req("/api/playground/team-race/chat", {
    method: "POST",
    body: { sessionId, author: "A1", text: "gs" },
  });
  if (c1.result.type !== "spawn") throw new Error("spawn gs");

  const c2 = await req("/api/playground/team-race/chat", {
    method: "POST",
    body: { sessionId, author: "B1", text: "fener" },
  });
  if (c2.result.type !== "spawn") throw new Error("spawn fb");

  const c3 = await req("/api/playground/team-race/chaos", {
    method: "POST",
    body: { sessionId, enabled: true },
  });
  if (!c3.snapshot?.chaos) throw new Error("chaos open");

  const gsId = c1.lastSpawn.id;
  const elim = await req("/api/playground/team-race/eliminate", {
    method: "POST",
    body: { sessionId, entityId: gsId },
  });
  if (elim.roundEnded) throw new Error("round should NOT auto-end before min chaos");

  const chaos = await req("/api/playground/team-race/chaos", {
    method: "POST",
    body: { sessionId, enabled: true },
  });
  if (!chaos.snapshot?.chaos) throw new Error("chaos");

  console.log("OK — playground API akışı (erken bitiş koruması) çalışıyor");
  console.log("  session:", sessionId);
  console.log("  chaos min duration:", chaos.snapshot.settings.chaosMinDurationMs);
  console.log("  kalan takımlar:", Object.keys(elim.snapshot.activeByTeam || {}));
}

main().catch((e) => {
  console.error("FAIL:", e.message);
  console.error("Sunucuyu baslat.cmd ile başlatın.");
  process.exit(1);
});
