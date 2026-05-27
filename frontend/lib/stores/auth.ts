import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CompanyBrief, UserResponse, UserRole } from "@/lib/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserResponse | null;
  companies: CompanyBrief[];
  activeCompanyId: string | null;
  activeRole: UserRole | null;
  activeWarehouseId: string | null;
  language: "uz" | "ru";

  setTokens: (access: string, refresh: string) => void;
  setUser: (user: UserResponse, companies: CompanyBrief[]) => void;
  setCompanyContext: (
    companyId: string,
    role: UserRole,
    accessToken: string,
    warehouseId?: string | null
  ) => void;
  setLanguage: (lang: "uz" | "ru") => void;
  clearAuth: () => void;

  isAuthenticated: () => boolean;
  hasCompany: () => boolean;
  isRole: (...roles: UserRole[]) => boolean;
  isReadOnly: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      companies: [],
      activeCompanyId: null,
      activeRole: null,
      activeWarehouseId: null,
      language: "uz",

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      setUser: (user, companies) =>
        set({ user, companies }),

      setCompanyContext: (companyId, role, accessToken, warehouseId = null) =>
        set({
          activeCompanyId: companyId,
          activeRole: role,
          activeWarehouseId: warehouseId,
          accessToken,
        }),

      setLanguage: (lang) => set({ language: lang }),

      clearAuth: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          companies: [],
          activeCompanyId: null,
          activeRole: null,
          activeWarehouseId: null,
        }),

      isAuthenticated: () => !!get().accessToken && !!get().user,
      hasCompany: () => !!get().activeCompanyId,
      isRole: (...roles) => roles.includes(get().activeRole as UserRole),
      isReadOnly: () => get().activeRole === "DIRECTOR",
    }),
    {
      name: "asptex-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        companies: state.companies,
        activeCompanyId: state.activeCompanyId,
        activeRole: state.activeRole,
        activeWarehouseId: state.activeWarehouseId,
        language: state.language,
      }),
    }
  )
);
