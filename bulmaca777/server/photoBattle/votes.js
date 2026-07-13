/** Sohbetten 1 / 2 oyu — Türkçe + emoji */
export function parsePhotoVote(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  const t = raw.toLowerCase().replace(/\s+/g, " ");

  if (/^(1|bir|sol|left|a|ilk|üçbir|üç bir)$/.test(t)) return 1;
  if (/^(2|iki|sağ|sag|right|b|ikinci)$/.test(t)) return 2;
  if (/^1[\s!.,:;)]/.test(t) || t === "1️⃣") return 1;
  if (/^2[\s!.,:;)]/.test(t) || t === "2️⃣") return 2;

  const digit = t.match(/^([12])$/);
  if (digit) return Number(digit[1]);

  return null;
}
