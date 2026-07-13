import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = join(__dirname, "..", "public");

const adminIndex = `<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>YouTube Bulmacaları — Panel</title>
  <link rel="stylesheet" href="admin.css" />
  <script src="/socket.io/socket.io.js"></script>
</head>
<body>
  <TAG id="setupScreen" class="app setup">
    <header class="brand">
      <h1>YouTube Bulmacaları</h1>
      <p class="subtitle">Merhaba, <strong id="currentUser">-</strong> · <a href="#" id="btnLogout">Çıkış</a></p>
    </header>
    <section class="panel guide">
      <h2>Nasıl çalışır?</h2>
      <ol class="steps">
        <li><strong>Yayın oluştur</strong> — aşağıdan bir isim verin.</li>
        <li><strong>Soruları yazın</strong> — sırayla sorulur; doğru bilince sonrakine geçilir.</li>
        <li><strong>OBS</strong> — linki tarayıcı kaynağı olarak ekleyin.</li>
        <li><strong>YouTube</strong> — canlı yayını bağlayın, <em>Başlat</em> deyin.</li>
      </ol>
    </section>
    <section class="panel">
      <h2>Yayınlarım</h2>
      <ul id="roomList" class="room-list"></ul>
    </section>
    <section class="panel">
      <h2>Yeni yayın</h2>
      <p class="help">Örnek: Cumartesi akşam yayını…</p>
      <input id="newRoomName" placeholder="Yayın adı (örn. KanalAdı)" />
      <button class="btn primary" id="btnCreateRoom" type="button">Yayın oluştur</button>
    </section>
  </TAG>
  <TAG id="dashboard" class="app hidden">
    <header class="brand">
      <p class="brand-tag">YouTube Bulmacaları</p>
      <h1 id="roomName">Yayın</h1>
      <p class="subtitle">Kod: <code id="roomIdDisplay">-</code></p>
    </header>
    <section class="panel guide compact">
      <h2>Hızlı başlangıç</h2>
      <ol class="steps">
        <li>Soruları düzenleyip <strong>Kaydet</strong></li>
        <li>OBS linkini kopyalayıp tarayıcı kaynağı ekleyin</li>
        <li>YouTube canlı yayın + video ID</li>
        <li><strong>Başlat</strong> — doğru cevap = sıradaki soru</li>
      </ol>
    </section>
    <section class="panel">
      <h2>Kontrol</h2>
      <TAG class="status-grid">
        <TAG class="stat"><span class="stat-label">YouTube</span><span id="authStatus">-</span></TAG>
        <TAG class="stat"><span class="stat-label">Durum</span><span id="gameState">-</span></TAG>
        <TAG class="stat"><span class="stat-label">Sıra</span><span id="questionOrder">-</span></TAG>
      </TAG>
      <TAG class="actions-row">
        <a class="btn secondary" id="authLink" href="#">YouTube bağla</a>
        <button class="btn primary" id="btnStart">Başlat</button>
        <button class="btn" id="btnStop">Durdur</button>
        <button class="btn" id="btnSkip">Sonraki soru (atla)</button>
      </TAG>
    </section>
    <section class="panel">
      <h2>Sorular (sırayla)</h2>
      <p class="help">1. sorudan başlar. Doğru cevap gelince sohbette tebrik ve otomatik sonraki soru.</p>
      <TAG id="questionsEditor"></TAG>
      <TAG class="actions-row">
        <button class="btn" id="btnAddQuestion">+ Soru ekle</button>
        <button class="btn primary" id="btnSaveQuestions">Soruları kaydet</button>
      </TAG>
    </section>
    <section class="panel">
      <h2>OBS ekranı</h2>
      <p class="help">OBS → Kaynak Ekle → <strong>Tarayıcı</strong>. <strong>Şeffaf arka plan</strong> açık olsun.</p>
      <TAG class="url-box"><label>Yatay (1920×1080)</label><code id="urlHorizontal"></code><button class="copy" data-target="urlHorizontal">Kopyala</button></TAG>
      <TAG class="url-box"><label>Dikey (1080×1920)</label><code id="urlVertical"></code><button class="copy" data-target="urlVertical">Kopyala</button></TAG>
    </section>
    <section class="panel">
      <h2>YouTube canlı yayın</h2>
      <p class="help">Yayın <strong>canlı</strong> iken <code>v=</code> kodunu yazın.</p>
      <input id="videoId" placeholder="Video ID" />
      <button class="btn" id="btnSaveVideo" type="button">Kaydet</button>
    </section>
    <section class="panel">
      <h2>Sohbet botu</h2>
      <p class="help"><code>[Bot adı] mesaj</code> formatında yazar.</p>
      <label>Bot adı</label>
      <input id="botName" placeholder="YouTube Bulmacaları" />
      <label><input type="checkbox" id="announceWrong" checked /> Yanlış cevaplara da yaz</label>
      <label>Doğru mesaj</label>
      <input id="winMessage" placeholder="Tebrikler {user}! Doğru: {answer}" />
      <label>Yanlış mesaj</label>
      <input id="wrongMessage" placeholder="{user}, olmadı. Tekrar dene!" />
      <button class="btn" id="btnSaveBot" type="button">Bot ayarlarını kaydet</button>
    </section>
    <section class="panel mock-panel hidden" id="mockPanel">
      <h2>Test modu</h2>
      <TAG class="mock-form">
        <input id="mockAuthor" value="Testİzleyici" />
        <input id="mockText" placeholder="Cevap" />
        <button class="btn primary" id="btnMockSend">Gönder</button>
      </TAG>
    </section>
    <section class="panel"><h2>Günlük</h2><ul class="log" id="log"></ul></section>
  </TAG>
  <script src="admin.js"></script>
</body>
</html>`;

