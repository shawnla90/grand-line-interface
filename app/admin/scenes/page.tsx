/**
 * app/admin/scenes/page.tsx — the scene inspector (DEV-ONLY).
 *
 * The same guard as /admin/place: 404 in production, never in a deployed build.
 * It exists to answer "why is this scene not on screen" with a reason rather
 * than a shrug, and to make the two traps in the resolver VISIBLE instead of
 * merely asserted — scrub to 322/323 and watch Water 7's base gate fight its own
 * earliest variant; scrub to 239 and watch Skypiea's tie resolve.
 *
 * It ignores FLAGS.narrativeScenes on purpose: the flag governs what a READER
 * sees, and this page has no readers.
 */

import { notFound } from "next/navigation";
import { loadScenes } from "@/lib/scenes-load";
import SceneInspector from "@/components/admin/SceneInspector";
import currentChapter from "@/canon/current-chapter.json";

export const dynamic = "force-dynamic";

export default async function AdminScenesPage({
  searchParams,
}: {
  searchParams: Promise<{ [k: string]: string | string[] | undefined }>;
}) {
  if (process.env.NODE_ENV === "production") notFound();
  const sp = await searchParams;
  const raw = Array.isArray(sp.ch) ? sp.ch[0] : sp.ch;
  const ch = Number.parseInt(raw ?? "", 10);
  const { scenes, _meta } = loadScenes();
  return (
    <SceneInspector
      scenes={scenes}
      warnings={_meta.warnings}
      chapter={Number.isFinite(ch) ? ch : currentChapter.latest_official_chapter}
      chapterMax={currentChapter.latest_official_chapter}
    />
  );
}
