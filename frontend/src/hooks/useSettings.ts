import { useState, useEffect } from "react";
import { settingsService } from "../api/services/settingsService";
import { SettingsResponse } from "../types/settings";
import { toast } from "sonner";

export const useSettings = () => {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setIsLoading(true);
        const data = await settingsService.getSettings();
        setSettings(data);
        setError(null);
      } catch (err: any) {
        setError(err.message || "Failed to load settings.");
        toast.error("Failed to load settings");
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const saveSettings = async (updatedSettings: SettingsResponse) => {
    try {
      setIsSaving(true);
      await settingsService.updateSettings(updatedSettings);
      setSettings(updatedSettings);
      toast.success("Settings saved successfully.");
      setError(null);
    } catch (err: any) {
      toast.error("Failed to save settings.", { description: err.message });
      setError(err.message || "Failed to save settings.");
    } finally {
      setIsSaving(false);
    }
  };

  return { settings, isLoading, isSaving, error, saveSettings };
};
