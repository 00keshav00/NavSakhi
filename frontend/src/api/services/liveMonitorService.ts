import { apiClient, StandardResponse } from "../client";
import { LiveMonitorResponse } from "../../types/liveMonitor";

// Internal mocked state to simulate a moving journey for Phase 5 UI validation
let mockProgress = 0;
let mockLat = 12.9716;
let mockLng = 77.5946;
let mockTimelineCounter = 2;

if (typeof navigator !== 'undefined' && navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      mockLat = pos.coords.latitude;
      mockLng = pos.coords.longitude;
    },
    (err) => console.log("Geolocation error", err)
  );
}

export const liveMonitorService = {
  getMonitorStatus: async (journeyId: string): Promise<LiveMonitorResponse> => {
    try {
      // The exact URL as defined in API_CONTRACT.md
      const response = await apiClient.get<StandardResponse<LiveMonitorResponse>>(`/api/v1/journeys/${journeyId}/monitor`);
      return response.data.data;
    } catch (error: any) {
      if (!error.response || error.response.status === 404 || error.response.status === 500) {
        
        // Progress the mock state simulating real-time telemetry
        mockProgress = Math.min(mockProgress + 5, 100);
        mockLat += 0.0001; // simulate movement North
        mockLng += 0.0001; // simulate movement East
        mockTimelineCounter++;

        const agentTimeline = [
          { id: "t1", action: "Journey Started & Route Verified", time: "10m ago", icon: "play" },
          { id: "t2", action: "Weather context initialized: Clear skies", time: "9m ago", icon: "cloud" },
        ];
        
        if (mockTimelineCounter > 4) agentTimeline.unshift({ id: "t3", action: "Re-evaluating crowd density...", time: "2m ago", icon: "activity" });
        if (mockTimelineCounter > 8) agentTimeline.unshift({ id: "t4", action: "Safety Score optimized: Maintained 98%", time: "Just now", icon: "shield" });

        const fakeGeoJSON = {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              properties: {},
              geometry: {
                type: "LineString",
                coordinates: [
                  [77.5946, 12.9716],
                  [77.5980, 12.9750],
                  [77.6020, 12.9780],
                ]
              }
            }
          ]
        };

        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              journey_id: journeyId || "j_mock_123",
              is_active: mockProgress < 100,
              status_summary: {
                distance_remaining: 2100 - (2100 * (mockProgress / 100)),
                eta: 1440 - (1440 * (mockProgress / 100)),
                transport_mode: "walking",
                progress_percentage: mockProgress,
                current_segment: "Approaching 4th Ave Intersection"
              },
              safety_score: {
                current: 98,
                trend: "improving",
                confidence: 96,
                risk_level: "Low"
              },
              ai_recommendation: {
                recommendation: "Continue on the recommended route.",
                reason: "Conditions remain optimal. Crowd density is stable and lighting is sufficient.",
                confidence: 98,
                warnings: ["Stay alert near the upcoming intersection."],
                suggested_action: "Keep device accessible."
              },
              environment_summary: {
                weather_condition: "Clear",
                visibility: "High (10km)",
                lighting: "Optimal (Streetlights active)",
                crowd_density: "Low",
                police_presence: "Patrol within 1km",
                road_condition: "Dry"
              },
              realtime_alerts: [
                { id: "a1", severity: "info", time: "5m ago", description: "Traffic easing up ahead." }
              ],
              agent_timeline: agentTimeline,
              current_route: {
                distance: 2100,
                duration: 1440,
                safety_score: 98,
                weather_impact: "Positive",
                community_impact: "Neutral",
                risk_factors: ["Intersection crossing"],
                geometry: fakeGeoJSON
              },
              current_location: { lat: mockLat, lng: mockLng }
            });
          }, 300); // 300ms network delay
        });
      }
      
      throw new Error(error.response?.data?.message || "Failed to load live monitor data");
    }
  }
};
