/** Admin icinde gomulu canli panel — play/index.html ile senkron. */
export const ADMIN_RACE_MOUNT_HTML = `  <div class="play-room-hub__inner">
    <p id="playBlocked" class="play-blocked hidden" role="alert"></p>
    <p id="playLoading" class="play-loading">Sunucuya bağlanılıyor…</p>
    <p class="play-autopilot hidden" id="autopilotBanner" role="status"></p>
<header class="play-topbar play-topbar--embed" id="playTopbar">
    <div class="play-topbar-brand">
      <p class="play-kicker">Bulmaca777</p>
      <h1 class="play-title">Bayrak yarışı</h1>
      <p class="play-room-tag hidden" id="roomTag"></p>
    </div>
    <div class="play-topbar-meta">
      <span class="play-phase-pill" id="phaseLabel">Beklemede</span>
      <span class="play-round-pill" id="roundLabel">Tur —</span>
      <span class="play-stat-pill">Arena <strong id="statArena">0</strong></span>
      <span class="play-stat-pill">Spawn <strong id="statSpawns">0</strong></span>
      <span class="play-stat-pill">Eşleşmeyen <strong id="statUnmatched">0</strong></span>
    </div>
    <div class="play-topbar-controls" aria-label="Tur kontrolleri">
      <div class="play-control-group play-control-group--primary">
        <button type="button" class="btn btn-primary btn-sm" id="btnStart" title="Yeni tur başlat">▶ Başlat</button>
        <button type="button" class="btn btn-sm" id="btnStop" title="Turı durdur">■ Durdur</button>
        <button type="button" class="btn btn-sm btn-danger" id="btnReset" title="Skor ve turları sıfırla">↺ Sıfırla</button>
      </div>
      <div class="play-control-group">
        <button type="button" class="btn btn-sm btn-accent" id="btnChaos" title="Toplanmayı atla, kaosu başlat">⚡ Kaos</button>
        <button type="button" class="btn btn-sm btn-warning" id="btnShock" title="Canlı şok dalgası tetikle">💥 Şok</button>
        <button type="button" class="btn btn-sm btn-accent" id="btnAutoSim" title="Sahte sohbet mesajları">💬 Sim</button>
        <button type="button" class="btn btn-sm btn-ghost" id="btnScenarioMenu" title="Sahne önizleme menüsü">🧪 Sahne</button>
      </div>
    </div>
    </header>
<main class="play-body" id="playMain">
    <aside class="play-dock play-dock--left" aria-label="Tur ve ayarlar">
      <div class="play-dock-block">
        <h2 class="play-dock-title">Tur ayarları</h2>
        <div class="play-preset-block">
          <div class="play-preset-head">
            <h3 class="play-dock-subtitle">Ön ayarlar</h3>
            <span class="play-preset-status" id="presetActiveLabel" aria-live="polite">—</span>
          </div>
          <div class="play-preset-grid" role="group" aria-label="Tur ön ayarları">
            <button type="button" class="play-preset-btn" data-race-preset="standard_auto" aria-pressed="false">
              <span class="play-preset-btn__title">Standart</span>
              <span class="play-preset-btn__sub">Otomatik</span>
            </button>
            <button type="button" class="play-preset-btn" data-race-preset="standard_auto_fast" aria-pressed="false">
              <span class="play-preset-btn__title">Hızlı</span>
              <span class="play-preset-btn__sub">Otomatik + sim</span>
            </button>
            <button type="button" class="play-preset-btn" data-race-preset="sim_lab" aria-pressed="false">
              <span class="play-preset-btn__title">Simülasyon</span>
              <span class="play-preset-btn__sub">Stres testi</span>
            </button>
            <button type="button" class="play-preset-btn" data-race-preset="manual" aria-pressed="false">
              <span class="play-preset-btn__title">Manuel</span>
              <span class="play-preset-btn__sub">Siz yönetin</span>
            </button>
            <button type="button" class="play-preset-btn play-preset-btn--wide" data-race-preset="chaos" aria-pressed="false">
              <span class="play-preset-btn__title">Yoğun kaos</span>
              <span class="play-preset-btn__sub">Dolu havuz · kısa tur</span>
            </button>
          </div>
          <p class="play-preset-hint muted" id="presetHint">Seçince ayarlar SQL’e kaydedilir.</p>
        </div>
        <div class="play-settings-grid play-settings-grid--auto">
          <label class="play-compact-field play-compact-field--check">
            <input type="checkbox" id="raceAutopilotOn" checked /> Otomatik tur
          </label>
          <label class="play-compact-field play-compact-field--check">
            <input type="checkbox" id="raceAutoStartOn" checked /> Bağlanınca başlat
          </label>
          <label class="play-compact-field play-compact-field--check">
            <input type="checkbox" id="raceRequireYt" /> YouTube şart
          </label>
          <label class="play-compact-field play-compact-field--check">
            <input type="checkbox" id="raceAudienceSimOn" checked /> Sessizlikte yapay sohbet
          </label>
          <label class="play-compact-field">
            <span>Toplam tur</span>
            <input type="number" id="raceMaxRounds" min="1" max="30" value="8" title="Kaç tur oynanacak (kazananlar listelenir)" />
          </label>
          <label class="play-compact-field">
            <span>Sonraki tur (sn)</span>
            <input type="number" id="autoNextRoundSec" min="4" max="120" value="12" />
          </label>
          <label class="play-compact-field">
            <span>Yeniden dene (sn)</span>
            <input type="number" id="autoRetryRoundSec" min="10" max="300" value="45" />
          </label>
          <label class="play-compact-field">
            <span>Kaos hazırlık (sn)</span>
            <input type="number" id="chaosGraceSec" min="2" max="20" value="5" title="Kaos başlayınca elenme yok" />
          </label>
          <label class="play-compact-field">
            <span>Min. kaos (sn)</span>
            <input type="number" id="chaosMinSec" min="5" max="90" value="12" title="Tur en erken bu süre sonra biter" />
          </label>
        </div>
        <div class="play-settings-grid">
          <label class="play-compact-field">
            <span>Toplanma (sn)</span>
            <input type="range" id="gatherDurationRange" min="60" max="600" value="300" />
            <output id="gatherDurationOut">300</output>
          </label>
          <label class="play-compact-field">
            <span>Min. kişi</span>
            <input type="range" id="minParticipantsRange" min="1" max="15" value="3" />
            <output id="minParticipantsOut">3</output>
          </label>
          <label class="play-compact-field">
            <span>Min. takım</span>
            <input type="range" id="minTeamsRange" min="2" max="8" value="2" />
            <output id="minTeamsOut">2</output>
          </label>
          <label class="play-compact-field">
            <span>Min. spawn</span>
            <input type="range" id="minSpawnsRange" min="1" max="20" value="3" />
            <output id="minSpawnsOut">3</output>
          </label>
          <label class="play-compact-field">
            <span>Kaos top</span>
            <input type="range" id="chaosMinRange" min="4" max="40" value="8" />
            <output id="chaosMinOut">8</output>
          </label>
          <label class="play-compact-field">
            <span>Kaosta tekrar (sn)</span>
            <input type="range" id="cooldownRange" min="2" max="25" value="5" />
            <output id="cooldownOut">5</output>
          </label>
          <label class="play-compact-field play-compact-field--wide">
            <span>Kaos tetik</span>
            <select id="chaosTriggerSelect">
              <option value="time_or_count" selected>Süre veya havuz</option>
              <option value="time">Sadece süre</option>
              <option value="count">Sadece havuz</option>
              <option value="manual">Manuel (havuz otomatik, sürede Kaos)</option>
            </select>
          </label>
        </div>
        <button type="button" class="btn btn-sm btn-primary btn-block" id="btnSaveRaceSettings">Ayarları kaydet (SQL)</button>
        <p class="play-settings-hint">YouTube ve OBS linkleri için <a href="/admin/" id="linkAdminInline">yayın ayarları</a> sayfasını kullanın.</p>
      </div>
    </aside>

    <section class="play-stage" id="playStage" data-arena-layout="vertical" aria-label="Arena simülasyonu">
      <div class="play-arena" id="arena">
        <img class="play-arena-bg" src="/team-race/background.jpg" alt="" />
        <canvas id="arenaCanvas" class="play-arena-canvas" aria-label="Fizik arena"></canvas>
        <aside class="play-arena-rail play-arena-rail--left" data-cal-slot="railLeft" aria-label="Tur kazananları">
          <p class="play-rail-title">Kazananlar</p>
          <ul class="play-arena-winners" id="arenaRoundWinners">
            <li class="muted">—</li>
          </ul>
        </aside>
        <aside class="play-arena-rail play-arena-rail--right" data-cal-slot="railRight" aria-label="En çok yazanlar">
          <p class="play-rail-title">En çok yazan</p>
          <p class="play-rail-sub muted">kim kaç mesaj</p>
          <ol class="play-arena-top5" id="arenaTopViewers">
            <li class="muted">—</li>
          </ol>
        </aside>
        <div class="play-arena-badge" id="arenaBadge" data-cal-slot="arenaBadge">Arenada: 0</div>
        <div class="play-arena-promo hidden" id="arenaPromoAlert" data-cal-slot="arenaPromoAlert" aria-live="polite"></div>
        <div class="play-round-hud hidden" id="phaseBanner" data-cal-slot="phaseBanner" aria-live="polite">
          <nav class="play-round-hud__steps" id="phaseSteps" aria-label="Tur fazları">
            <span class="play-step is-active" data-step="gathering">1 · Toplanma</span>
            <span class="play-step" data-step="chaos">2 · Kaos</span>
          </nav>
          <div class="play-round-hud__head">
            <p class="play-round-hud__phase" id="phaseBannerTitle">Toplanma</p>
            <p class="play-round-hud__timer" id="phaseBannerTimer">5:00</p>
          </div>
          <div class="play-round-hud__pool">
            <span class="play-round-hud__pool-label">Havuz</span>
            <div class="play-pool-bar"><div class="play-pool-fill" id="poolFill"></div></div>
          </div>
          <ul class="play-round-hud__chips">
            <li class="play-chip" id="chipParticipants"><span>İzleyici</span><strong>0/3</strong></li>
            <li class="play-chip" id="chipTeams"><span>Takım</span><strong>0/2</strong></li>
            <li class="play-chip" id="chipSpawns"><span>Spawn</span><strong>0/3</strong></li>
          </ul>
          <p class="play-round-hud__hint" id="hudSub"></p>
        </div>
        <p class="play-arena-elim-flash" id="elimFlash" data-cal-slot="elimFlash" aria-live="polite"></p>
        <div class="play-winner tr-winner-card hidden" id="winnerCard" data-cal-slot="winnerCard">
          <div class="tr-winner-card__flag">
            <img class="team-flag team-flag--xl" id="winnerFlag" alt="" />
          </div>
          <p class="tr-winner-card__kicker" id="winnerTitle">Tur kazananı</p>
          <p class="tr-winner-card__name play-winner-name" id="winnerName"></p>
          <p class="tr-winner-card__badge" id="winnerBadge"></p>
          <p class="tr-winner-card__meta play-winner-meta muted" id="winnerMeta"></p>
        </div>
        <div class="play-activity-ticker" data-cal-slot="activityTicker" aria-live="polite">
          <ul class="play-activity-strip" id="activityStrip"></ul>
        </div>
      </div>
    </section>

    <aside class="play-dock play-dock--right" aria-label="Sohbet ve takip">
      <div class="play-dock-block">
        <h2 class="play-dock-title">Sohbet testi</h2>
        <label class="play-compact-field play-compact-field--inline">
          <span>İsim</span>
          <input type="text" id="authorInput" value="Ahmet" maxlength="40" />
        </label>
        <label class="play-compact-field play-compact-field--inline">
          <span>Takım</span>
          <input type="text" id="chatInput" placeholder="gs, fener…" maxlength="120" />
        </label>
        <button type="button" class="btn btn-primary btn-block btn-sm" id="btnSend">Gönder</button>
        <p class="play-feedback" id="chatFeedback"></p>
        <h3 class="play-dock-subtitle">Hızlı takım seç</h3>
        <div class="play-team-grid" id="teamQuickGrid"></div>
      </div>
      <div class="play-dock-block play-dock-block--feeds">
        <h2 class="play-dock-title">Canlı akış</h2>
        <ul class="play-live-chat play-feed-clip" id="liveChatFeed" aria-live="polite"></ul>
      </div>
      <div class="play-dock-row">
        <div class="play-mini-feed">
          <h3>Spawn</h3>
          <ul class="play-feed play-feed-clip" id="spawnFeed"></ul>
        </div>
        <div class="play-mini-feed">
          <h3>Elenen</h3>
          <ul class="play-eliminated play-feed-clip" id="eliminatedFeed">
            <li class="muted">—</li>
          </ul>
        </div>
        <div class="play-mini-feed">
          <h3>Arena</h3>
          <ul class="play-leaderboard play-feed-clip" id="leaderboard"></ul>
        </div>
      </div>
    </aside>
  </main>
  </div>`;
