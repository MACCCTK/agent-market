import { Space_Grotesk, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const displayFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display"
});

const bodyFont = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-body"
});

export const metadata = {
  title: "OpenClaw Agent Marketplace",
  description: "Frontend-only concept for the OpenClaw task marketplace."
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${displayFont.variable} ${bodyFont.variable}`}>
      <body>{children}</body>
    </html>
  );
}
