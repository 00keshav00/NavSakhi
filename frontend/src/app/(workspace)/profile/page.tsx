"use client";

import { motion } from "framer-motion";
import { 
  User, MapPin, Award, ShieldCheck, Activity, Map as MapIcon, 
  Users, AlertOctagon, PhoneCall, CheckCircle2, ChevronRight, ShieldAlert, Star
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useProfile } from "@/hooks/useProfile";
import Image from "next/image";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogClose, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { profileService } from "@/api/services/profileService";
import { toast } from "sonner";

export default function ProfilePage() {
  const { profile, isLoading, reloadProfile } = useProfile();
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ full_name: "", phone: "", current_city: "" });
  const [isSaving, setIsSaving] = useState(false);

  if (isLoading || !profile) {
    return (
      <div className="flex h-full w-full flex-col p-8 space-y-8 animate-pulse">
        <div className="h-48 w-full rounded-3xl bg-secondary/30" />
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="h-64 w-full rounded-3xl bg-secondary/30" />
          <div className="h-64 w-full rounded-3xl bg-secondary/30" />
        </div>
      </div>
    );
  }

  const { user_info, stats, journey_history, emergency_contacts, achievements } = profile;

  const handleEditClick = () => {
    setEditForm({
      full_name: user_info.full_name || "",
      phone: user_info.phone || "",
      current_city: user_info.current_city || ""
    });
    setIsEditing(true);
  };

  const handleSaveProfile = async () => {
    try {
      setIsSaving(true);
      await profileService.updateProfile(editForm);
      toast.success("Profile updated successfully!");
      reloadProfile();
      setIsEditing(false);
    } catch (error) {
      toast.error("Failed to update profile.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto px-6 py-8 md:px-10 lg:px-12">
      
      <div className="mb-8 flex items-center justify-between">
        <h1 className="font-[family-name:var(--font-jakarta)] text-3xl font-extrabold tracking-tight text-foreground">
          Profile Overview
        </h1>
        <Button variant="outline" onClick={handleEditClick} className="rounded-full border-primary/20 text-primary hover:bg-primary/10">
          Edit Profile
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        
        {/* Left Column (User Info & Contacts) */}
        <div className="flex flex-col gap-8 lg:col-span-4">
          
          {/* Section 1: User Info Card */}
          <div className="glass-card flex flex-col items-center rounded-3xl border-border/50 p-8 text-center relative overflow-hidden">
             <div className="absolute top-0 left-0 right-0 h-24 bg-gradient-to-b from-primary/10 to-transparent" />
             <div className="relative mb-4 flex h-28 w-28 items-center justify-center rounded-full bg-secondary shadow-xl border-4 border-background">
                {user_info.is_online && (
                  <div className="absolute bottom-1 right-1 h-5 w-5 rounded-full bg-success border-4 border-background z-10" />
                )}
                <User size={48} className="text-muted-foreground" />
             </div>
             <h2 className="font-[family-name:var(--font-jakarta)] text-2xl font-bold text-foreground">
               {user_info.full_name}
             </h2>
             <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground font-medium">
               <MapPin size={14} /> {user_info.current_city}
             </div>
             
             {user_info.is_premium && (
               <div className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-primary border border-primary/20">
                 <Star size={12} /> {stats.trust_level}
               </div>
             )}

             <div className="mt-8 grid w-full grid-cols-2 gap-4 border-t border-border/50 pt-6">
                <div className="flex flex-col items-center">
                  <span className="text-xs font-bold uppercase text-muted-foreground">Member Since</span>
                  <span className="text-sm font-semibold mt-1">{user_info.member_since}</span>
                </div>
                <div className="flex flex-col items-center border-l border-border/50">
                  <span className="text-xs font-bold uppercase text-muted-foreground">Active</span>
                  <span className="text-sm font-semibold mt-1">{user_info.last_active}</span>
                </div>
             </div>
          </div>

          {/* Section 4: Emergency Contacts */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-foreground">Emergency Contacts</h3>
              <Button variant="ghost" size="sm" className="text-primary h-8 px-2">Add New</Button>
            </div>
            <div className="flex flex-col gap-3">
              {emergency_contacts.map(contact => (
                <div key={contact.id} className="glass-card flex items-center justify-between rounded-2xl p-4 border-border/50">
                   <div className="flex items-center gap-3">
                     <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-foreground">
                       <User size={18} />
                     </div>
                     <div className="flex flex-col">
                       <div className="flex items-center gap-2">
                         <span className="text-sm font-bold">{contact.name}</span>
                         {contact.is_primary && (
                           <span className="bg-primary/20 text-primary text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-sm">Primary</span>
                         )}
                       </div>
                       <span className="text-xs font-medium text-muted-foreground">{contact.relationship} • {contact.phone}</span>
                     </div>
                   </div>
                   <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                     <PhoneCall size={16} />
                   </Button>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Column (Stats & History) */}
        <div className="flex flex-col gap-8 lg:col-span-8">
          
          {/* Section 2: Safety & Community Stats */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard icon={ShieldCheck} label="Safe Journeys" value={stats.safe_journeys.toString()} color="text-success" />
            <StatCard icon={MapIcon} label="Distance (km)" value={stats.total_distance_km.toString()} color="text-primary" />
            <StatCard icon={Activity} label="Avg Safety" value={`${stats.avg_safety_score}%`} color="text-warning" />
            <StatCard icon={Users} label="Verified Reports" value={stats.verified_reports.toString()} color="text-info" />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
             <div className="glass-card p-6 rounded-3xl border-border/50 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-bold uppercase text-muted-foreground flex items-center gap-2"><AlertOctagon size={14} className="text-danger"/> SOS Triggers</span>
                  <span className="text-2xl font-black">{stats.sos_triggered}</span>
                </div>
                <div className="flex flex-col gap-1 text-right">
                  <span className="text-xs font-bold uppercase text-muted-foreground flex items-center gap-2 justify-end">Routes Avoided <ShieldAlert size={14} className="text-warning"/></span>
                  <span className="text-2xl font-black">{stats.dangerous_routes_avoided}</span>
                </div>
             </div>
             
             <div className="glass-card p-6 rounded-3xl border-border/50 flex flex-col justify-center">
               <span className="text-xs font-bold uppercase text-muted-foreground flex items-center gap-2 mb-2"><Award size={14} className="text-primary"/> Community Reputation</span>
               <div className="flex items-end gap-3">
                 <span className="text-3xl font-black text-primary">{stats.reputation_score}</span>
                 <span className="text-sm font-semibold text-muted-foreground mb-1">pts</span>
               </div>
               <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden mt-3">
                  <div className="h-full bg-primary rounded-full w-[85%]" />
               </div>
             </div>
          </div>

          {/* Section 6: Achievements */}
          <div className="flex flex-col gap-4">
            <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-foreground">Achievements</h3>
            <div className="flex gap-4 overflow-x-auto pb-2 no-scrollbar">
              {achievements.map(ach => (
                <div key={ach.id} className={`glass-card flex min-w-[140px] flex-col items-center justify-center rounded-2xl border p-4 text-center ${ach.unlocked ? 'border-primary/20 bg-primary/5' : 'border-border/50 opacity-50 grayscale'}`}>
                  <div className={`mb-3 flex h-12 w-12 items-center justify-center rounded-full ${ach.unlocked ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'}`}>
                    <Award size={24} />
                  </div>
                  <span className="text-xs font-bold">{ach.title}</span>
                  {ach.date && <span className="text-[10px] text-muted-foreground mt-1">{ach.date}</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Journey History */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-foreground">Recent Journeys</h3>
              <Button variant="link" className="text-primary">View All</Button>
            </div>
            <div className="flex flex-col gap-3">
              {journey_history.map(journey => (
                <div key={journey.id} className="glass-card flex items-center justify-between rounded-2xl p-5 border-border/50 hover:bg-secondary/20 transition-colors cursor-pointer group">
                   <div className="flex items-center gap-4">
                     <div className={`flex h-12 w-12 items-center justify-center rounded-full ${
                       journey.status === 'Completed' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
                     }`}>
                       {journey.status === 'Completed' ? <CheckCircle2 size={20} /> : <AlertOctagon size={20} />}
                     </div>
                     <div className="flex flex-col gap-1">
                       <span className="text-sm font-bold text-foreground flex items-center gap-2">
                         {journey.source} <ChevronRight size={14} className="text-muted-foreground" /> {journey.destination}
                       </span>
                       <div className="flex items-center gap-3 text-xs font-medium text-muted-foreground">
                         <span>{journey.date}</span>
                         <span className="w-1 h-1 rounded-full bg-border" />
                         <span>{journey.transport}</span>
                         <span className="w-1 h-1 rounded-full bg-border" />
                         <span>{journey.duration}</span>
                       </div>
                     </div>
                   </div>
                   <div className="flex flex-col items-end gap-1">
                     <span className={`text-xs font-bold uppercase tracking-wider ${journey.safety_score >= 90 ? 'text-success' : 'text-warning'}`}>
                       Score: {journey.safety_score}%
                     </span>
                     <span className="text-[10px] font-semibold text-muted-foreground">{journey.status}</span>
                   </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      <Dialog open={isEditing} onOpenChange={setIsEditing}>
        <DialogContent className="sm:max-w-[425px] bg-card border-border">
          <DialogHeader>
            <DialogTitle className="font-[family-name:var(--font-jakarta)] font-bold text-xl">Edit Profile</DialogTitle>
            <DialogDescription>
              Update your personal details here. Click save when you're done.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-muted-foreground">Full Name</label>
              <Input 
                value={editForm.full_name} 
                onChange={(e) => setEditForm({...editForm, full_name: e.target.value})}
                className="bg-secondary/50 border-border" 
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-muted-foreground">Phone Number</label>
              <Input 
                value={editForm.phone} 
                onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                className="bg-secondary/50 border-border" 
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-muted-foreground">City</label>
              <Input 
                value={editForm.current_city} 
                onChange={(e) => setEditForm({...editForm, current_city: e.target.value})}
                className="bg-secondary/50 border-border" 
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditing(false)}>Cancel</Button>
            <Button onClick={handleSaveProfile} disabled={isSaving} className="bg-primary text-white hover:bg-primary/90">
              {isSaving ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any, label: string, value: string, color: string }) {
  return (
    <div className="glass-card flex flex-col justify-center rounded-3xl border-border/50 p-5">
      <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-secondary ${color}`}>
        <Icon size={20} />
      </div>
      <span className="text-2xl font-black text-foreground">{value}</span>
      <span className="mt-1 text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
    </div>
  );
}