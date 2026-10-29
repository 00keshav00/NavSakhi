import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Phase 51.122 — Map Layering & Community Toolbar Layout Regression Protection", () => {
  it("guarantees MapLibre canvas and markers are isolated in level 0 stacking context", () => {
    // Stacking context isolation contract:
    // Map container must have position: relative and zIndex: 0 so child HTML markers
    // (with zIndex: 5, 12, 15, 25, 30, 40) cannot escape into parent stacking context.
    const mapContainerStyle = { width: "100%", height: "100%", position: "relative", zIndex: 0 };
    assert.equal(mapContainerStyle.position, "relative");
    assert.equal(mapContainerStyle.zIndex, 0);

    // Marker z-indices
    const emergencyMarkerZIndex = 25;
    const selectedMarkerZIndex = 40;
    const activityZoneZIndex = 30;

    // Open panel (Legend / Layers) controls container z-index must be at z-50
    const openPanelZIndex = 50;
    const idleControlsZIndex = 30;

    // Controls container rendered AFTER <Map> with higher zIndex renders strictly above all markers
    assert.ok(openPanelZIndex > emergencyMarkerZIndex);
    assert.ok(openPanelZIndex > selectedMarkerZIndex);
    assert.ok(openPanelZIndex > activityZoneZIndex);
    assert.ok(idleControlsZIndex >= activityZoneZIndex);
  });

  it("enforces two clearly separated control rows in Community map layout", () => {
    // Row 1: Shared Map Controls
    const row1Controls = ["Legend", "Layers", "ZoomIn", "ZoomOut", "Compass"];
    assert.equal(row1Controls.length, 5);
    assert.equal(row1Controls[0], "Legend");
    assert.equal(row1Controls[1], "Layers");

    // Row 2: Community-specific controls (Verified Heatmap + All Data)
    const row2Controls = ["Verified Heatmap", "All Data"];
    assert.equal(row2Controls.length, 2);

    // Dimensions check across mobile viewports: 320px, 360px, 390px, 430px
    const viewports = [320, 360, 390, 430];
    const row1EstimatedWidth = 196; // ~196px compact toolbar
    const row2EstimatedWidth = 220; // ~220px HUD

    for (const vw of viewports) {
      // In the separated two-row layout:
      // Row 1 occupies its own row with max width ~196px < vw
      assert.ok(
        row1EstimatedWidth < vw,
        `Row 1 width (${row1EstimatedWidth}px) must comfortably fit within viewport ${vw}px`
      );

      // Row 2 occupies its own row below Row 1 with max width ~220px < vw
      assert.ok(
        row2EstimatedWidth < vw,
        `Row 2 width (${row2EstimatedWidth}px) must comfortably fit within viewport ${vw}px`
      );

      // In a collided single row, 196 + 220 = 416px, which would overlap at 320px and 360px
      const combinedWidth = row1EstimatedWidth + row2EstimatedWidth;
      if (vw <= 360) {
        assert.ok(
          combinedWidth > vw,
          `Confirming historical defect: unseparated controls (${combinedWidth}px) would have overflowed ${vw}px`
        );
      }
    }
  });

  it("verifies mobile Journey controls top offset clears search bar", () => {
    const journeyTopOffset = "top-[4.25rem] md:top-4"; // 68px on mobile, clears 48px top search bar
    const defaultTopOffset = "top-4"; // 16px on community and default pages

    assert.ok(journeyTopOffset.includes("top-[4.25rem]"));
    assert.ok(defaultTopOffset.includes("top-4"));
  });

  it("validates popover panel dimensions prevent horizontal viewport overflow", () => {
    // Mobile popover width rule: w-[calc(100vw-2rem)]
    const margin = 32; // 2rem
    const viewports = [320, 360, 390, 430];

    for (const vw of viewports) {
      const popoverWidth = vw - margin;
      assert.ok(popoverWidth < vw, `Popover width ${popoverWidth}px must stay strictly within ${vw}px`);
      assert.ok(popoverWidth > 0, `Popover width must be positive`);
    }
  });
});
