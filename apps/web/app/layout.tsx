import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenClaw Agent Marketplace",
  description: "Task-based agent rental marketplace for OpenClaw capability packages."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-slate-500">OpenClaw</p>
              <h1 className="text-xl font-semibold text-slate-900">Agent Marketplace</h1>
            </div>
            <nav className="flex gap-6 text-sm text-slate-600">
              <Link href="/" className="hover:text-slate-900">
                Templates
              </Link>
              <Link href="/owner/dashboard" className="hover:text-slate-900">
                Owner Dashboard
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
