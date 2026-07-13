import { readFileSync, writeFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  answersMatch,
  extractAnswerFromComment,
  extractNameFromComment,
  isBotFormattedChat,
  parseChatCommand,
} from "./utils.js";
import { buildWinMessage, buildWrongMessage } from "./bot.js";
import {
  parseAgeFromText,
  getCorrectAge,
  isCelebrityAgeQuestion,
  classifyAgeGuess,
  buildWrongBroadcast,
  pickIdlePromo,
  firstNameShoutout,
  buildLeaderPrizeBroadcast,
  pickPrRotationPromo,
  DEFAULT_CELEBRITY_PRIZE_LABEL,
} from "./celebrityAgeFeedback.js";
import {
  isFootballQuizQuestion,
  matchFootballAnswer,
} from "./football/footballMatch.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DEFAULT_QUESTIONS_PATH = join(__dirname, "..", "data", "questions.json");

export class GameEngine {
  constructor(options = {}) {
    this.questionsPath = options.questionsPath ?? DEFAULT_QUESTIONS_PATH;
    this.questions = [];
    this.currentIndex = -1;
    this.state = "idle";
    this.winner = null;
    this.processedMessageIds = new Set();
    this.wrongRepliedAuthors = new Set();
    /** @type {Map<string, { displayName: string, avatarUrl: string|null, points: number }>} */
    this.playerScores = new Map();
    this.answerFeed = [];
    this.feedMax = Math.min(20, Math.max(3, Number(options.feedMax) || 7));
    /** @type {Set<string>} */
    this._questionPlayerKeys = new Set();
    this._questionAttemptCount = 0;
    /** @type {{ displayName: string, answer: string, correct: boolean, at: string } | null} */
    this._lastAnswer = null;
    this.pointsPerCorrect = options.pointsPerCorrect ?? 10;
    this.botSettings = {
      botName: options.botName ?? "YouTube Bulmacalari",
      announceWrong: options.announceWrong === true,
      winMessage: options.winMessage ?? null,
      wrongMessage: options.wrongMessage ?? null,
    };
    this.nextQuestionDelayMs = options.nextQuestionDelayMs ?? 5000;
    this.holdWinnerUntilNextCorrect =
      options.holdWinnerUntilNextCorrect !== false;
    this.celebrityCloseYears = Math.max(
      1,
      Number(options.celebrityCloseYears) || 2
    );
    this.celebrityWarmYears = Math.max(
      this.celebrityCloseYears + 1,
      Number(options.celebrityWarmYears) || 5
    );
    this.broadcastHoldMs = Math.max(
      2500,
      Number(options.broadcastHoldMs) || 6500
    );
    this.celebrityCorrectFlashMs = Math.max(
      3000,
      Math.min(
        8000,
        Number(options.celebrityCorrectFlashMs) || 5000
      )
    );
    this.celebrityPrRotateMs = Math.max(
      3500,
      Number(options.celebrityPrRotateMs) || 5500
    );
    this._broadcastFollowTimer = null;
    this._broadcastRotateTimer = null;
    /** @type {Array<{ key: string, text: string, kind: string, displayName: string, authorKey?: string, botReply?: object }>} */
    this._wrongBroadcastQueue = [];
    this._wrongQueuePlaying = false;
    this._wrongQueueTimer = null;
    this.wrongBroadcastHoldMs = Math.max(
      3000,
      Math.min(12000, Number(options.wrongBroadcastHoldMs) || 5000)
    );
    this.wrongBroadcastQueueMax = Math.min(
      30,
      Math.max(5, Number(options.wrongBroadcastQueueMax) || 15)
    );
    this.celebrityPrizeLabel =
      String(options.celebrityPrizeLabel || DEFAULT_CELEBRITY_PRIZE_LABEL).trim()
        .slice(0, 72) || DEFAULT_CELEBRITY_PRIZE_LABEL;
    /** @type {{ text: string, kind: string, until: number, displayName?: string } | null} */
    this._broadcast = null;
    /** Aktif soru başlangıcı — bundan önceki sohbet mesajları yoksayılır */
    this.questionActiveSince = null;
    this._advanceTimer = null;
    this.onStateChange = options.onStateChange ?? (() => {});
    this.onBotReply = options.onBotReply ?? (() => {});
    this.onPersist = options.onPersist ?? (() => {});
    this.loadQuestions();
  }

