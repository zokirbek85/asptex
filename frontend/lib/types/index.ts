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
  company_type: CompanyType;
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
export type AdjustmentStatus = "DRAFT" | "POSTED";
export type WasteType = "ST_3" | "ST_7_11" | "ST_1" | "ST_36" | "ST_98" | "MYCHKA" | "ROVNITSA";
export type PackagingItemType = "BAG" | "CONE" | "PACKAGE" | "CORRUGATED_SHEET" | "PARAFFIN" | "BOX";
export type CounterpartyType = "BUYER" | "TOLLING_OWNER" | "BOTH";
export type LineCategory = "PRODUCTION_INBOUND" | "RECEIPT" | "PRODUCTION_ISSUE" | "SALE_OUTBOUND" | "PACKAGING_ISSUE";

// ── Company ───────────────────────────────────────────────────────────────────

export type CompanyType = "YARN_SPINNING" | "GINNING";

export interface Company {
  id: string;
  name: string;
  short_name: string | null;
  tax_id: string | null;
  address: string | null;
  company_type: CompanyType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CompanyCreate {
  name: string;
  short_name?: string | null;
  tax_id?: string | null;
  address?: string | null;
  company_type: CompanyType;
}

export interface CompanyUpdate {
  name?: string;
  short_name?: string | null;
  tax_id?: string | null;
  address?: string | null;
  company_type?: CompanyType;
}

// ── User ──────────────────────────────────────────────────────────────────────

export interface UserRoleRecord {
  id: string;
  user_id: string;
  company_id: string;
  company_name: string;
  role: UserRole;
  warehouse_id: string | null;
  warehouse_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface User {
  id: string;
  username: string;
  email: string | null;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  preferred_language: "uz" | "ru";
  created_at: string;
  updated_at: string;
  roles: UserRoleRecord[];
}

export interface UserCreate {
  username: string;
  email?: string | null;
  full_name: string;
  password: string;
  preferred_language?: "uz" | "ru";
  is_superadmin?: boolean;
}

export interface UserUpdate {
  email?: string | null;
  full_name?: string;
  preferred_language?: "uz" | "ru";
}

export interface UserRoleAssign {
  company_id: string;
  role: UserRole;
  warehouse_id?: string | null;
}

// ── Warehouse ─────────────────────────────────────────────────────────────────

export interface Warehouse {
  id: string;
  company_id: string;
  code: string;
  name: string;
  warehouse_type: WarehouseType;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WarehouseCreate {
  code: string;
  name: string;
  warehouse_type: WarehouseType;
  description?: string | null;
  sort_order?: number;
}

export interface WarehouseUpdate {
  name?: string;
  description?: string | null;
  sort_order?: number;
}

// ── Counterparty ──────────────────────────────────────────────────────────────

export interface CounterpartyContact {
  id: string;
  contact_type: string;
  contact_value: string;
  label: string | null;
  is_primary: boolean;
}

export interface Counterparty {
  id: string;
  company_id: string;
  name: string;
  short_name: string | null;
  country: string | null;
  tax_id: string | null;
  counterparty_type: CounterpartyType;
  notes: string | null;
  is_active: boolean;
  merged_into_id: string | null;
  contacts: CounterpartyContact[];
  created_at: string;
  updated_at: string;
}

export interface CounterpartyCreate {
  name: string;
  short_name?: string | null;
  country?: string | null;
  tax_id?: string | null;
  counterparty_type?: CounterpartyType;
  notes?: string | null;
  contacts?: Array<{ contact_type: string; contact_value: string; label?: string | null; is_primary?: boolean }>;
}

export interface CounterpartyUpdate {
  name?: string;
  short_name?: string | null;
  country?: string | null;
  tax_id?: string | null;
  counterparty_type?: CounterpartyType;
  notes?: string | null;
}

// ── Contract ──────────────────────────────────────────────────────────────────

export interface Contract {
  id: string;
  company_id: string;
  contract_number: string;
  contract_date: string;
  counterparty_id: string;
  counterparty_name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContractCreate {
  contract_number: string;
  contract_date: string;
  counterparty_id: string;
  description?: string | null;
}

export interface ContractUpdate {
  contract_number?: string;
  contract_date?: string;
  description?: string | null;
}

// ── Count Catalog ─────────────────────────────────────────────────────────────

export interface CountCatalog {
  id: string;
  company_id: string;
  count_value: string;
  yarn_type: string | null;
  composition: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CountCreate {
  count_value: string;
  yarn_type?: string | null;
  composition?: string | null;
  description?: string | null;
}

export interface CountUpdate {
  yarn_type?: string | null;
  composition?: string | null;
  description?: string | null;
}

// ── Lot ───────────────────────────────────────────────────────────────────────

export interface StockSummaryItem {
  count_id: string;
  count_value: string;
  owner_id: string | null;
  owner_name: string | null;
  total_kg: number;
  warehouse_id: string;
  warehouse_name: string;
}

export interface Lot {
  id: string;
  company_id: string;
  lot_number: string;
  year: number;
  sequence_number: number;
  status: LotStatus;
  opened_at: string;
  closed_at: string | null;
  closed_by: string | null;
  close_reason: string | null;
  auto_closed: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
  stock_summary: StockSummaryItem[];
  tolling_lot_id: string | null;
}
