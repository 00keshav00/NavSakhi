import json
import math
import logging
from collections import defaultdict
import heapq
import os
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

class TransitGraph:
    def __init__(self, osm_file: str):
        self.adj = defaultdict(list)
        self.nodes = {}  # idx -> (lat, lon)
        self.coord_map = {}
        self.node_idx = 0
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
                
            for element in data.get("elements", []):
                if element["type"] == "way":
                    geom = element.get("geometry", [])
                    way_idxs = []
                    for pt in geom:
                        lat, lon = pt["lat"], pt["lon"]
                        k = f"{lat:.5f},{lon:.5f}"
                        if k not in self.coord_map:
                            self.coord_map[k] = self.node_idx
                            self.nodes[self.node_idx] = (lat, lon)
                            self.node_idx += 1
                        way_idxs.append(self.coord_map[k])
                        
                    for i in range(len(way_idxs) - 1):
                        u, v = way_idxs[i], way_idxs[i+1]
                        dist = self.haversine(self.nodes[u][0], self.nodes[u][1], self.nodes[v][0], self.nodes[v][1])
                        self.adj[u].append((v, dist))
                        self.adj[v].append((u, dist)) # Bidirectional
            
            # Bridge OSM breaks (tunnel portals, viaduct ends, crossover switches) within 45m
            # Using spatial grid buckets to keep runtime sub-millisecond
            grid = defaultdict(list)
            for u, (lat, lon) in self.nodes.items():
                grid[(int(lat * 100), int(lon * 100))].append(u)
                
            dead_ends = [u for u in self.nodes if len(self.adj[u]) <= 1]
            stitched = 0
            for u in dead_ends:
                lat_u, lon_u = self.nodes[u]
                c_lat, c_lon = int(lat_u * 100), int(lon_u * 100)
                best_v = None
                best_d = float('inf')
                
                for d_lat in (-1, 0, 1):
                    for d_lon in (-1, 0, 1):
                        for v in grid.get((c_lat + d_lat, c_lon + d_lon), []):
                            if v == u:
                                continue
                            lat_v, lon_v = self.nodes[v]
                            d = self.haversine(lat_u, lon_u, lat_v, lon_v)
                            if 0.5 < d < best_d:
                                best_d = d
                                best_v = v
                                
                if best_d <= 45.0 and best_v is not None:
                    self.adj[u].append((best_v, best_d))
                    self.adj[best_v].append((u, best_d))
                    stitched += 1
                        
            self.loaded = True
            logger.info(f"Loaded transit network graph ({path}) with {len(self.nodes)} spatial track nodes (bridged {stitched} portal/crossover transitions).")
        except Exception as e:
            logger.error(f"Failed to load transit graph: {e}")
            
    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
    def find_nearest_track_node(self, lat: float, lon: float, max_dist_m: float = 500):
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
            
        start_idx = self.find_nearest_track_node(start_lat, start_lon, max_dist_m=600)
        end_idx = self.find_nearest_track_node(end_lat, end_lon, max_dist_m=600)
        
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
        # Terminal snapping: begin exactly at station coordinate [lon, lat]
        coords.append([start_lon, start_lat])
        for n in path:
            pt = [self.nodes[n][1], self.nodes[n][0]]
            if coords[-1] != pt:
                coords.append(pt)
        # Terminal snapping: terminate exactly at destination station coordinate [lon, lat]
        end_pt = [end_lon, end_lat]
        if coords[-1] != end_pt:
            coords.append(end_pt)
            
        return coords, dist_map[end_idx], "SUCCESS"

global_transit_graph = None
global_metro_graph = None
global_suburban_graph = None

osm_metro = os.path.join(os.getcwd(), "osm_metro_lines.json")
osm_suburban = os.path.join(os.getcwd(), "osm_suburban_lines.json")

if os.path.exists(osm_metro):
    global_metro_graph = TransitGraph(osm_metro)

if os.path.exists(osm_suburban):
    global_suburban_graph = TransitGraph(osm_suburban)

def get_graph_for_mode(mode: str) -> Optional[TransitGraph]:
    m = mode.lower() if mode else ""
    if "metro" in m:
        return global_metro_graph
    if "suburban" in m or "train" in m or "rail" in m or "mrts" in m:
        return global_suburban_graph
    return None

