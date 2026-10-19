# SafeShe Routing Architecture

This document explains the Next.js App Router structure and how navigation and middleware act together to secure the application.

## Route Map

```text
/ (Root)
│
├── /login (Public)
│   └── page.tsx -> Authentication UI
│
├── / (Protected Workspace Group)
│   ├── /home
│   │   └── page.tsx -> Dashboard
│   ├── /journey
│   │   └── page.tsx -> Route Planner
│   ├── /live
│   │   └── page.tsx -> Telemetry Monitor
│   ├── /activity
│   │   └── page.tsx -> History
│   ├── /community
│   │   └── page.tsx -> Anomaly Map
│   ├── /assistant
│   │   └── page.tsx -> AI Chat
│   ├── /emergency
│   │   └── page.tsx -> SOS Center
│   ├── /profile
│   │   └── page.tsx -> User Profile
│   └── /settings
│       └── page.tsx -> App Settings
```

## Middleware Protection Strategy

The application uses `frontend/src/middleware.ts` to implement a strict, server-side route guarding strategy based on JWT tokens stored in cookies (`safeshe_token`).

### The Rules
1. **Public Routes**: `/` (Landing Page) and `/login` (Auth Page).
2. **Protected Routes**: Everything else (all routes within the `(workspace)` group).

### Execution Flow
When a user requests a URL, the Next.js Edge Middleware executes before the page is even rendered:

1. **Check for Token**: Reads `request.cookies.get('safeshe_token')`.
2. **Unauthorized Access**: If the user lacks a token and attempts to access `/home`, the middleware issues a `307 Temporary Redirect` to `/login`.
3. **Authenticated Public Access**: If the user *has* a token and attempts to access the `/login` page or the landing page (`/`), they are forcefully redirected to `/home` to prevent them from logging in twice or seeing public marketing material.

## The `(workspace)` Route Group

The `frontend/src/app/(workspace)` directory is a Next.js Route Group.

The parenthesis `()` mean that "workspace" is **not** included in the URL path. Therefore, the file `app/(workspace)/home/page.tsx` resolves to the URL `/home`, not `/workspace/home`.

### Why use a Route Group?
By grouping all authenticated routes inside `(workspace)`, SafeShe applies a shared layout (`app/(workspace)/layout.tsx`) that contains the `Sidebar` and `FloatingAssistant`. 

This prevents the `Sidebar` from rendering on the public landing page or the `/login` page, which exist outside of this route group.
