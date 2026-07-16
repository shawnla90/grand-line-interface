/**
 * app/admin/place/page.tsx — the /admin/place tool (DEV-ONLY).
 *
 * Renders the coordinate editor. Guarded so it 404s in production and never ships
 * in a deployed build — the tool writes into canon/ and is only ever for local
 * authoring. Loads the world exactly like app/page.tsx (committed artifact, no
 * fetch) and hands it to the client editor.
 */

import { notFound } from "next/navigation";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import PlaceEditor from "@/components/admin/PlaceEditor";

export const dynamic = "force-dynamic";

export default function AdminPlacePage() {
  if (process.env.NODE_ENV === "production") notFound();
  const world = buildWorld(loadCanon());
  return <PlaceEditor world={world} />;
}
