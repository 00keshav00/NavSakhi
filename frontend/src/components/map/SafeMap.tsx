"use client";

import { useEffect, useRef, useState } from "react";
import Map, { Source, Layer, Marker, NavigationControl } from "react-map-gl/maplibre";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

if (typeof window !== "undefined") {
  maplibregl.setWorkerUrl("/maplibre-worker.js");
}

const DEFAULT_MAP_STYLE = {
  version: 8 as const,
  sources: {
    "osm-raster": {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap Contributors"
    }
  },
  layers: [
    {
      id: "osm-raster-layer",
      type: "raster",
      source: "osm-raster",
      minzoom: 0,
      maxzoom: 19
    }
  ]
};

export default function SafeMap({
  source,
  destination,
  routeGeometry, // Expects a FeatureCollection
  onLocationDetected,
  onRouteClick
}: any) {
  const mapRef = useRef<any>(null);
  const [viewState, setViewState] = useState({
    longitude: 80.2090, // Chennai Default
    latitude: 13.0827,
    zoom: 12
  });
  const isFirstLoad = useRef(true);

  // Initial Geolocation
  useEffect(() => {
    if ("geolocation" in navigator && !source && isFirstLoad.current) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          setViewState((prev) => ({ ...prev, longitude: lng, latitude: lat }));
          onLocationDetected?.(lat, lng);
          isFirstLoad.current = false;
        },
        (error) => console.error("Geolocation error", error)
      );
    }
  }, [source, onLocationDetected]);

  // Fit bounds dynamically across ALL features
  useEffect(() => {
    if (!mapRef.current) return;
    
    let allLngs: number[] = [];
    let allLats: number[] = [];

    // Safe bounds extraction
    if (source && Array.isArray(source.coordinates) && source.coordinates.length >= 2) {
      allLngs.push(source.coordinates[0]);
      allLats.push(source.coordinates[1]);
    }
    if (destination && Array.isArray(destination.coordinates) && destination.coordinates.length >= 2) {
      allLngs.push(destination.coordinates[0]);
      allLats.push(destination.coordinates[1]);
    }

    if (routeGeometry && routeGeometry.features) {
      routeGeometry.features.forEach((feature: any) => {
        if (!feature.geometry || !feature.geometry.coordinates || !Array.isArray(feature.geometry.coordinates)) return;
        
        const extractCoords = (coords: any[]) => {
          if (coords.length === 0) return;
          if (typeof coords[0] === 'number') {
            allLngs.push(coords[0]);
            allLats.push(coords[1]);
          } else if (Array.isArray(coords[0])) {
            coords.forEach(c => extractCoords(c));
          }
        };
        extractCoords(feature.geometry.coordinates);
      });
    }

    if (allLngs.length > 0 && allLats.length > 0) {
      mapRef.current.fitBounds([
        [Math.min(...allLngs), Math.min(...allLats)],
        [Math.max(...allLngs), Math.max(...allLats)]
      ], { padding: 50, duration: 1000 });
    }
  }, [routeGeometry, source, destination]);

  return (
    <div className="relative w-full h-full bg-slate-100 overflow-hidden">
      {(!routeGeometry || !routeGeometry.features || routeGeometry.features.length === 0) && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-white/50 backdrop-blur-sm">
          <div className="bg-white px-6 py-4 rounded-xl shadow-lg border border-purple-100 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-600">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
            </div>
            <div>
              <h3 className="font-bold text-slate-800">No route geometry available</h3>
              <p className="text-sm text-slate-500">The routing engine could not provide coordinates for this path.</p>
            </div>
          </div>
        </div>
      )}
      <Map
        ref={mapRef}
        mapLib={maplibregl}
        {...viewState}
        onMove={(e) => setViewState(e.viewState)}
        mapStyle={DEFAULT_MAP_STYLE as any}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["route-layer-fg-inactive", "route-layer-fg-active"]}
        onClick={(e) => {
          if (e.features && e.features.length > 0) {
            onRouteClick?.(e.features[0].properties);
          }
        }}
      >
        <NavigationControl position="top-right" />
        
        {(() => {
          const sCoords = source?.coordinates;
          if (Array.isArray(sCoords) && sCoords.length >= 2 && sCoords[0] !== undefined) {
            return (
              <Marker longitude={sCoords[0]} latitude={sCoords[1]} anchor="bottom">
                <div className="w-5 h-5 bg-blue-600 rounded-full border-2 border-white shadow-md z-10" />
              </Marker>
            );
          }
          return null;
        })()}
        
        {(() => {
          const dCoords = destination?.coordinates;
          if (Array.isArray(dCoords) && dCoords.length >= 2 && dCoords[0] !== undefined) {
            return (
              <Marker longitude={dCoords[0]} latitude={dCoords[1]} anchor="bottom">
                <div className="w-5 h-5 bg-red-500 rounded-full border-2 border-white shadow-md z-10" />
              </Marker>
            );
          }
          return null;
        })()}
        
        {routeGeometry && (
          <Source id="route-source" type="geojson" data={routeGeometry}>
            {/* Inactive Routes (Background layer) */}
            <Layer
              id="route-layer-bg-inactive"
              type="line"
              filter={["!=", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#ffffff", "line-width": 8, "line-opacity": 0.5 }}
            />
            <Layer
              id="route-layer-fg-inactive"
              type="line"
              filter={["!=", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": ["get", "color"], "line-width": 4, "line-opacity": 0.4 }}
            />
            
            {/* Active Route (Foreground layer) */}
            <Layer
              id="route-layer-bg-active"
              type="line"
              filter={["==", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#ffffff", "line-width": 10, "line-opacity": 1.0 }}
            />
            {/* Active Outline for emphasis */}
            <Layer
              id="route-layer-outline-active"
              type="line"
              filter={["==", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#000000", "line-width": 12, "line-opacity": 0.15 }}
            />
            <Layer
              id="route-layer-fg-active"
              type="line"
              filter={["==", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": ["get", "color"], "line-width": 6, "line-opacity": 1.0 }}
            />
          </Source>
        )}
      </Map>
    </div>
  );
}