  serializeState() {
    return {
      state: this.state,
      currentIndex: this.currentIndex,
      winner: this.winner,
      playerScores: [...this.playerScores.entries()],
      answerFeed: [...this.answerFeed],
      processedMessageIds: [...this.processedMessageIds].slice(-800),
      wrongRepliedAuthors: [...this.wrongRepliedAuthors],
      questionActiveSince: this.questionActiveSince,
    };
  }

  restoreState(data) {
    if (!data || typeof data !== "object") return;
    const allowed = new Set(["idle", "active", "winner", "ended"]);
    if (allowed.has(data.state)) this.state = data.state;
    if (Number.isInteger(data.currentIndex)) this.currentIndex = data.currentIndex;
    this.winner = data.winner ?? null;

    this.playerScores = new Map();
    if (Array.isArray(data.playerScores)) {
      for (const entry of data.playerScores) {
        if (Array.isArray(entry) && entry.length >= 2) {
          this.playerScores.set(entry[0], this._normalizePlayerRow(entry[1]));
        }
      }
    }

    this.processedMessageIds = new Set(
      Array.isArray(data.processedMessageIds) ? data.processedMessageIds : []
    );
    this.wrongRepliedAuthors = new Set(
      Array.isArray(data.wrongRepliedAuthors) ? data.wrongRepliedAuthors : []
    );
    this.questionActiveSince =
      typeof data.questionActiveSince === "string" ? data.questionActiveSince : null;

    this._rebuildLeaderboardFeed();
  }

  setBotSettings(settings) {
    this.botSettings = { ...this.botSettings, ...settings };
  }

