import type { MetadataRoute } from "next";

/**
 * NavSakhi Search Engine Crawling Directives
 * Strictly protects user privacy by disallowing authenticated, personalized,
 * live telemetry, and transit routing pages from indexing.
 */
export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL;

  return {
    rules: [
      {
        userAgent: "*",
        allow: [
          "/",
          "/resources",
          "/login",
        ],
        disallow: [
          "/home",
          "/journey",
          "/live",
          "/emergency",
          "/assistant",
          "/community",
          "/profile",
          "/settings",
          "/activity",
          "/developer",
          "/test-map",
          "/api/",
        ],
      },
    ],
    sitemap: baseUrl ? `${baseUrl.replace(/\/$/, "")}/sitemap.xml` : undefined,
  };
}