const loginIndex = `<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Giriş — YouTube Bulmacaları</title>
  <link rel="stylesheet" href="/admin/admin.css" />
  <link rel="stylesheet" href="login.css" />
</head>
<body>
  <TAG class="login-wrap">
    <TAG class="panel login-card">
      <h1>YouTube Bulmacaları</h1>
      <p class="help">Canlı yayında bulmaca soruları. İzleyiciler yoruma cevap yazar; doğru bilince sıradaki soruya geçilir.</p>
      <TAG class="tabs">
        <button type="button" class="tab active" data-tab="login">Giriş</button>
        <button type="button" class="tab" data-tab="register">Kayıt ol</button>
      </TAG>
      <form id="formLogin" class="tab-panel">
        <label>Kullanıcı adı</label>
        <input name="username" required autocomplete="username" />
        <label>Şifre</label>
        <input name="password" type="password" required autocomplete="current-password" />
        <button type="submit" class="btn primary">Giriş yap</button>
      </form>
      <form id="formRegister" class="tab-panel hidden">
        <label>Kullanıcı adı (en az 3 harf)</label>
        <input name="username" required />
        <label>Şifre (en az 6 karakter)</label>
        <input name="password" type="password" required />
        <button type="submit" class="btn primary">Hesap oluştur</button>
      </form>
      <p class="error hidden" id="error"></p>
    </TAG>
  </TAG>
  <script src="login.js"></script>
</body>
</html>`;

const overlayIndex = `<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>YouTube Bulmacaları</title>
  <link rel="stylesheet" href="overlay.css" />
  <script src="/socket.io/socket.io.js"></script>
</head>
<body>
  <TAG class="layout" id="layout">
    <header class="top-bar">
      <span class="badge">YOUTUBE BULMACALARI</span>
      <span class="counter" id="counter">Soru 0 / 0</span>
    </header>
    <main class="stage">
      <TAG class="idle" id="idle">
        <p class="idle-title">Hazır…</p>
        <p class="idle-sub">Panelden Başlat deyin. Doğru cevap = sıradaki soru.</p>
      </TAG>
      <article class="question-card hidden" id="questionCard">
        <p class="label" id="orderLabel">SORU 1</p>
        <h1 class="question-text" id="questionText"></h1>
        <p class="hint" id="hintText"></p>
        <p class="instruction">Cevabı canlı yayın yorumuna yazın!</p>
      </article>
      <article class="winner-card hidden" id="winnerCard">
        <p class="label winner-label">DOĞRU!</p>
        <h2 class="winner-name" id="winnerName"></h2>
        <p class="winner-answer" id="winnerAnswer"></p>
        <p class="next-hint">Sıradaki soruya geçiliyor…</p>
      </article>
      <article class="ended-card hidden" id="endedCard">
        <p class="ended-title">Tüm sorular bitti</p>
        <p class="ended-sub">YouTube Bulmacaları</p>
      </article>
    </main>
    <footer class="progress-bar">
      <TAG class="progress-fill" id="progressFill"></TAG>
    </footer>
  </TAG>
  <script src="overlay.js"></script>
</body>
</html>`;

const rootIndex = `<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="refresh" content="0;url=/login/" />
  <title>YouTube Bulmacaları</title>
</head>
<body>
  <p><a href="/login/">YouTube Bulmacaları</a></p>
</body>
</html>`;

function tagToDiv(html) {
  return html.replace(/<TAG/g, "<div").replace(/<\/TAG>/g, "</div>");
}

const map = {
  "admin/index.html": adminIndex,
  "login/index.html": loginIndex,
  "overlay/index.html": overlayIndex,
  "index.html": rootIndex,
};

for (const [rel, html] of Object.entries(map)) {
  writeFileSync(join(publicDir, rel), tagToDiv(html), "utf8");
  console.log("OK", rel);
}
