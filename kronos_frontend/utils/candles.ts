// Candle-list merging for the /chart page's scroll-back history.

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

/** Fold the latest page (from the 10s poll) into the loaded series: history older than the
 *  page is kept, and the page replaces everything from its first bar on (the last bar is
 *  still forming, so its values change between polls). */
export function mergeLatest(loaded: Candle[], latest: Candle[]): Candle[] {
  if (latest.length === 0) return loaded;
  const first = latest[0].time;
  return [...loaded.filter((x) => x.time < first), ...latest];
}

/** Put an older page in front of the loaded series. Only bars strictly older than the
 *  current first bar are taken; `added` is how many, so the caller can keep the view steady
 *  (and 0 means the start of the available history). */
export function prependOlder(
  loaded: Candle[],
  older: Candle[],
): { candles: Candle[]; added: number } {
  const oldest = loaded.length ? loaded[0].time : Infinity;
  const seen = new Set<number>();
  const fresh = older
    .filter((x) => x.time < oldest)
    .sort((a, b) => a.time - b.time)
    .filter((x) => (seen.has(x.time) ? false : (seen.add(x.time), true)));
  return { candles: [...fresh, ...loaded], added: fresh.length };
}
