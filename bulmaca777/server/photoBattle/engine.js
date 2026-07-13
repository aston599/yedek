import { randomBytes } from "crypto";
import { parsePhotoVote } from "./votes.js";
import { normalizePhotoBattleSettings } from "./settings.js";

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function authorKey(msg) {
  return (
    String(msg?.authorChannelId || msg?.channelId || "").trim() ||
    String(msg?.author || "anon").trim().toLowerCase()
  );
}

function displayAuthor(msg) {
  const n = String(msg?.author || "İzleyici").trim();
  return n.startsWith("@") ? n : `@${n}`;
}

export class PhotoBattleEngine {
  constructor(options = {}) {
    this.roomId = options.roomId;
    this.mediaBaseUrl =
      options.mediaBaseUrl || `/media/rooms/${options.roomId}/photo-pool/images`;
    this.settings = normalizePhotoBattleSettings(options.settings);
    /** @type {Array<{ id: string, imageUrl: string, label: string, eliminated?: boolean }>} */
    this.pool = [];
    this.phase = "idle";
    this.queue = [];
    this.left = null;
    this.right = null;
    this.champion = null;
    this.matchNumber = 0;
    this.resultWinnerSide = null;
    this.voteEndsAt = 0;
    this.resultUntil = 0;
    /** @type {Map<string, 1|2>} */
    this.votedAuthors = new Map();
    this._timer = null;
    this.onStateChange = options.onStateChange ?? (() => {});
    this.onPersist = options.onPersist ?? (() => {});
  }

  isRunning() {
    return this.phase === "voting" || this.phase === "result";
  }

  _imageUrl(filename) {
    return `${this.mediaBaseUrl}/${filename}`;
  }

  setPool(entries) {
    this.pool = (entries || []).map((e) => ({
      id: e.id,
      imageUrl: e.imageUrl,
      label: e.label || "",
      filename: e.filename,
      eliminated: Boolean(e.eliminated),
    }));
  }

  getPoolEntries() {
    return this.pool.map((p) => ({
      id: p.id,
      imageUrl: p.imageUrl,
      label: p.label,
      filename: p.filename,
      eliminated: Boolean(p.eliminated),
    }));
  }

  updateSettings(patch) {
    this.settings = normalizePhotoBattleSettings({
      ...this.settings,
      ...(patch || {}),
    });
    this._emit();
    this.onPersist();
  }

  _poolItem(id) {
    return this.pool.find((p) => p.id === id);
  }

  _activeIds() {
    return this.pool.filter((p) => !p.eliminated).map((p) => p.id);
  }

  _makeContestant(id) {
    const p = this._poolItem(id);
    if (!p) return null;
    return {
      id: p.id,
      imageUrl: p.imageUrl,
      label: p.label || "",
      votes: 0,
      voters: [],
    };
  }

  _publicSide(side) {
    if (!side) return null;
    const max = this.settings.maxVotersListed;
    return {
      id: side.id,
      imageUrl: side.imageUrl,
      label: side.label,
      votes: side.votes,
      voters: side.voters.slice(0, max),
    };
  }

  getSnapshot() {
    const now = Date.now();
    const lv = this.left?.votes || 0;
    const rv = this.right?.votes || 0;
    const total = lv + rv;
    let leftPct = 50;
    if (total > 0) leftPct = (lv / total) * 100;
    return {
      phase: this.phase,
      settings: { ...this.settings },
      poolCount: this.pool.length,
      activeCount: this._activeIds().length,
      matchNumber: this.matchNumber,
      title: this.settings.title,
      left: this._publicSide(this.left),
      right: this._publicSide(this.right),
      champion: this.champion
        ? {
            id: this.champion.id,
            imageUrl: this.champion.imageUrl,
            label: this.champion.label,
            votes: this.champion.votes,
          }
        : null,
      voteBar: {
        leftPct,
        rightPct: 100 - leftPct,
        leftVotes: lv,
        rightVotes: rv,
        total,
      },
      voteRemainingMs:
        this.phase === "voting" ? Math.max(0, this.voteEndsAt - now) : 0,
      voteDurationMs: this.settings.voteDurationSec * 1000,
      resultWinnerSide: this.resultWinnerSide,
      resultRemainingMs:
        this.phase === "result" ? Math.max(0, this.resultUntil - now) : 0,
    };
  }

  serializeState() {
    return {
      settings: this.settings,
      pool: this.pool,
      phase: this.phase,
      queue: this.queue,
      left: this.left,
      right: this.right,
      champion: this.champion,
      matchNumber: this.matchNumber,
      resultWinnerSide: this.resultWinnerSide,
      voteEndsAt: this.voteEndsAt,
      resultUntil: this.resultUntil,
      votedAuthors: [...this.votedAuthors.entries()],
    };
  }

  restoreState(data) {
    if (!data || typeof data !== "object") return;
    this.settings = normalizePhotoBattleSettings(data.settings);
    this.pool = data.pool || [];
    this.phase = data.phase || "idle";
    this.queue = data.queue || [];
    this.left = data.left || null;
    this.right = data.right || null;
    this.champion = data.champion || null;
    this.matchNumber = data.matchNumber || 0;
    this.resultWinnerSide = data.resultWinnerSide || null;
    this.voteEndsAt = data.voteEndsAt || 0;
    this.resultUntil = data.resultUntil || 0;
    this.votedAuthors = new Map(data.votedAuthors || []);
    if (this.isRunning()) this._startTimer();
    else this._stopTimer();
  }

  _emit() {
    this.onStateChange(this.getSnapshot());
  }

  _startTimer() {
    this._stopTimer();
    this._timer = setInterval(() => this.tick(), 200);
  }

