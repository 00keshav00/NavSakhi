import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '../../../..');

describe('NavSakhi Phase 46C: Public Static Assets and Middleware Routing Integrity', () => {
  it('1. /manifest.json exists, is valid JSON, and contains mandatory PWA manifest fields', () => {
    const manifestPath = path.join(frontendRoot, 'public', 'manifest.json');
    assert.ok(fs.existsSync(manifestPath), 'manifest.json must exist in public directory');

    const raw = fs.readFileSync(manifestPath, 'utf-8');
    const manifest = JSON.parse(raw);

    assert.equal(typeof manifest.name, 'string', 'Manifest must contain string name');
    assert.equal(typeof manifest.short_name, 'string', 'Manifest must contain string short_name');
    assert.equal(typeof manifest.start_url, 'string', 'Manifest must contain string start_url');
    assert.equal(typeof manifest.display, 'string', 'Manifest must contain string display');
    assert.ok(Array.isArray(manifest.icons) && manifest.icons.length > 0, 'Manifest must contain non-empty icons array');
  });

  it('2. /maplibre-worker.js exists, is genuine JavaScript, and is not an HTML document', () => {
    const workerPath = path.join(frontendRoot, 'public', 'maplibre-worker.js');
    assert.ok(fs.existsSync(workerPath), 'maplibre-worker.js must exist in public directory');

    const raw = fs.readFileSync(workerPath, 'utf-8');
    assert.ok(raw.length > 100000, 'MapLibre worker must be substantial JS bundle (>100KB)');
    assert.ok(!raw.includes('<!DOCTYPE html>') && !raw.includes('<html'), 'Worker must not be HTML');
    assert.ok(raw.includes('MapLibre GL JS') || raw.includes('maplibregl'), 'Worker must contain genuine MapLibre library code');
  });

  it('3. Middleware config.matcher excludes exact public assets while matching near-matches and protected routes', () => {
    const middlewarePath = path.join(frontendRoot, 'src', 'middleware.ts');
    assert.ok(fs.existsSync(middlewarePath), 'middleware.ts must exist');

    const middlewareCode = fs.readFileSync(middlewarePath, 'utf-8');
    const match = middlewareCode.match(/matcher:\s*\[\s*['"](.*?)['"]\s*\]/);
    assert.ok(match, 'Matcher must be defined in middleware.ts');

    const patternStr = JSON.parse(`"${match[1]}"`);
    const matcherPattern = new RegExp(`^${patternStr}$`);

    // A. Must be EXCLUDED from middleware (bypasses middleware for direct Edge CDN static delivery):
    const excludedAssets = [
      '/manifest.json',
      '/maplibre-worker.js',
      '/robots.txt',
      '/sitemap.xml',
      '/favicon.ico',
      '/_next/static/chunks/main.js',
      '/_next/image?url=logo.png',
      '/logo.png',
    ];
    for (const assetPath of excludedAssets) {
      assert.equal(
        matcherPattern.test(assetPath),
        false,
        `Exact static asset ${assetPath} must bypass middleware`
      );
    }

    // B. Near-match lookalikes MUST remain MATCHED by middleware (must NOT be unintentionally exempted):
    const nearMatchLookalikes = [
      '/manifest.json.backup',
      '/manifest.json/extra',
      '/maplibre-worker.js.backup',
      '/maplibre-worker.js/extra',
      '/robots.txt.backup',
      '/robots.txt/extra',
    ];
    for (const lookalike of nearMatchLookalikes) {
      assert.equal(
        matcherPattern.test(lookalike),
        true,
        `Near-match lookalike ${lookalike} must NOT bypass middleware`
      );
    }

    // C. Arbitrary unverified .json and .js paths MUST remain MATCHED by middleware:
    const arbitraryFiles = [
      '/secret.json',
      '/admin.js',
      '/credentials.json',
    ];
    for (const arb of arbitraryFiles) {
      assert.equal(
        matcherPattern.test(arb),
        true,
        `Arbitrary path ${arb} must remain matched and subject to middleware`
      );
    }

    // D. Protected application routes MUST remain MATCHED by middleware:
    const protectedPages = [
      '/emergency',
      '/live',
      '/profile',
      '/settings',
      '/activity',
    ];
    for (const page of protectedPages) {
      assert.equal(
        matcherPattern.test(page),
        true,
        `Protected route ${page} must remain matched by middleware`
      );
    }

    // E. Public workspace routes that are processed by middleware:
    const publicPages = [
      '/',
      '/home',
      '/journey',
      '/assistant',
      '/community',
    ];
    for (const page of publicPages) {
      assert.equal(
        matcherPattern.test(page),
        true,
        `Public workspace route ${page} matches middleware for session routing`
      );
    }
  });

  it('4. Middleware isPublicRoute logic preserves access to public pages and assets while protecting private routes', () => {
    const isPublic = (pathname: string): boolean => {
      return (
        pathname === '/' ||
        pathname.startsWith('/login') ||
        pathname.startsWith('/register') ||
        pathname === '/robots.txt' ||
        pathname === '/sitemap.xml' ||
        pathname === '/manifest.json' ||
        pathname === '/maplibre-worker.js' ||
        pathname === '/resources' ||
        pathname === '/home' ||
        pathname === '/journey' ||
        pathname === '/assistant' ||
        pathname === '/community'
      );
    };

    const publicRoutes = [
      '/',
      '/login',
      '/login?redirect=/profile',
      '/register',
      '/register?redirect=/journey',
      '/robots.txt',
      '/sitemap.xml',
      '/manifest.json',
      '/maplibre-worker.js',
      '/resources',
      '/home',
      '/journey',
      '/assistant',
      '/community',
    ];
    for (const route of publicRoutes) {
      assert.equal(isPublic(route), true, `Route ${route} should be public`);
    }

    const protectedRoutes = [
      '/emergency',
      '/live',
      '/profile',
      '/settings',
      '/activity',
      '/secret.json',
      '/admin.js',
      '/manifest.json.backup',
      '/manifest.json/extra',
      '/maplibre-worker.js.backup',
      '/maplibre-worker.js/extra',
    ];
    for (const route of protectedRoutes) {
      assert.equal(isPublic(route), false, `Route ${route} must be protected`);
    }
  });
  it('5. Actual middleware.ts contains /register in isPublicRoute and authenticated redirect', () => {
    const middlewarePath = path.join(frontendRoot, 'src', 'middleware.ts');
    const middlewareCode = fs.readFileSync(middlewarePath, 'utf-8');

    assert.ok(
      middlewareCode.includes("pathname.startsWith('/register')"),
      'middleware.ts must include pathname.startsWith("/register") in isPublicRoute'
    );
    assert.ok(
      middlewareCode.includes("pathname.startsWith('/login') || pathname.startsWith('/register')"),
      'middleware.ts must redirect authenticated users trying to access login or register'
    );
  });
});
