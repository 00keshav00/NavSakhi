"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

export default function TestMapPage() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    (window as any).maplibregl = maplibregl;
    if (mapInstance.current || !mapContainer.current) return;

    mapInstance.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          test: {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] }
          }
        },
        layers: []
      }
    });

    const map = mapInstance.current;

    setTimeout(() => {
      console.log("=== TEST MAP LOGS ===");
      console.log("map.loaded():", map.loaded());
      console.log("map.isStyleLoaded():", map.isStyleLoaded());
    }, 2000);

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  return (
    <div style={{ width: "100vw", height: "100vh" }}>
      <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
