import {
  applyYoutubeAxiosDefaults,
  patchYoutubeChatFetch,
  fetchWatchPageHtml,
} from "./youtubePageFetch.js";
import {
  parseYouTubeVideoIds,
  resolveInnerChatPollMs,
  resolveInnerChatErrorBackoffBaseMs,
} from "./utils.js";

applyYoutubeAxiosDefaults();
patchYoutubeChatFetch();

const { LiveChat } = await import("youtube-chat");
import { auditRecord } from "./auditLog.js";

function defaultStreamHealth() {
  return {
    consecutiveErrors: 0,
    backoffMs: resolveInnerChatErrorBackoffBaseMs(),
    coolingUntil: 0,
    lastLogAt: 0,
    starting: false,
    last400At: 0,
  };
}

/**
 * YouTube canlı sohbet — resmi API kotası olmadan (youtube-chat / iç uç).
 * 400 / geçici hatalarda: dinlemeyi durdur, üst üste istek atma, backoff ile yeniden dene.
 */
export class InnerYouTubeChatService {
  constructor({ videoId = "" } = {}) {
    this.videoIds = parseYouTubeVideoIds(String(videoId || "").trim());
    this.videoId = this.videoIds[0] || "";
    this.liveChatId = null;
    this.onMessage = null;
    this.onStreamEnded = null;
    this.onListenError = null;
    this._polling = false;
    this._retryTimers = new Map();
    this._pollingMode = "idle";
    this._liveChats = new Map();
    /** @type {Map<string, ReturnType<typeof defaultStreamHealth>>} */
    this._streamHealth = new Map();
    this._seenIds = new Set();
    this._seenQueue = [];
    this._pollIntervalMs = resolveInnerChatPollMs();
  }

  _getHealth(videoId) {
    if (!this._streamHealth.has(videoId)) {
      this._streamHealth.set(videoId, defaultStreamHealth());
    }
    return this._streamHealth.get(videoId);
  }

  isStreamCooling(videoId) {
    return this._getHealth(videoId).coolingUntil > Date.now();
  }

  setVideoId(videoId) {
    this.setVideoIds(parseYouTubeVideoIds(String(videoId || "").trim()));
  }

  setVideoIds(videoIds = []) {
    const next = [...new Set((videoIds || []).map((v) => String(v || "").trim()).filter(Boolean))];
    this.videoIds = next;
    this.videoId = next[0] || "";
    if (this._pollingMode === "live" && this._polling) {
      this._stopRemovedStreams();
      void this._ensureLiveChats().catch((err) => {
        console.error("[Inner chat videoId]", err.message);
      });
    }
  }

  async sendMessage(text) {
    console.log("[Bot]", String(text).slice(0, 200));
    return text;
  }

  setPollingMode(mode) {
    const next = mode === "live" ? "live" : "idle";
    if (this._pollingMode === next) {
      if (next === "live" && this._polling && this.videoIds.length) {
        void this._ensureLiveChats().catch((err) => {
          this._logThrottled("_global", err?.message || err);
        });
      }
      return;
    }
    this._pollingMode = next;
    if (next === "live" && this._polling && this.videoIds.length) {
      void this._ensureLiveChats().catch((err) => {
        this._logThrottled("_global", err?.message || err);
      });
    } else if (next === "idle") {
      this._stopAllLiveChats();
    }
  }

  _logThrottled(videoId, msg) {
    const h = this._getHealth(videoId);
    const now = Date.now();
    if (now - h.lastLogAt < 60_000) return;
    h.lastLogAt = now;
    const preview = String(msg || "").slice(0, 160);
    console.warn("[Inner chat]", videoId, preview);
    auditRecord({
      category: "youtube",
      level: "warn",
      message: `chat poll ${videoId}: ${preview}`,
      detail: {
        consecutiveErrors: h.consecutiveErrors,
        backoffMs: h.backoffMs,
        pollIntervalMs: this._pollIntervalMs,
      },
    });
  }

  _trimSeen() {
    while (this._seenIds.size > 8000 && this._seenQueue.length) {
      const old = this._seenQueue.shift();
      this._seenIds.delete(old);
    }
  }

