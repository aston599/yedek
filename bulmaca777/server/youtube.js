import { google } from "googleapis";
import {
  formatApiError,
  isQuotaExceededError,
  isStreamEndedError,
  resolveYoutubeMinPollMs,
  resolveYoutubeMaxPollMs,
  resolveYoutubeIdlePollMs,
  resolveYoutubeLiveCheckEveryPolls,
  resolveYoutubeLiveCheckQuietSec,
} from "./utils.js";
import { recordYoutubeQuota, getYoutubeQuotaSnapshot } from "./youtubeQuota.js";
import { readFileSync, writeFileSync, existsSync, unlinkSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const SCOPES = [
  "https://www.googleapis.com/auth/youtube.force-ssl",
];

export class YouTubeChatService {
  constructor({
    clientId,
    clientSecret,
    redirectUri,
    videoId,
    liveChatId,
    tokensPath,
  }) {
    this.tokensPath = tokensPath;
    this.videoId = videoId;
    this.liveChatId = liveChatId;
    this.minPollIntervalMs = resolveYoutubeMinPollMs();
    this.maxPollIntervalMs = resolveYoutubeMaxPollMs();
    this.pollIntervalMs = this.minPollIntervalMs;
    this._pollTimer = null;
    this._pageToken = null;
    this._polling = false;
    this._quotaPausedUntil = 0;
    this._lastQuotaLogAt = 0;
    this.onMessage = null;
    this.onStreamEnded = null;
    this._pollCycle = 0;
    this._liveCheckEveryPolls = resolveYoutubeLiveCheckEveryPolls();
    this._idlePollMs = resolveYoutubeIdlePollMs();
    /** live = oyun aktif; idle = bağlı ama oyun yok — list API çağrılmaz */
    this._pollingMode = "idle";
    this._quietPollStreak = 0;
    this._lastPollHadMessages = false;
    this._lastMessageAt = 0;
    this._liveCheckQuietSec = resolveYoutubeLiveCheckQuietSec();

    this.oauth2 = new google.auth.OAuth2(
      clientId,
      clientSecret,
      redirectUri
    );

    if (tokensPath && existsSync(tokensPath)) {
      try {
        const tokens = JSON.parse(readFileSync(tokensPath, "utf-8"));
        this.oauth2.setCredentials(tokens);
      } catch {
        /* yeniden auth gerekir */
      }
    }

    this.oauth2.on("tokens", (tokens) => {
      const merged = { ...this.oauth2.credentials, ...tokens };
      this.oauth2.setCredentials(merged);
      if (this.tokensPath) {
        try {
          writeFileSync(this.tokensPath, JSON.stringify(merged, null, 2));
        } catch {
          /* yoksay */
        }
      }
    });

    this.youtube = google.youtube({ version: "v3", auth: this.oauth2 });
  }

  persistCredentials() {
    if (!this.tokensPath) return;
    writeFileSync(
      this.tokensPath,
      JSON.stringify(this.oauth2.credentials, null, 2),
      "utf-8"
    );
  }

  getAuthUrl(state) {
    return this.oauth2.generateAuthUrl({
      access_type: "offline",
      prompt: "consent",
      scope: SCOPES,
      state: state ?? undefined,
    });
  }

  async handleCallback(code) {
    const { tokens } = await this.oauth2.getToken(code);
    this.oauth2.setCredentials(tokens);
    this.persistCredentials();
    return tokens;
  }

  isAuthenticated() {
    const creds = this.oauth2.credentials;
    return Boolean(creds?.access_token);
  }

  /** OAuth token dosyasını siler; kanal bağlantısını bu odada kaldırır */
  clearStoredAuth() {
    this.stopPolling();
    this.oauth2.setCredentials({});
    this.liveChatId = null;
    this._pageToken = null;
    if (this.tokensPath && existsSync(this.tokensPath)) {
      try {
        unlinkSync(this.tokensPath);
      } catch {
        /* yoksay */
      }
    }
  }

  /** Süresi dolmuş access token varsa yeniler */
  async ensureAccessToken() {
    if (!this.isAuthenticated()) return false;
    try {
      const { credentials } = this.oauth2;
      if (
        credentials.expiry_date &&
        credentials.expiry_date <= Date.now() + 60_000
      ) {
        await this.oauth2.getAccessToken();
        this.persistCredentials();
      }
      return true;
    } catch {
      return false;
    }
  }

  isQuotaPaused() {
    return Date.now() < this._quotaPausedUntil;
  }

  /** Kota hatası sonrası sunucu duraklatmasını kaldırır (Cloud kotası artırıldıysa) */
  clearQuotaPause() {
    this._quotaPausedUntil = 0;
    this.pollIntervalMs = this.minPollIntervalMs;
  }

  getQuotaState() {
    return {
      paused: this.isQuotaPaused(),
      resumesAt: this._quotaPausedUntil || null,
      pollingMode: this._pollingMode,
      pollIntervalMs: this.pollIntervalMs,
      projectQuota: getYoutubeQuotaSnapshot(),
    };
  }

  _haltPollTimer() {
    if (this._pollTimer) {
      clearTimeout(this._pollTimer);
      this._pollTimer = null;
    }
  }

  setPollingMode(mode) {
    const next = mode === "live" ? "live" : "idle";
    if (this._pollingMode === next) return;
    this._pollingMode = next;
    this._quietPollStreak = 0;
    if (next === "live") {
      this.pollIntervalMs = this.minPollIntervalMs;
      if (this._polling && !this._pollTimer) {
        this._schedulePoll();
      }
    } else {
      this._haltPollTimer();
    }
  }

  _clampPollInterval(ms) {
    return Math.min(
      this.maxPollIntervalMs,
      Math.max(this.minPollIntervalMs, ms)
    );
  }

  _trackApi(method) {
    recordYoutubeQuota(method);
  }

  _pauseForQuota(err) {
    const pauseMs = Math.max(
      60_000,
      Number(process.env.YOUTUBE_QUOTA_PAUSE_MS) || 15 * 60 * 1000
    );
    this._quotaPausedUntil = Date.now() + pauseMs;
    this.pollIntervalMs = Math.max(this.pollIntervalMs, 60_000);
    this.stopPolling();
    if (Date.now() - this._lastQuotaLogAt > 30_000) {
      this._lastQuotaLogAt = Date.now();
      console.error("[YouTube] Kota aşıldı, API duraklatıldı:", formatApiError(err));
    }
  }

  /** Bağlı YouTube kanalı (OAuth sonrası) */
  async getChannelInfo() {
    if (!this.isAuthenticated()) return null;
    if (this.isQuotaPaused()) {
      const err = new Error("YouTube API kotası dolu; kısa süre sonra tekrar deneyin.");
      err.code = "quotaExceeded";
      throw err;
    }
    await this.ensureAccessToken();
    let res;
    try {
      res = await this.youtube.channels.list({
        part: ["snippet"],
        mine: true,
      });
      this._trackApi("channelsList");
    } catch (err) {
      if (isQuotaExceededError(err)) this._pauseForQuota(err);
      throw err;
    }
    const ch = res.data.items?.[0];
    if (!ch) return null;
    const thumb =
      ch.snippet?.thumbnails?.high?.url ||
      ch.snippet?.thumbnails?.medium?.url ||
      ch.snippet?.thumbnails?.default?.url ||
      "";
    const customUrl = ch.snippet?.customUrl || "";
    return {
      id: ch.id,
      title: ch.snippet?.title || "",
      customUrl,
      thumbnailUrl: thumb,
      channelUrl: customUrl
        ? `https://www.youtube.com/${customUrl.replace(/^\//, "")}`
        : ch.id
          ? `https://www.youtube.com/channel/${ch.id}`
          : "",
    };
  }

  /** Kanal + abone + son video (OAuth / yenile — ~3 API birimi) */
  async getChannelProfile() {
    const basic = await this.getChannelInfo();
    if (!basic?.id) return basic;

    let channelRes;
    try {
      channelRes = await this.youtube.channels.list({
        part: ["statistics", "contentDetails"],
        id: [basic.id],
      });
      this._trackApi("channelsList");
    } catch (err) {
      if (isQuotaExceededError(err)) this._pauseForQuota(err);
      return { ...basic, subscriberCount: "", videoCount: "" };
    }

    const row = channelRes.data.items?.[0];
    const stats = row?.statistics || {};
    const uploadsId = row?.contentDetails?.relatedPlaylists?.uploads;

    const profile = {
      ...basic,
      subscriberCount: stats.subscriberCount || "",
      videoCount: stats.videoCount || "",
      lastVideoId: "",
      lastVideoTitle: "",
      lastVideoPublishedAt: "",
      lastVideoDuration: "",
      lastVideoWasLive: false,
    };

    if (!uploadsId) return profile;

    let playlistRes;
    try {
      playlistRes = await this.youtube.playlistItems.list({
        part: ["snippet", "contentDetails"],
        playlistId: uploadsId,
        maxResults: 1,
      });
      this._trackApi("playlistItemsList");
    } catch (err) {
      if (isQuotaExceededError(err)) this._pauseForQuota(err);
      return profile;
    }

    const item = playlistRes.data.items?.[0];
    const videoId = item?.contentDetails?.videoId;
    if (!videoId) return profile;

    profile.lastVideoId = videoId;
    profile.lastVideoTitle = item.snippet?.title || "";
    profile.lastVideoPublishedAt = item.snippet?.publishedAt || "";

    try {
      const videoRes = await this.youtube.videos.list({
        part: ["contentDetails", "liveStreamingDetails"],
        id: [videoId],
      });
      this._trackApi("videosList");
      const video = videoRes.data.items?.[0];
      profile.lastVideoDuration = video?.contentDetails?.duration || "";
      profile.lastVideoWasLive = Boolean(
        video?.liveStreamingDetails?.actualStartTime
      );
    } catch (err) {
      if (isQuotaExceededError(err)) this._pauseForQuota(err);
    }

    return profile;
  }

  _streamEndedError(message) {
    const err = new Error(message || "Yayın sona erdi");
    err.code = "STREAM_ENDED";
    return err;
  }

  /** videos.list — yayın kapandı mı (1 kota birimi) */
  async checkBroadcastStillLive() {
    if (!this.videoId) return false;
    if (this.isQuotaPaused()) return true;

    let res;
    try {
      res = await this.youtube.videos.list({
        part: ["liveStreamingDetails"],
        id: [this.videoId],
      });
      this._trackApi("videosList");
    } catch (err) {
      if (isQuotaExceededError(err)) {
        this._pauseForQuota(err);
        return true;
      }
      if (isStreamEndedError(err)) return false;
      return true;
    }

    const video = res.data.items?.[0];
    if (!video) return false;

    const details = video.liveStreamingDetails;
    if (!details) return false;
    if (details.actualEndTime) return false;

    const activeChat = details.activeLiveChatId;
    if (activeChat) {
      this.liveChatId = activeChat;
      return true;
    }

    if (details.actualStartTime) return true;
    return false;
  }

  async resolveLiveChatId() {
    if (this.isQuotaPaused()) {
      throw new Error(
        "YouTube API kotası dolu. Kota sıfırlanana kadar bekleyin veya Google Cloud’da kotayı artırın."
      );
    }
    if (this.liveChatId) return this.liveChatId;

    if (!this.videoId) {
      throw new Error(
        "Canlı yayın linki gerekli. Panelde bu oda için Sohbet botu → yayın linki → Sohbete bağlan."
      );
    }

    let res;
    try {
      res = await this.youtube.videos.list({
        part: ["liveStreamingDetails"],
        id: [this.videoId],
      });
      this._trackApi("videosList");
    } catch (err) {
      if (isQuotaExceededError(err)) this._pauseForQuota(err);
      throw new Error(formatApiError(err));
    }

    const video = res.data.items?.[0];
    const chatId = video?.liveStreamingDetails?.activeLiveChatId;
    if (!chatId) {
      throw new Error(
        "Canlı sohbet bulunamadı. Yayın şu an canlı mı? Paneldeki link, o anki yayının watch veya /live adresi olmalı."
      );
    }
    this.liveChatId = chatId;
    return chatId;
  }

  async sendMessage(text) {
    const liveChatId = await this.resolveLiveChatId();
    try {
      await this.youtube.liveChatMessages.insert({
        part: ["snippet"],
        requestBody: {
          snippet: {
            liveChatId,
            type: "textMessageEvent",
            textMessageDetails: { messageText: text },
          },
        },
      });
      this._trackApi("liveChatMessagesInsert");
    } catch (err) {
      if (isQuotaExceededError(err)) this._pauseForQuota(err);
      throw new Error(formatApiError(err));
    }
  }

  async pollOnce() {
    if (!this.isAuthenticated()) return;
    if (this.isQuotaPaused()) {
      this.pollIntervalMs = Math.max(this.pollIntervalMs, 60_000);
      return;
    }

    if (this._pollingMode !== "live") {
      return;
    }

    this._pollCycle += 1;
    const recentChat =
      this._lastMessageAt > 0 &&
      Date.now() - this._lastMessageAt < this._liveCheckQuietSec * 1000;
    if (
      !recentChat &&
      this._pollCycle % this._liveCheckEveryPolls === 0
    ) {
      const stillLive = await this.checkBroadcastStillLive();
      if (!stillLive) {
        throw this._streamEndedError("Canlı yayın kapandı");
      }
    }

    const liveChatId = this.liveChatId || (await this.resolveLiveChatId());
    let res;
    try {
      res = await this.youtube.liveChatMessages.list({
        liveChatId,
        part: ["snippet", "authorDetails"],
        pageToken: this._pageToken ?? undefined,
      });
      this._trackApi("liveChatMessagesList");
    } catch (err) {
      if (isQuotaExceededError(err)) {
        this._pauseForQuota(err);
        return;
      }
      if (isStreamEndedError(err)) {
        throw this._streamEndedError(formatApiError(err));
      }
      throw err;
    }

    this._pageToken = res.data.nextPageToken;
    const apiMs = Number(res.data.pollingIntervalMillis);
    let interval = this.minPollIntervalMs;
    if (Number.isFinite(apiMs) && apiMs > 0) {
      interval = Math.max(this.minPollIntervalMs, apiMs);
    }
    interval = this._clampPollInterval(interval);

    const items = res.data.items ?? [];
    let textCount = 0;
    for (const item of items) {
      const snippet = item.snippet;
      if (snippet?.type !== "textMessageEvent") continue;

      const text = snippet.textMessageDetails?.messageText;
      if (!text) continue;
      textCount += 1;
      this._lastMessageAt = Date.now();

      this.onMessage?.({
        id: item.id,
        author: item.authorDetails?.displayName ?? "Anonim",
        channelId: item.authorDetails?.channelId ?? null,
        avatarUrl: item.authorDetails?.profileImageUrl ?? null,
        text,
        publishedAt: snippet.publishedAt,
      });
    }

    if (textCount > 0) {
      this._quietPollStreak = 0;
      this._lastPollHadMessages = true;
      this.pollIntervalMs = interval;
    } else {
      this._quietPollStreak += 1;
      this._lastPollHadMessages = false;
      const quietBase = Number(process.env.YOUTUBE_QUIET_POLL_MS) || 20_000;
      const quietCap = Math.min(
        60_000,
        Math.max(quietBase, interval * 1.5)
      );
      let slow = interval;
      if (this._quietPollStreak >= 3) slow = Math.max(slow, quietBase);
      if (this._quietPollStreak >= 12) slow = Math.max(slow, quietBase + 10_000);
      if (this._quietPollStreak >= 24) slow = Math.max(slow, quietCap);
      this.pollIntervalMs = this._clampPollInterval(slow);
    }
  }

  startPolling(onMessage) {
    this.onMessage = onMessage;
    if (this._polling) return;
    this._polling = true;
    this._schedulePoll();
  }

  stopPolling() {
    this._polling = false;
    this._haltPollTimer();
  }

  _schedulePoll() {
    if (!this._polling) return;

    this.pollOnce()
      .catch((err) => {
        if (err?.code === "STREAM_ENDED" || isStreamEndedError(err)) {
          console.log("[YouTube] Yayın bitti, dinleme durduruluyor:", err.message);
          this.stopPolling();
          const cb = this.onStreamEnded;
          this.onStreamEnded = null;
          cb?.(err.message);
          return;
        }
        console.error("[YouTube]", err.message);
      })
      .finally(() => {
        if (!this._polling || this._pollingMode !== "live") {
          this._haltPollTimer();
          return;
        }
        this._pollTimer = setTimeout(
          () => this._schedulePoll(),
          this.pollIntervalMs
        );
      });
  }
}

/** Geliştirme / API olmadan test */
export class MockChatService {
  constructor() {
    this.onMessage = null;
    this._polling = false;
    this._queue = [];
  }

  isAuthenticated() {
    return true;
  }

  getAuthUrl() {
    return null;
  }

  async sendMessage(text) {
    console.log("[Mock Chat →]", text);
    return text;
  }

  startPolling(onMessage) {
    this.onMessage = onMessage;
    this._polling = true;
  }

  stopPolling() {
    this._polling = false;
  }

  inject(author, text) {
    if (!this._polling || !this.onMessage) return;
    const name = author || "Test";
    this.onMessage({
      id: `mock-${Date.now()}`,
      author: name,
      channelId: `mock-${name.toLowerCase().replace(/\s+/g, "-")}`,
      avatarUrl: `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(name)}`,
      text,
      publishedAt: new Date().toISOString(),
    });
  }
}
