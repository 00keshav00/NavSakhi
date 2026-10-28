"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { 
  ShieldCheck, ArrowRight, Eye, EyeOff, Lock, Mail, Loader2, AlertCircle, KeyRound, Info
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useLogin } from "@/hooks/useLogin";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import { getSafeRedirectUrl, getFriendlyRedirectInfo } from "@/utils/safeRedirect";

// Zod Validation Schema
const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  rememberMe: z.boolean().optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

function LoginForm() {
  const { login, loginAsTestUser, isLoading, error } = useLogin();
  const searchParams = useSearchParams();
  const rawRedirect = searchParams.get("redirect");
  const friendlyRedirect = rawRedirect ? getFriendlyRedirectInfo(rawRedirect) : null;
  const safeRedirectTarget = rawRedirect ? getSafeRedirectUrl(rawRedirect) : undefined;
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  const onSubmit = (data: LoginFormValues) => {
    login({
      email: data.email,
      password: data.password,
      remember_me: data.rememberMe
    }, safeRedirectTarget);
  };

  const handleForgotPassword = () => {
    toast.info("Password Recovery Notice", {
      description: "Password reset via email is unavailable because an external email provider is not configured for this prototype.",
    });
  };

  const handleGoogleUnavailable = () => {
    toast.info("Google Sign-In Unavailable", {
      description: "OAuth 2.0 credentials are not configured for this local prototype. Please sign in with your email and password.",
    });
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-background flex flex-col items-center justify-center p-4">
      {/* Dynamic Mesh Gradient Background */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50vw] h-[50vw] rounded-full bg-primary/10 blur-[100px] animate-aurora opacity-50 dark:opacity-30" />
        <div className="absolute top-[30%] -right-[10%] w-[40vw] h-[40vw] rounded-full bg-rose-200/20 blur-[100px] animate-aurora opacity-50 dark:opacity-30" style={{ animationDelay: "-5s" }} />
      </div>

      <div className="w-full max-w-md z-10 animate-slide-up">
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <Link href="/" className="inline-block transition-transform hover:scale-105">
            <div className="relative h-14 w-52 mb-3 flex items-center justify-center">
              <Image 
                src="/images/navsakhi/navsakhi_logo_official.png" 
                alt="NavSakhi - Safer Journeys • Stronger Women" 
                width={200} 
                height={64} 
                className="h-12 w-auto object-contain" 
                priority 
              />
            </div>
          </Link>
          <p className="text-muted-foreground text-sm font-light">
            Authenticate to access your secure workspace
          </p>
        </div>

        {/* Form Card */}
        <div className="glass-card rounded-3xl p-8 border border-border/50 shadow-2xl">
          
          {friendlyRedirect && (
            <div className="mb-6 rounded-xl bg-amber-500/10 border border-amber-500/20 p-3.5 flex items-center gap-2.5 text-amber-600 dark:text-amber-400 text-xs font-medium">
              <KeyRound size={18} className="shrink-0" />
              <span>{friendlyRedirect.message}</span>
            </div>
          )}

          <AnimatePresence mode="wait">
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -10, height: 0 }}
                animate={{ opacity: 1, y: 0, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-6 rounded-xl bg-danger/10 border border-danger/20 p-4 flex items-start gap-3 text-danger"
              >
                <AlertCircle size={20} className="shrink-0 mt-0.5" />
                <p className="text-sm font-medium">{error}</p>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
            {/* Email Field */}
            <div className="space-y-1">
              <label className="text-sm font-semibold text-foreground ml-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
                <Input 
                  {...register("email")}
                  disabled={isLoading}
                  placeholder="name@example.com"
                  className={`pl-10 h-12 rounded-xl bg-background/50 border-border/50 focus:bg-background ${errors.email ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                />
              </div>
              {errors.email && (
                <p className="text-danger text-xs font-medium ml-1 flex items-center gap-1 mt-1">
                  <AlertCircle size={12} /> {errors.email.message}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div className="space-y-1">
              <div className="flex justify-between items-center ml-1">
                <label className="text-sm font-semibold text-foreground">Password</label>
                <button 
                  type="button" 
                  onClick={handleForgotPassword}
                  className="text-xs font-semibold text-primary hover:underline transition-all"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
                <Input 
                  {...register("password")}
                  disabled={isLoading}
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  className={`pl-10 pr-10 h-12 rounded-xl bg-background/50 border-border/50 focus:bg-background ${errors.password ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-danger text-xs font-medium ml-1 flex items-center gap-1 mt-1">
                  <AlertCircle size={12} /> {errors.password.message}
                </p>
              )}
            </div>

            {/* Remember Me */}
            <div className="flex items-center gap-2 mt-1">
              <input 
                type="checkbox" 
                id="remember" 
                {...register("rememberMe")}
                disabled={isLoading}
                className="rounded border-border/50 bg-background/50 text-primary focus:ring-primary h-4 w-4" 
              />
              <label htmlFor="remember" className="text-sm font-medium text-muted-foreground cursor-pointer">
                Remember this device
              </label>
            </div>

            {/* Submit Button */}
            <Button 
              type="submit"
              disabled={isLoading}
              className="h-12 w-full rounded-xl bg-primary text-primary-foreground font-bold text-base mt-2 shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all group"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  Sign In <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </Button>
          </form>

          {/* Social / Alternatives */}
          <div className="mt-7 flex flex-col items-center gap-4">
            <div className="flex w-full items-center gap-3">
              <div className="h-px flex-1 bg-border/50" />
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">or</span>
              <div className="h-px flex-1 bg-border/50" />
            </div>
            
            <Button 
              type="button"
              variant="outline"
              disabled={isLoading}
              onClick={() => loginAsTestUser(safeRedirectTarget)}
              className="w-full h-11 rounded-xl border-primary/30 bg-primary/5 text-xs font-semibold text-primary hover:bg-primary/10 transition-colors flex items-center justify-center gap-2"
            >
              <ShieldCheck className="w-4 h-4 text-primary" />
              Sign In with Local Test Account (Development Mode)
            </Button>

            <Button 
              type="button"
              variant="outline"
              disabled={isLoading}
              onClick={handleGoogleUnavailable}
              className="w-full h-11 rounded-xl border-border/50 bg-background/30 backdrop-blur text-xs font-medium text-muted-foreground hover:bg-secondary transition-colors"
            >
              <svg className="w-4 h-4 mr-2.5 opacity-60" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Google Sign-In (Unavailable in Prototype)
            </Button>
          </div>
        </div>

        {/* Footer / Status */}
        <div className="mt-8 flex flex-col items-center gap-3">
          <p className="text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link 
              href={safeRedirectTarget ? `/register?redirect=${encodeURIComponent(safeRedirectTarget)}` : "/register"} 
              className="font-bold text-primary hover:underline"
            >
              Create one
            </Link>
          </p>

          <Link href="/home" className="text-xs text-muted-foreground hover:text-foreground font-medium underline transition-colors">
            Continue exploring as Guest &rarr;
          </Link>

          <div className="pt-4 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground/80">
            <Link href="/terms" className="hover:text-primary transition-colors underline">Terms</Link>
            <span>&bull;</span>
            <Link href="/privacy" className="hover:text-primary transition-colors underline">Privacy Policy</Link>
            <span>&bull;</span>
            <Link href="/limitations" className="hover:text-primary transition-colors underline">AI/ML Limitations</Link>
            <span>&bull;</span>
            <Link href="/safety-guidelines" className="hover:text-primary transition-colors underline">Emergency Helplines</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}