import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Openclaw - Mode B",
  description: "Forex session scalper backtest dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-bg text-fg min-h-screen">{children}</body>
    </html>
  );
}
