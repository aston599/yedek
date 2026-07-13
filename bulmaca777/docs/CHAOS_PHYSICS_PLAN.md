# Kaos fizik sadeleştirme planı

## Sorun (eski sistem)

Kaos modunda **8+ ayrı kuvvet/düzeltme** aynı anda çalışıyordu; birbirini iptal ediyor veya titretiyordu:

| Katman | Sorun |
|--------|--------|
| Salınımlı yerçekimi (sin/cos) | Yön sürekli değişiyor, öngörülemez |
| `_applyChaosStir` | Orbit + funnel + wander + rastgele kick |
| `_applyChaosCrowdPush` | O(n²) çift döngü, overlap ile çarpışıyor |
| `_applyChaosDuelPressure` | 1v1 özel hack |
| `_boostStalledChaosBodies` | Yavaş topa zorla hız → titreme |
| `_applyChaosOverlapVelocityFix` | `_separateBallOverlaps` ile çift |
| `_stabilizeRestingOnRing` | Kaosta donma hissi |
| `_maybeTriggerShockWave` (60 sn) | Sunucu ile uyumsuz otomatik şok |
| `_nudgeTowardExit` | Tüm topları sürekli çıkışa çekiyordu |

## Hedef model (basit)

```
Toplanma                    Kaos
────────                    ────
↓ yerçekimi                 ↓ sabit yerçekimi
sürtünme, uyku              hafif teğet orbit (dönen çember)
çarpışma                    dönen duvar + çıkış boşluğu
                            elenme grace sonrası → çıkışa hafif çekim
                            şok = sadece manuel / sunucu (triggerShockWave)
```

## Tek kaos döngüsü (60 FPS)

1. `_applyChaosGravity()` — `y: 1`, scale sabit
2. `_applyChaosForces()` — teğet orbit + (grace sonrası) çıkış yönü
3. Duvar döndür (`_ringRotation`)
4. `Matter.Engine.update` (4 alt adım)
5. `_separateBallOverlaps(3)` — iç içe geçme yok
6. `_constrainToRing` — halka sınırı
7. `_assistExitThroughGap` — boşluktan düşüş
8. `_checkEliminations` — grace + çıkış

## Kaldırılanlar

- `_applyChaosStir`, `_applyChaosCrowdPush`, `_applyChaosDuelPressure`
- `_boostStalledChaosBodies`, `_applyChaosOverlapVelocityFix`, `_syncChaosBulletMode`
- `_stabilizeRestingOnRing` (kaos)
- `_maybeTriggerShockWave` otomatik çağrı (API/manuel şok kalır)
- Kaosta `_enforceRingCollider` + `_clampInsideRing` ikiliği → sadece `_constrainToRing`

## Giriş (toplanma → kaos)

- `_enterChaosMotion()`: materyal + tek seferlik teğet hız (orbit hissi)
- Otomatik şok yok

## Test

- `scripts/test-arena-physics.js` — kaos adımları yeni döngüyle hizalı
- Ortalama hız bandı: 3–12 (aşırı zıplama yok)
