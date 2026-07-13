# Takım yarışı — referans ve mimari

## `team-race-changed/` (orijinal oyun paketi)

| Dosya | Açıklama |
|--------|-----------|
| `game.exe` | Pygame + **pymunk** ile derlenmiş Windows oyunu (kaynak kod yok) |
| `background.jpg` | Arena arka planı → `public/team-race/background.jpg` ile aynı |
| `flags/*.png` | 18 takım bayrağı → `public/team-race/flags/` ile eşleşir |
| `country_aliases.json` | Sohbet takım eşlemesi → `data/team-race/aliases.json` ile aynı içerik |

`game.exe` içinde `pymunk`, `Space`, `gravity` stringleri doğrulandı; sayısal parametreler kapalı kaynak olduğu için web sürümünde Matter.js ile **davranışsal** eşleme yapılır (yüksek restitution, orbit kuvveti, dönen çıkış).

## Web mimarisi

```
YouTube chat → InnerYouTubeChatService → TeamRaceEngine (server)
                    ↓ Socket.IO race:state / race:spawn
              play.js / overlay.js → TeamRaceArena (Matter.js, tarayıcı)
                    ↓ POST /race/eliminate (çukur / dış halka)
              TeamRaceEngine → kazanan / yeni tur
```

- **Sunucu:** kim spawn olur, kaos zamanı, elenme listesi, seri skoru.
- **İstemci:** çarpışma, düşme, çizim — sunucu konum senkronu yapmaz (görsel küçük sapmalar olabilir).

## Benzer açık kaynak (GitHub)

| Proje | Not |
|--------|-----|
| [liabru/matter-js](https://github.com/liabru/matter-js) | Kullandığımız 2D motor; Ball Pool demo |
| [matter-js#1332](https://github.com/liabru/matter-js/issues/1332) | Çok dairede “erime” — yüksek `positionIterations`, `slop`, `isBullet` |
| [viblo/pymunk](https://github.com/viblo/pymunk) | Orijinal `game.exe` motor ailesi |
| [mikewesthad/phaser-matter-collision-plugin](https://github.com/mikewesthad/phaser-matter-collision-plugin) | Matter çarpışma olayları (Phaser) |

## Test komutları

```bash
node scripts/simulate-team-race.js    # motor kuralları (41 test)
node scripts/test-arena-physics.js    # Matter arena (12 test)
node scripts/benchmark-arena-physics.js  # uzun koşu metrikleri
```

**Girdap karşılaştırma (tarayıcı):** [`/play/vortex-lab.html`](/play/vortex-lab.html) — 10 stil, geri bildirim raporu kopyala.

## Fizik sürümü

Tarayıcı önbelleği: `arena-physics.js?v=72` (`play.js`, `overlay.js`, `circle-lab.js`).

## Kaos fazı (nasıl çalışmalı)

1. **Toplanma** — toplar altta birikir (kapalı halka).
2. **Kaos** — halka pembe, döner; çıkış boşluğu açılır.
3. Toplar birbirini iter (girdap); dönen halka teğet hız verir; şok dağıtır.
4. Grace süresi bitince çıkışa yakın toplar dışarı itilir → **elenir**.
5. Son kalan takım kazanır (sunucu).

Fizik: toplanma ile aynı özel simülasyon (`_customCircleStep`), Matter motoru devre dışı.
