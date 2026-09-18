import { apiClient, StandardResponse } from "../client";
import { CommunityReportCreate, CommunityReportResponse, CommunityIntelligenceResponse } from "../../types/community";

export const communityService = {
  createReport: async (data: CommunityReportCreate): Promise<StandardResponse<CommunityReportResponse>> => {
    // Exact URL defined in API Contract
    const response = await apiClient.post<StandardResponse<CommunityReportResponse>>("/api/v1/community/", data);
    return response.data;
  },

  getIntelligence: async (filters: { type: string; verification: string; }): Promise<CommunityIntelligenceResponse> => {
    try {
      // Pass filters directly to the backend to handle the business logic
      const response = await apiClient.get<StandardResponse<CommunityIntelligenceResponse>>("/api/v1/community/intelligence", {
        params: filters
      });
      return response.data.data;
    } catch (error: any) {
      if (!error.response || error.response.status === 404 || error.response.status === 500) {
        console.warn("Backend Intelligence API not found. Using mock response for UI testing.");
        
        // Mocking a rich DTO payload simulating Bangalore telemetry data for UI validation
        return new Promise((resolve) => {
          setTimeout(() => {
            
            // Mock dynamic report filtering based on requested frontend parameters
            const allReports: CommunityReportResponse[] = [
              {
                id: "r1", _id: "r1", location: { type: "Point", coordinates: [77.5946, 12.9716] },
                report_type: "Harassment", severity: "High", verification_status: "Verified",
                description: "Group of individuals harassing commuters near the transit station.",
                time: "10m ago", distance: 450, upvotes: 12, downvotes: 0, verification_timestamp: "2m ago"
              },
              {
                id: "r2", _id: "r2", location: { type: "Point", coordinates: [77.6000, 12.9780] },
                report_type: "Dark Area", severity: "Medium", verification_status: "Pending",
                description: "Streetlights are completely out on 4th block.",
                time: "1h ago", distance: 1200, upvotes: 4, downvotes: 1
              },
              {
                id: "r3", _id: "r3", location: { type: "Point", coordinates: [77.5900, 12.9700] },
                report_type: "Heavy Crowd", severity: "Low", verification_status: "Verified",
                description: "Protest happening, extreme crowd density.",
                time: "3h ago", distance: 800, upvotes: 45, downvotes: 2, verification_timestamp: "2h ago"
              },
              {
                id: "r4", _id: "r4", location: { type: "Point", coordinates: [77.5850, 12.9750] },
                report_type: "Harassment", severity: "High", verification_status: "Unverified",
                description: "Suspicious activity reported in alley.",
                time: "5h ago", distance: 1500, upvotes: 1, downvotes: 4
              }
            ];

            const filteredReports = allReports.filter(r => {
              if (filters.type !== 'All' && r.report_type !== filters.type) return false;
              if (filters.verification !== 'All' && r.verification_status !== filters.verification) return false;
              return true;
            });

            resolve({
              reports: filteredReports,
              statistics: {
                total: 142,
                verified: 89,
                pending: 34,
                unverified: 19,
                high_risk_areas: 4,
                safe_zones: 12
              },
              trending: {
                most_reported_areas: ["Downtown Transit Center", "4th Block Commercial", "North Campus"],
                most_common_incidents: ["Harassment (34%)", "Dark Areas (28%)"],
                recent_activity: ["Surge in harassment reports near Transit Center."]
              },
              insights: [
                "Night reports reduced by 18% in verified Safe Zones.",
                "AI Agent has rerouted 450 users away from the Transit Center today due to verified hazard data."
              ],
              heatmap_data: {
                verified_only: [
                  { lat: 12.9716, lng: 77.5946, weight: 1.0 },
                  { lat: 12.9700, lng: 77.5900, weight: 0.8 },
                ],
                all_reports: [
                  { lat: 12.9716, lng: 77.5946, weight: 1.0 },
                  { lat: 12.9780, lng: 77.6000, weight: 0.6 },
                  { lat: 12.9700, lng: 77.5900, weight: 0.8 },
                  { lat: 12.9750, lng: 77.5850, weight: 0.4 },
                ]
              }
            });
          }, 600); // 600ms latency
        });
      }
      throw new Error(error.response?.data?.message || "Failed to load community intelligence.");
    }
  }
};
