import type { Metadata } from "next";
import { LandingView } from "@/components/landing/LandingView";

export const metadata: Metadata = {
  title: "NavSakhi | Intelligent Women's Safety Architecture",
  description: "Evidence-driven personal safety platform for women, combining verified multimodal transit routing, environmental risk proxy scoring, data-driven weather, and consent-based live monitoring.",
};

export default function LandingPage() {
  return <LandingView />;
}