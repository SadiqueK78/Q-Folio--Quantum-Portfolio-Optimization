import { useEffect, useRef, useState } from "react";
import { loadYouTubeIframeAPI } from "../lib/youtube";

interface Props {
  channelId: string;
  channelName: string;
  reloadKey: number;
}

// YouTube Player API error codes: 2 = invalid param, 5 = HTML5 error,
// 100 = video not found/removed, 101/150 = embedding disallowed by owner.
// For a channel with no active live broadcast, the live_stream embed
// typically fires 100 or 150 rather than ever reaching "playing".
const UNAVAILABLE_ERROR_CODES = new Set([2, 5, 100, 101, 150]);

export function LiveChannelPlayer({ channelId, channelName, reloadKey }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<any>(null);
  const domId = useRef(`yt-player-${channelId}-${Math.random().toString(36).slice(2)}`);

  const [status, setStatus] = useState<"loading" | "playing" | "unavailable">("loading");
  const [muted, setMuted] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    loadYouTubeIframeAPI().then((YT) => {
      if (cancelled || !containerRef.current) return;

      // Build the iframe ourselves so its src can use the channel-live embed
      // trick; YT.Player then wraps this EXISTING iframe (by element id)
      // rather than replacing it, which is what lets the JS API's onError /
      // onStateChange events fire for a channel-based live embed.
      const origin = window.location.origin;
      const iframe = document.createElement("iframe");
      iframe.id = domId.current;
      iframe.src =
        `https://www.youtube.com/embed/live_stream?channel=${channelId}` +
        `&enablejsapi=1&autoplay=1&mute=1&playsinline=1&rel=0&origin=${encodeURIComponent(origin)}`;
      iframe.style.width = "100%";
      iframe.style.height = "100%";
      iframe.style.border = "0";
      iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
      iframe.allowFullscreen = true;

      containerRef.current.innerHTML = "";
      containerRef.current.appendChild(iframe);

      playerRef.current = new YT.Player(domId.current, {
        events: {
          onStateChange: (e: any) => {
            if (cancelled) return;
            // 1 = playing, 3 = buffering — either means the stream is live and loading fine
            if (e.data === 1 || e.data === 3) setStatus("playing");
          },
          onError: (e: any) => {
            if (cancelled) return;
            if (UNAVAILABLE_ERROR_CODES.has(e.data)) setStatus("unavailable");
          },
        },
      });

      // Safety net: if neither onStateChange nor onError fires within 12s
      // (some "no live broadcast" cases fail silently instead of erroring),
      // treat the tile as unavailable rather than spinning forever.
      const timeout = window.setTimeout(() => {
        if (!cancelled) setStatus((s) => (s === "loading" ? "unavailable" : s));
      }, 12000);

      return () => window.clearTimeout(timeout);
    });

    return () => {
      cancelled = true;
      try {
        playerRef.current?.destroy?.();
      } catch {
        /* ignore teardown errors */
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelId, reloadKey]);

  function toggleMute() {
    const player = playerRef.current;
    if (!player) return;
    if (muted) {
      player.unMute?.();
      player.setVolume?.(100);
      setMuted(false);
    } else {
      player.mute?.();
      setMuted(true);
    }
  }

  return (
    <div className="relative w-full h-full bg-canvas">
      <div ref={containerRef} className="absolute inset-0" />

      {status === "loading" && (
        <div className="absolute inset-0 flex items-center justify-center bg-canvas/90">
          <div className="flex items-center gap-2 text-ink-muted text-xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber" />
            </span>
            Connecting to {channelName}\u2026
          </div>
        </div>
      )}

      {status === "unavailable" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface-raised gap-2 px-4 text-center">
          <div className="text-sm text-ink">{channelName}</div>
          <div className="text-xs text-ink-muted">Not currently broadcasting live</div>
          <a
            href={`https://www.youtube.com/channel/${channelId}/live`}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-amber hover:underline mt-1"
          >
            Check on YouTube
          </a>
        </div>
      )}

      {status === "playing" && (
        <button
          onClick={toggleMute}
          className="absolute bottom-2 right-2 z-10 text-xs px-2.5 py-1 rounded bg-canvas/80 border border-hairline text-ink hover:border-amber transition-colors"
        >
          {muted ? "\ud83d\udd07 Unmute" : "\ud83d\udd0a Mute"}
        </button>
      )}
    </div>
  );
}
