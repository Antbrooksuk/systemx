import type { Metadata } from "next";
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
      <body className="bg-bg text-fg h-screen overflow-hidden flex flex-col">
        {children}
      </body>
    </html>
  );
}
