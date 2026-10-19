# SafeShe Frontend File Index

This document provides a complete, numbered index of every file within the `frontend/` directory that is relevant to the application's source code architecture.

====================================
Frontend folders found : 28
Frontend files found : 73
====================================

## Directory Tree

```text
frontend/
├── components.json
├── eslint.config.mjs
├── next.config.ts
├── package.json
├── postcss.config.mjs
├── tsconfig.json
└── src/
    ├── middleware.ts
    ├── api/
    │   ├── client.ts
    │   └── services/
    │       ├── assistantService.ts
    │       ├── authService.ts
    │       ├── communityService.ts
    │       ├── dashboardService.ts
    │       ├── emergencyService.ts
    │       ├── healthService.ts
    │       ├── journeyService.ts
    │       ├── liveMonitorService.ts
    │       ├── profileService.ts
    │       └── settingsService.ts
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── (workspace)/
    │   │   ├── layout.tsx
    │   │   ├── activity/page.tsx
    │   │   ├── assistant/page.tsx
    │   │   ├── community/page.tsx
    │   │   ├── emergency/page.tsx
    │   │   ├── home/page.tsx
    │   │   ├── journey/page.tsx
    │   │   ├── live/page.tsx
    │   │   ├── profile/page.tsx
    │   │   └── settings/page.tsx
    │   └── login/
    │       └── page.tsx
    ├── components/
    │   ├── theme-provider.tsx
    │   ├── agent/
    │   │   ├── AgentPanel.tsx
    │   │   └── FloatingAssistant.tsx
    │   ├── cards/
    │   │   └── MetricCard.tsx
    │   ├── journey/
    │   │   ├── JourneyForm.tsx
    │   │   └── LiveStatusPanel.tsx
    │   ├── layout/
    │   │   └── Sidebar.tsx
    │   ├── map/
    │   │   └── SafeMap.tsx
    │   ├── providers/
    │   │   └── query-provider.tsx
    │   └── ui/
    │       ├── badge.tsx
    │       ├── button.tsx
    │       ├── card.tsx
    │       ├── dialog.tsx
    │       ├── input.tsx
    │       ├── progress.tsx
    │       ├── scroll-area.tsx
    │       ├── select.tsx
    │       ├── separator.tsx
    │       ├── skeleton.tsx
    │       ├── switch.tsx
    │       └── textarea.tsx
    ├── hooks/
    │   ├── useAssistant.ts
    │   ├── useCommunity.ts
    │   ├── useDashboard.ts
    │   ├── useEmergency.ts
    │   ├── useHealth.ts
    │   ├── useJourney.ts
    │   ├── useLiveMonitor.ts
    │   ├── useLogin.ts
    │   ├── useProfile.ts
    │   └── useSettings.ts
    ├── lib/
    │   └── utils.ts
    ├── store/
    │   ├── authStore.ts
    │   └── emergencyStore.ts
    └── types/
        ├── assistant.ts
        ├── auth.ts
        ├── community.ts
        ├── dashboard.ts
        ├── emergency.ts
        ├── journey.ts
        ├── liveMonitor.ts
        ├── profile.ts
        └── settings.ts
```

## File Inventory

**File 1**
Path: `frontend/package.json`
Extension: `.json`
Category: Config

**File 2**
Path: `frontend/next.config.ts`
Extension: `.ts`
Category: Config

**File 3**
Path: `frontend/tsconfig.json`
Extension: `.json`
Category: Config

**File 4**
Path: `frontend/components.json`
Extension: `.json`
Category: Config

**File 5**
Path: `frontend/postcss.config.mjs`
Extension: `.mjs`
Category: Config

**File 6**
Path: `frontend/eslint.config.mjs`
Extension: `.mjs`
Category: Config

**File 7**
Path: `frontend/src/middleware.ts`
Extension: `.ts`
Category: Middleware

**File 8**
Path: `frontend/src/api/client.ts`
Extension: `.ts`
Category: API Configuration

**File 9**
Path: `frontend/src/api/services/assistantService.ts`
Extension: `.ts`
Category: API Service

**File 10**
Path: `frontend/src/api/services/authService.ts`
Extension: `.ts`
Category: API Service

**File 11**
Path: `frontend/src/api/services/communityService.ts`
Extension: `.ts`
Category: API Service

**File 12**
Path: `frontend/src/api/services/dashboardService.ts`
Extension: `.ts`
Category: API Service

**File 13**
Path: `frontend/src/api/services/emergencyService.ts`
Extension: `.ts`
Category: API Service

**File 14**
Path: `frontend/src/api/services/healthService.ts`
Extension: `.ts`
Category: API Service

**File 15**
Path: `frontend/src/api/services/journeyService.ts`
Extension: `.ts`
Category: API Service

