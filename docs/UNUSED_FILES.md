# SafeShe Frontend Audit: Unused Files

During the deep file-by-file analysis, the following files were identified as orphaned or dead code. They are not imported into the component tree and are safely removable.

## 1. `components/journey/JourneyForm.tsx`
**Reasoning**: This component appears to be an older, static mockup of the Journey Planner input controls. It contains hardcoded toggles (`PreferenceToggle`) and disconnected React state. The actual production UI is implemented natively within `app/(workspace)/journey/page.tsx`.
**Action**: Can be safely deleted.

## 2. `components/journey/LiveStatusPanel.tsx`
**Reasoning**: This component was likely intended for the Live Monitor view, but `app/(workspace)/live/page.tsx` implements its own highly customized HUD (Heads Up Display) overlaying the `SafeMap` directly. `LiveStatusPanel.tsx` is not imported anywhere in the current tree.
**Action**: Can be safely deleted.

## Conclusion
The frontend is remarkably clean. Out of 73 active source files, only 2 components are unused. The rest of the dependency graph is fully interconnected.
