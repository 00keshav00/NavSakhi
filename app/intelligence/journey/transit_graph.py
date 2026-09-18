import json
import math
import logging
from collections import defaultdict
import heapq
import os

logger = logging.getLogger(__name__)

class TransitGraph:
    def __init__(self, osm_file: str):
        self.adj = defaultdict(list)
        self.nodes = {}  # idx -> (lat, lon)
        self.coord_map = {}
        self.loaded = False
        if isinstance(osm_file, str):
            self.load_graph(osm_file)
        elif isinstance(osm_file, list):
            for path in osm_file:
                self.load_graph(path)
        
    def load_graph(self, path: str):
        if not os.path.exists(path):
            logger.warning(f"OSM transit geometry file {path} not found.")
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            node_idx = 0
            for element in data.get("elements", []):
                if element["type"] == "way":
                    geom = element.get("geometry", [])
                    way_idxs = []
                    for pt in geom:
                        lat, lon = pt["lat"], pt["lon"]
                        k = f"{lat:.5f},{lon:.5f}"
                        if k not in self.coord_map:
                            self.coord_map[k] = node_idx
                            self.nodes[node_idx] = (lat, lon)
                            node_idx += 1
                        way_idxs.append(self.coord_map[k])
                        
                    for i in range(len(way_idxs) - 1):
                        u, v = way_idxs[i], way_idxs[i+1]
                        dist = self.haversine(self.nodes[u][0], self.nodes[u][1], self.nodes[v][0], self.nodes[v][1])
                        self.adj[u].append((v, dist))
                        self.adj[v].append((u, dist)) # Bidirectional
                        
            self.loaded = True
            logger.info(f"Loaded transit network graph with {len(self.nodes)} spatial track nodes.")
        except Exception as e:
            logger.error(f"Failed to load transit graph: {e}")
            
    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
    def find_nearest_track_node(self, lat: float, lon: float, max_dist_m: float = 2000):
        best_dist = float('inf')
        best_idx = None
        for idx, (n_lat, n_lon) in self.nodes.items():
            dist = self.haversine(lat, lon, n_lat, n_lon)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        if best_dist > max_dist_m:
            return None
        return best_idx
        
    def build_transit_segment(self, mode: str, start_lat: float, start_lon: float, end_lat: float, end_lon: float):
        if not self.loaded:
            return None, 0, "MISSING_GRAPH"
            
        start_idx = self.find_nearest_track_node(start_lat, start_lon)
        end_idx = self.find_nearest_track_node(end_lat, end_lon)
        
        if start_idx is None or end_idx is None:
            return None, 0, "NO_NEARBY_TRACKS"
            
        dist_map = {start_idx: 0}
        prev = {}
        pq = [(0, start_idx)]
        
        while pq:
            d, u = heapq.heappop(pq)
            if u == end_idx:
                break
            if d > dist_map.get(u, float('inf')):
                continue
            for v, w in self.adj[u]:
                alt = d + w
                if alt < dist_map.get(v, float('inf')):
                    dist_map[v] = alt
                    prev[v] = u
                    heapq.heappush(pq, (alt, v))
                    
        if end_idx not in prev and start_idx != end_idx:
            return None, 0, "NO_NETWORK_CONNECTION"
            
        path = []
        curr = end_idx
        while curr != start_idx:
            path.append(curr)
            curr = prev[curr]
        path.append(start_idx)
        path.reverse()
        
        coords = []
        # Return [lon, lat] for GeoJSON LineString
        for n in path:
            coords.append([self.nodes[n][1], self.nodes[n][0]])
            
        return coords, dist_map[end_idx], "SUCCESS"

global_transit_graph = None
osm_metro = os.path.join(os.getcwd(), "osm_metro_lines.json")
osm_suburban = os.path.join(os.getcwd(), "osm_suburban_lines.json")
valid_paths = [p for p in [osm_metro, osm_suburban] if os.path.exists(p)]

if valid_paths:
    global_transit_graph = TransitGraph(valid_paths)
