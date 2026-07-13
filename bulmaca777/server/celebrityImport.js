/** CSV / TSV: isim, yaş, doğum_tarihi, foto_link */

function ageAnswerVariants(age) {
  const n = String(age || "").replace(/\D/g, "");
  if (!n) return [];
  return [
    n,
    `${n} yaş`,
    `${n} yas`,
    `${n} yaşında`,
    `${n} yasinda`,
    `${n} yasinda`,
  ];
}

function parseLine(line) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) return null;

  let parts;
  if (trimmed.includes("\t")) {
    parts = trimmed.split("\t").map((s) => s.trim());
  } else {
    parts = trimmed.split(",").map((s) => s.trim());
    if (parts.length > 4) {
      const url = parts.slice(3).join(",").trim();
      parts = [parts[0], parts[1], parts[2], url];
    }
  }

  if (parts.length < 4) return null;

  const [name, age, birthDate, imageUrl] = parts;
  if (!name || !age || !imageUrl) return null;
  if (/^isim/i.test(name) && /yaş|yas/i.test(age)) return null;

  const id = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);

  return {
    id: id || `celeb-${Math.random().toString(36).slice(2, 8)}`,
    hint: "Ünlülerin Yaşını Tahmin Et",
    question: `${name} kaç yaşında?`,
    imageUrl: imageUrl.startsWith("http") ? imageUrl : `https://${imageUrl}`,
    answers: ageAnswerVariants(age),
    points: 10,
    meta: { name, age: Number(age) || age, birthDate },
  };
}

export function parseCelebrityCsv(text, options = {}) {
  const hint = options.hint || "Ünlülerin Yaşını Tahmin Et";
  const lines = String(text || "")
    .trim()
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  const questions = [];
  const seen = new Set();

  for (const line of lines) {
    const row = parseLine(line);
    if (!row) continue;
    row.hint = hint;
    let key = row.id;
    let n = 0;
    while (seen.has(key)) {
      n += 1;
      key = `${row.id}-${n}`;
    }
    seen.add(key);
    row.id = key;
    questions.push(row);
  }

  return questions;
}

/** Ünlü yaş paketi mi (foto + «kaç yaşında» sorusu) */
export function isCelebrityAgeQuiz(questions) {
  const list = Array.isArray(questions) ? questions : [];
  if (!list.length) return false;
  const sample = list.slice(0, Math.min(5, list.length));
  return sample.every(
    (q) =>
      q?.imageUrl &&
      /kaç\s+yaşında/i.test(String(q.question || ""))
  );
}
