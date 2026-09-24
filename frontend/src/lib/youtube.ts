// Minimal loader for the YouTube IFrame Player API, shared across every
// live-channel tile. We need the real JS API (not just a raw <iframe src=...>)
// because it's the only way to detect "this channel isn't live right now"
// (onError) instead of silently showing YouTube's own broken-video screen
// inside our layout, and it's what lets us autoplay-muted + offer a real
// unmute button per tile.

let loadPromise: Promise<any> | null = null;

export function loadYouTubeIframeAPI(): Promise<any> {
  if ((window as any).YT?.Player) {
    return Promise.resolve((window as any).YT);
  }
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve) => {
    const previous = (window as any).onYouTubeIframeAPIReady;
    (window as any).onYouTubeIframeAPIReady = () => {
      previous?.();
      resolve((window as any).YT);
    };
    const script = document.createElement("script");
    script.src = "https://www.youtube.com/iframe_api";
    script.async = true;
    document.head.appendChild(script);
  });

  return loadPromise;
}
