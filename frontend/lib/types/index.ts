// ── Auth & User types ─────────────────────────────────────────────────────────

export type UserRole =
  | "ADMIN"
  | "DIRECTOR"
  | "DEPUTY_DIRECTOR"
  | "WH_RAW"
  | "WH_FINISHED"
  | "PRODUCTION"
  | "ACCOUNTANT";

export interface CompanyBrief {
  id: string;
  name: string;
  short_name: string | null;
  role: UserRole;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string | null;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  preferred_language: "uz" | "ru";
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserResponse;
  companies: CompanyBrief[];
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export interface MeResponse {
  user: UserResponse;
  company_id: string | null;
  role: UserRole | null;
  warehouse_id: string | null;
}

// ── Shared types ──────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  code: string;
  field?: string;
}

// ── Enums ─────────────────────────────────────────────────────────────────────

export type WarehouseType = "RAW_COTTON" | "FINISHED_GOODS" | "WASTE" | "PACKAGING";
export type LotStatus = "OPEN" | "CLOSED" | "BLOCKED";
export type ReportStatus = "DRAFT" | "SUBMITTED" | "CLOSED";
export type ShipmentStatus = "ACTIVE" | "PARTIALLY_CANCELLED" | "CANCELLED";
export type WasteType = "ST_3" | "ST_7_11" | "ST_1" | "ST_36" | "ST_98" | "MYCHKA" | "ROVNITSA";
export type PackagingItemType = "BAG" | "CONE" | "PACKAGE" | "CORRUGATED_SHEET" | "PARAFFIN" | "BOX";
