/**
 * Safe redirect and route-label mapping utility.
 * Prevents open redirects, protocol-relative exploits, and external URL forwarding.
 */

export interface FriendlyRedirectInfo {
  label: string;
  message: string;
  safePath: string;
}

const ALLOWED_INTERNAL_ROUTES = [
  "/journey",
  "/home",
  "/live",
  "/assistant",
  "/emergency",
  "/profile",
  "/settings",
  "/community",
  "/resources",
  "/safety-guidelines",
  "/about",
  "/help",
  "/limitations",
  "/terms",
  "/privacy",
  "/accessibility",
] as const;

/**
 * Validates that a redirect target string is strictly an allowed internal application route.
 * Rejects external URLs, protocol-relative targets (e.g. //attacker.com), javascript:, data:, etc.
 * Defaults to fallback (default: /home) if target is invalid or untrusted.
 */
export function getSafeRedirectUrl(target?: string | null, fallback = "/home"): string {
  if (!target || typeof target !== "string") {
    return fallback;
  }

  const trimmed = target.trim();

  // Must start with exactly one forward slash and not followed by another slash or backslash
  if (!trimmed.startsWith("/") || trimmed.startsWith("//") || trimmed.startsWith("/\\")) {
    return fallback;
  }

  // Reject URLs containing schemes or dangerous protocols
  if (trimmed.includes("://") || trimmed.toLowerCase().includes("javascript:") || trimmed.toLowerCase().includes("data:")) {
    return fallback;
  }

  // Extract base pathname before query params or fragments
  const [pathname] = trimmed.split(/[?#]/);

  // Check if pathname matches or begins with an allowed internal route
  const isAllowed = ALLOWED_INTERNAL_ROUTES.some(
    (allowed) => pathname === allowed || pathname.startsWith(`${allowed}/`)
  );

  return isAllowed ? trimmed : fallback;
}

/**
 * Returns user-friendly, empathetic sign-in messages instead of exposing raw route text.
 */
export function getFriendlyRedirectInfo(target?: string | null): FriendlyRedirectInfo {
  const safePath = getSafeRedirectUrl(target, "/home");
  const [pathname] = safePath.split(/[?#]/);

  switch (pathname) {
    case "/journey":
      return {
        label: "continue your journey",
        message: "Sign in to continue your journey.",
        safePath,
      };
    case "/home":
      return {
        label: "access your dashboard",
        message: "Sign in to access your dashboard.",
        safePath,
      };
    case "/live":
      return {
        label: "access live journey monitoring",
        message: "Sign in to access live journey monitoring.",
        safePath,
      };
    case "/assistant":
      return {
        label: "chat with NavSakhi Companion",
        message: "Sign in to chat with NavSakhi Companion.",
        safePath,
      };
    case "/emergency":
      return {
        label: "access emergency protocols",
        message: "Sign in to access emergency protocols.",
        safePath,
      };
    case "/profile":
      return {
        label: "access your profile",
        message: "Sign in to access your profile.",
        safePath,
      };
    case "/settings":
      return {
        label: "access account settings",
        message: "Sign in to access account settings.",
        safePath,
      };
    case "/community":
      return {
        label: "access community safety intelligence",
        message: "Sign in to access community safety intelligence.",
        safePath,
      };
    case "/resources":
      return {
        label: "access legal rights and helplines",
        message: "Sign in to access legal rights and helplines.",
        safePath,
      };
    case "/safety-guidelines":
      return {
        label: "safety guidelines",
        message: "You can view safety guidelines directly without signing in, or sign in below to continue.",
        safePath,
      };
    case "/about":
      return {
        label: "about NavSakhi",
        message: "You can learn about NavSakhi directly without signing in, or sign in below to continue.",
        safePath,
      };
    case "/help":
      return {
        label: "help and support",
        message: "You can access help and support directly without signing in, or sign in below to continue.",
        safePath,
      };
    case "/limitations":
      return {
        label: "AI and ML limitations",
        message: "You can review AI and ML limitations directly without signing in, or sign in below to continue.",
        safePath,
      };
    case "/terms":
      return {
        label: "terms and conditions",
        message: "You can review terms and conditions directly without signing in, or sign in below to continue.",
        safePath,
      };
    case "/privacy":
      return {
        label: "privacy policy",
        message: "You can review our privacy policy directly without signing in, or sign in below to continue.",
        safePath,
      };
    case "/accessibility":
      return {
        label: "accessibility statement",
        message: "You can review accessibility statements directly without signing in, or sign in below to continue.",
        safePath,
      };
    default:
      return {
        label: "access your secure workspace",
        message: "Sign in to access your secure workspace.",
        safePath,
      };
  }
}
