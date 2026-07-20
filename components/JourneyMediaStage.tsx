"use client";

import { useEffect, useRef } from "react";
import type { JourneyMediaPlayback } from "@/lib/journey-treatment";

/** The authored chapter cut over the live map. The source stays the master MP4. */
export default function JourneyMediaStage({ playback }: { playback: JourneyMediaPlayback | null }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !playback) {
      video?.pause();
      return;
    }
    const wanted = playback.sourceStartS + playback.elapsedMs / 1000;
    if (Math.abs(video.currentTime - wanted) > 0.5) video.currentTime = wanted;
    void video.play().catch(() => {
      // The map and captions remain complete if a browser blocks delayed media.
    });
  }, [playback]);

  return (
    <div
      className={[
        "pointer-events-none absolute inset-0 z-[18] grid place-items-center transition-opacity duration-500",
        playback ? "opacity-100" : "opacity-0",
      ].join(" ")}
      aria-hidden={!playback}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(6,13,25,0.18),rgba(6,13,25,0.72))]" />
      <div className="relative h-[min(68vh,620px)] overflow-hidden rounded-[24px] border border-gold/45 bg-black shadow-[0_24px_80px_rgba(0,0,0,0.72)] aspect-[9/16]">
        <video
          ref={videoRef}
          src="/art/breakdowns/1188/op1188.mp4"
          poster="/art/breakdowns/1188/poster.jpg"
          preload="metadata"
          playsInline
          className="h-full w-full object-cover"
        />
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent px-4 pt-12 pb-4 text-center">
          <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-gold">Chapter 1188</div>
          <div className="mt-1 font-document text-sm italic text-parchment">VOHU — the cut lands in the atlas</div>
        </div>
      </div>
    </div>
  );
}
