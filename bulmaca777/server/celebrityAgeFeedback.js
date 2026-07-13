/** Ünlü yaş — yakınlık mesajları ve isim formatı */

export function parseAgeFromText(text) {
  const m = String(text || "").match(/\b(\d{1,3})\b/);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  return Number.isFinite(n) && n > 0 && n < 120 ? n : null;
}

export function getCorrectAge(question) {
  const meta = Number(question?.meta?.age);
  if (Number.isFinite(meta) && meta > 0) return Math.round(meta);
  const ans = question?.answers?.[0];
  const fromAns = parseAgeFromText(ans);
  return fromAns;
}

export function isCelebrityAgeQuestion(question) {
  if (!question) return false;
  const fk = question?.meta?.gameKind;
  if (fk === "football-club" || fk === "football-nationality") return false;
  if (question.meta?.age != null) return true;
  return /kaç\s+yaşında/i.test(String(question.question || ""));
}

export function firstNameShoutout(displayName) {
  const raw = String(displayName || "İzleyici")
    .replace(/^@/, "")
    .trim();
  const first = raw.split(/\s+/)[0] || raw;
  return first.toLocaleUpperCase("tr-TR");
}

/**
 * @returns {"correct"|"close"|"warm"|"far"|null}
 */
export function classifyAgeGuess(guessAge, correctAge, closeYears = 2, warmYears = 5) {
  if (guessAge == null || correctAge == null) return null;
  const diff = Math.abs(guessAge - correctAge);
  if (diff === 0) return "correct";
  if (diff <= closeYears) return "close";
  if (diff <= warmYears) return "warm";
  return "far";
}

export const DEFAULT_CELEBRITY_PRIZE_LABEL = "EN YÜKSEK PUANA ÖDÜL VAR!";

export const CELEBRITY_PRIZE_PROMOS = [
  DEFAULT_CELEBRITY_PRIZE_LABEL,
  "LİSTENİN ZİRVESİ ÖDÜLÜ ALIR!",
  "PUAN TOPLA — ÖDÜL SENİN OLSUN!",
  "EN ÇOK PUAN = ÖDÜL!",
  "ZİRVEDE KİM VAR? ÖDÜL ONUN!",
];

/** Abone / beğen — ekstra puan PR */
export const CELEBRITY_ENGAGEMENT_PROMOS = [
  "ABONE VE BEĞEN — FAZLADAN PUAN KAZANIRSIN!",
  "BEĞEN + ABONE OL — EKSTRA PUAN!",
  "ABONE OL, DAHA ÇOK PUAN TOPLA!",
  "YORUM AT, PUANINI YÜKSELT!",
  "CANLI BEĞENİ = EKSTRA PUAN!",
];

/** BİLDİN sonrası ve boş anlarda dönen PR metinleri */
export const CELEBRITY_PR_ROTATION = [
  ...CELEBRITY_ENGAGEMENT_PROMOS,
  "HADİ BULABİLİRSİN!",
  "BİLMEYE YAKLAŞTIN — TEKRAR DENE!",
  "ÇOK YAKINSIN — BİR RAKAM DAHA!",
  "SOHBETE YAŞ YAZ — HADİ!",
  "KİM BİLECEK? SEN BİLECEKSİN!",
  "HADİ CEVABI BİLEBİLİRSİN!",
  "TEK RAKAM YETER — ÖRN. 32",
  ...CELEBRITY_PRIZE_PROMOS,
];

const PROMO_IDLE = [
  "HADİ CEVABI BİLEBİLİRSİN!",
  "SOHBETE YAŞ YAZ!",
  "İLK DOĞRU BİLEN KAZANIR!",
  "TEK RAKAM YETER — ÖRN. 32",
  "KİM BİLECEK?",
  ...CELEBRITY_ENGAGEMENT_PROMOS,
  ...CELEBRITY_PRIZE_PROMOS,
];

function promoSubjectName(question) {
  return String(question?.meta?.name || question?.meta?.player || "").trim();
}

