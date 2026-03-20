import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SYSTEM-X",
  description: "Forex session scalper",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-bg text-fg min-h-screen">
        <nav className="flex gap-1 px-4 pt-4">
          <Link
            href="/"
            className="px-4 py-2 text-sm font-medium text-muted hover:text-fg transition-colors"
          >
            Backtest
          </Link>
          <Link
            href="/live"
            className="px-4 py-2 text-sm font-medium text-muted hover:text-fg transition-colors border-b-2 border-border"
          >
            Live
          </Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
