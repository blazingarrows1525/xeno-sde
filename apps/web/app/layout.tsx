import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/app-shell";
import { SESSION_COOKIE, decodeSession } from "@/lib/auth";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Kairos — AI-native CRM",
  description: "An autonomous-but-supervised growth marketer for D2C brands.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#05060f",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const jar = await cookies();
  const user = await decodeSession(jar.get(SESSION_COOKIE)?.value);
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <Providers>
          <AppShell user={user}>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
