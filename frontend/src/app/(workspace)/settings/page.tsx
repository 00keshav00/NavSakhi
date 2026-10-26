"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { 
  Palette, Bell, Lock, AlertOctagon, Bot, Navigation, Code, Save, Activity,
  User as UserIcon, ShieldAlert, Plus, Phone, Mail, Trash2, Edit2, Star, CheckCircle2,
  AlertCircle, ShieldCheck, HeartHandshake, Info, Scale, ArrowRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { useSettings } from "@/hooks/useSettings";
import { useAuthStore } from "@/store/authStore";
import { userService } from "@/api/services/userService";
import { User, EmergencyContact } from "@/types/auth";
import { SettingsResponse } from "@/types/settings";
import { Footer } from "@/components/layout/Footer";
import { toast } from "sonner";

type TabId = 'profile' | 'contacts' | 'notifications' | 'privacy' | 'emergency' | 'ai' | 'location' | 'developer' | 'appearance' | 'legal';


export default function SettingsPage() {
  const { settings, isLoading: isSettingsLoading, isSaving: isSettingsSaving, saveSettings } = useSettings();
  const authUser = useAuthStore((state) => state.user);
  const updateUserStore = useAuthStore((state) => state.updateUser);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [activeTab, setActiveTab] = useState<TabId>('profile');

  // Local state for app settings preferences
  const [localSettings, setLocalSettings] = useState<SettingsResponse | null>(settings);

  // Profile data from canonical backend API
  const [profileUser, setProfileUser] = useState<User | null>(authUser);
  const [isProfileLoading, setIsProfileLoading] = useState(false);
  const [isProfileSaving, setIsProfileSaving] = useState(false);
  const [profileForm, setProfileForm] = useState({
    full_name: authUser?.full_name || "",
    phone_number: authUser?.phone_number || "",
    age: authUser?.age ? String(authUser.age) : "",
  });

  // Emergency Contacts state
  const [contacts, setContacts] = useState<EmergencyContact[]>(authUser?.emergency_contacts || []);
  const [isContactDialogOpen, setIsContactDialogOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<EmergencyContact | null>(null);
  const [contactForm, setContactForm] = useState({
    name: "",
    relationship: "Family",
    country_code: "+91",
    phone_number: "",
    email: "",
    is_primary: false,
  });
  const [contactFormError, setContactFormError] = useState<string | null>(null);
  const [isContactSaving, setIsContactSaving] = useState(false);

  // Delete contact confirmation dialog state
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [contactToDelete, setContactToDelete] = useState<EmergencyContact | null>(null);
  const [isDeletingContact, setIsDeletingContact] = useState(false);

  // Sync settings when loaded
  if (settings && !localSettings) {
    setLocalSettings(settings);
  }

  // Load canonical backend profile on mount
  useEffect(() => {
    if (!isAuthenticated) return;

    let isMounted = true;
    const fetchProfile = async () => {
      try {
        setIsProfileLoading(true);
        const user = await userService.getProfile();
        if (isMounted) {
          setProfileUser(user);
          updateUserStore(user);
          setProfileForm({
            full_name: user.full_name || user.username || "",
            phone_number: user.phone_number || "",
            age: user.age ? String(user.age) : "",
          });
          setContacts(user.emergency_contacts || []);
        }
      } catch (err: any) {
        console.warn("[SettingsPage] Could not fetch canonical backend profile:", err);
      } finally {
        if (isMounted) setIsProfileLoading(false);
      }
    };

    fetchProfile();
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, updateUserStore]);

  const handleSaveProfile = async () => {
    setIsProfileSaving(true);
    try {
      const payload: { full_name?: string; phone_number?: string; age?: number } = {};

      if (profileForm.full_name.trim()) {
        payload.full_name = profileForm.full_name.trim();
      }
      if (profileForm.phone_number.trim()) {
        payload.phone_number = profileForm.phone_number.trim();
      }
      if (profileForm.age.trim()) {
        const parsedAge = parseInt(profileForm.age.trim(), 10);
        if (isNaN(parsedAge) || parsedAge < 13 || parsedAge > 120) {
          toast.error("Invalid Age", { description: "Age must be between 13 and 120." });
          setIsProfileSaving(false);
          return;
        }
        payload.age = parsedAge;
      }

      const updatedUser = await userService.updateProfile(payload);
      setProfileUser(updatedUser);
      updateUserStore(updatedUser);
      toast.success("Profile Updated", {
        description: "Your registration and profile details have been saved.",
      });
    } catch (err: any) {
      toast.error("Profile Update Failed", {
        description: err.message || "Failed to persist profile details to backend.",
      });
    } finally {
      setIsProfileSaving(false);
    }
  };

  const openAddContactDialog = () => {
    setEditingContact(null);
    setContactForm({
      name: "",
      relationship: "Family",
      country_code: "+91",
      phone_number: "",
      email: "",
      is_primary: contacts.length === 0, // Auto-primary if first contact
    });
    setContactFormError(null);
    setIsContactDialogOpen(true);
  };

  const openEditContactDialog = (contact: EmergencyContact) => {
    setEditingContact(contact);
    let cc = "+91";
    let num = contact.phone_number;

    if (num.startsWith("+")) {
      // Basic country code extraction
      if (num.startsWith("+91")) {
        cc = "+91";
        num = num.slice(3);
      } else if (num.startsWith("+1")) {
        cc = "+1";
        num = num.slice(2);
      } else if (num.startsWith("+44")) {
        cc = "+44";
        num = num.slice(3);
      }
    }

    setContactForm({
      name: contact.name,
      relationship: contact.relationship || "Family",
      country_code: cc,
      phone_number: num,
      email: contact.email || "",
      is_primary: contact.is_primary || false,
    });
    setContactFormError(null);
    setIsContactDialogOpen(true);
  };

  const handleSaveContact = async () => {
    setContactFormError(null);

    const name = contactForm.name.trim();
    if (name.length < 2) {
      setContactFormError("Contact name must be at least 2 characters long.");
      return;
    }

    const cleanNumber = contactForm.phone_number.replace(/[\s\-\(\)]/g, "");
    if (!cleanNumber || cleanNumber.length < 7 || cleanNumber.length > 15) {
      setContactFormError("Please enter a valid phone number (7 to 15 digits).");
      return;
    }

    const fullPhone = contactForm.phone_number.startsWith("+") 
      ? cleanNumber 
      : `${contactForm.country_code}${cleanNumber}`;

    setIsContactSaving(true);
    try {
      if (editingContact) {
        // Update existing contact
        const updatedUser = await userService.updateEmergencyContact(editingContact.id, {
          name,
          relationship: contactForm.relationship,
          phone_number: fullPhone,
          email: contactForm.email.trim() || undefined,
          is_primary: contactForm.is_primary,
        });
        setContacts(updatedUser.emergency_contacts || []);
        updateUserStore(updatedUser);
        toast.success("Contact Updated", {
          description: `Updated emergency details for ${name}.`,
        });
      } else {
        // Add new contact
        const updatedUser = await userService.addEmergencyContact({
          name,
          relationship: contactForm.relationship,
          phone_number: fullPhone,
          email: contactForm.email.trim() || undefined,
          is_primary: contactForm.is_primary,
        });
        setContacts(updatedUser.emergency_contacts || []);
        updateUserStore(updatedUser);
        toast.success("Contact Saved", {
          description: `${name} has been added to your emergency contacts.`,
        });
      }
      setIsContactDialogOpen(false);
    } catch (err: any) {
      setContactFormError(err.message || "Failed to save contact.");
      toast.error("Failed to Save Contact", {
        description: err.message || "Backend persistence error.",
      });
    } finally {
      setIsContactSaving(false);
    }
  };

  const handleSetPrimary = async (contactId: string) => {
    try {
      const updatedUser = await userService.updateEmergencyContact(contactId, {
        is_primary: true,
      });
      setContacts(updatedUser.emergency_contacts || []);
      updateUserStore(updatedUser);
      toast.success("Primary Contact Set", {
        description: "Primary point of contact updated successfully.",
      });
    } catch (err: any) {
      toast.error("Update Failed", {
        description: err.message || "Failed to set primary contact.",
      });
    }
  };

  const confirmDeleteContact = (contact: EmergencyContact) => {
    setContactToDelete(contact);
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteContact = async () => {
    if (!contactToDelete) return;
    setIsDeletingContact(true);
    try {
      const updatedUser = await userService.deleteEmergencyContact(contactToDelete.id);
      setContacts(updatedUser.emergency_contacts || []);
      updateUserStore(updatedUser);
      toast.success("Contact Removed", {
        description: `${contactToDelete.name} was removed from emergency contacts.`,
      });
      setIsDeleteDialogOpen(false);
      setContactToDelete(null);
    } catch (err: any) {
      toast.error("Failed to Remove Contact", {
        description: err.message || "Could not delete contact from backend.",
      });
    } finally {
      setIsDeletingContact(false);
    }
  };

  const tabs: { id: TabId, label: string, icon: any }[] = [
    { id: 'profile', label: 'Profile Details', icon: UserIcon },
    { id: 'contacts', label: 'Emergency Contacts', icon: ShieldAlert },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'privacy', label: 'Privacy & Security', icon: Lock },
    { id: 'emergency', label: 'Emergency Protocol', icon: AlertOctagon },
    { id: 'ai', label: 'Intelligence Config', icon: Bot },
    { id: 'location', label: 'Routing & Location', icon: Navigation },
    { id: 'developer', label: 'Developer', icon: Code },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'legal', label: 'Legal & Transparency', icon: Scale },
  ];


  const updateNestedSetting = (category: keyof SettingsResponse, key: string, value: any) => {
    setLocalSettings((prev) => {
      if (!prev) return prev;
      const section = prev[category] as Record<string, any>;
      return {
        ...prev,
        [category]: {
          ...section,
          [key]: value,
        },
      };
    });
  };

  const handleSaveSettings = () => {
    if (localSettings) {
      saveSettings(localSettings);
    }
  };

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto px-6 py-8 md:px-10 lg:px-12">
      
      {/* Page Title & Save Action */}
      <div className="mb-8 flex items-center justify-between">
         <div className="flex flex-col">
           <h1 className="font-[family-name:var(--font-jakarta)] text-3xl font-extrabold tracking-tight text-foreground">
             Account Settings
           </h1>
           <span className="text-sm font-medium text-muted-foreground mt-1">
             Manage your verified registration profile, emergency points of contact, and safety preferences
           </span>
         </div>
         {activeTab !== 'profile' && activeTab !== 'contacts' && (
           <Button onClick={handleSaveSettings} disabled={isSettingsSaving} className="rounded-full bg-primary text-primary-foreground hover:bg-primary/90 gap-2 h-10 px-6">
             {isSettingsSaving ? <Activity size={16} className="animate-spin" /> : <Save size={16} />}
             {isSettingsSaving ? 'Saving...' : 'Save Preferences'}
           </Button>
         )}
      </div>

      <div className="flex flex-col md:flex-row gap-8 lg:gap-12 min-h-[600px]">
        
        {/* Left Sidebar Navigation */}
        <div className="w-full md:w-64 shrink-0 flex flex-col gap-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 text-left ${
                activeTab === tab.id 
                  ? 'bg-primary text-primary-foreground font-bold shadow-md' 
                  : 'text-muted-foreground font-medium hover:bg-secondary hover:text-foreground'
              }`}
            >
              <div className="flex items-center gap-3">
                <tab.icon size={19} className={activeTab === tab.id ? 'text-primary-foreground' : 'text-muted-foreground'} />
                <span>{tab.label}</span>
              </div>
              {tab.id === 'contacts' && contacts.length > 0 && (
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${activeTab === tab.id ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-secondary text-muted-foreground'}`}>
                  {contacts.length}
                </span>
              )}
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
               
               {/* TAB 1: PROFILE DETAILS */}
               {activeTab === 'profile' && (
                 <div className="flex flex-col gap-8">
                   <div className="flex flex-col border-b border-border/50 pb-4">
                     <h2 className="font-[family-name:var(--font-jakarta)] text-xl font-bold text-foreground">
                       Profile Details
                     </h2>
                     <p className="text-sm font-medium text-muted-foreground mt-1">
                       View your registration information and edit your personal details.
                     </p>
                   </div>

                   {/* Section 1: Account / Security Identifiers (Read-Only) */}
                   <div className="space-y-4">
                     <div className="flex items-center gap-2">
                       <Lock size={16} className="text-muted-foreground" />
                       <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                         Account & Security Identifiers (Read-Only)
                       </h3>
                     </div>

                     <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                       {/* Username */}
                       <div className="flex flex-col gap-1.5 p-4 rounded-2xl bg-secondary/30 border border-border/60">
                         <div className="flex items-center justify-between">
                           <span className="text-xs font-bold text-muted-foreground">Username</span>
                           <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-muted/60 text-muted-foreground flex items-center gap-1">
                             <Lock size={10} /> Immutable
                           </span>
                         </div>
                         <span className="text-sm font-semibold text-foreground">
                           {profileUser?.username || "—"}
                         </span>
                         <span className="text-[11px] text-muted-foreground">
                           Canonical account identifier set at registration.
                         </span>
                       </div>

                       {/* Email */}
                       <div className="flex flex-col gap-1.5 p-4 rounded-2xl bg-secondary/30 border border-border/60">
                         <div className="flex items-center justify-between">
                           <span className="text-xs font-bold text-muted-foreground">Email Address</span>
                           <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                             <CheckCircle2 size={10} /> Verified
                           </span>
                         </div>
                         <span className="text-sm font-semibold text-foreground">
                           {profileUser?.email || "—"}
                         </span>
                         <span className="text-[11px] text-muted-foreground">
                           Primary security address for authentication and notices.
                         </span>
                       </div>
                     </div>
                   </div>

                   {/* Section 2: Personal Profile Details (Editable) */}
                   <div className="space-y-5 pt-2">
                     <div className="flex items-center gap-2">
                       <UserIcon size={16} className="text-primary" />
                       <h3 className="text-sm font-bold uppercase tracking-wider text-foreground">
                         Personal Details (Editable)
                       </h3>
                     </div>

                     <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                       {/* Full Name */}
                       <div className="flex flex-col gap-2">
                         <label className="text-xs font-bold text-foreground">Full Name</label>
                         <Input
                           value={profileForm.full_name}
                           onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                           placeholder="e.g. Priya Raman"
                           className="bg-secondary/40 border-border/60 h-11 rounded-xl"
                         />
                         <span className="text-[11px] text-muted-foreground">Display name across NavSakhi services.</span>
                       </div>

                       {/* Mobile Phone */}
                       <div className="flex flex-col gap-2">
                         <label className="text-xs font-bold text-foreground">Mobile Phone Number</label>
                         <Input
                           value={profileForm.phone_number}
                           onChange={(e) => setProfileForm({ ...profileForm, phone_number: e.target.value })}
                           placeholder="e.g. +91 98765 43210"
                           className="bg-secondary/40 border-border/60 h-11 rounded-xl"
                         />
                         <span className="text-[11px] text-muted-foreground">10-15 digits with optional country code (+).</span>
                       </div>

                       {/* Age (Optional) */}
                       <div className="flex flex-col gap-2">
                         <label className="text-xs font-bold text-foreground">Age (Optional)</label>
                         <Input
                           type="number"
                           min={13}
                           max={120}
                           value={profileForm.age}
                           onChange={(e) => setProfileForm({ ...profileForm, age: e.target.value })}
                           placeholder="e.g. 26"
                           className="bg-secondary/40 border-border/60 h-11 rounded-xl max-w-xs"
                         />
                         <span className="text-[11px] text-muted-foreground">Used for demographic route safety adaptations.</span>
                       </div>
                     </div>

                     <div className="pt-4 flex items-center gap-4">
                       <Button 
                         onClick={handleSaveProfile} 
                         disabled={isProfileSaving}
                         className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 h-11 px-8 gap-2 font-bold shadow-md shadow-primary/20"
                       >
                         {isProfileSaving ? <Activity size={16} className="animate-spin" /> : <Save size={16} />}
                         {isProfileSaving ? "Saving..." : "Save Profile Details"}
                       </Button>
                     </div>
                   </div>
                 </div>
               )}

               {/* TAB 2: EMERGENCY CONTACTS */}
               {activeTab === 'contacts' && (
                 <div className="flex flex-col gap-6">
                   <div className="flex items-center justify-between border-b border-border/50 pb-4">
                     <div className="flex flex-col">
                       <h2 className="font-[family-name:var(--font-jakarta)] text-xl font-bold text-foreground">
                         Emergency Points of Contact (POCs)
                       </h2>
                       <p className="text-sm font-medium text-muted-foreground mt-1">
                         Saved contacts pre-staged for manual emergency sharing and quick dialing.
                       </p>
                     </div>
                     <Button 
                       onClick={openAddContactDialog}
                       className="rounded-full bg-primary text-primary-foreground hover:bg-primary/90 gap-2 h-10 px-5 font-bold shadow-md shadow-primary/20"
                     >
                       <Plus size={16} /> Add Contact
                     </Button>
                   </div>

                    {/* Prototype Disclosure Callout */}
                    <div className="p-3.5 rounded-2xl bg-secondary/40 border border-border/70 text-xs text-muted-foreground flex items-start gap-2.5">
                      <Info size={16} className="text-primary shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <span className="font-bold text-foreground">Emergency Contact Scope &amp; Privacy</span>
                        <p className="leading-relaxed">
                          Contacts are stored on your account to pre-stage phone numbers in the Emergency SOS screen for quick manual phone calls and device sharing. 
                          <strong> Adding a contact does not dispatch automated background SMS or notify police. In an immediate crisis, always call 112 directly.</strong>
                        </p>
                      </div>
                    </div>

                   {/* Contacts Grid / List */}
                   {contacts.length === 0 ? (
                     <div className="p-8 rounded-3xl bg-secondary/20 border border-border/50 flex flex-col items-center justify-center text-center space-y-3">
                       <div className="w-12 h-12 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
                         <ShieldAlert size={24} />
                       </div>
                       <h3 className="font-bold text-foreground text-base">No Emergency Contacts Registered</h3>
                       <p className="text-xs text-muted-foreground max-w-md">
                         Add at least one trusted friend, family member, or guardian. When SOS is triggered, your primary point of contact is alerted with live location telemetry.
                       </p>
                       <Button 
                         onClick={openAddContactDialog}
                         variant="outline"
                         className="mt-2 border-primary/30 text-primary hover:bg-primary/10 rounded-xl"
                       >
                         <Plus size={16} className="mr-1.5" /> Add First Contact
                       </Button>
                     </div>
                   ) : (
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                       {contacts.map((contact) => (
                         <div 
                           key={contact.id} 
                           className={`p-5 rounded-2xl border transition-all flex flex-col justify-between gap-4 ${
                             contact.is_primary 
                               ? 'bg-amber-500/5 border-amber-500/30 shadow-md shadow-amber-500/5' 
                               : 'bg-secondary/30 border-border/60 hover:border-border'
                           }`}
                         >
                           <div className="flex items-start justify-between gap-3">
                             <div className="flex items-center gap-3">
                               <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${
                                 contact.is_primary ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300' : 'bg-primary/10 text-primary'
                               }`}>
                                 {contact.name.charAt(0).toUpperCase()}
                               </div>
                               <div className="flex flex-col">
                                 <span className="font-bold text-foreground text-sm flex items-center gap-2">
                                   {contact.name}
                                   {contact.is_primary && (
                                     <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                                       <Star size={10} className="fill-amber-500" /> Primary POC
                                     </span>
                                   )}
                                 </span>
                                 <span className="text-xs text-muted-foreground font-medium">
                                   {contact.relationship || "Family"}
                                 </span>
                               </div>
                             </div>

                             <div className="flex items-center gap-1">
                               <button
                                 type="button"
                                 onClick={() => openEditContactDialog(contact)}
                                 className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-colors"
                                 title="Edit Contact"
                               >
                                 <Edit2 size={15} />
                               </button>
                               <button
                                 type="button"
                                 onClick={() => confirmDeleteContact(contact)}
                                 className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                                 title="Remove Contact"
                               >
                                 <Trash2 size={15} />
                               </button>
                             </div>
                           </div>

                           <div className="space-y-1.5 pt-2 border-t border-border/40 text-xs">
                             <div className="flex items-center gap-2 text-foreground font-mono">
                               <Phone size={13} className="text-muted-foreground" />
                               <span>{contact.phone_number}</span>
                             </div>
                             {contact.email && (
                               <div className="flex items-center gap-2 text-muted-foreground">
                                 <Mail size={13} className="text-muted-foreground" />
                                 <span className="truncate">{contact.email}</span>
                               </div>
                             )}
                           </div>

                           {!contact.is_primary && (
                             <div className="pt-2">
                               <Button
                                 size="sm"
                                 variant="ghost"
                                 onClick={() => handleSetPrimary(contact.id)}
                                 className="w-full h-8 text-xs font-semibold text-muted-foreground hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-500/10 rounded-lg justify-center gap-1.5"
                               >
                                 <Star size={13} /> Set as Primary POC
                               </Button>
                             </div>
                           )}
                         </div>
                       ))}
                     </div>
                   )}
                 </div>
               )}

               {/* TAB 3: NOTIFICATIONS */}
               {activeTab === 'notifications' && localSettings && (
                 <SettingsGroup title="Alert Preferences" desc="Control how NavSakhi Agent communicates with you.">
                   <ToggleRow label="Journey Alerts" desc="Receive updates regarding route safety variations." checked={localSettings.notifications.journey_alerts} onChange={(v) => updateNestedSetting('notifications', 'journey_alerts', v)} />
                   <ToggleRow label="Community Incident Alerts" desc="Ping when a high-severity incident is verified nearby." checked={localSettings.notifications.community_alerts} onChange={(v) => updateNestedSetting('notifications', 'community_alerts', v)} />
                   <ToggleRow label="Weather Warnings" desc="Notifications for sudden rain or hazardous conditions." checked={localSettings.notifications.weather_alerts} onChange={(v) => updateNestedSetting('notifications', 'weather_alerts', v)} />
                   <ToggleRow label="AI Proactive Push" desc="Allow Intelligence Coordinator to push urgent recommendations." checked={localSettings.notifications.ai_notifications} onChange={(v) => updateNestedSetting('notifications', 'ai_notifications', v)} />
                 </SettingsGroup>
               )}

               {/* TAB 4: PRIVACY */}
               {activeTab === 'privacy' && localSettings && (
                 <SettingsGroup title="Privacy & Security" desc="Manage what data is shared with the community and ML layers.">
                   <ToggleRow label="Share Live Location" desc="Allows live telemetry synchronization during an active monitored journey." checked={localSettings.privacy.share_live_location} onChange={(v) => updateNestedSetting('privacy', 'share_live_location', v)} />
                   <ToggleRow label="Anonymous Community Reports" desc="Hide your name from reports you submit." checked={localSettings.privacy.anonymous_community_reports} onChange={(v) => updateNestedSetting('privacy', 'anonymous_community_reports', v)} />
                   <ToggleRow label="Opt-in to Analytics" desc="Help improve routing algorithms." checked={localSettings.privacy.analytics} onChange={(v) => updateNestedSetting('privacy', 'analytics', v)} />
                 </SettingsGroup>
               )}

               {/* TAB 5: EMERGENCY PROTOCOL */}
               {activeTab === 'emergency' && localSettings && (
                 <SettingsGroup title="Emergency Protocol" desc="Configure SOS behavior and trigger actions.">
                   <ToggleRow label="Quick-Dial Primary Contact" desc="Pre-populates your device phone dialer with primary contact when SOS countdown ends." checked={localSettings.emergency.auto_call_emergency_contact} onChange={(v) => updateNestedSetting('emergency', 'auto_call_emergency_contact', v)} />
                   <ToggleRow label="Pre-Stage Distress Link" desc="Generates a live tracking link ready for manual device sharing (Web Share / SMS)." checked={localSettings.emergency.share_journey_automatically} onChange={(v) => updateNestedSetting('emergency', 'share_journey_automatically', v)} />
                   <ToggleRow label="Use Countdown Timer" desc="5-second delay to cancel false alarms." checked={localSettings.emergency.emergency_countdown} onChange={(v) => updateNestedSetting('emergency', 'emergency_countdown', v)} />
                 </SettingsGroup>
               )}

               {/* TAB 6: AI CONFIG */}
               {activeTab === 'ai' && localSettings && (
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

               {/* TAB 7: LOCATION */}
               {activeTab === 'location' && localSettings && (
                 <SettingsGroup title="Routing Exclusions" desc="Set global constraints for the pathfinding ML models.">
                   <ToggleRow label="Avoid Dark Areas" desc="Prioritize well-lit streets." checked={localSettings.location.avoid_dark_areas} onChange={(v) => updateNestedSetting('location', 'avoid_dark_areas', v)} />
                   <ToggleRow label="Avoid Construction" desc="Route around active building zones." checked={localSettings.location.avoid_construction} onChange={(v) => updateNestedSetting('location', 'avoid_construction', v)} />
                   <ToggleRow label="Avoid High Crowd Density" desc="Prefer quieter routes." checked={localSettings.location.avoid_crowds} onChange={(v) => updateNestedSetting('location', 'avoid_crowds', v)} />
                 </SettingsGroup>
               )}

               {/* TAB 8: DEVELOPER */}
               {activeTab === 'developer' && localSettings && (
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

               {/* TAB 9: APPEARANCE */}
               {activeTab === 'appearance' && (
                  <SettingsGroup title="Appearance" desc="Visual theme settings.">
                     <div className="text-sm text-muted-foreground italic">Theme management is synchronized with system preferences.</div>
                  </SettingsGroup>
               )}

               {/* TAB 10: LEGAL & TRANSPARENCY */}
               {activeTab === 'legal' && (
                 <SettingsGroup title="Legal, Transparency & Disclosures" desc="Prototype scope, user agreements, privacy notices, and safety guidelines.">
                   <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     <Link href="/terms" className="glass-card p-4 rounded-2xl border border-border/70 hover:border-primary/50 transition-all flex flex-col gap-1.5">
                       <span className="font-bold text-sm text-foreground flex items-center justify-between">Terms of Use <ArrowRight size={14} className="text-primary"/></span>
                       <span className="text-xs text-muted-foreground">User agreement, permitted usage, disclaimer of safety guarantees.</span>
                     </Link>
                     <Link href="/privacy" className="glass-card p-4 rounded-2xl border border-border/70 hover:border-primary/50 transition-all flex flex-col gap-1.5">
                       <span className="font-bold text-sm text-foreground flex items-center justify-between">Privacy Policy <ArrowRight size={14} className="text-primary"/></span>
                       <span className="text-xs text-muted-foreground">Telemetry processing, data retention, and consent management.</span>
                     </Link>
                     <Link href="/limitations" className="glass-card p-4 rounded-2xl border border-border/70 hover:border-primary/50 transition-all flex flex-col gap-1.5">
                       <span className="font-bold text-sm text-foreground flex items-center justify-between">AI &amp; ML Limitations <ArrowRight size={14} className="text-primary"/></span>
                       <span className="text-xs text-muted-foreground">Environmental scoring proxies, synthetic models, not crime prediction.</span>
                     </Link>
                     <Link href="/safety-guidelines" className="glass-card p-4 rounded-2xl border border-border/70 hover:border-primary/50 transition-all flex flex-col gap-1.5">
                       <span className="font-bold text-sm text-foreground flex items-center justify-between">Safety Guidelines <ArrowRight size={14} className="text-primary"/></span>
                       <span className="text-xs text-muted-foreground">Emergency numbers (112, 1091), transit advice, and SOS guidance.</span>
                     </Link>
                     <Link href="/accessibility" className="glass-card p-4 rounded-2xl border border-border/70 hover:border-primary/50 transition-all flex flex-col gap-1.5">
                       <span className="font-bold text-sm text-foreground flex items-center justify-between">Accessibility Statement <ArrowRight size={14} className="text-primary"/></span>
                       <span className="text-xs text-muted-foreground">WCAG 2.1 conformance, screen reader support, contrast standards.</span>
                     </Link>
                     <Link href="/about" className="glass-card p-4 rounded-2xl border border-border/70 hover:border-primary/50 transition-all flex flex-col gap-1.5">
                       <span className="font-bold text-sm text-foreground flex items-center justify-between">About NavSakhi <ArrowRight size={14} className="text-primary"/></span>
                       <span className="text-xs text-muted-foreground">Academic demonstration scope, research pillars, and architecture.</span>
                     </Link>
                     <Link href="/help" className="glass-card p-4 rounded-2xl border border-border/70 hover:border-primary/50 transition-all flex flex-col gap-1.5 md:col-span-2">
                       <span className="font-bold text-sm text-foreground flex items-center justify-between">Help &amp; FAQ <ArrowRight size={14} className="text-primary"/></span>
                       <span className="text-xs text-muted-foreground">Common questions, route planning walkthroughs, and troubleshooting.</span>
                     </Link>
                   </div>
                 </SettingsGroup>
               )}


             </motion.div>
           </AnimatePresence>
        </div>
      </div>

      {/* ADD / EDIT EMERGENCY CONTACT MODAL */}
      <Dialog open={isContactDialogOpen} onOpenChange={setIsContactDialogOpen}>
        <DialogContent className="max-w-md bg-card border border-border/80 rounded-2xl p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="font-[family-name:var(--font-jakarta)] text-lg font-bold">
              {editingContact ? "Edit Emergency Contact" : "Add Emergency Point of Contact"}
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Provide verified contact information. Supports international country codes.
            </DialogDescription>
          </DialogHeader>

          {contactFormError && (
            <div className="rounded-xl bg-destructive/10 border border-destructive/20 p-3 flex items-start gap-2.5 text-destructive text-xs">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{contactFormError}</span>
            </div>
          )}

          <div className="space-y-4 py-2">
            {/* Contact Name */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-foreground">Contact Name *</label>
              <Input
                value={contactForm.name}
                onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                placeholder="e.g. Ananya Raman"
                className="bg-secondary/40 border-border/60 rounded-xl h-10"
              />
            </div>

            {/* Relationship */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-foreground">Relationship *</label>
              <select
                value={contactForm.relationship}
                onChange={(e) => setContactForm({ ...contactForm, relationship: e.target.value })}
                className="w-full h-10 rounded-xl bg-secondary/40 border border-border/60 px-3 text-sm focus:ring-1 focus:ring-primary outline-none"
              >
                <option value="Family">Family</option>
                <option value="Parent">Parent</option>
                <option value="Sibling">Sibling</option>
                <option value="Spouse/Partner">Spouse / Partner</option>
                <option value="Friend">Friend</option>
                <option value="Guardian">Guardian</option>
                <option value="Colleague">Colleague</option>
                <option value="Other">Other</option>
              </select>
            </div>

            {/* Phone Number with Country Code */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-foreground">Phone Number *</label>
              <div className="flex gap-2">
                <select
                  value={contactForm.country_code}
                  onChange={(e) => setContactForm({ ...contactForm, country_code: e.target.value })}
                  className="w-24 h-10 rounded-xl bg-secondary/40 border border-border/60 px-2 text-sm focus:ring-1 focus:ring-primary outline-none shrink-0"
                >
                  <option value="+91">+91 (IN)</option>
                  <option value="+1">+1 (US)</option>
                  <option value="+44">+44 (UK)</option>
                  <option value="+61">+61 (AU)</option>
                  <option value="+65">+65 (SG)</option>
                  <option value="+971">+971 (AE)</option>
                </select>
                <Input
                  value={contactForm.phone_number}
                  onChange={(e) => setContactForm({ ...contactForm, phone_number: e.target.value })}
                  placeholder="9876543210"
                  className="flex-1 bg-secondary/40 border-border/60 rounded-xl h-10 font-mono"
                />
              </div>
            </div>

            {/* Email (Optional) */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-foreground">Email Address (Optional)</label>
              <Input
                type="email"
                value={contactForm.email}
                onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                placeholder="contact@example.com"
                className="bg-secondary/40 border-border/60 rounded-xl h-10"
              />
            </div>

            {/* Set as Primary Checkbox */}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="is_primary_checkbox"
                checked={contactForm.is_primary}
                onChange={(e) => setContactForm({ ...contactForm, is_primary: e.target.checked })}
                className="rounded border-border text-primary focus:ring-primary h-4 w-4"
              />
              <label htmlFor="is_primary_checkbox" className="text-xs font-semibold text-foreground cursor-pointer select-none">
                Designate as Primary Emergency Contact (pre-selected for quick dialing and emergency sharing)
              </label>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsContactDialogOpen(false)}
              className="rounded-xl border-border"
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleSaveContact}
              disabled={isContactSaving}
              className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-bold"
            >
              {isContactSaving ? <Activity size={15} className="animate-spin mr-1.5" /> : null}
              {isContactSaving ? "Saving..." : "Save Contact"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DELETE CONFIRMATION MODAL */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="max-w-sm bg-card border border-border/80 rounded-2xl p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-destructive flex items-center gap-2">
              <Trash2 size={18} /> Remove Emergency Contact
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground pt-1">
              Are you sure you want to remove <span className="font-bold text-foreground">{contactToDelete?.name}</span> from your saved emergency contacts?
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="gap-2 sm:gap-0 pt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsDeleteDialogOpen(false);
                setContactToDelete(null);
              }}
              className="rounded-xl border-border"
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleDeleteContact}
              disabled={isDeletingContact}
              className="rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90 font-bold"
            >
              {isDeletingContact ? <Activity size={15} className="animate-spin mr-1.5" /> : null}
              {isDeletingContact ? "Removing..." : "Remove Contact"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Official Comprehensive Footer */}
      <div className="mt-12 -mx-6 md:-mx-10 lg:-mx-12">
        <Footer />
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