import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fuel",
  description: "AI Nutrition & Training Coach",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
