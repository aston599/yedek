/** Ortak ölçek ayarları — overlay + kalibrasyon */
window.BulmacaLayoutScales = {
  DEFAULT: {
    live: 1,
    counter: 1,
    questionMeta: 1,
    question: 1,
    answer: 1,
    feedAvatar: 1,
    feedName: 1,
    feedPoints: 1,
    feedCheck: 1,
    winnerHint: 1,
    winnerName: 1,
    winnerAnswer: 1,
  },

  KEYS: [
    { key: "live", label: "Canlı yayın" },
    { key: "counter", label: "Sayaç (boşta)" },
    { key: "questionMeta", label: "Soru sayacı (4/50)" },
    { key: "question", label: "Bulmaca metni" },
    { key: "winnerHint", label: "Tebrikler başlık" },
    { key: "winnerName", label: "Kazanan adı" },
    { key: "winnerAnswer", label: "Kazanan cevap" },
    { key: "feedAvatar", label: "Profil foto" },
    { key: "feedName", label: "Kullanıcı adı" },
    { key: "feedPoints", label: "Puan" },
    { key: "feedCheck", label: "Tik (✓)" },
  ],

  merge(scales) {
    return { ...this.DEFAULT, ...(scales || {}) };
  },

  apply(root, scales) {
    if (!root) return;
    const s = this.merge(scales);
    const map = {
      live: "--scale-live",
      counter: "--scale-counter",
      questionMeta: "--scale-question-meta",
      question: "--scale-question",
      answer: "--scale-answer",
      feedAvatar: "--scale-feed-avatar",
      feedName: "--scale-feed-name",
      feedPoints: "--scale-feed-points",
      feedCheck: "--scale-feed-check",
      winnerHint: "--scale-winner-hint",
      winnerName: "--scale-winner-name",
      winnerAnswer: "--scale-winner-answer",
    };
    for (const [key, varName] of Object.entries(map)) {
      root.style.setProperty(varName, String(s[key] ?? 1));
    }
  },
};