  _extractMessageText(chatItem) {
    const msg = chatItem?.message;
    if (typeof msg === "string") return msg;
    if (Array.isArray(msg)) {
      return msg
        .map((p) => {
          if (typeof p === "string") return p;
          if (p?.text) return p.text;
          if (p?.emojiText) return p.emojiText;
          return "";
        })
        .join("")
        .trim();
    }
    return String(msg || "").trim();
  }

  _streamCount() {
    return this.videoIds.length;
  }

  _stopRemovedStreams() {
    for (const videoId of [...this._liveChats.keys()]) {
      if (!this.videoIds.includes(videoId)) this._stopLiveChat(videoId);
    }
  }

  async _refreshWatchContext(videoId) {
    try {
      await fetchWatchPageHtml(videoId);
    } catch (err) {
      this._logThrottled(videoId, `watch yenileme: ${err.message || err}`);
    }
  }

  _scheduleBackoffRetry(videoId, reason) {
    const health = this._getHealth(videoId);
    health.consecutiveErrors += 1;
    const is400 = /\b400\b|status code 400/i.test(String(reason || ""));
    if (is400) health.last400At = Date.now();

    const base = resolveInnerChatErrorBackoffBaseMs();
    health.backoffMs = Math.min(
      120_000,
      Math.floor(base * Math.pow(1.55, Math.min(health.consecutiveErrors - 1, 6)))
    );
    health.coolingUntil = Date.now() + health.backoffMs;

    const hint = is400
      ? `Sohbet yenileme (400) — ${Math.round(health.backoffMs / 1000)} sn sonra tekrar`
      : String(reason || "Geçici hata").slice(0, 120);

    this._logThrottled(videoId, hint);
    this.onListenError?.(videoId, hint);

    const refreshFirst = is400 && health.consecutiveErrors % 3 === 0;
    if (refreshFirst) {
      void this._refreshWatchContext(videoId).finally(() => {
        this._scheduleListenRetry(videoId, health.backoffMs);
      });
    } else {
      this._scheduleListenRetry(videoId, health.backoffMs);
    }
  }

  _handleStreamError(videoId, err) {
    const msg = err?.message || String(err);
    const health = this._getHealth(videoId);
    if (health.coolingUntil > Date.now()) return;

    this._stopLiveChat(videoId);

    const transient = /finished live|stream ended|offline|not live|ended|timeout|reset|econn/i.test(
      msg
    );
    if (transient) {
      this._scheduleBackoffRetry(videoId, msg);
      return;
    }

    this._scheduleBackoffRetry(videoId, msg);
  }

  async _ensureLiveChat(videoId) {
    if (!videoId || this._pollingMode !== "live") return;
    if (this._liveChats.has(videoId)) return;

    const health = this._getHealth(videoId);
    if (health.coolingUntil > Date.now()) return;
    if (health.starting) return;

    health.starting = true;
    try {
      const liveChat = new LiveChat({ liveId: videoId }, this._pollIntervalMs);
      this._liveChats.set(videoId, liveChat);

      liveChat.on("chat", (item) => {
        const h = this._getHealth(videoId);
        h.consecutiveErrors = 0;
        h.backoffMs = resolveInnerChatErrorBackoffBaseMs();
        h.coolingUntil = 0;

        const id =
          item?.id ||
          `${videoId}-${item?.author?.channelId || "anon"}-${item?.timestamp?.getTime?.() || Date.now()}`;
        const scopedId = `${videoId}:${id}`;
        if (this._seenIds.has(scopedId)) return;
        this._seenIds.add(scopedId);
        this._seenQueue.push(scopedId);
        this._trimSeen();

        const text = this._extractMessageText(item);
        if (!text) return;

        this.onMessage?.({
          id: scopedId,
          author: item?.author?.name || "İzleyici",
          channelId: item?.author?.channelId || id,
          avatarUrl: item?.author?.thumbnail?.url || null,
          text,
          sourceVideoId: videoId,
          publishedAt:
            item?.timestamp instanceof Date
              ? item.timestamp.toISOString()
              : new Date().toISOString(),
        });
      });

      liveChat.on("end", (reason) => {
        this._stopLiveChat(videoId);
        this._scheduleBackoffRetry(
          videoId,
          reason || "Yayın ara verdi — yeniden bağlanılıyor"
        );
      });

      liveChat.on("error", (err) => {
        this._handleStreamError(videoId, err);
      });

      const ok = await liveChat.start();
      if (!ok) {
        this._liveChats.delete(videoId);
        const hint =
          "Canli sohbet acilamadi — yayin kapali olabilir veya video ID yanlis.";
        this._scheduleBackoffRetry(videoId, hint);
        return;
      }

      this._clearRetry(videoId);
      health.consecutiveErrors = 0;
      health.coolingUntil = 0;
      console.log(
        "[Inner chat] start OK",
        videoId,
        `(poll ${this._pollIntervalMs}ms)`
      );
      auditRecord({
        category: "youtube",
        level: "info",
        message: `start OK ${videoId}`,
        detail: {
          activeStreams: [...this._liveChats.keys()],
          pollIntervalMs: this._pollIntervalMs,
        },
      });
    } finally {
      health.starting = false;
    }
  }

