"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { 
  ShieldCheck, 
  ArrowRight, 
  Eye, 
  EyeOff, 
  Lock, 
  Mail, 
  User, 
  Phone, 
  Users, 
  Loader2, 
  AlertCircle, 
  Info,
  CheckCircle2,
  Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRegister } from "@/hooks/useRegister";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";

// Zod Validation Schema matching backend validation rules
const registerSchema = z.object({
  fullName: z.string().min(2, "Full name must be at least 2 characters"),
  email: z.string().min(1, "Email is required").email("Please enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(72, "Password cannot exceed 72 characters")
    .regex(/[0-9!@#$%^&*()_+\-=\[\]{};':",.<>/?]/, "Password must include at least one number or symbol"),
  confirmPassword: z.string().min(1, "Please confirm your password"),
  emergencyContactName: z.string().min(2, "Emergency contact name must be at least 2 characters"),
  emergencyContactRelationship: z.string().min(1, "Relationship is required"),
  emergencyCountryCode: z.string().min(1, "Country code required"),
  emergencyContactPhone: z
    .string()
    .min(10, "Phone number must be at least 10 digits")
    .regex(/^[0-9]{10,14}$/, "Please enter a valid 10-14 digit phone number"),
  acknowledgedLimitations: z.literal(true, {
    errorMap: () => ({ message: "You must acknowledge prototype limitations to create an account" }),
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type RegisterFormValues = z.infer<typeof registerSchema>;

function RegisterForm() {
  const { register: submitRegister, isLoading, error } = useRegister();
  const searchParams = useSearchParams();
  const redirectTarget = searchParams.get("redirect");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
      emergencyContactName: "",
      emergencyContactRelationship: "Family",
      emergencyCountryCode: "+91",
      emergencyContactPhone: "",
      acknowledgedLimitations: true,
    },
  });

  const onSubmit = (data: RegisterFormValues) => {
    const formattedPhone = `${data.emergencyCountryCode.trim()}${data.emergencyContactPhone.trim()}`;
    submitRegister({
      fullName: data.fullName,
      email: data.email,
      password: data.password,
      confirmPassword: data.confirmPassword,
      emergencyContactName: data.emergencyContactName,
      emergencyContactRelationship: data.emergencyContactRelationship,
      emergencyContactPhone: formattedPhone,
      acknowledgedLimitations: data.acknowledgedLimitations,
    }, redirectTarget || undefined);
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-background flex flex-col items-center justify-center p-4 py-8">
      {/* Dynamic Ambient Background Glows */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[15%] -left-[10%] w-[55vw] h-[55vw] rounded-full bg-primary/10 blur-[130px] dark:bg-primary/5" />
        <div className="absolute top-[35%] -right-[10%] w-[45vw] h-[45vw] rounded-full bg-rose-200/25 dark:bg-primary/5 blur-[130px]" />
      </div>

      <div className="w-full max-w-lg z-10 animate-slide-up">
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-6">
          <Link href="/" className="inline-block transition-transform hover:scale-105">
            <div className="relative h-14 w-52 mb-2 flex items-center justify-center">
              <Image 
                src="/images/navsakhi/navsakhi_logo_official.png" 
                alt="NavSakhi - Safer Journeys • Stronger Women" 
                width={200} 
                height={64} 
                className="h-11 w-auto object-contain" 
                priority 
              />
            </div>
          </Link>
          <h1 className="font-[family-name:var(--font-jakarta)] text-2xl font-bold text-foreground">
            Create Your Account
          </h1>
          <p className="text-muted-foreground text-xs sm:text-sm mt-1 max-w-sm">
            Configure your secure profile, saved preferences, and designated emergency contact.
          </p>
        </div>

        {/* Form Card */}
        <div className="glass-card rounded-3xl p-6 sm:p-8 border border-border/70 shadow-2xl backdrop-blur-2xl">
          
          <AnimatePresence mode="wait">
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -10, height: 0 }}
                animate={{ opacity: 1, y: 0, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-5 rounded-2xl bg-danger/10 border border-danger/25 p-4 flex items-start gap-3 text-danger text-xs leading-relaxed"
              >
                <AlertCircle size={18} className="shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="font-bold block">Registration Notice</span>
                  <p>{error}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 text-left">
            
            {/* Account Details Group */}
            <div className="space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-primary">
                <User size={14} />
                <span>Personal Account Credentials</span>
              </div>

              {/* Full Name */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-foreground ml-1">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input 
                    {...register("fullName")}
                    disabled={isLoading}
                    placeholder="Priya Raman"
                    className={`pl-9 h-11 rounded-xl bg-background/50 border-border/70 text-sm focus:bg-background ${errors.fullName ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                  />
                </div>
                {errors.fullName && (
                  <p className="text-danger text-[11px] font-medium ml-1 flex items-center gap-1 mt-0.5">
                    <AlertCircle size={11} /> {errors.fullName.message}
                  </p>
                )}
              </div>

              {/* Email Address */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-foreground ml-1">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input 
                    {...register("email")}
                    disabled={isLoading}
                    type="email"
                    placeholder="priya@example.com"
                    className={`pl-9 h-11 rounded-xl bg-background/50 border-border/70 text-sm focus:bg-background ${errors.email ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                  />
                </div>
                {errors.email && (
                  <p className="text-danger text-[11px] font-medium ml-1 flex items-center gap-1 mt-0.5">
                    <AlertCircle size={11} /> {errors.email.message}
                  </p>
                )}
              </div>

              {/* Passwords (2-col on sm) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Password */}
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground ml-1">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input 
                      {...register("password")}
                      disabled={isLoading}
                      type={showPassword ? "text" : "password"}
                      placeholder="Min 8 characters"
                      className={`pl-9 pr-9 h-11 rounded-xl bg-background/50 border-border/70 text-sm focus:bg-background ${errors.password ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-3 text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="text-danger text-[11px] font-medium ml-1 flex items-center gap-1 mt-0.5">
                      <AlertCircle size={11} /> {errors.password.message}
                    </p>
                  )}
                </div>

                {/* Confirm Password */}
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground ml-1">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input 
                      {...register("confirmPassword")}
                      disabled={isLoading}
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="Repeat password"
                      className={`pl-9 pr-9 h-11 rounded-xl bg-background/50 border-border/70 text-sm focus:bg-background ${errors.confirmPassword ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-3 text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                    >
                      {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p className="text-danger text-[11px] font-medium ml-1 flex items-center gap-1 mt-0.5">
                      <AlertCircle size={11} /> {errors.confirmPassword.message}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Emergency Contact Group */}
            <div className="mt-2 pt-3 border-t border-border/50 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-rose-500">
                <Users size={14} />
                <span>Designated Emergency Contact</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-normal -mt-1">
                This contact will be pre-staged in your Emergency SOS sharing sheet. No notification or message is sent until you explicitly trigger the action.
              </p>

              {/* Emergency Contact Name & Relationship */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground ml-1">Contact Name</label>
                  <Input 
                    {...register("emergencyContactName")}
                    disabled={isLoading}
                    placeholder="Ananya Raman"
                    className={`h-11 rounded-xl bg-background/50 border-border/70 text-sm focus:bg-background ${errors.emergencyContactName ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                  />
                  {errors.emergencyContactName && (
                    <p className="text-danger text-[11px] font-medium ml-1 flex items-center gap-1 mt-0.5">
                      <AlertCircle size={11} /> {errors.emergencyContactName.message}
                    </p>
                  )}
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground ml-1">Relationship</label>
                  <select
                    {...register("emergencyContactRelationship")}
                    disabled={isLoading}
                    className="w-full h-11 rounded-xl bg-background/50 border border-border/70 px-3 text-sm text-foreground focus:bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="Family">Family / Parent</option>
                    <option value="Spouse">Spouse / Partner</option>
                    <option value="Sibling">Sibling</option>
                    <option value="Friend">Trusted Friend</option>
                    <option value="Colleague">Colleague / Peer</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              {/* Phone with Country Code */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-foreground ml-1">Contact Phone Number</label>
                <div className="flex gap-2">
                  <Input 
                    {...register("emergencyCountryCode")}
                    disabled={isLoading}
                    placeholder="+91"
                    className="w-20 h-11 rounded-xl bg-background/50 border-border/70 text-center font-mono text-sm focus:bg-background"
                  />
                  <div className="relative flex-1">
                    <Phone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input 
                      {...register("emergencyContactPhone")}
                      disabled={isLoading}
                      type="tel"
                      placeholder="9876543210"
                      className={`pl-9 h-11 rounded-xl bg-background/50 border-border/70 text-sm font-mono focus:bg-background ${errors.emergencyContactPhone ? 'border-danger/50 focus-visible:ring-danger/30' : ''}`}
                    />
                  </div>
                </div>
                {errors.emergencyContactPhone && (
                  <p className="text-danger text-[11px] font-medium ml-1 flex items-center gap-1 mt-0.5">
                    <AlertCircle size={11} /> {errors.emergencyContactPhone.message}
                  </p>
                )}
              </div>
            </div>

            {/* Prototype Limitation Acknowledgement */}
            <div className="mt-2 pt-3 border-t border-border/50">
              <div className="p-3 rounded-2xl bg-secondary/50 border border-border/60 text-xs text-muted-foreground space-y-2">
                <div className="flex items-start gap-2.5">
                  <input 
                    type="checkbox" 
                    id="ack"
                    {...register("acknowledgedLimitations")}
                    disabled={isLoading}
                    className="mt-0.5 rounded border-border/60 text-primary focus:ring-primary h-4 w-4 shrink-0" 
                  />
                  <label htmlFor="ack" className="cursor-pointer text-[11px] leading-relaxed select-none">
                    <strong>Prototype Acknowledgement:</strong> I understand NavSakhi is a working software prototype. I agree to the{" "}
                    <Link href="/terms" target="_blank" className="font-semibold text-primary underline hover:text-primary/80">Terms &amp; Conditions</Link>,{" "}
                    <Link href="/privacy" target="_blank" className="font-semibold text-primary underline hover:text-primary/80">Privacy Policy</Link>, and{" "}
                    <Link href="/limitations" target="_blank" className="font-semibold text-primary underline hover:text-primary/80">AI &amp; ML Limitations</Link>. Its emergency flows are simulated, do not dispatch police or send automated background SMS, and saving an emergency contact does not automatically alert that contact. In an emergency, I will dial 112 directly.
                  </label>
                </div>
                {errors.acknowledgedLimitations && (
                  <p className="text-danger text-[11px] font-medium flex items-center gap-1">
                    <AlertCircle size={11} /> {errors.acknowledgedLimitations.message}
                  </p>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <Button 
              type="submit"
              disabled={isLoading}
              className="h-12 w-full rounded-2xl bg-primary text-primary-foreground font-bold text-sm mt-2 shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all group"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating Account...
                </>
              ) : (
                <>
                  Complete Registration <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </Button>
          </form>

          {/* Guest & Sign In Options */}
          <div className="mt-6 pt-4 border-t border-border/50 flex flex-col items-center gap-3 text-xs text-muted-foreground">
            <p>
              Already have an account?{" "}
              <Link href={redirectTarget ? `/login?redirect=${redirectTarget}` : "/login"} className="font-bold text-primary hover:underline">
                Sign In
              </Link>
            </p>
            <Link href="/home" className="text-muted-foreground hover:text-foreground font-medium underline transition-colors">
              Continue exploring as Guest &rarr;
            </Link>
          </div>

        </div>

        {/* Security Disclosures & Legal Links */}
        <div className="mt-6 text-center text-[11px] text-muted-foreground max-w-sm mx-auto space-y-2">
          <p className="flex items-center justify-center gap-1.5">
            <ShieldCheck size={14} className="text-emerald-500" />
            <span>Encrypted passwords (bcrypt) &bull; Zero plaintext persistence</span>
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-muted-foreground/80">
            <Link href="/terms" className="hover:text-primary transition-colors underline">Terms</Link>
            <span>&bull;</span>
            <Link href="/privacy" className="hover:text-primary transition-colors underline">Privacy Policy</Link>
            <span>&bull;</span>
            <Link href="/limitations" className="hover:text-primary transition-colors underline">AI/ML Limitations</Link>
            <span>&bull;</span>
            <Link href="/safety-guidelines" className="hover:text-primary transition-colors underline">Helplines</Link>
          </div>
        </div>

      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <RegisterForm />
    </Suspense>
  );
}
