import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

async def run_audit():
    results = []
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient() as client:
        # Phase 3 & 4: Schema Validation (GET)
        res = await client.get(f"{base_url}/api/v1/profile/")
        results.append(f"GET /api/v1/profile/ -> {res.status_code}")
        
        res = await client.get(f"{base_url}/api/v1/settings/")
        results.append(f"GET /api/v1/settings/ -> {res.status_code}")
        
        res = await client.get(f"{base_url}/api/v1/dashboard/overview")
        results.append(f"GET /api/v1/dashboard/overview -> {res.status_code}")
        
        # Missing fields -> 422
        res = await client.post(f"{base_url}/api/v1/community/", json={})
        results.append(f"POST /api/v1/community/ (empty) -> {res.status_code}")
        
        # Valid Community Post -> 201
        valid_community = {
            "location": {"coordinates": [77.5946, 12.9716], "type": "Point"},
            "report_type": "Roadblock",
            "description": "Tree fallen"
        }
        res = await client.post(f"{base_url}/api/v1/community/", json=valid_community)
        results.append(f"POST /api/v1/community/ (valid) -> {res.status_code}")
        
        # Invalid Journey Post -> 422
        res = await client.post(f"{base_url}/api/v1/journeys/", json={"source": "A"})
        results.append(f"POST /api/v1/journeys/ (invalid) -> {res.status_code}")
        
        # Valid Journey Post -> 200
        valid_journey = {
            "source": "VIT Chennai",
            "destination": "Kelambakkam",
            "transport_mode": "walking"
        }
        res = await client.post(f"{base_url}/api/v1/journeys/", json=valid_journey)
        results.append(f"POST /api/v1/journeys/ (valid) -> {res.status_code}")
        if res.status_code == 200:
            j_id = res.json().get("data", {}).get("journey_id")
            results.append(f"  Got journey ID: {j_id}")
            
            if j_id:
                # Phase 9: Start Journey
                start_res = await client.post(f"{base_url}/api/v1/journeys/{j_id}/start")
                results.append(f"POST /api/v1/journeys/{j_id}/start -> {start_res.status_code}")
                
                # Phase 11: Monitor Journey
                monitor_res = await client.get(f"{base_url}/api/v1/journeys/{j_id}/monitor")
                results.append(f"GET /api/v1/journeys/{j_id}/monitor -> {monitor_res.status_code}")
        
    with open("audit_results.txt", "w") as f:
        f.write("\n".join(results))
    
    logger.info("AUDIT COMPLETE")

def trigger_audit():
    asyncio.create_task(run_audit())
