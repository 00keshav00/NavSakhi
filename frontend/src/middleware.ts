import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('navsakhi_token')?.value || request.cookies.get('safeshe_token')?.value;
  const { pathname } = request.nextUrl;

  // Public workspace routes accessible to guests without account creation:
  // - Landing page, Login
  // - Public Dashboard (/home) with weather and overview
  // - Journey planner (/journey) with map, transit network, and road safety scoring
  // - AI Assistant (/assistant) for general safety inquiries
  // - Community insights (/community)
  // - Safety resources and emergency helplines (/resources)
  // - Static public assets: /manifest.json and /maplibre-worker.js are served directly
  //   via exact-path checks here so that other .js/.json paths remain protected by auth.
  const isPublicRoute =
    pathname === '/' ||
    pathname.startsWith('/login') ||
    pathname === '/robots.txt' ||
    pathname === '/sitemap.xml' ||
    pathname === '/manifest.json' ||
    pathname === '/maplibre-worker.js' ||
    pathname === '/resources' ||
    pathname === '/home' ||
    pathname === '/journey' ||
    pathname === '/assistant' ||
    pathname === '/community';

  // Protect account-specific routes:
  // - Emergency SOS workflow (/emergency)
  // - Live personalized telemetry monitoring (/live)
  // - Saved journey history & audit logs (/activity)
  // - Emergency contacts management & profile (/settings, /profile)
  if (!token && !isPublicRoute) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // If a user is authenticated and tries to access login, redirect to workspace
  if (token && pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/home', request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Apply middleware to all routes except API, static files, images,
  // and exact standalone public assets: /manifest.json, /maplibre-worker.js, /favicon.ico, /robots.txt, /sitemap.xml.
  // End-anchoring ((?:...)$) ensures that prefix/near-match lookalikes (e.g. /manifest.json.backup, /maplibre-worker.js/extra)
  // are NOT exempted and continue through authentication middleware checks.
  matcher: ['/((?!api|_next/static|_next/image|(?:favicon\\.ico|manifest\\.json|maplibre-worker\\.js|robots\\.txt|sitemap\\.xml)$|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|txt|xml)$).*)'],
};
