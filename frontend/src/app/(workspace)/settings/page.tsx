"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Palette, Bell, Lock, AlertOctagon, Bot, Navigation, Globe, Mic, Code, Save, Activity
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useSettings } from "@/hooks/useSettings";

type TabId = 'appearance' | 'notifications' | 'privacy' | 'emergency' | 'ai' | 'location' | 'developer';

export default function SettingsPage() {
  const { settings, isLoading, isSaving, saveSettings } = useSettings();
  const [activeTab, setActiveTab] = useState<TabId>('notifications');

  // Local state to handle form modifications before saving
  const [localSettings, setLocalSettings] = useState(settings);

  // Sync local state when backend settings load
  if (settings && !localSettings) {
    setLocalSettings(settings);
  }

  if (isLoading || !localSettings) {
    return (
      <div className="flex h-full w-full p-8 animate-pulse gap-8">
         <div className="w-64 h-[600px] bg-secondary/30 rounded-3xl" />
         <div className="flex-1 h-[600px] bg-secondary/30 rounded-3xl" />
      </div>
    );
  }

  const handleSave = () => {
    saveSettings(localSettings);
  };

  const tabs: { id: TabId, label: string, icon: any }[] = [
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'privacy', label: 'Privacy & Security', icon: Lock },
    { id: 'emergency', label: 'Emergency Protocol', icon: AlertOctagon },
    { id: 'ai', label: 'Intelligence Config', icon: Bot },
    { id: 'location', label: 'Routing & Location', icon: Navigation },
    { id: 'developer', label: 'Developer', icon: Code },
  ];

  const updateNestedSetting = (category: keyof typeof localSettings, key: string, value: any) => {
    setLocalSettings(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        [category]: {
          ...prev[category],
          [key]: value
        }
      };
    });
  };

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto px-6 py-8 md:px-10 lg:px-12">
      
      <div className="mb-8 flex items-center justify-between">
         <div className="flex flex-col">
           <h1 className="font-[family-name:var(--font-jakarta)] text-3xl font-extrabold tracking-tight text-foreground">
             Settings
           </h1>
           <span className="text-sm font-medium text-muted-foreground mt-1">Manage your intelligent safety preferences</span>
         </div>
         <Button onClick={handleSave} disabled={isSaving} className="rounded-full bg-primary text-primary-foreground hover:bg-primary/90 gap-2 h-10 px-6">
           {isSaving ? <Activity size={16} className="animate-spin" /> : <Save size={16} />}
           {isSaving ? 'Saving...' : 'Save Changes'}
         </Button>
      </div>

      <div className="flex flex-col md:flex-row gap-8 lg:gap-12 min-h-[600px]">
        
        {/* Left Sidebar Navigation */}
        <div className="w-full md:w-64 shrink-0 flex flex-col gap-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === tab.id 
                  ? 'bg-primary text-primary-foreground font-bold shadow-md' 
                  : 'text-muted-foreground font-medium hover:bg-secondary hover:text-foreground'
              }`}
            >
              <tab.icon size={20} className={activeTab === tab.id ? 'text-primary-foreground' : 'text-muted-foreground'} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right Content Area */}
        <div className="flex-1 glass-card rounded-3xl border-border/50 p-8 shadow-xl bg-card/40">
           <AnimatePresence mode="wait">
             <motion.div
               key={activeTab}
               initial={{ opacity: 0, y: 10 }}
               animate={{ opacity: 1, y: 0 }}
               exit={{ opacity: 0, y: -10 }}
               transition={{ duration: 0.2 }}
               className="flex flex-col gap-8"
             >
               
               {activeTab === 'notifications' && (
                 <SettingsGroup title="Alert Preferences" desc="Control how SafeShe Agent communicates with you.">
                   <ToggleRow label="Journey Alerts" desc="Receive updates regarding route safety variations." checked={localSettings.notifications.journey_alerts} onChange={(v) => updateNestedSetting('notifications', 'journey_alerts', v)} />
                   <ToggleRow label="Community Incident Alerts" desc="Ping when a high-severity incident is verified nearby." checked={localSettings.notifications.community_alerts} onChange={(v) => updateNestedSetting('notifications', 'community_alerts', v)} />
                   <ToggleRow label="Weather Warnings" desc="Notifications for sudden rain or hazardous conditions." checked={localSettings.notifications.weather_alerts} onChange={(v) => updateNestedSetting('notifications', 'weather_alerts', v)} />
                   <ToggleRow label="AI Proactive Push" desc="Allow Intelligence Coordinator to push urgent recommendations." checked={localSettings.notifications.ai_notifications} onChange={(v) => updateNestedSetting('notifications', 'ai_notifications', v)} />
                 </SettingsGroup>
               )}

               {activeTab === 'privacy' && (
                 <SettingsGroup title="Privacy & Security" desc="Manage what data is shared with the community and ML layers.">
                   <ToggleRow label="Share Live Location" desc="Required for real-time Agent monitoring. (Encrypted)" checked={localSettings.privacy.share_live_location} onChange={(v) => updateNestedSetting('privacy', 'share_live_location', v)} />
                   <ToggleRow label="Anonymous Community Reports" desc="Hide your name from reports you submit." checked={localSettings.privacy.anonymous_community_reports} onChange={(v) => updateNestedSetting('privacy', 'anonymous_community_reports', v)} />
                   <ToggleRow label="Opt-in to Analytics" desc="Help improve routing algorithms." checked={localSettings.privacy.analytics} onChange={(v) => updateNestedSetting('privacy', 'analytics', v)} />
                 </SettingsGroup>
               )}

               {activeTab === 'emergency' && (
                 <SettingsGroup title="Emergency Protocol" desc="Configure SOS behavior and trigger actions.">
                   <ToggleRow label="Auto-Call Emergency Contact" desc="Dial primary contact automatically when SOS finishes countdown." checked={localSettings.emergency.auto_call_emergency_contact} onChange={(v) => updateNestedSetting('emergency', 'auto_call_emergency_contact', v)} />
                   <ToggleRow label="Share Journey Automatically" desc="Broadcast live location link to all contacts." checked={localSettings.emergency.share_journey_automatically} onChange={(v) => updateNestedSetting('emergency', 'share_journey_automatically', v)} />
                   <ToggleRow label="Use Countdown Timer" desc="5-second delay to cancel false alarms." checked={localSettings.emergency.emergency_countdown} onChange={(v) => updateNestedSetting('emergency', 'emergency_countdown', v)} />
                 </SettingsGroup>
               )}

               {activeTab === 'ai' && (
                 <SettingsGroup title="Intelligence Configuration" desc="Tune the Journey Intelligence Coordinator's logic.">
                   <ToggleRow label="Enable AI Recommendations" desc="Allow Agent to auto-reroute during transit." checked={localSettings.ai_preferences.enable_ai_recommendations} onChange={(v) => updateNestedSetting('ai_preferences', 'enable_ai_recommendations', v)} />
                   
                   <div className="flex flex-col gap-2 pt-4">
                     <span className="text-sm font-bold">Safety Sensitivity</span>
                     <select 
                       value={localSettings.ai_preferences.safety_sensitivity}
                       onChange={(e) => updateNestedSetting('ai_preferences', 'safety_sensitivity', e.target.value)}
                       className="w-full max-w-xs h-10 rounded-lg bg-secondary/50 border border-border/50 px-3 text-sm focus:ring-1 focus:ring-primary outline-none"
                     >
                       <option value="Low">Low (Fastest routes prioritized)</option>
                       <option value="Medium">Medium (Balanced)</option>
                       <option value="High">High (Max Safety prioritized)</option>
                     </select>
                   </div>
                 </SettingsGroup>
               )}

               {activeTab === 'location' && (
                 <SettingsGroup title="Routing Exclusions" desc="Set global constraints for the pathfinding ML models.">
                   <ToggleRow label="Avoid Dark Areas" desc="Prioritize well-lit streets." checked={localSettings.location.avoid_dark_areas} onChange={(v) => updateNestedSetting('location', 'avoid_dark_areas', v)} />
                   <ToggleRow label="Avoid Construction" desc="Route around active building zones." checked={localSettings.location.avoid_construction} onChange={(v) => updateNestedSetting('location', 'avoid_construction', v)} />
                   <ToggleRow label="Avoid High Crowd Density" desc="Prefer quieter routes." checked={localSettings.location.avoid_crowds} onChange={(v) => updateNestedSetting('location', 'avoid_crowds', v)} />
                 </SettingsGroup>
               )}

               {activeTab === 'developer' && (
                 <SettingsGroup title="Developer Mode" desc="System health and versioning (Read-only)">
                   <ToggleRow label="Enable Developer Options" desc="Shows debug UI layers." checked={localSettings.developer.developer_mode} onChange={(v) => updateNestedSetting('developer', 'developer_mode', v)} />
                   <div className="grid grid-cols-2 gap-4 mt-6 bg-secondary/30 p-4 rounded-xl border border-border/50">
                     <div className="flex flex-col gap-1">
                       <span className="text-[10px] font-bold uppercase text-muted-foreground">API Version</span>
                       <span className="text-sm font-mono">{localSettings.developer.api_version}</span>
                     </div>
                     <div className="flex flex-col gap-1">
                       <span className="text-[10px] font-bold uppercase text-muted-foreground">Build Version</span>
                       <span className="text-sm font-mono">{localSettings.developer.build_version}</span>
                     </div>
                   </div>
                 </SettingsGroup>
               )}

               {/* Placeholders for simpler tabs */}
               {activeTab === 'appearance' && (
                  <SettingsGroup title="Appearance" desc="Visual theme settings.">
                     <div className="text-sm text-muted-foreground italic">Theme management is currently locked by system administration.</div>
                  </SettingsGroup>
               )}

             </motion.div>
           </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function SettingsGroup({ title, desc, children }: { title: string, desc: string, children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col border-b border-border/50 pb-4">
        <h2 className="font-[family-name:var(--font-jakarta)] text-xl font-bold text-foreground">{title}</h2>
        <p className="text-sm font-medium text-muted-foreground mt-1">{desc}</p>
      </div>
      <div className="flex flex-col gap-5">
        {children}
      </div>
    </div>
  );
}

function ToggleRow({ label, desc, checked, onChange }: { label: string, desc: string, checked: boolean, onChange: (val: boolean) => void }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex flex-col pr-8">
        <span className="text-sm font-bold text-foreground">{label}</span>
        <span className="text-xs font-medium text-muted-foreground mt-0.5">{desc}</span>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}