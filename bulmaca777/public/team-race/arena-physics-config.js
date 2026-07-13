/**

 * Arena fizik — toplanma ve kaos aynı özel daire motoru (px/s).

 *

 * KAOS (game.exe / pymunk hissi):

 * - Toplar serbest, sekerek çarpışır

 * - Halka döner; çıkış boşluğundan düşen elenir

 * - Grace süresi sonra çıkışa hafif çekim

 * - Şok dalgası: radyal patlama + çıkış yönü

 */

const DEFAULT_ARENA_PHYSICS_CFG = {

  stepMs: 1000 / 60,

  positionIterations: 10,

  velocityIterations: 8,

  ringStroke: 3,

  ringLineGathering: 5,

  ringLineChaos: 6,

  shellCount: 36,

  shellRadius: 8,

  ballRadiusMin: 10,

  ballRadiusMax: 14,

  ballRadiusFactor: 0.042,

  gathering: {

    gravityAccel: 620,

    ballRestitution: 0.05,

    airDragPerSec: 0.85,

    maxSpeedPx: 300,

    spawnVxPx: 18,

    spawnVyPx: 55,

    collisionIterations: 5,

    spawnDropYFactor: 0.68,

    sleepSpeedPx: 6,

  },

  chaos: {
    /** Girdap Lab — Yapay ω×r: ortada döner, halka görsel, shellSpinTransfer=0 */
    gravityAccel: 0,
    ballRestitution: 0.42,
    airDragPerSec: 0.22,
    maxSpeedPx: 280,
    collisionIterations: 7,
    chaosWarmupMs: 2800,
    chaosWarmRestitution: 0.34,
    chaosWarmMaxSpeedPx: 200,
    autoShockIntervalMs: 20_000,
    centerSpinRadPerSec: 2,
    centerSpinBlend: 0.38,
    enterSpinBlend: 1,
    centerSpinRadiusFactor: 0.44,
    centerSpinMinRadiusFactor: 0.12,
    centerSpinDirection: 1,
    ringSpinRadPerSec: 0.58,
    shellPushExtra: 0.5,
    /** 0 = toplar halka dönüşüne kapılmaz; sadece ω×r + çarpışma */
    shellSpinTransfer: 0,
    /** Orta girdap bölgesi (r faktörü) — köşelerde kalmaz */
    unpackRadiusFactor: 0.18,
    centerHoldRadiusFactor: 0.22,
    centerHoldPullPx: 520,

    /** Çıkış boşluğu: merkezden min. mesafe (r faktörü) */

    exitGapMinDistFactor: 0.48,

    exitAccelPx: 130,

    exitRimBoostPx: 95,

    shockBurstPx: 230,

    shockExitBoostPx: 125,

    spawnVxPx: 48,

    spawnVyPx: 42,

  },

};



export const ARENA_PHYSICS_CFG = cloneArenaPhysicsConfig(DEFAULT_ARENA_PHYSICS_CFG);



export function cloneArenaPhysicsConfig(src = DEFAULT_ARENA_PHYSICS_CFG) {

  return JSON.parse(JSON.stringify(src));

}



export function resetArenaPhysicsConfig() {

  const fresh = cloneArenaPhysicsConfig(DEFAULT_ARENA_PHYSICS_CFG);

  Object.assign(ARENA_PHYSICS_CFG, fresh);

  ARENA_PHYSICS_CFG.gathering = fresh.gathering;

  ARENA_PHYSICS_CFG.chaos = fresh.chaos;

  return ARENA_PHYSICS_CFG;

}



export { DEFAULT_ARENA_PHYSICS_CFG };


