import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  return NextResponse.next();
  const token = request.cookies.get('safeshe_token')?.value;
  const { pathname } = request.nextUrl;

  const isPublicRoute = pathname === '/' || pathname.startsWith('/login');
  
  // Protect all workspace routes (e.g. /home, /journey, /emergency, etc.)
  // If a user is not authenticated and tries to access a protected route, redirect to login
  if (!token && !isPublicRoute) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // If a user is authenticated and tries to access the login or root page, redirect to workspace
  if (token && isPublicRoute) {
    return NextResponse.redirect(new URL('/home', request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Apply middleware to all routes except API, static files, images, etc.
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
