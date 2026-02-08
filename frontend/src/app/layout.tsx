import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import "@rainbow-me/rainbowkit/styles.css";
import { ProjectProvider } from "@/context/ProjectContext";
import { Providers } from "./providers";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Yellow-fier - Yellow Network Integration Agent",
  description: "Transform your app to use Yellow Network State Channels",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          <ProjectProvider>
            {children}
          </ProjectProvider>
        </Providers>
      </body>
    </html>
  );
}