**File 16**
Path: `frontend/src/api/services/liveMonitorService.ts`
Extension: `.ts`
Category: API Service

**File 17**
Path: `frontend/src/api/services/profileService.ts`
Extension: `.ts`
Category: API Service

**File 18**
Path: `frontend/src/api/services/settingsService.ts`
Extension: `.ts`
Category: API Service

**File 19**
Path: `frontend/src/app/globals.css`
Extension: `.css`
Category: Config (Styles)

**File 20**
Path: `frontend/src/app/layout.tsx`
Extension: `.tsx`
Category: Server Component / Layout

**File 21**
Path: `frontend/src/app/page.tsx`
Extension: `.tsx`
Category: Server Component / Page

**File 22**
Path: `frontend/src/app/(workspace)/layout.tsx`
Extension: `.tsx`
Category: Server Component / Layout

**File 23**
Path: `frontend/src/app/(workspace)/activity/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 24**
Path: `frontend/src/app/(workspace)/assistant/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 25**
Path: `frontend/src/app/(workspace)/community/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 26**
Path: `frontend/src/app/(workspace)/emergency/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 27**
Path: `frontend/src/app/(workspace)/home/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 28**
Path: `frontend/src/app/(workspace)/journey/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 29**
Path: `frontend/src/app/(workspace)/live/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 30**
Path: `frontend/src/app/(workspace)/profile/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 31**
Path: `frontend/src/app/(workspace)/settings/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 32**
Path: `frontend/src/app/login/page.tsx`
Extension: `.tsx`
Category: Client Component / Page

**File 33**
Path: `frontend/src/components/theme-provider.tsx`
Extension: `.tsx`
Category: Client Component / Provider

**File 34**
Path: `frontend/src/components/agent/AgentPanel.tsx`
Extension: `.tsx`
Category: Client Component

**File 35**
Path: `frontend/src/components/agent/FloatingAssistant.tsx`
Extension: `.tsx`
Category: Client Component

**File 36**
Path: `frontend/src/components/cards/MetricCard.tsx`
Extension: `.tsx`
Category: Client Component

**File 37**
Path: `frontend/src/components/journey/JourneyForm.tsx`
Extension: `.tsx`
Category: Client Component

**File 38**
Path: `frontend/src/components/journey/LiveStatusPanel.tsx`
Extension: `.tsx`
Category: Client Component

**File 39**
Path: `frontend/src/components/layout/Sidebar.tsx`
Extension: `.tsx`
Category: Client Component

**File 40**
Path: `frontend/src/components/map/SafeMap.tsx`
Extension: `.tsx`
Category: Client Component

**File 41**
Path: `frontend/src/components/providers/query-provider.tsx`
Extension: `.tsx`
Category: Client Component / Provider

**File 42 - 53**
Paths: `frontend/src/components/ui/*.tsx` (badge, button, card, dialog, input, progress, scroll-area, select, separator, skeleton, switch, textarea)
Extension: `.tsx`
Category: Client Component / UI Primitive

**File 54**
Path: `frontend/src/hooks/useAssistant.ts`
Extension: `.ts`
Category: Hook

**File 55**
Path: `frontend/src/hooks/useCommunity.ts`
Extension: `.ts`
Category: Hook

**File 56**
Path: `frontend/src/hooks/useDashboard.ts`
Extension: `.ts`
Category: Hook

**File 57**
Path: `frontend/src/hooks/useEmergency.ts`
Extension: `.ts`
Category: Hook

**File 58**
Path: `frontend/src/hooks/useHealth.ts`
Extension: `.ts`
Category: Hook

**File 59**
Path: `frontend/src/hooks/useJourney.ts`
Extension: `.ts`
Category: Hook

**File 60**
Path: `frontend/src/hooks/useLiveMonitor.ts`
Extension: `.ts`
Category: Hook

**File 61**
Path: `frontend/src/hooks/useLogin.ts`
Extension: `.ts`
Category: Hook

**File 62**
Path: `frontend/src/hooks/useProfile.ts`
Extension: `.ts`
Category: Hook

**File 63**
Path: `frontend/src/hooks/useSettings.ts`
Extension: `.ts`
Category: Hook

**File 64**
Path: `frontend/src/lib/utils.ts`
Extension: `.ts`
Category: Utility

**File 65**
Path: `frontend/src/store/authStore.ts`
Extension: `.ts`
Category: Store

**File 66**
Path: `frontend/src/store/emergencyStore.ts`
Extension: `.ts`
Category: Store

**File 67 - 75**
Paths: `frontend/src/types/*.ts` (assistant, auth, community, dashboard, emergency, journey, liveMonitor, profile, settings)
Extension: `.ts`
Category: Type
