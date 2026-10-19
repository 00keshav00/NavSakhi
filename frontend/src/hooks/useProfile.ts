import { useState, useEffect } from "react";
import { profileService } from "../api/services/profileService";
import { ProfileResponse } from "../types/profile";
import { toast } from "sonner";

export const useProfile = () => {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = async () => {
    try {
      setIsLoading(true);
      const data = await profileService.getProfile();
      setProfile(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load profile.");
      toast.error("Failed to load profile");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  return { profile, isLoading, error, reloadProfile: fetchProfile };
};
