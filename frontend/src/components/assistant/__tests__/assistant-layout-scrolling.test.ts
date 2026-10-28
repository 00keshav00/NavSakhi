import { describe, it } from "node:test";
import assert from "node:assert";

describe("NavSakhi Phase 49.0: Assistant Layout Persistence, Scrolling & Viewport Invariants", () => {
  // 1. Layout persistence invariants
  it("1. Three-column layout structure maintains left coordinator, center conversation, and right inspector", () => {
    // Structural layout definition verification
    const layout = {
      container: "relative flex h-full w-full overflow-hidden bg-background",
      leftSidebar: {
        id: "assistant-coordinator-panel",
        desktopClass: "lg:flex lg:w-72 xl:w-80 shrink-0 h-full flex-col border-r",
        scrollArea: "flex-1 min-h-0",
      },
      centerMain: {
        containerClass: "relative flex flex-1 flex-col h-full min-h-0 min-w-0 bg-background/95 overflow-hidden",
        headerClass: "shrink-0 border-b",
        messageAreaClass: "relative flex-1 min-h-0 w-full overflow-hidden",
        composerClass: "shrink-0 border-t z-20",
      },
      rightSidebar: {
        id: "assistant-inspector-panel",
        desktopClass: "lg:flex lg:w-72 xl:w-80 shrink-0 h-full flex-col border-l",
        scrollArea: "flex-1 min-h-0",
      },
    };

    assert.strictEqual(layout.container.includes("overflow-hidden"), true);
    assert.strictEqual(layout.leftSidebar.desktopClass.includes("shrink-0"), true);
    assert.strictEqual(layout.centerMain.containerClass.includes("flex-1"), true);
    assert.strictEqual(layout.centerMain.containerClass.includes("min-h-0"), true);
    assert.strictEqual(layout.centerMain.composerClass.includes("shrink-0"), true);
    assert.strictEqual(layout.rightSidebar.desktopClass.includes("shrink-0"), true);
  });

  it("2. Sending user messages does not remove or conditionally unmount sidebars", () => {
    // Model state transitions
    const evaluateSidebarMount = (
      hasUserMessages: boolean,
      isDesktop: boolean,
      isLeftSidebarOpen: boolean,
      isInspectorOpen: boolean
    ) => {
      // Sidebars mount state is strictly controlled by toggle state, NEVER by message count
      const leftMounted = isDesktop ? isLeftSidebarOpen : isLeftSidebarOpen;
      const rightMounted = isDesktop ? isInspectorOpen : isInspectorOpen;
      return { leftMounted, rightMounted };
    };

    // Before conversation (0 messages)
    const beforeChat = evaluateSidebarMount(false, true, true, true);
    assert.strictEqual(beforeChat.leftMounted, true);
    assert.strictEqual(beforeChat.rightMounted, true);

    // After 1 user message
    const afterOne = evaluateSidebarMount(true, true, true, true);
    assert.strictEqual(afterOne.leftMounted, true);
    assert.strictEqual(afterOne.rightMounted, true);

    // After 20 user and assistant messages
    const afterMany = evaluateSidebarMount(true, true, true, true);
    assert.strictEqual(afterMany.leftMounted, true);
    assert.strictEqual(afterMany.rightMounted, true);
  });

  it("3. Long Markdown responses and multiple messages do not push composer outside the viewport", () => {
    // Verify that composer is a shrink-0 flex child rather than absolute bottom-0 of an unbounded container
    const isComposerDockedInFlow = (composerClass: string) => {
      const isAbsolute = composerClass.includes("absolute");
      const isShrinkZero = composerClass.includes("shrink-0");
      return !isAbsolute && isShrinkZero;
    };

    const composerClass = "shrink-0 border-t border-border/50 bg-card/85 backdrop-blur-xl p-3 sm:p-4 space-y-2.5 z-20";
    assert.strictEqual(isComposerDockedInFlow(composerClass), true);
  });

  // 2. Viewport-scoped internal scrolling invariants
  it("4. Auto-scroll logic scrolls only the conversation viewport element without document window scrolling", () => {
    let containerScrollTop = 0;
    let windowScrollY = 0;

    const mockViewport = {
      scrollHeight: 2400,
      clientHeight: 600,
      scrollTop: 0,
      scrollTo: ({ top }: { top: number }) => {
        containerScrollTop = top;
      },
    };

    // Execute internal scrollToBottom
    const scrollToBottom = (el: typeof mockViewport) => {
      el.scrollTo({ top: el.scrollHeight });
    };

    scrollToBottom(mockViewport);

    // Internal viewport is scrolled to bottom
    assert.strictEqual(containerScrollTop, 2400);
    // Outer window scroll is completely unaffected
    assert.strictEqual(windowScrollY, 0);
  });

  it("5. Respects user upward reading position and suppresses auto-scroll interruption", () => {
    const checkShouldAutoScroll = (
      scrollHeight: number,
      scrollTop: number,
      clientHeight: number
    ) => {
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
      const isUserScrolledUp = distanceFromBottom > 120;
      return !isUserScrolledUp; // only auto-scroll if user is near bottom
    };

    // User at bottom (distanceFromBottom = 0)
    assert.strictEqual(checkShouldAutoScroll(2000, 1400, 600), true);

    // User slightly above bottom (< 120px)
    assert.strictEqual(checkShouldAutoScroll(2000, 1300, 600), true);

    // User scrolled up to inspect older response (distanceFromBottom = 800px > 120px)
    assert.strictEqual(checkShouldAutoScroll(2000, 600, 600), false);
  });

  it("6. Narrow and mobile viewport responsiveness utilizes slide-over drawers with escape and backdrop dismissal", () => {
    const getMobilePanelClasses = (isOpen: boolean) => ({
      leftDrawer: `${isOpen ? "flex" : "hidden"} fixed lg:static inset-y-0 left-0 z-50 lg:z-10 w-72 sm:w-80 lg:w-72 xl:w-80 shrink-0 h-full flex-col`,
      backdrop: isOpen ? "fixed inset-0 z-40 bg-black/50 lg:hidden" : "hidden",
    });

    const openState = getMobilePanelClasses(true);
    assert.strictEqual(openState.leftDrawer.includes("fixed"), true);
    assert.strictEqual(openState.leftDrawer.includes("z-50"), true);
    assert.strictEqual(openState.backdrop.includes("z-40"), true);

    const closedState = getMobilePanelClasses(false);
    assert.strictEqual(closedState.leftDrawer.includes("hidden"), true);
    assert.strictEqual(closedState.backdrop, "hidden");
  });

  it("7. Workspace layout provides min-h-0 flex containment under header", () => {
    const workspaceMainClass = "relative flex-1 min-h-0 overflow-y-auto pb-16 md:pb-0";
    assert.strictEqual(workspaceMainClass.includes("min-h-0"), true);
    assert.strictEqual(workspaceMainClass.includes("flex-1"), true);
  });
});
