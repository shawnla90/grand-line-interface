import { notFound } from "next/navigation";
import SimProof from "@/components/dev/SimProof";

/**
 * /dev/sim-proof — the East Blue 2.5D proof stage. DEV ONLY: this route 404s
 * in production builds outright, so the sandbox (and its flag bypass) can
 * never reach a reader. The real integration surface stays WorldMap behind
 * NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS.
 */
export default async function SimProofPage({
  searchParams,
}: {
  // Next 16: searchParams is a Promise (see node_modules/next/dist/docs/).
  searchParams: Promise<{ ch?: string }>;
}) {
  if (process.env.NODE_ENV === "production") notFound();
  const params = await searchParams;
  const ch = Math.max(1, Number.parseInt(params.ch ?? "51", 10) || 51);
  return <SimProof initialChapter={ch} />;
}