function questionPromptPromo(question) {
  const name = promoSubjectName(question);
  if (!name) return null;
  const upper = name.toLocaleUpperCase("tr-TR");
  const fk = question?.meta?.gameKind;
  if (fk === "football-club") return `${upper} HANGİ TAKIMDA? HADİ BUL!`;
  if (fk === "football-nationality") return `${upper} HANGİ ÜLKE? HADİ BUL!`;
  if (isCelebrityAgeQuestion(question)) return `${upper} KAÇ YAŞINDA? HADİ BUL!`;
  return null;
}

export function pickPrRotationPromo(question, prizeLabel = DEFAULT_CELEBRITY_PRIZE_LABEL) {
  const roll = Math.random();
  if (roll < 0.38) {
    return CELEBRITY_ENGAGEMENT_PROMOS[
      Math.floor(Math.random() * CELEBRITY_ENGAGEMENT_PROMOS.length)
    ];
  }
  if (roll < 0.62) {
    const prompt = questionPromptPromo(question);
    if (prompt) return prompt;
  }
  const pool = [prizeLabel, ...CELEBRITY_PR_ROTATION.filter((p) => p !== prizeLabel)];
  return pool[Math.floor(Math.random() * pool.length)];
}

export function buildWrongBroadcast(displayName, kind, question, answerText = null) {
  const name = firstNameShoutout(displayName);
  const guess = String(answerText || "")
    .trim()
    .slice(0, 24);
  const celeb = question?.meta?.name
    ? String(question.meta.name).toUpperCase("tr-TR")
    : null;

  if (kind === "close") {
    const variants = guess
      ? [
          `${name}, ${guess} — YAKLAŞTIN!`,
          `${name}, ${guess} YAKIN — BİRAZ DAHA!`,
        ]
      : [`${name}, YAKLAŞTIN!`, `${name}, ÇOK YAKINSIN!`, `${name}, NEREDEYSE!`];
    return variants[Math.floor(Math.random() * variants.length)];
  }
  if (kind === "warm") {
    const variants = guess
      ? [
          `${name}, ${guess} — DAHA YAKLAŞ!`,
          `${name}, ${guess} OLMADI — TEKRAR DENE!`,
        ]
      : [`${name}, BİRAZ DAHA!`, `${name}, DAHA YAKLAŞ!`, `${name}, TEKRAR DENE!`];
    return variants[Math.floor(Math.random() * variants.length)];
  }
  if (kind === "far") {
    const variants = guess
      ? [
          `${name}, ${guess} YANLIŞ!`,
          `${name}: ${guess} — TEKRAR DENE!`,
        ]
      : [
          `${name}, OLMADI!`,
          `${name}, BİR DAHA!`,
          celeb ? `${name}, ${celeb} DEĞİL!` : `${name}, FARKLI DENE!`,
        ];
    return variants[Math.floor(Math.random() * variants.length)];
  }
  return guess ? `${name}, ${guess} YANLIŞ — TEKRAR DENE!` : `${name}, TEKRAR DENE!`;
}

export function pickIdlePromo(question, prizeLabel = DEFAULT_CELEBRITY_PRIZE_LABEL) {
  const roll = Math.random();
  if (roll < 0.32) {
    return CELEBRITY_ENGAGEMENT_PROMOS[
      Math.floor(Math.random() * CELEBRITY_ENGAGEMENT_PROMOS.length)
    ];
  }
  if (roll < 0.5) {
    const pool = [prizeLabel, ...CELEBRITY_PRIZE_PROMOS.filter((p) => p !== prizeLabel)];
    return pool[Math.floor(Math.random() * pool.length)];
  }
  const prompt = questionPromptPromo(question);
  if (prompt && roll < 0.68) return prompt;
  return PROMO_IDLE[Math.floor(Math.random() * PROMO_IDLE.length)];
}

export function buildLeaderPrizeBroadcast(displayName, prizeLabel = DEFAULT_CELEBRITY_PRIZE_LABEL) {
  const name = firstNameShoutout(displayName);
  const variants = [
    `${name} LİDER — ${prizeLabel}`,
    `${name}, ZİRVEDESİN! ${prizeLabel}`,
    `ÖDÜL İÇİN ${name} YAKIN — PUAN TOPLA!`,
  ];
  return variants[Math.floor(Math.random() * variants.length)];
}
