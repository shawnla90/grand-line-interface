/**
 * app/breakdown/[chapter]/page.tsx — the chapter breakdown cut.
 *
 * Unlike /event/[slug], this route does NOT collapse locked and nonexistent
 * into one byte-identical page. The reasoning is in lib/breakdowns.ts: the cut
 * is already public on TikTok/YouTube, so its existence isn't the secret — its
 * CONTENT is. A reader short of the chapter gets the number and a pre-blurred
 * poster and nothing else.
 *
 * The branch happens on the SERVER. The locked payload never contains the video
 * path, the title, the beats, or the theory slugs, so there is nothing to
 * recover from view-source. That is the whole point of doing it here rather
 * than hiding a rendered player with CSS.
 *
 * NOTE (Next.js 16): `params` and `searchParams` are both Promises.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import { readChapter } from "@/lib/entry";
import { loadBreakdowns } from "@/lib/breakdowns-load";
import { breakdownAt, readerChapterForBreakdown } from "@/lib/breakdowns";
import { BRAND } from "@/config/brand";

type Props = {
  params: Promise<{ chapter: string }>;
  searchParams: Promise<{ [k: string]: string | string[] | undefined }>;
};

function parseChapter(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const [{ chapter: raw }, sp] = await Promise.all([params, searchParams]);
  const n = parseChapter(raw);
  if (n === null) return { title: `Not found — ${BRAND.shortName}`, robots: { index: false } };

  const view = breakdownAt(loadBreakdowns(), n, readerChapterForBreakdown(sp));

  // A locked breakdown must not leak its title into <title> or OG tags.
  if (view.state !== "charted") {
    return {
      title: `Chapter ${n} breakdown — ${BRAND.shortName}`,
      description: "Catch up to unlock this breakdown.",
      robots: { index: false, follow: false },
    };
  }
  return {
    title: `${view.data.title} — Chapter ${view.data.chapter} — ${BRAND.shortName}`,
    description: BRAND.tagline,
  };
}

export default async function Page({ params, searchParams }: Props) {
  const [{ chapter: raw }, sp] = await Promise.all([params, searchParams]);
  const n = parseChapter(raw);
  if (n === null) notFound();

  // Gate on the UNCLAMPED chapter (see readerChapterForBreakdown): the atlas
  // clamp caps at chapterMax=1185 and would wall a 1188 breakdown forever.
  const view = breakdownAt(loadBreakdowns(), n, readerChapterForBreakdown(sp));
  if (view.state === "none") notFound();

  // ctx is only for threading ?ch onto atlas links, which DO want the clamp.
  const world = buildWorld(loadCanon());
  const ctx = readChapter(world, sp);

  const ch = (p: string) => `${p}?ch=${ctx.chapter}`;

  if (view.state === "locked") {
    return (
      <main className="mx-auto max-w-3xl px-6 py-16">
        <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Breakdown</p>
        <h1 className="mt-2 text-3xl font-semibold">Chapter {view.chapter}</h1>

        <div className="relative mt-8 overflow-hidden rounded-sm border border-rope/70">
          {/* Pre-blurred file baked at build time. The sharp frame is never sent. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={view.locked_poster_path}
            alt=""
            aria-hidden
            className="w-full"
          />
          <div className="absolute inset-0 grid place-items-center bg-sea/70 p-6 text-center">
            <div>
              <p className="text-lg font-semibold">You&rsquo;re at chapter {ctx.chapter}.</p>
              <p className="mt-2 text-sm text-ink/70">
                This breakdown covers chapter {view.chapter}. It unlocks when you get there.
              </p>
            </div>
          </div>
        </div>

        <p className="mt-6 text-sm text-ink/60">
          Set your chapter on the{" "}
          <Link href={ch("/")} className="underline underline-offset-4">
            atlas
          </Link>
          .
        </p>
      </main>
    );
  }

  const b = view.data;

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <p className="text-xs uppercase tracking-[0.2em] text-ink/50">
        Breakdown &middot; Chapter {b.chapter}
      </p>
      <h1 className="mt-2 text-3xl font-semibold">{b.title}</h1>

      <video
        src={b.video_path}
        poster={b.poster_path}
        controls
        playsInline
        preload="metadata"
        className="mt-8 w-full rounded-sm border border-rope/70 bg-black"
      />

      {b.beats.length > 0 && (
        <section className="mt-10">
          <h2 className="text-sm uppercase tracking-[0.16em] text-ink/50">The beats</h2>
          <ol className="mt-4 space-y-2">
            {b.beats.map((beat) => (
              <li key={`${beat.at}-${beat.text.slice(0, 12)}`} className="flex gap-4 text-sm">
                <span className="shrink-0 tabular-nums text-ink/45">
                  {Math.floor(beat.at / 60)}:{String(Math.floor(beat.at % 60)).padStart(2, "0")}
                </span>
                <span>{beat.text}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {b.theory_refs.length > 0 && (
        <section className="mt-10">
          <h2 className="text-sm uppercase tracking-[0.16em] text-ink/50">Receipts</h2>
          <ul className="mt-4 flex flex-wrap gap-2">
            {b.theory_refs.map((slug) => (
              <li key={slug}>
                <Link
                  href={ch(`/theory/${slug}`)}
                  className="inline-block rounded-full border border-rope/70 px-3 py-1 text-sm underline-offset-4 hover:underline"
                >
                  {slug.replace(/-/g, " ")}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-12 text-xs leading-relaxed text-ink/45">{b.credit.line}</p>
    </main>
  );
}
