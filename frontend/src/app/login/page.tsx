"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { 
  ShieldCheck, ArrowRight, Eye, EyeOff, Lock, Mail, Loader2, AlertCircle, Activity
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useLogin } from "@/hooks/useLogin";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

// Zod Validation Schema
const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  rememberMe: z.boolean().optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login, isLoading, error } = useLogin();
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
    });
  };

  const handlePlaceholder = (feature: string) => {
    toast.info(`${feature} coming soon`, {
      description: "This feature is currently in development.",
    });
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-background flex flex-col items-center justify-center p-4">
      {/* Dynamic Mesh Gradient Background (reused from Landing) */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50vw] h-[50vw] rounded-full bg-primary/10 blur-[100px] animate-aurora opacity-50 dark:opacity-30" />
        <div className="absolute top-[30%] -right-[10%] w-[40vw] h-[40vw] rounded-full bg-rose-gold/10 blur-[100px] animate-aurora opacity-50 dark:opacity-30" style={{ animationDelay: "-5s" }} />
      </div>

      <div className="w-full max-w-md z-10 animate-slide-up">
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-iris text-white shadow-lg shadow-primary/25 mb-4">
            <ShieldCheck size={32} />
          </div>
          <h1 className="text-3xl font-[family-name:var(--font-jakarta)] font-extrabold tracking-tight text-foreground">
            Welcome to Safe<span className="text-primary">She</span>
          </h1>
          <p className="text-muted-foreground mt-2 font-light">
            Authenticate to access your secure workspace
          </p>
        </div>

        {/* Form Card */}
        <div className="glass-card rounded-3xl p-8 border border-border/50 shadow-2xl">
          
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

          <div className="flex flex-col gap-5">
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
                  onClick={() => handlePlaceholder("Password Recovery")}
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
              type="button"
              onClick={handleSubmit(onSubmit)}
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
          </div>

          {/* Social / Alternatives */}
          <div className="mt-8 flex flex-col items-center gap-4">
            <div className="flex w-full items-center gap-3">
              <div className="h-px flex-1 bg-border/50" />
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">or continue with</span>
              <div className="h-px flex-1 bg-border/50" />
            </div>
            
            <Button 
              type="button"
              variant="outline"
              disabled={isLoading}
              onClick={() => handlePlaceholder("Google SSO")}
              className="w-full h-12 rounded-xl border-border/50 bg-background/30 backdrop-blur font-semibold hover:bg-secondary transition-colors"
            >
              <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Google
            </Button>
          </div>
        </div>

        {/* Footer / Status */}
        <div className="mt-8 flex flex-col items-center gap-4">
          <p className="text-sm text-muted-foreground">
            Don't have an account?{" "}
            <button onClick={() => handlePlaceholder("Registration")} className="font-semibold text-primary hover:underline">
              Create one
            </button>
          </p>

          <div className="inline-flex items-center gap-2 rounded-full border border-border/50 bg-card/30 px-3 py-1 text-xs text-muted-foreground backdrop-blur-sm">
            <Activity size={14} className="text-success animate-pulse" />
            Backend Connected
          </div>
        </div>
      </div>
    </div>
  );
}