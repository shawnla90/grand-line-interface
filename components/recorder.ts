/**
 * components/recorder.ts — the in-browser journey recorder. PURE, no React.
 *
 * One job: while the cinematic journey plays, capture the map canvas into a
 * downloadable .webm — the clean "map-only" export for cutting a TikTok
 * without screen-recording chrome.
 *
 * HOW: a compositor canvas redraws the map's WebGL canvas every frame (which
 * is why the map must be constructed with preserveDrawingBuffer — see
 * WorldMap's ?record=1 path) and paints the journey caption INTO the frame,
 * so the export narrates itself. `captureStream(30)` + MediaRecorder does the
 * encoding; vp9 with a vp8 fallback, webm either way.
 *
 * THE HONEST LIMIT, stated where the feature lives: pooled DOM markers — the
 * SHIP included — are HTML, not canvas. They do not exist in this export.
 * The recording shows the sea chart, the voyage line, the 3D islands, the 2.5D
 * story scenes and the captions. Full-fidelity capture (ship and all markers)
 * remains the OS screen recorder; this button is the map-only cut.
 */

export type JourneyRecorder = {
  /** Stop, encode, and trigger the .webm download. Resolves when saved. */
  stop: () => Promise<void>;
};

export type RecorderOptions = {
  /** The map's WebGL canvas (`.maplibregl-canvas`). */
  canvas: HTMLCanvasElement;
  /** Read every frame; drawn bottom-centre into the export. */
  getCaption: () => { label: string; fact: string };
  filename?: string;
};

export function startJourneyRecorder(opts: RecorderOptions): JourneyRecorder | null {
  const src = opts.canvas;
  const comp = document.createElement("canvas");
  comp.width = src.width;
  comp.height = src.height;
  const ctx = comp.getContext("2d");
  if (!ctx) return null;

  const mime = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"].find(
    (m) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(m),
  );
  if (!mime) return null;

  const stream = comp.captureStream(30);
  const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 12_000_000 });
  const chunks: Blob[] = [];
  rec.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data);
  };

  let raf: number | null = null;
  const dpr = Math.max(1, comp.width / Math.max(1, src.clientWidth));
  const draw = () => {
    // The source canvas can resize mid-run (dock collapse, rotation); the
    // compositor keeps its founding size and letterboxes the difference.
    ctx.fillStyle = "#0b1d33";
    ctx.fillRect(0, 0, comp.width, comp.height);
    ctx.drawImage(src, 0, 0, comp.width, comp.height);

    const { label, fact } = opts.getCaption();
    if (label) {
      const cx = comp.width / 2;
      const y = comp.height - 64 * dpr;
      ctx.textAlign = "center";
      ctx.fillStyle = "rgba(6, 14, 25, 0.72)";
      const w = Math.max(ctx.measureText(label).width, fact ? ctx.measureText(fact).width : 0) + 48 * dpr;
      ctx.beginPath();
      ctx.roundRect(cx - w / 2, y - 22 * dpr, w, fact ? 46 * dpr : 32 * dpr, 10 * dpr);
      ctx.fill();
      ctx.fillStyle = "rgba(238, 230, 214, 0.95)";
      ctx.font = `italic ${14 * dpr}px Georgia, serif`;
      ctx.fillText(label, cx, y);
      if (fact) {
        ctx.fillStyle = "rgba(238, 230, 214, 0.66)";
        ctx.font = `${11 * dpr}px Georgia, serif`;
        ctx.fillText(fact, cx, y + 17 * dpr);
      }
    }
    raf = requestAnimationFrame(draw);
  };
  raf = requestAnimationFrame(draw);
  rec.start(1000); // chunk every second so a crashed tab still has most of the run

  return {
    stop: () =>
      new Promise<void>((resolve) => {
        rec.onstop = () => {
          if (raf !== null) cancelAnimationFrame(raf);
          for (const t of stream.getTracks()) t.stop();
          const blob = new Blob(chunks, { type: "video/webm" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = opts.filename ?? "grand-line-journey.webm";
          a.click();
          // Give the click a beat before revoking, or the download races it.
          setTimeout(() => URL.revokeObjectURL(url), 4000);
          resolve();
        };
        rec.stop();
      }),
  };
}
