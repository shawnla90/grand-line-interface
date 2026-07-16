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

export const metadata: Metadata = {
  title: `${BRAND.name} — ${BRAND.shortName === BRAND.name ? "a spoiler-safe One Piece atlas" : BRAND.shortName}`,
  description: BRAND.tagline,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} ${pirata.variable} ${fell.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
