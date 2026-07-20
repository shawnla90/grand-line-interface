import type { Metadata } from "next";
import { Geist, Geist_Mono, IM_Fell_English, Pirata_One } from "next/font/google";
import { BRAND } from "@/config/brand";
import "./globals.css";

// next/font self-hosts these at BUILD time — no request-time call to Google, and
// no external font request from the browser.
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
// Phase 9: the chart's voice. Pirata One (OFL) titles the places; IM Fell
// English (OFL, a real 17th-century sea-document face) speaks the furniture.
// Instruments stay Geist Mono — the readouts are a cockpit, not a poster.
const pirata = Pirata_One({ variable: "--font-pirata", weight: "400", subsets: ["latin"] });
const fell = IM_Fell_English({ variable: "--font-fell", weight: "400", subsets: ["latin"], style: ["normal", "italic"] });

const siteTitle = `${BRAND.name} — ${BRAND.shortName === BRAND.name ? "a spoiler-safe One Piece atlas" : BRAND.shortName}`;

export const metadata: Metadata = {
  // Crawlers need ABSOLUTE og:image urls; without a base, Next emits relative
  // ones and every share preview silently falls back to nothing.
  // NEXT_PUBLIC_SITE_URL is set in production; localhost is the dev default.
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: siteTitle,
  description: BRAND.tagline,
  alternates: { canonical: "/" },
  openGraph: {
    title: siteTitle,
    description: BRAND.promise,
    url: "/",
    siteName: BRAND.name,
    type: "website",
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: `${BRAND.name} spoiler-safe atlas` }],
  },
  twitter: {
    card: "summary_large_image",
    title: siteTitle,
    description: BRAND.promise,
    images: ["/opengraph-image"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} ${pirata.variable} ${fell.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
