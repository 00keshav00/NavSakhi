import urllib.request
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_journey(origin, destination, name):
    print(f"\n==========================================")
    print(f"Testing Journey: {name}")
    print(f"Origin: {origin}, Destination: {destination}")
    print(f"==========================================")
    
    # 1. Login
    login_data = json.dumps({'email': 'testuser@example.com', 'password': 'password123'}).encode('utf-8')
    req = urllib.request.Request('http://localhost:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        token = res['data']['access_token']
        
    # 2. Plan journey
    plan_data = json.dumps({
        'source': f"{origin['latitude']}, {origin['longitude']}",
        'destination': f"{destination['latitude']}, {destination['longitude']}",
        'preferences': ['safest']
    }).encode('utf-8')
    
    req2 = urllib.request.Request('http://localhost:8000/api/v1/journeys/', data=plan_data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    })
    try:
        with urllib.request.urlopen(req2) as resp2:
            res2 = json.loads(resp2.read().decode('utf-8'))
            data = res2['data']
            routes = data.get('recommended_routes', [])
            print(f"Total routes returned: {len(routes)}")
            for i, r in enumerate(routes):
                modes = [s.get('transport_mode') for s in r.get('segments', [])]
                dist = r.get('distance')
                eta = r.get('eta')
                score = r.get('safety_score')
                status = r.get('score_status')
                cov = r.get('scoreable_coverage_ratio')
                route_id = r.get('id')
                chain = r.get('travel_mode_chain')
                print(f"  Route {i+1} [{route_id}] ({r.get('route_name')}): chain='{chain}', dist={dist}, eta={eta}, score={score} ({status}, cov={cov})")
                for j, seg in enumerate(r.get('segments', [])):
                    coords_cnt = len(seg.get('polyline', {}).get('geometry', {}).get('coordinates', []))
                    print(f"    Leg {j+1}: mode={seg.get('transport_mode')}, name='{seg.get('segment_name')}', dist={seg.get('distance')}, eta={seg.get('eta')}, coords={coords_cnt}, score={seg.get('safety_score')} ({seg.get('score_status')}), color={seg.get('color')}")
    except Exception as e:
        print(f"Error testing journey: {e}")

if __name__ == '__main__':
    # Test 1: VIT Chennai -> Marina Mall (MTC Bus Corridor)
    test_journey(
        {'latitude': 12.8406, 'longitude': 80.1534, 'address': 'VIT Chennai'},
        {'latitude': 12.8230, 'longitude': 80.2285, 'address': 'The Marina Mall, OMR'},
        'VIT Chennai to The Marina Mall (Bus Corridor)'
    )
    
    # Test 2: Chennai Central to Chennai Airport (Metro Blue Line corridor)
    test_journey(
        {'latitude': 13.0827, 'longitude': 80.2755, 'address': 'Chennai Central'},
        {'latitude': 12.9800, 'longitude': 80.1639, 'address': 'Chennai Airport'},
        'Chennai Central to Airport (Metro Corridor)'
    )
    
    # Test 3: Chennai Beach to Tambaram (Suburban Rail corridor)
    test_journey(
        {'latitude': 13.0924, 'longitude': 80.2938, 'address': 'Chennai Beach'},
        {'latitude': 12.9249, 'longitude': 80.1197, 'address': 'Tambaram'},
        'Chennai Beach to Tambaram (Suburban Rail Corridor)'
    )
