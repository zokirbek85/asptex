import { apiClient } from "./client";
import type { LotStatus, PackagingItemType, WasteType } from "@/lib/types";

export interface FinishedGoodsStockItem {
  lot_id: string;
  lot_number: string;
  lot_status: LotStatus;
  count_id: string | null;
  count_value: string | null;
  owner_id: string | null;
  owner_name: string | null;
  quantity_kg: number;
  quantity_bags: number | null;
}

export interface WasteStockItem {
  waste_type: WasteType;
  display_name: string;
  quantity_kg: number;
}

export interface PackagingStockItem {
  pkg_item_type: PackagingItemType;
  display_name: string;
  unit_type: "kg" | "dona" | "komplekt";
  quantity_units: number | null;
  quantity_kg: number;
}

export interface RawCottonStockItem {
  lot_id: string | null;
  lot_number: string | null;
  count_id: string | null;
  count_value: string | null;
  owner_id: string | null;
  owner_name: string | null;
  quantity_kg: number;
  quantity_kip: number | null;
}

export const stockApi = {
  finishedGoods: (params: { warehouse_id: string; lot_id?: string; count_id?: string; owner_id?: string; lot_status?: LotStatus }) =>
    apiClient.get<FinishedGoodsStockItem[]>("/finished-goods/stock", params),

  rawCotton: (params: { warehouse_id: string }) =>
    apiClient.get<RawCottonStockItem[]>("/raw-cotton/stock", params),

  waste: (params: { warehouse_id: string }) =>
    apiClient.get<WasteStockItem[]>("/waste/stock", params),

  packaging: (params: { warehouse_id: string }) =>
    apiClient.get<PackagingStockItem[]>("/packaging/stock", params),

  rawCottonBalanceSummary: (params: { warehouse_id: string }) =>
    apiClient.get<{ own_kg: number; tolling_kg: number; total_kg: number; own_items: number; tolling_items: number }>("/raw-cotton/balance-summary", params),
};
