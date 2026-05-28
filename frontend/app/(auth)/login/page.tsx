"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/stores/auth";
import { AsptexLogo } from "@/components/brand/AsptexLogo";
import { cn } from "@/lib/utils";

const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
});
type LoginForm = z.infer<typeof loginSchema>;

const LABELS = {
  uz: {
    subtitle: "To'qimachilik ERP tizimi",
    username: "Foydalanuvchi nomi",
    password: "Parol",
    login: "Kirish",
    tagline: "Ishlab chiqarishni nazorat qiling",
  },
  ru: {
    subtitle: "Система управления текстилем",
    username: "Имя пользователя",
    password: "Пароль",
    login: "Войти",
    tagline: "Управляйте производством",
  },
} as const;

export default function LoginPage() {
  const router = useRouter();
  const { setTokens, setUser, language, setLanguage } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const labels = LABELS[language];

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    try {
      const response = await authApi.login(data.username, data.password);
      setTokens(response.access_token, response.refresh_token);
      setUser(response.user, response.companies);
      router.push("/select-company");
    } catch (err: any) {
      toast.error(err.message || (language === "uz" ? "Kirish amalga oshmadi" : "Ошибка входа"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen overflow-hidden">
      {/* ── Left panel: decorative ────────────────────────── */}
      <div
        className="hidden lg:flex lg:w-[55%] flex-col items-start justify-between p-12"
        style={{
          background: "linear-gradient(145deg, #050E1A 0%, #0B1E38 50%, #0D2B45 100%)",
        }}
      >
        {/* Top logo */}
        <AsptexLogo variant="full" size={36} onDark />

        {/* Center content */}
        <div className="max-w-lg">
          {/* Abstract weave pattern */}
          <div className="mb-10 relative h-48 w-full opacity-20">
            <svg viewBox="0 0 400 200" className="w-full h-full" aria-hidden>
              {Array.from({ length: 8 }).map((_, i) => (
                <line
                  key={`h${i}`}
                  x1="0" y1={i * 28} x2="400" y2={i * 28 + 14}
                  stroke="#6FDBC4" strokeWidth="1.5" strokeLinecap="round"
                  opacity={0.4 + i * 0.08}
                />
              ))}
              {Array.from({ length: 12 }).map((_, i) => (
                <line
                  key={`v${i}`}
                  x1={i * 36} y1="0" x2={i * 36 + 18} y2="200"
                  stroke="#1565C0" strokeWidth="1" strokeLinecap="round"
                  opacity={0.3 + i * 0.05}
                />
              ))}
              <circle cx="200" cy="100" r="40" stroke="#00A88E" strokeWidth="1.5" fill="none" opacity="0.5" />
              <circle cx="200" cy="100" r="20" stroke="#6FDBC4" strokeWidth="1" fill="none" opacity="0.4" />
            </svg>
          </div>

          <h1
            className="text-4xl font-bold leading-tight mb-4"
            style={{ color: "#E8EFF7" }}
          >
            {labels.tagline}
          </h1>
          <p
            className="text-base leading-relaxed"
            style={{ color: "#8FA3BC" }}
          >
            {language === "uz"
              ? "Ombor, ishlab chiqarish, jo'natmalar va hisobotlarni yagona tizimda boshqaring."
              : "Управляйте складом, производством, отгрузками и отчётностью в единой системе."}
          </p>
        </div>

        {/* Bottom: feature pills */}
        <div className="flex gap-3 flex-wrap">
          {[
            language === "uz" ? "Ombor nazorati" : "Контроль склада",
            language === "uz" ? "Kunlik hisobotlar" : "Суточные отчёты",
            language === "uz" ? "Jo'natmalar" : "Отгрузки",
            language === "uz" ? "Real-time" : "Real-time",
          ].map((pill) => (
            <span
              key={pill}
              className="rounded-full px-3.5 py-1.5 text-[12px] font-medium"
              style={{
                background: "rgba(21,101,192,0.2)",
                color: "#6FDBC4",
                border: "1px solid rgba(111,219,196,0.2)",
              }}
            >
              {pill}
            </span>
          ))}
        </div>
      </div>

      {/* ── Right panel: login form ───────────────────────── */}
      <div className="flex flex-1 flex-col items-center justify-center p-6 bg-background">
        {/* Language switcher — top right */}
        <div className="absolute right-6 top-5 flex items-center rounded-lg border border-border overflow-hidden">
          {(["uz", "ru"] as const).map((lang) => (
            <button
              key={lang}
              onClick={() => setLanguage(lang)}
              className={cn(
                "px-3 py-1.5 text-[12px] font-semibold transition-colors",
                language === lang
                  ? "bg-primary text-white"
                  : "text-foreground-muted hover:bg-muted"
              )}
            >
              {lang.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Mobile logo */}
        <div className="mb-8 lg:hidden">
          <AsptexLogo variant="full" size={36} />
        </div>

        <div className="w-full max-w-[380px]">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-foreground">
              {language === "uz" ? "Xush kelibsiz" : "Добро пожаловать"}
            </h2>
            <p className="mt-1.5 text-[14px] text-foreground-muted">{labels.subtitle}</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {/* Username */}
            <div>
              <label className="block text-[13px] font-medium text-foreground mb-1.5">
                {labels.username}
              </label>
              <input
                {...register("username")}
                type="text"
                autoComplete="username"
                autoFocus
                className={cn(
                  "asptex-input w-full rounded-[10px] border px-4 py-2.5 text-[14px]",
                  "bg-surface text-foreground placeholder:text-foreground-subtle",
                  "border-border transition-all",
                  errors.username && "border-danger"
                )}
                placeholder={labels.username}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-[13px] font-medium text-foreground mb-1.5">
                {labels.password}
              </label>
              <div className="relative">
                <input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  className={cn(
                    "asptex-input w-full rounded-[10px] border px-4 py-2.5 pr-10 text-[14px]",
                    "bg-surface text-foreground placeholder:text-foreground-subtle",
                    "border-border transition-all",
                    errors.password && "border-danger"
                  )}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-subtle hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                "w-full rounded-[10px] py-2.5 text-[14px] font-semibold text-white",
                "bg-primary hover:bg-primary/90 active:scale-[0.99]",
                "disabled:opacity-60 disabled:cursor-not-allowed",
                "transition-all duration-150 flex items-center justify-center gap-2 mt-2"
              )}
            >
              {isLoading && <Loader2 size={16} className="animate-spin" />}
              {labels.login}
            </button>
          </form>

          <p className="mt-8 text-center text-[11px] text-foreground-subtle">
            ASPTEX ERP © {new Date().getFullYear()}
          </p>
        </div>
      </div>
    </div>
  );
}
