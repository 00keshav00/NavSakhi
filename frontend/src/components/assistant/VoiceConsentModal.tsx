"use client";

import React from "react";
import { Mic, Shield, Lock, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface VoiceConsentModalProps {
  isOpen: boolean;
  onConsent: () => void;
  onDecline: () => void;
}

export function VoiceConsentModal({
  isOpen,
  onConsent,
  onDecline,
}: VoiceConsentModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onDecline()}>
      <DialogContent className="sm:max-w-md bg-card border-border/80 shadow-2xl backdrop-blur-2xl">
        <DialogHeader className="space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary border border-primary/20">
            <Mic className="h-6 w-6" />
          </div>
          <DialogTitle className="text-center text-lg font-extrabold text-foreground tracking-tight">
            Voice Assistant & Speech Privacy
          </DialogTitle>
          <DialogDescription className="text-center text-xs text-muted-foreground leading-relaxed">
            NavSakhi supports free browser-based voice input. Please review our privacy and safety boundaries before enabling microphone access.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2 text-xs">
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-secondary/40 border border-border/50">
            <Lock className="h-4 w-4 text-primary shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-bold text-foreground">Zero Audio Storage</span>
              <p className="text-muted-foreground leading-normal">
                NavSakhi never records, stores, or uploads your raw audio to our backend servers. Recognition occurs live via your browser.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-secondary/40 border border-border/50">
            <Shield className="h-4 w-4 text-primary shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-bold text-foreground">Browser Vendor Processing Notice</span>
              <p className="text-muted-foreground leading-normal">
                Standard browser speech recognition (e.g. in Chrome, Edge, or Safari) may process speech via vendor servers to return text transcripts.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300">
            <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-bold">Strict Safety Boundary</span>
              <p className="text-[11px] leading-normal opacity-90">
                Spoken words populate the text composer for your review. Speaking words like &quot;help&quot; or &quot;SOS&quot; will <strong>never</strong> trigger automated emergency dispatch or modify monitored journeys.
              </p>
            </div>
          </div>
        </div>

        <DialogFooter className="flex flex-col-reverse sm:flex-row gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onDecline}
            className="w-full sm:w-auto text-xs font-semibold"
          >
            Continue with Text Only
          </Button>
          <Button
            type="button"
            onClick={onConsent}
            className="w-full sm:w-auto bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold"
          >
            I Understand &amp; Enable Voice
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
