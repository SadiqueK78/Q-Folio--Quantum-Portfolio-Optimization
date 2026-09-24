import { useState } from "react";
import { Card } from "../components/Card";
import { LiveChannelPlayer } from "../components/LiveChannelPlayer";

interface Channel {
  id: string;
  channelId: string;
  name: string;
  description: string;
}

// Verified YouTube channel IDs (looked up directly, not guessed).
const CHANNELS: Channel[] = [
  { id: "cnbc", channelId: "UCrp_UI8XtuYfpiqluWLD7Lw", name: "CNBC Television", description: "US markets, breaking business news" },
  { id: "cnbctv18", channelId: "UCmRbHAgG2k2vDUvb3xsEunQ", name: "CNBC-TV18", description: "India's leading business news \u2014 NSE/BSE coverage" },
  { id: "bloomberg", channelId: "UCIALMKvObZNtJ6AmdCLP7Lg", name: "Bloomberg Television", description: "Global markets and finance" },
  { id: "yahoo", channelId: "UCEAZeUIeJs0IjQiqTCdVSIg", name: "Yahoo Finance", description: "Market coverage, stocks, business news" },
];

export function LiveTV() {
  const [reloadKey, setReloadKey] = useState(0);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-xl text-ink">Live TV</h1>
          <p className="text-sm text-ink-muted mt-1">
            All four networks play automatically, muted (browsers block autoplay with sound) \u2014 use the speaker icon on a tile to unmute it.
          </p>
        </div>
        <button
          onClick={() => setReloadKey((k) => k + 1)}
          className="text-xs px-3 py-1.5 rounded border border-hairline text-ink-muted hover:text-ink hover:border-ink-faint transition-colors shrink-0"
        >
          Reload All
        </button>
      </div>

      <Card>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {CHANNELS.map((ch) => (
            <div key={ch.id} className="space-y-2">
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-display text-ink">{ch.name}</span>
                <span className="text-[11px] text-ink-muted">{ch.description}</span>
              </div>
              <div className="w-full rounded-lg overflow-hidden border border-hairline" style={{ aspectRatio: "16 / 9" }}>
                <LiveChannelPlayer channelId={ch.channelId} channelName={ch.name} reloadKey={reloadKey} />
              </div>
            </div>
          ))}
        </div>
        <div className="text-[11px] text-ink-faint mt-4">
          A tile shows "Not currently broadcasting live" if that network has no active YouTube live stream right now \u2014
          this is normal for channels that only stream live during trading hours or scheduled programming, not a bug in
          this app. Streams are provided directly by each network via YouTube and are not hosted, cached, or modified here.
        </div>
      </Card>
    </div>
  );
}
