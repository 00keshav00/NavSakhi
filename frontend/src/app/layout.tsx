import type { Metadata, Viewport } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { ReactQueryProvider } from "@/components/providers/query-provider";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({ 
  subsets: ["latin"],
  variable: "--font-jakarta",
  display: "swap",
});

const baseUrl = process.env.NEXT_PUBLIC_APP_URL 
  ? new URL(process.env.NEXT_PUBLIC_APP_URL)
  : undefined;

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFF7FA" },
    { media: "(prefers-color-scheme: dark)", color: "#180D1C" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  metadataBase: baseUrl,
  title: {
    default: "NavSakhi | Intelligent Women's Safety Architecture",
    template: "%s | NavSakhi",
  },
  description: "Next-generation proactive women's safety platform combining real-time multi-modal transit routing, live telemetry monitoring, verified support networks, and environmental risk assessment.",
  applicationName: "NavSakhi",
  authors: [{ name: "NavSakhi Team" }],
  keywords: [
    "women safety",
    "safe transit",
    "Chennai metro safety",
    "MTC bus routes",
    "safety navigation",
    "emergency assistance",
    "live telemetry"
  ],
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: baseUrl?.toString(),
    siteName: "NavSakhi",
    title: "NavSakhi | Safer Journeys, Stronger Women",
    description: "Proactive safety companion for women with data-driven transit corridors, live telemetry tracking, and emergency support.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "NavSakhi - Proactive Safety Companion",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "NavSakhi | Safer Journeys, Stronger Women",
    description: "Proactive safety companion for women with data-driven transit corridors and live telemetry.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jakarta.variable} font-sans antialiased min-h-screen bg-background text-foreground`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <ReactQueryProvider>
            {children}
          </ReactQueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}