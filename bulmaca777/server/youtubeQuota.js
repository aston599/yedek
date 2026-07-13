/**
 * YouTube Data API v3 günlük kota tahmini (proje geneli, tüm odalar paylaşır).
 * Birimler: https://developers.google.com/youtube/v3/determine_quota_cost
 */
const COST = {
  liveChatMessagesList: 5,
  liveChatMessagesInsert: 50,
  videosList: 1,
  channelsList: 1,
  playlistItemsList: 1,
};

let dayKey = "";
let usage = {
  liveChatMessagesList: 0,
  liveChatMessagesInsert: 0,
  videosList: 0,
  channelsList: 0,
  playlistItemsList: 0,
};

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function rollDay() {
  const k = todayKey();
  if (k !== dayKey) {
    dayKey = k;
    usage = {
      liveChatMessagesList: 0,
      liveChatMessagesInsert: 0,
      videosList: 0,
      channelsList: 0,
      playlistItemsList: 0,
    };
  }
}

export function recordYoutubeQuota(method) {
  rollDay();
  if (usage[method] != null) usage[method] += 1;
}

export function getYoutubeQuotaSnapshot() {
  rollDay();
  const units =
    usage.liveChatMessagesList * COST.liveChatMessagesList +
    usage.liveChatMessagesInsert * COST.liveChatMessagesInsert +
    usage.videosList * COST.videosList +
    usage.channelsList * COST.channelsList +
    usage.playlistItemsList * COST.playlistItemsList;
  const limit = Math.max(
    1000,
    Number(process.env.YOUTUBE_DAILY_QUOTA_LIMIT) || 10_000
  );
  return {
    day: dayKey,
    units,
    limit,
    percent: Math.min(100, Math.round((units / limit) * 1000) / 10),
    calls: { ...usage },
    costs: { ...COST },
  };
}

/** Tahmini saatlik tüketim (mevcut poll aralığına göre) */
export function estimateHourlyListUnits(pollIntervalMs, liveCheckEveryPolls) {
  const ms = Math.max(3000, Number(pollIntervalMs) || 10_000);
  const listsPerHour = Math.floor(3_600_000 / ms);
  const liveChecksPerHour = Math.ceil(listsPerHour / Math.max(1, liveCheckEveryPolls));
  return listsPerHour * COST.liveChatMessagesList + liveChecksPerHour * COST.videosList;
}
