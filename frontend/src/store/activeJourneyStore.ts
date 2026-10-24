import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ActiveJourneyState {
  activeJourneyId: string | null;
  selectedRouteId: string | null;
  setActiveJourney: (journeyId: string, routeId?: string) => void;
  clearActiveJourney: () => void;
}

export const useActiveJourneyStore = create<ActiveJourneyState>()(
  persist(
    (set) => ({
      activeJourneyId: null,
      selectedRouteId: null,

      setActiveJourney: (journeyId: string, routeId?: string) =>
        set({
          activeJourneyId: journeyId,
          selectedRouteId: routeId || null,
        }),

      clearActiveJourney: () =>
        set({
          activeJourneyId: null,
          selectedRouteId: null,
        }),
    }),
    {
      name: "safeshe-active-journey",
    }
  )
);
