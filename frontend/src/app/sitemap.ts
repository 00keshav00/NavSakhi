import type { MetadataRoute } from "next";

/**
 * NavSakhi Public Sitemap Generator
 * Indexes exclusively public-facing informational and legal resource pages.
 * Never exposes private user journeys, telemetry streams, or authenticated views.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL;

  // If no public domain is configured in production, omit generating absolute entries
  if (!baseUrl) {
    return [];
  }

  const cleanBase = baseUrl.replace(/\/$/, "");
  const lastModified = new Date();

  return [
    {
      url: `${cleanBase}/`,
      lastModified,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${cleanBase}/resources`,
      lastModified,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${cleanBase}/login`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];
}
