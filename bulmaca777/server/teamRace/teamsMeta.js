/** Süper Lig takım kodları → görünen ad (/public/team-race/flags/{code}.png) */
export const TEAM_DISPLAY_NAMES = Object.freeze({
  gs: "Galatasaray",
  fb: "Fenerbahçe",
  bjk: "Beşiktaş",
  ts: "Trabzonspor",
  ibfk: "Başakşehir",
  ala: "Alanyaspor",
  ant: "Antalyaspor",
  eyp: "Eyüpspor",
  fkg: "Fatih Karagümrük",
  gfk: "Gaziantep FK",
  gb: "Gençlerbirliği",
  goz: "Göztepe",
  kas: "Kasımpaşa",
  kay: "Kayserispor",
  koc: "Kocaelispor",
  kon: "Konyaspor",
  riz: "Rizespor",
  sam: "Samsunspor",
});

export function teamDisplayName(code) {
  const c = String(code || "").toLowerCase();
  return TEAM_DISPLAY_NAMES[c] || c.toUpperCase();
}

export function flagUrlForTeam(code) {
  const c = String(code || "").toLowerCase();
  if (!c) return "";
  return `/team-race/flags/${c}.png`;
}