  async _ensureLiveChats() {
    if (this._pollingMode !== "live") return;
    for (const videoId of this.videoIds) {
      if (!this.isStreamCooling(videoId)) {
        await this._ensureLiveChat(videoId);
      }
    }
  }

  _clearRetry(videoId) {
    const t = this._retryTimers.get(videoId);
    if (t) {
      clearTimeout(t);
      this._retryTimers.delete(videoId);
    }
  }

  _scheduleListenRetry(videoId, delayMs) {
    this._clearRetry(videoId);
    if (this._pollingMode !== "live" || !this._polling) return;
    const wait = Math.max(5000, Number(delayMs) || resolveInnerChatErrorBackoffBaseMs());
    const timer = setTimeout(() => {
      this._retryTimers.delete(videoId);
      const health = this._getHealth(videoId);
      health.coolingUntil = 0;
      if (
        this._pollingMode === "live" &&
        this._polling &&
        this.videoIds.includes(videoId) &&
        !this._liveChats.has(videoId)
      ) {
        void this._ensureLiveChat(videoId);
      }
    }, wait);
    this._retryTimers.set(videoId, timer);
  }

  _stopLiveChat(videoId) {
    this._clearRetry(videoId);
    const liveChat = this._liveChats.get(videoId);
    if (liveChat) {
      try {
        liveChat.stop();
      } catch {
        /* yoksay */
      }
      this._liveChats.delete(videoId);
    }
    const health = this._getHealth(videoId);
    health.starting = false;
  }

  _stopAllLiveChats() {
    for (const videoId of [...this._liveChats.keys()]) {
      this._stopLiveChat(videoId);
    }
  }

  startPolling(onMessage) {
    this.onMessage = onMessage;
    if (this._polling) return;
    this._polling = true;
    if (this._pollingMode === "live" && this.videoIds.length) {
      void this._ensureLiveChats().catch((err) => {
        console.error("[Inner chat start]", err.message);
      });
    }
  }

  stopPolling() {
    this._polling = false;
    for (const videoId of [...this._retryTimers.keys()]) {
      this._clearRetry(videoId);
    }
    this._stopAllLiveChats();
  }

  getQuotaState() {
    return {
      pollingMode: this._pollingMode,
      pollIntervalMs: this._pollIntervalMs,
      streamCount: this._streamCount(),
      activeStreamIds: [...this._liveChats.keys()],
      coolingStreams: this.videoIds.filter((id) => this.isStreamCooling(id)),
      projectQuota: null,
    };
  }

  getDebugState() {
    const health = {};
    for (const id of this.videoIds) {
      const h = this._getHealth(id);
      health[id] = {
        consecutiveErrors: h.consecutiveErrors,
        backoffMs: h.backoffMs,
        coolingMs: Math.max(0, h.coolingUntil - Date.now()),
        active: this._liveChats.has(id),
      };
    }
    return {
      polling: this._polling,
      pollingMode: this._pollingMode,
      pollIntervalMs: this._pollIntervalMs,
      videoIds: [...this.videoIds],
      activeStreamIds: [...this._liveChats.keys()],
      seenCacheSize: this._seenIds.size,
      streamHealth: health,
    };
  }
}