  loadQuestions(filePath = this.questionsPath) {
    if (!existsSync(filePath)) {
      this.questions = [];
      return;
    }
    const raw = readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw);
    this.questions = Array.isArray(parsed)
      ? parsed.map((q) => this._normalizeQuestion(q))
      : [];
  }

  loadQuestionsFromJson(json) {
    try {
      this.questions = JSON.parse(json || "[]").map((q) => this._normalizeQuestion(q));
      this.saveQuestions();
    } catch {
      this.questions = [];
    }
  }

  saveQuestions(filePath = this.questionsPath) {
    writeFileSync(filePath, JSON.stringify(this.questions, null, 2), "utf-8");
  }

  getQuestionsJson() {
    return JSON.stringify(this.questions);
  }

  _playerKey(channelId, displayName) {
    if (channelId) return `yt:${channelId}`;
    return `name:${String(displayName || "anon").trim().toLowerCase()}`;
  }

  _playerPointsValue(row) {
    const n = Number(row?.points);
    return Number.isFinite(n) && n > 0 ? Math.round(n) : 0;
  }

  _normalizePlayerRow(row) {
    if (!row || typeof row !== "object") {
      return { displayName: "Anonim", avatarUrl: null, points: 0 };
    }
    return {
      displayName: String(row.displayName || "Anonim").trim() || "Anonim",
      avatarUrl: row.avatarUrl ?? null,
      points: this._playerPointsValue(row),
    };
  }

  _touchPlayer({ channelId, displayName, avatarUrl }) {
    const key = this._playerKey(channelId, displayName);
    let row = this.playerScores.get(key);
    if (!row) {
      row = {
        displayName: displayName || "Anonim",
        avatarUrl: avatarUrl || null,
        points: 0,
      };
      this.playerScores.set(key, row);
    } else {
      row = this._normalizePlayerRow(row);
      if (displayName) row.displayName = displayName;
      if (avatarUrl) row.avatarUrl = avatarUrl;
      this.playerScores.set(key, row);
    }
    return row;
  }

  /** Top 7 — yalnızca puanı olanlar (0 puanlı yanlış denemeler listede görünmez) */
  _rebuildLeaderboardFeed() {
    const rows = [...this.playerScores.values()]
      .map((p) => this._normalizePlayerRow(p))
      .filter((p) => p.points > 0)
      .sort(
        (a, b) =>
          b.points - a.points ||
          a.displayName.localeCompare(b.displayName, "tr")
      )
      .slice(0, this.feedMax)
      .map((p, rank) => ({
        displayName: p.displayName,
        avatarUrl: p.avatarUrl,
        points: p.points,
        rank: rank + 1,
      }));

    this.answerFeed = rows;
  }

  getSnapshot() {
    const q = this.getCurrentQuestion();
    return {
      state: this.state,
      currentIndex: this.currentIndex,
      totalQuestions: this.questions.length,
      question: q,
      winner: this.winner,
      botName: this.botSettings.botName,
      progress: this.questions.length
        ? Math.round(((this.currentIndex + 1) / this.questions.length) * 100)
        : 0,
      feed: this.answerFeed.map((row) => ({
        displayName: row.displayName,
        avatarUrl: row.avatarUrl ?? null,
        points: Math.max(0, Math.round(Number(row.points) || 0)),
        rank: row.rank,
      })),
      interaction: this._getInteractionSnapshot(),
      broadcast: this._broadcastForSnapshot(),
      holdWinnerUntilNextCorrect: this.holdWinnerUntilNextCorrect,
      prizeLabel: this._isCelebritySession() ? this.celebrityPrizeLabel : null,
    };
  }

  _isCelebritySession() {
    const q = this.getCurrentQuestion();
    if (isCelebrityAgeQuestion(q)) return true;
    return (this.questions || []).some((row) => isCelebrityAgeQuestion(row));
  }

  /** Ünlü yaş veya futbol — soru doğru bilinene kadar ekranda kalır */
  _locksQuestionUntilCorrect(question) {
    return (
      isCelebrityAgeQuestion(question) || isFootballQuizQuestion(question)
    );
  }

  _isPromoQuizSession() {
    return (this.questions || []).some(
      (row) => isCelebrityAgeQuestion(row) || isFootballQuizQuestion(row)
    );
  }

  _broadcastForSnapshot() {
    if (!this._broadcast) return null;
    if (Date.now() > this._broadcast.until) {
      this._broadcast = null;
      return null;
    }
    const { text, kind, displayName } = this._broadcast;
    return { text, kind, displayName: displayName || null };
  }

  _clearPromoTimers() {
    if (this._broadcastFollowTimer) {
      clearTimeout(this._broadcastFollowTimer);
      this._broadcastFollowTimer = null;
    }
    if (this._broadcastRotateTimer) {
      clearInterval(this._broadcastRotateTimer);
      this._broadcastRotateTimer = null;
    }
  }

  _clearBroadcastTimers() {
    this._clearPromoTimers();
    this._clearWrongBroadcastQueue();
  }

  _clearWrongBroadcastQueue() {
    this._wrongBroadcastQueue = [];
    this._wrongQueuePlaying = false;
    if (this._wrongQueueTimer) {
      clearTimeout(this._wrongQueueTimer);
      this._wrongQueueTimer = null;
    }
  }

  _wrongQueueKey(channelId, displayName) {
    return `${String(channelId || "").trim()}:${String(displayName || "").trim()}`;
  }

  /**
   * Yanlış cevap şeridi — sırayla, her biri wrongBroadcastHoldMs (varsayılan 5 sn).
   * Aynı kişi tekrar yazarsa kuyruktaki kaydı güncellenir (stacklenmez).
   */
  _enqueueWrongBroadcast(entry) {
    if (!entry?.text) return;
    this._clearPromoTimers();
    const key = entry.key || this._wrongQueueKey(entry.channelId, entry.displayName);
    const item = { ...entry, key };
    const idx = this._wrongBroadcastQueue.findIndex((e) => e.key === key);
    if (idx >= 0) {
      this._wrongBroadcastQueue[idx] = item;
    } else {
      if (this._wrongBroadcastQueue.length >= this.wrongBroadcastQueueMax) {
        this._wrongBroadcastQueue.shift();
      }
      this._wrongBroadcastQueue.push(item);
    }
    this._pumpWrongBroadcastQueue();
  }

  _pumpWrongBroadcastQueue() {
    if (this._wrongQueuePlaying) return;
    if (this.state !== "active") {
      this._clearWrongBroadcastQueue();
      return;
    }
    if (!this._wrongBroadcastQueue.length) {
      const q = this.getCurrentQuestion();
      if (this.state === "active" && q && this._locksQuestionUntilCorrect(q)) {
        this._startPrRotation(q);
      } else if (q) {
        this._maybeIdlePromo(q);
      }
      this._emit();
      return;
    }

    const item = this._wrongBroadcastQueue.shift();
    this._wrongQueuePlaying = true;
    this._broadcast = {
      text: String(item.text).slice(0, 96),
      kind: item.kind || "wrong",
      displayName: item.displayName || null,
      until: Date.now() + this.wrongBroadcastHoldMs,
    };

    if (
      item.botReply &&
      item.authorKey &&
      !this.wrongRepliedAuthors.has(item.authorKey)
    ) {
      this.wrongRepliedAuthors.add(item.authorKey);
      this.onBotReply(item.botReply);
    }

    this._emit();

    this._wrongQueueTimer = setTimeout(() => {
      this._wrongQueueTimer = null;
      this._wrongQueuePlaying = false;
      if (this._broadcast?.text === item.text) {
        this._broadcast = null;
      }
      this._pumpWrongBroadcastQueue();
    }, this.wrongBroadcastHoldMs);
  }

  _setBroadcast(text, kind, displayName = null, holdMs = null) {
    if (!text) return;
    this._clearPromoTimers();
    this._broadcast = {
      text: String(text).slice(0, 96),
      kind: kind || "promo",
      displayName,
      until: Date.now() + (holdMs ?? this.broadcastHoldMs),
    };
  }

  _startPrRotation(question) {
    const tick = () => {
      const qNow = this.getCurrentQuestion();
      if (!qNow || !this._locksQuestionUntilCorrect(qNow)) {
        this._clearPromoTimers();
        return;
      }
      if (this.state !== "active") {
        this._clearPromoTimers();
        return;
      }
      if (this._wrongQueuePlaying || this._wrongBroadcastQueue.length) {
        return;
      }
      const q = question || this.getCurrentQuestion();
      this._broadcast = {
        text: pickPrRotationPromo(q, this.celebrityPrizeLabel).slice(0, 96),
        kind: "engage",
        displayName: null,
        until: Date.now() + this.celebrityPrRotateMs,
      };
      this._emit();
    };
    tick();
    this._broadcastRotateTimer = setInterval(tick, this.celebrityPrRotateMs);
  }

  _setBroadcastCorrectCascade(displayName, points, question) {
    this._clearWrongBroadcastQueue();
    this._setBroadcast(
      `${firstNameShoutout(displayName)}, BİLDİN! +${points}p`,
      "correct",
      displayName,
      this.celebrityCorrectFlashMs
    );
    this._broadcastFollowTimer = setTimeout(() => {
      this._broadcastFollowTimer = null;
      if (!this._isCelebritySession()) return;
      this._startPrRotation(question);
    }, this.celebrityCorrectFlashMs);
  }

  _maybeIdlePromo(question) {
    if (!this._locksQuestionUntilCorrect(question)) return;
    if (this._wrongQueuePlaying || this._wrongBroadcastQueue.length) return;
    if (this._broadcast && Date.now() < this._broadcast.until) return;
    if (this.winner && this.holdWinnerUntilNextCorrect) return;
    this._setBroadcast(
      pickIdlePromo(question, this.celebrityPrizeLabel),
      "promo"
    );
  }

  _celebrityHoldWinner() {
    const q = this.getCurrentQuestion();
    return this.holdWinnerUntilNextCorrect && this._locksQuestionUntilCorrect(q);
  }

  _scheduleAdvanceAfterCorrect(question) {
    const delay = isCelebrityAgeQuestion(question)
      ? this.celebrityCorrectFlashMs
      : 4000;
    this.state = "active";
    this._clearAdvanceTimer();
    if (this._broadcastFollowTimer) {
      clearTimeout(this._broadcastFollowTimer);
      this._broadcastFollowTimer = null;
    }
    this._broadcastFollowTimer = setTimeout(() => {
      this._broadcastFollowTimer = null;
      if (this.state !== "active") return;
      this._goNext({ preserveWinner: true });
    }, delay);
  }

  _clearScores() {
    this.playerScores.clear();
    this.answerFeed = [];
  }

  _resetQuestionInteraction() {
    this._questionPlayerKeys = new Set();
    this._questionAttemptCount = 0;
    this._lastAnswer = null;
  }

  _resetSessionInteraction() {
    this._resetQuestionInteraction();
  }

  _recordAnswerAttempt({ channelId, displayName, answerText, correct }) {
    const key = this._playerKey(channelId, displayName);
    this._questionPlayerKeys.add(key);
    this._questionAttemptCount += 1;
    const answer = String(answerText || "").trim().slice(0, 48);
    this._lastAnswer = {
      displayName: String(displayName || "Anonim").trim() || "Anonim",
      answer,
      correct: !!correct,
      at: new Date().toISOString(),
    };
  }

  _getInteractionSnapshot() {
    return {
      activePlayers: this.playerScores.size,
      questionPlayers: this._questionPlayerKeys.size,
      questionAttempts: this._questionAttemptCount,
      lastAnswer: this._lastAnswer ? { ...this._lastAnswer } : null,
    };
  }

  getCurrentQuestion() {
    if (this.currentIndex < 0 || this.currentIndex >= this.questions.length) {
      return null;
    }
    return this._normalizeQuestion(this.questions[this.currentIndex]);
  }

  _emit() {
    this.onStateChange(this.getSnapshot());
    this.onPersist();
  }

  _clearWrongReplies() {
    this.wrongRepliedAuthors.clear();
  }

  _markQuestionActive() {
    this.questionActiveSince = new Date().toISOString();
  }

  _isStaleForCurrentQuestion(publishedAt) {
    if (!this.questionActiveSince || !publishedAt) return false;
    const msgMs = new Date(publishedAt).getTime();
    const sinceMs = new Date(this.questionActiveSince).getTime();
    if (!Number.isFinite(msgMs) || !Number.isFinite(sinceMs)) return false;
    return msgMs < sinceMs - 1500;
  }

  start() {
    if (!this.questions.length) throw new Error("Soru listesi bos");
    this.currentIndex = 0;
    this.state = "active";
    this.winner = null;
    this.processedMessageIds.clear();
    this._clearWrongReplies();
    this._clearScores();
    this._resetSessionInteraction();
    this._clearAdvanceTimer();
    this._markQuestionActive();
    const q = this.getCurrentQuestion();
    if (q && this._locksQuestionUntilCorrect(q)) {
      this._startPrRotation(q);
    } else {
      this._maybeIdlePromo(q);
    }
    this._emit();
    return this.getSnapshot();
  }

  stop() {
    return this.reset();
  }

  /** Puana, sıraya ve duruma sıfırla (idle) */
  reset() {
    this._clearAdvanceTimer();
    this._clearBroadcastTimers();
    this.state = "idle";
    this.currentIndex = -1;
    this.winner = null;
    this.processedMessageIds.clear();
    this._clearWrongReplies();
    this._clearScores();
    this._resetSessionInteraction();
    this._broadcast = null;
    this._emit();
    return this.getSnapshot();
  }

  _questionPoints(question) {
    const pts = Number(question?.points);
    if (Number.isFinite(pts) && pts > 0) return Math.round(pts);
    return this.pointsPerCorrect;
  }

  _normalizeQuestion(raw) {
    if (!raw || typeof raw !== "object") return raw;
    const imageUrl = String(raw.imageUrl || raw.image || "").trim() || null;
    return {
      ...raw,
      imageUrl,
      points: this._questionPoints(raw),
    };
  }

  skip() {
    if (this.state === "idle" || this.state === "ended") return this.getSnapshot();
    const q = this.getCurrentQuestion();
    if (q && this._locksQuestionUntilCorrect(q)) {
      this._setBroadcast(
        "DOĞRU CEVAP BEKLENİYOR — SORU ATLANAMAZ",
        "promo",
        null,
        4500
      );
      this._emit();
      return this.getSnapshot();
    }
    this._goNext();
    return this.getSnapshot();
  }

  setQuestions(questions) {
    this.questions = (questions || []).map((q) => this._normalizeQuestion(q));
    this.saveQuestions();
    if (this.currentIndex >= this.questions.length) {
      this.currentIndex = this.questions.length - 1;
    }
    this._emit();
  }

  handleChatMessage({
    id,
    author,
    channelId,
    avatarUrl,
    text,
    publishedAt,
  }) {
    if (!id || this.processedMessageIds.has(id)) return null;
    this.processedMessageIds.add(id);

    if (isBotFormattedChat(text, this.botSettings.botName)) return null;

    const cmd = parseChatCommand(text);
    if (cmd) {
      return {
        type: "command",
        command: cmd.command,
        args: cmd.args,
        author,
        channelId,
        id,
      };
    }

    let question = this.getCurrentQuestion();
    const celebrityQ = isCelebrityAgeQuestion(question);
    const footballQ = isFootballQuizQuestion(question);

    if (this.state !== "active") return null;

    if (this._isStaleForCurrentQuestion(publishedAt)) return null;

    if (!question) return null;

    const answerText = extractAnswerFromComment(text);
    if (!answerText || answerText.length < 1) return null;

    const nameFromComment = extractNameFromComment(text);
    const displayName = nameFromComment || author;
    const vars = {
      user: displayName,
      answer: answerText,
      question: question.question,
      bot: this.botSettings.botName,
    };

    const player = this._touchPlayer({ channelId, displayName, avatarUrl });
    const isCorrect = footballQ
      ? matchFootballAnswer(answerText, question)
      : answersMatch(answerText, question.answers);
    this._recordAnswerAttempt({
      channelId,
      displayName,
      answerText,
      correct: isCorrect,
    });

    if (!isCorrect) {
      const authorKey = `${this.currentIndex}:${channelId || author}`;
      let broadcastText = null;
      let broadcastKind = "wrong";

      if (footballQ) {
        const guess = String(answerText || "").trim().slice(0, 24);
        broadcastText = guess
          ? `${firstNameShoutout(displayName)}, ${guess} YANLIŞ!`
          : `${firstNameShoutout(displayName)}, YANLIŞ — TEKRAR DENE!`;
      } else if (celebrityQ) {
        const guessAge = parseAgeFromText(answerText);
        const correctAge = getCorrectAge(question);
        const kind = classifyAgeGuess(
          guessAge,
          correctAge,
          this.celebrityCloseYears,
          this.celebrityWarmYears
        );
        broadcastKind = kind || "far";
        broadcastText = buildWrongBroadcast(
          displayName,
          broadcastKind,
          question,
          answerText
        );
      }

      if (broadcastText) {
        const botPayload =
          this.botSettings.announceWrong &&
          !this.wrongRepliedAuthors.has(authorKey)
            ? {
                authorKey,
                botReply: {
                  type: "wrong",
                  chatText: buildWrongMessage(this.botSettings, vars),
                  user: displayName,
                  answer: answerText,
                },
              }
            : {};

        this._enqueueWrongBroadcast({
          channelId,
          displayName,
          text: broadcastText,
          kind: broadcastKind,
          ...botPayload,
        });
      }

      this._emit();
      return { type: "wrong", user: displayName, broadcast: Boolean(broadcastText) };
    }

    player.points += this._questionPoints(question);

    this.winner = {
      id,
      displayName,
      answer: answerText,
      avatarUrl: avatarUrl ?? null,
      at: publishedAt ?? new Date().toISOString(),
    };

    this._clearWrongBroadcastQueue();

    const lockQuestion = this._locksQuestionUntilCorrect(question);

    if (celebrityQ) {
      this._setBroadcastCorrectCascade(
        displayName,
        this._questionPoints(question),
        question
      );
    } else {
      this._setBroadcast(
        `${firstNameShoutout(displayName)}, BİLDİN! +${this._questionPoints(question)}p`,
        "correct",
        displayName,
        lockQuestion ? this.celebrityCorrectFlashMs : null
      );
    }

    this._rebuildLeaderboardFeed();

    const chatText = buildWinMessage(this.botSettings, vars);
    this.onBotReply({
      type: "correct",
      chatText,
      user: displayName,
      winner: this.winner,
    });

    if (lockQuestion) {
      this._scheduleAdvanceAfterCorrect(question);
    } else {
      this.state = "winner";
      this._advanceTimer = setTimeout(
        () => this._goNext(),
        this.nextQuestionDelayMs
      );
    }

    this._emit();

    return { type: "correct", winner: this.winner, chatText };
  }

  _goNext(opts = {}) {
    this._clearAdvanceTimer();
    this._clearWrongBroadcastQueue();
    this._clearPromoTimers();
    if (!opts.preserveWinner) this.winner = null;
    this._clearWrongReplies();
    this._resetQuestionInteraction();

    if (this.currentIndex + 1 >= this.questions.length) {
      this.state = "ended";
      this._rebuildLeaderboardFeed();
      if (this._isCelebritySession()) {
        const top = this.answerFeed[0];
        if (top?.displayName) {
          this._setBroadcast(
            buildLeaderPrizeBroadcast(top.displayName, this.celebrityPrizeLabel),
            "prize",
            top.displayName
          );
        } else {
          this._setBroadcast(this.celebrityPrizeLabel, "prize");
        }
      } else {
        this._broadcast = null;
      }
      this._emit();
      return;
    }

    this.currentIndex += 1;
    this.state = "active";
    this._markQuestionActive();
    this._rebuildLeaderboardFeed();
    const q = this.getCurrentQuestion();
    if (q && this._locksQuestionUntilCorrect(q)) {
      this._startPrRotation(q);
    } else {
      this._maybeIdlePromo(q);
    }
    this._emit();
  }

  _clearAdvanceTimer() {
    if (this._advanceTimer) {
      clearTimeout(this._advanceTimer);
      this._advanceTimer = null;
    }
  }

  seedDemoPreview() {
    if (!this.questions.length) {
      throw new Error("Önce en az bir soru ekleyin");
    }

    this._clearAdvanceTimer();
    this.currentIndex = 0;
    this.state = "active";
    this.winner = null;
    this.processedMessageIds.clear();
    this._clearWrongReplies();
    this._clearScores();
    this._resetSessionInteraction();
    this._markQuestionActive();

    const names = [
      "ZekiBulmaca",
      "HizliCozucu",
      "BulmacaSever",
      "OyuncuMert",
      "MantikliAdam",
      "CevapciKiz",
      "UstaCozum",
    ];
    const demoPoints = [15, 12, 10, 8, 6, 5, 4];

    names.forEach((displayName, i) => {
      this.playerScores.set(`demo-${i}`, {
        displayName,
        avatarUrl: `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(displayName)}`,
        points: demoPoints[i],
      });
    });

    this._rebuildLeaderboardFeed();
    this._emit();
    return this.getSnapshot();
  }
}
