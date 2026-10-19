import urllib.request
import json
from app.services.auth_service import AuthService

token = AuthService.create_access_token("65e01234567890abcdef1234", "testuser@example.com")

def run_test(name, source_str, dest_str, preferences):
    print(f"\n==================== {name} ====================")
    payload = {
        "source": source_str,
        "destination": dest_str,
        "preferences": preferences
    }
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/journeys/",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            plan_response = data.get("data", {})
            routes = plan_response.get("recommended_routes", [])
            print(f"Total Routes Returned: {len(routes)}")
            for idx, r in enumerate(routes, 1):
                print(f"  [{idx}] {r.get('route_name')}")
                print(f"      Mode Category: {r.get('mode')}")
                print(f"      Travel Mode Chain: {r.get('travel_mode_chain')}")
                print(f"      ETA: {r.get('eta')} | Distance: {r.get('distance')}")
                print(f"      Overall Safety Score: {r.get('safety_score')} (Status: {r.get('score_status')})")
                print(f"      Recommended: {r.get('is_recommended')} | Labels: {r.get('ranking_labels')}")
                segments = r.get("segments", [])
                print(f"      Segments ({len(segments)} legs):")
                for s in segments:
                    geom = s.get("polyline", {}).get("geometry", {})
                    coords = geom.get("coordinates", [])
                    print(f"        * Leg {s.get('sequence')}: {s.get('segment_name')} ({s.get('transport_mode')})")
                    print(f"          - Color: {s.get('color')} | Distance: {s.get('distance')} | ETA: {s.get('eta')}")
                    print(f"          - Safety Score: {s.get('safety_score')} | Status: {s.get('score_status')}")
                    print(f"          - Polyline Points: {len(coords)} | Complete: {s.get('geometry_complete')}")
                    if coords:
                        print(f"          - Start pt: {coords[0]} -> End pt: {coords[-1]}")
            
            gemini = plan_response.get("ai_recommendation")
            if gemini:
                print(f"\n  AI Recommendation (Gemini / Verified Fallback):")
                print(f"    Title: {gemini.get('title')}")
                print(f"    Summary: {gemini.get('summary')}")
                print(f"    Reasoning: {gemini.get('reasoning')}")
            else:
                print("\n  AI Recommendation: None")
    except Exception as e:
        print(f"  Execution failed: {e}")

if __name__ == "__main__":
    # Test A: VIT Chennai to Marina Mall
    run_test("Test A: VIT Chennai to Marina Mall", "12.8448, 80.1527", "12.8359, 80.2291", ["safest"])

    # Test B: VIT Chennai to VR Chennai
    run_test("Test B: VIT Chennai to VR Chennai", "12.84480, 80.15271", "13.0796, 80.1956", ["transit", "safest"])

    # Test C: VIT Chennai to Kandigai
    run_test("Test C: VIT Chennai to Kandigai", "12.8448, 80.1527", "12.8350, 80.1410", ["safest"])
