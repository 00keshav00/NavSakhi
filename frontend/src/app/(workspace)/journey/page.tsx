"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  MapPin, Navigation, ShieldCheck, AlertTriangle, Footprints, Car, Bus, Search, 
  Clock, Train, Info, ArrowLeft, Bike, Leaf, Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import SafeMap from "@/components/map/SafeMap";
import { useJourney } from "@/hooks/useJourney";
import { MultimodalRoute, RouteSegment } from "@/types/journey";
import { toast } from "sonner";

export default function JourneyWizard() {
  const { data, isLoading, planJourney, resetJourney } = useJourney();
  
  // Layer State
  const [layer, setLayer] = useState<1 | 2>(1);

  // Form State (Layer 1)
  const [sourceInput, setSourceInput] = useState("");
  const [destInput, setDestInput] = useState("");
  const [timeMode, setTimeMode] = useState<"now" | "later">("now");
  const [laterDate, setLaterDate] = useState("");
  const [laterTime, setLaterTime] = useState("");
  const [transportPref, setTransportPref] = useState<"any" | "public" | "personal">("any");
  const [vehicleType, setVehicleType] = useState<"two_wheeler" | "four_wheeler">("four_wheeler");

  // Selection State (Layer 2)
  const [activeRouteId, setActiveRouteId] = useState<string | null>(null);

  // Extract Routes
  const routes: MultimodalRoute[] = data?.recommended_routes || [];
  const zeroDistance = data?.zero_distance || false;
  const warnings = data?.warnings || [];

  // Reset helper
  const handleBackToStrategy = () => {
    setLayer(1);
    setActiveRouteId(null);
  };

  const handleSearch = () => {
    if (!sourceInput || !destInput) {
      toast.error("Please enter source and destination.");
      return;
    }
    
    let preferences = ["safest"];
    if (transportPref === "public") preferences.push("public_transport");
    if (transportPref === "personal") {
      preferences.push("personal_vehicle");
      preferences.push(vehicleType);
    }
    
    let reqTime = undefined;
    if (timeMode === "later" && laterDate && laterTime) {
      reqTime = new Date(`${laterDate}T${laterTime}`).toISOString();
    }
    planJourney({
      source: sourceInput,
      destination: destInput,
      preferences: preferences,
      travel_time: reqTime
    });
  };

  const getModeIcon = (mode: string) => {
    const m = mode.toLowerCase();
    if (m.includes("walk")) return <Footprints className="w-4 h-4" />;
    if (m.includes("metro")) return <Train className="w-4 h-4" />;
    if (m.includes("rail") || m.includes("train") || m.includes("mrts")) return <Train className="w-4 h-4" />;
    if (m.includes("bus")) return <Bus className="w-4 h-4" />;
    if (m.includes("bike") || m.includes("two_wheeler")) return <Bike className="w-4 h-4" />;
    return <Car className="w-4 h-4" />;
  };

  const activeGeoJson = useMemo(() => {
    if (!routes || routes.length === 0) return null;
    let allFeatures: any[] = [];
    
    routes.forEach(route => {
      const isActive = route.id === activeRouteId;
      // In Layer 1, maybe show all faded? No, only show map in Layer 2.
      if (layer === 1) return; 
      
      const features = (route.segments || []).map(seg => {
        const feature = { ...(seg.polyline || { type: "Feature", geometry: { type: "LineString", coordinates: []} }) };
        if (!feature.properties) feature.properties = {};
        feature.properties.color = seg.color || "#4CAF50";
        feature.properties.isActive = isActive;
        feature.properties.routeId = route.id;
        return feature;
      });
      
      if (isActive) allFeatures.push(...features);
      else allFeatures.unshift(...features);
    });
    
    return { type: "FeatureCollection", features: allFeatures };
  }, [routes, activeRouteId, layer]);

  // LAYER 1: Strategy Selection View
  const renderLayer1 = () => (
    <div className="flex flex-col h-full bg-[#F6F2FF] p-4 md:p-8 max-w-4xl mx-auto space-y-6">
      <div className="bg-[#FCFAFF] p-6 rounded-xl shadow-sm border border-[#E5D9FF]">
        <h2 className="text-xl font-bold text-purple-950 dark:text-white mb-4">Journey Planner</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-purple-800">Source</label>
              <button 
                type="button"
                onClick={() => {
                  if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                      (pos) => setSourceInput(`${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)}`),
                      (err) => console.error("Geolocation error:", err)
                    );
                  }
                }}
                className="text-xs font-semibold text-purple-700 hover:text-purple-800 px-2 py-1 rounded bg-purple-100 hover:bg-purple-200 transition-colors"
              >
                Auto-detect
              </button>
            </div>
            <div className="relative">
              <MapPin className="absolute left-3 top-3 h-4 w-4 text-purple-600/80" />
              <Input className="pl-9 bg-[#FCFAFF]/60 backdrop-blur border-[#E5D9FF] text-purple-900 placeholder:text-purple-700 focus-visible:ring-purple-600" 
                value={sourceInput} 
                onChange={(e) => setSourceInput(e.target.value)} 
                placeholder="Where are you?" 
                
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-semibold text-purple-800">Destination</label>
            <div className="relative">
              <Navigation className="absolute left-3 top-3 h-4 w-4 text-purple-600/80" />
              <Input className="pl-9 bg-[#FCFAFF]/60 backdrop-blur border-[#E5D9FF] text-purple-900 placeholder:text-purple-700 focus-visible:ring-purple-600" 
                value={destInput} 
                onChange={(e) => setDestInput(e.target.value)} 
                placeholder="Where to?" 
                
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-purple-800">Travel Time</label>
            <div className="flex gap-2">
              <Button 
                variant={timeMode === "now" ? "default" : "outline"} 
                onClick={() => setTimeMode("now")}
                className="flex-1"
              >
                Travel Now
              </Button>
              <Button 
                variant={timeMode === "later" ? "default" : "outline"} 
                onClick={() => setTimeMode("later")}
                className="flex-1"
              >
                Travel Later
              </Button>
            </div>
            {timeMode === "later" && (
              <div className="flex gap-2 mt-2">
                <Input className="pl-9 bg-[#FCFAFF]/60 backdrop-blur border-[#E5D9FF] text-purple-900 placeholder:text-purple-700 focus-visible:ring-purple-600" type="date" value={laterDate} onChange={e => setLaterDate(e.target.value)} />
                <Input className="pl-9 bg-[#FCFAFF]/60 backdrop-blur border-[#E5D9FF] text-purple-900 placeholder:text-purple-700 focus-visible:ring-purple-600" type="time" value={laterTime} onChange={e => setLaterTime(e.target.value)} />
              </div>
            )}
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-semibold text-purple-800">Preference</label>
            <div className="flex gap-2">
              <Button size="sm" variant={transportPref === "any" ? "default" : "outline"} onClick={() => setTransportPref("any")}>Any</Button>
              <Button size="sm" variant={transportPref === "public" ? "default" : "outline"} onClick={() => setTransportPref("public")}>Public Transit</Button>
              <Button size="sm" variant={transportPref === "personal" ? "default" : "outline"} onClick={() => setTransportPref("personal")}>Personal Vehicle</Button>
            </div>
            {transportPref === "personal" && (
              <div className="flex gap-2 mt-2">
                <Button size="sm" variant={vehicleType === "two_wheeler" ? "secondary" : "outline"} onClick={() => setVehicleType("two_wheeler")}>Two Wheeler</Button>
                <Button size="sm" variant={vehicleType === "four_wheeler" ? "secondary" : "outline"} onClick={() => setVehicleType("four_wheeler")}>Four Wheeler</Button>
              </div>
            )}
          </div>
        </div>

        <Button onClick={handleSearch} disabled={isLoading} className="w-full h-12 text-lg">
          {isLoading ? "Validating Strategies..." : "Find Safe Routes"}
        </Button>
      </div>

      {isLoading && (
        <div className="bg-[#FCFAFF] p-6 rounded-xl shadow-sm border border-blue-100 flex flex-col items-center justify-center space-y-4">
           <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
           <p className="text-blue-700 font-medium">Resolving transport strategies & building geometry...</p>
        </div>
      )}

      {zeroDistance && !isLoading && (
         <div className="bg-green-50 p-6 rounded-xl shadow-sm border border-green-200 text-center">
            <h3 className="text-lg font-bold text-green-800">You're already at the destination.</h3>
            <p className="text-green-600">Distance: 0 km • Duration: 0 min</p>
         </div>
      )}

      {warnings.length > 0 && !isLoading && (
        <div className="bg-orange-50 border border-orange-200 p-4 rounded-xl space-y-2">
          {warnings.map((w, idx) => (
            <div key={idx} className="flex items-start gap-2 text-orange-800">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <p className="text-sm font-medium">{w}</p>
            </div>
          ))}
        </div>
      )}



      {!isLoading && routes.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-purple-950 dark:text-white">Available Strategies</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {routes.map((route) => (
              <div 
                key={route.id} 
                className="bg-[#FCFAFF] rounded-xl border border-[#E5D9FF] p-5 cursor-pointer hover:border-blue-500 hover:shadow-md transition-all group"
                onClick={() => {
                  setActiveRouteId(route.id);
                  setLayer(2);
                }}
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h4 className="font-bold text-purple-950 dark:text-white flex items-center gap-2">
                      {route.route_name}
                      {route.travel_mode_chain === "Multimodal" && <span className="bg-blue-50 text-blue-700 border border-blue-200 text-[10px] px-2 py-0.5 rounded-full font-semibold">AI VERIFIED</span>}
                    </h4>
                    <div className="flex items-center gap-1 mt-1 flex-wrap text-sm text-purple-800 font-medium">
                      {route.segments.map((seg, i) => (
                        <div key={i} className="flex items-center gap-1">
                          {getModeIcon(seg.transport_mode)}
                          <span className="capitalize">{seg.transport_mode}</span>
                          {i < route.segments.length - 1 && <span className="mx-1">→</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-purple-950 dark:text-white">{route.eta}</div>
                    <div className="text-xs text-purple-700">{route.distance}</div>
                  </div>
                </div>
                
                {/* Ranking Tags */}
                {route.recommendation_reason && route.recommendation_reason.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-[#E5D9FF]">
                    {route.recommendation_reason.map((r, i) => (
                      <span key={i} className="text-xs bg-[#ede7f6] text-purple-900 px-2 py-1 rounded-md font-medium">
                        {r}
                      </span>
                    ))}
                  </div>
                )}
                
                {route.overall_safety_score && (
                   <div className="mt-3 flex items-center gap-2 text-sm font-semibold text-green-700">
                     <ShieldCheck className="w-4 h-4" /> Safety Score: {route.overall_safety_score}
                   </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  // LAYER 2: Route Comparison View
  const renderLayer2 = () => {
    const activeRoute = routes.find(r => r.id === activeRouteId);
    
    return (
      <div className="flex flex-col md:flex-row h-[calc(100vh-4rem)] w-full overflow-hidden">
        {/* Left Panel: Comparison */}
        <div className="w-full md:w-96 bg-[#FCFAFF] border-r border-[#E5D9FF] flex flex-col h-full shrink-0 z-10 shadow-lg">
          <div className="p-4 border-b border-[#E5D9FF] flex items-center gap-3 bg-[#1B1035]">
            <Button variant="ghost" size="icon" onClick={handleBackToStrategy}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h2 className="font-bold text-purple-950 dark:text-white text-lg line-clamp-1">Route Details</h2>
          </div>
          
          <ScrollArea className="flex-1 p-4">
            {/* Route Selector (If multiple alternatives) */}
            {routes.length > 1 && (
              <div className="flex overflow-x-auto gap-2 pb-4 mb-4 scrollbar-hide">
                {routes.map(r => (
                  <button
                    key={r.id}
                    onClick={() => setActiveRouteId(r.id)}
                    className={`shrink-0 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                      r.id === activeRouteId 
                        ? "bg-blue-50 border-blue-300 text-blue-800 shadow-sm" 
                        : "bg-[#FCFAFF] border-[#E5D9FF] text-purple-800 hover:bg-[#1B1035]"
                    }`}
                  >
                    {r.route_name}
                  </button>
                ))}
              </div>
            )}
            
            {activeRoute && (
              <div className="space-y-6">
                {/* Header info */}
                <div>
                  <h3 className="text-2xl font-black text-purple-950 dark:text-white">{activeRoute.eta}</h3>
                  <p className="text-purple-700 font-medium">{activeRoute.distance} • {activeRoute.cost}</p>
                </div>
                
                {/* Safety & Environment */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-green-50 border border-green-200 p-3 rounded-xl">
                    <div className="flex items-center gap-1 text-green-800 font-bold mb-1">
                      <ShieldCheck className="w-4 h-4" /> Safety
                    </div>
                    <div className="text-2xl font-black text-green-900">{activeRoute.overall_safety_score}</div>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-xl">
                    <div className="flex items-center gap-1 text-emerald-800 font-bold mb-1">
                      <Leaf className="w-4 h-4" /> Env Risk
                    </div>
                    <div className="text-2xl font-black text-emerald-900">{activeRoute.environmental_risk}/100</div>
                  </div>
                </div>
                
                {/* Model Explainability */}
                {activeRoute.model_explainability && Object.keys(activeRoute.model_explainability).length > 0 && (
                  <div className="bg-[#1B1035] rounded-xl p-4 border border-[#E5D9FF]">
                    <h4 className="text-sm font-bold text-purple-900 mb-3 uppercase tracking-wider flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-blue-500" /> AI Safety Signals
                    </h4>
                    <div className="space-y-2">
                      {Object.entries(activeRoute.model_explainability).map(([key, val]) => (
                        <div key={key} className="flex justify-between items-center text-sm">
                          <span className="text-purple-800">{key}</span>
                          <span className={`font-bold ${val.startsWith('+') ? 'text-green-600' : 'text-orange-600'}`}>
                            {val}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Segments Timeline */}
                <div>
                  <h4 className="text-sm font-bold text-purple-900 mb-4 uppercase tracking-wider">Journey Timeline</h4>
                  <div className="space-y-0">
                    {activeRoute.segments.map((seg, i) => (
                      <div key={i} className="flex gap-4 group">
                        <div className="flex flex-col items-center">
                          <div 
                            className="w-8 h-8 rounded-full flex items-center justify-center text-white shadow-sm z-10"
                            style={{ backgroundColor: seg.color || "#3b82f6" }}
                          >
                            {getModeIcon(seg.transport_mode)}
                          </div>
                          {i < activeRoute.segments.length - 1 && (
                            <div className="w-1 flex-1 bg-slate-200 group-hover:bg-slate-300 transition-colors my-1 min-h-[3rem]" />
                          )}
                        </div>
                        <div className="pb-6 pt-1 flex-1">
                          <div className="flex justify-between items-start">
                            <div>
                              <h5 className="font-bold text-purple-950 dark:text-white text-sm">{seg.segment_name}</h5>
                              <p className="text-xs text-purple-700 font-medium capitalize mt-0.5">{seg.transport_mode}</p>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-bold text-purple-900">{seg.eta}</div>
                              <div className="text-xs text-purple-700">{seg.distance}</div>
                            </div>
                          </div>
                          {seg.reason && seg.reason !== "VALID" && seg.reason !== "Direct route" && (
                            <div className="mt-2 text-xs bg-[#ede7f6] p-2 rounded text-purple-800 border border-[#E5D9FF]">
                              {seg.reason}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </ScrollArea>
        </div>
        
        {/* Right Panel: Map */}
        <div className="flex-1 h-[50vh] md:h-full relative">
          <SafeMap 
            source={{ coordinates: data?.source_loc }}
            destination={{ coordinates: data?.dest_loc }}
            routeGeometry={activeGeoJson}
            onRouteClick={(props: any) => {
              if (props.routeId) setActiveRouteId(props.routeId);
            }}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="h-full w-full bg-[#F6F2FF]">
      {layer === 1 ? renderLayer1() : renderLayer2()}
    </div>
  );
}