  _stopTimer() {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }
  }

  tick() {
    const now = Date.now();
    if (this.phase === "voting" && now >= this.voteEndsAt) {
      this._finalizeVote();
      return;
    }
    if (this.phase === "result" && now >= this.resultUntil) {
      this._afterResult();
      return;
    }
    if (this.phase === "voting" || this.phase === "result") {
      this._emit();
    }
  }

  reset() {
    this._stopTimer();
    this.phase = "idle";
    this.queue = [];
    this.left = null;
    this.right = null;
    this.champion = null;
    this.matchNumber = 0;
    this.resultWinnerSide = null;
    this.voteEndsAt = 0;
    this.resultUntil = 0;
    this.votedAuthors.clear();
    for (const p of this.pool) p.eliminated = false;
    this._emit();
    this.onPersist();
    return this.getSnapshot();
  }

  stop() {
    this._stopTimer();
    this.phase = "idle";
    this.left = null;
    this.right = null;
    this.queue = [];
    this.votedAuthors.clear();
    this._emit();
    this.onPersist();
    return this.getSnapshot();
  }

  start() {
    const active = this._activeIds();
    if (active.length < 2) {
      const err = new Error("En az 2 görsel gerekli (havuz yükleyin).");
      err.status = 400;
      throw err;
    }
    this._stopTimer();
    this.champion = null;
    this.matchNumber = 0;
    for (const p of this.pool) p.eliminated = false;
    const ids = shuffle(active);
    this.queue = ids.slice(2);
    this.left = this._makeContestant(ids[0]);
    this.right = this._makeContestant(ids[1]);
    this._beginVoting();
    return this.getSnapshot();
  }

  skipVote() {
    if (this.phase !== "voting") return this.getSnapshot();
    this._finalizeVote();
    return this.getSnapshot();
  }

  _beginVoting() {
    this.matchNumber += 1;
    this.phase = "voting";
    this.resultWinnerSide = null;
    this.votedAuthors.clear();
    if (this.left) {
      this.left.votes = 0;
      this.left.voters = [];
    }
    if (this.right) {
      this.right.votes = 0;
      this.right.voters = [];
    }
    this.voteEndsAt = Date.now() + this.settings.voteDurationSec * 1000;
    this._startTimer();
    this._emit();
    this.onPersist();
  }

  _finalizeVote() {
    const lv = this.left?.votes || 0;
    const rv = this.right?.votes || 0;
    let winnerSide = 1;
    if (rv > lv) winnerSide = 2;
    else if (lv === rv) winnerSide = Math.random() < 0.5 ? 1 : 2;

    this.resultWinnerSide = winnerSide;
    this.phase = "result";
    this.resultUntil = Date.now() + this.settings.resultHoldSec * 1000;
    this._emit();
    this.onPersist();
  }

  _afterResult() {
    const winnerSide = this.resultWinnerSide;
    const winner = winnerSide === 1 ? this.left : this.right;
    const loser = winnerSide === 1 ? this.right : this.left;
    if (!winner || !loser) {
      this.stop();
      return;
    }

    const loserItem = this._poolItem(loser.id);
    if (loserItem) loserItem.eliminated = true;

    const active = this._activeIds();
    if (active.length <= 1) {
      const champ = this._poolItem(winner.id);
      this.champion = champ
        ? {
            id: champ.id,
            imageUrl: champ.imageUrl,
            label: champ.label,
            votes: winner.votes,
          }
        : null;
      this.phase = "champion";
      this.left = null;
      this.right = null;
      this._stopTimer();
      this._emit();
      this.onPersist();
      return;
    }

    let nextId = this.queue.shift();
    while (nextId && (nextId === winner.id || this._poolItem(nextId)?.eliminated)) {
      nextId = this.queue.shift();
    }
    if (!nextId) {
      const candidates = active.filter((id) => id !== winner.id);
      nextId = candidates[Math.floor(Math.random() * candidates.length)];
    }

    this.left = this._makeContestant(winner.id);
    this.right = this._makeContestant(nextId);
    if (!this.left || !this.right) {
      this.stop();
      return;
    }
    const stillQueued = active.filter(
      (id) => id !== this.left.id && id !== this.right.id && !this.queue.includes(id)
    );
    this.queue.push(...stillQueued);
    this._beginVoting();
  }

  handleChatMessage(msg) {
    if (this.phase !== "voting") return { type: "ignored" };
    const side = parsePhotoVote(msg?.text || msg?.message || "");
    if (!side) return { type: "ignored" };

    const key = authorKey(msg);
    const prev = this.votedAuthors.get(key);
    const target = side === 1 ? this.left : this.right;
    const other = side === 1 ? this.right : this.left;
    if (!target || !other) return { type: "ignored" };

    const author = displayAuthor(msg);
    const at = new Date().toISOString();
    const max = this.settings.maxVotersListed;

    if (prev === side) return { type: "duplicate", side };

    if (prev === 1 || prev === 2) {
      const prevTarget = prev === 1 ? this.left : this.right;
      prevTarget.votes = Math.max(0, prevTarget.votes - 1);
      const idx = prevTarget.voters.findIndex(
        (v) => v.authorKey === key || v.author === author
      );
      if (idx >= 0) prevTarget.voters.splice(idx, 1);
    }

    this.votedAuthors.set(key, side);
    target.votes += 1;
    target.voters.unshift({ author, authorKey: key, at });
    if (target.voters.length > max * 2) target.voters.length = max * 2;

    this._emit();
    this.onPersist();
    return { type: "vote", side, author };
  }
}

export function newPhotoId() {
  return randomBytes(6).toString("hex");
}
