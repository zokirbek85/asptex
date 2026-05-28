import { apiClient } from "./client";
import type { LotStatus, ShipmentStatus, WarehouseType } from "@/lib/types";

export interface DashboardSummary {
  finished_goods_kg: number;
  raw_cotton_kg: number;
  waste_kg: number;
  packaging_units: number;
  shipments_this_month: number;
  shipments_kg_this_month: number;
  active_lots: number;
  open_daily_reports: number;
  slow_stock_count: number;
  pending_adjustments: number;
}

export interface ChartDataPoint {
  date: string;
  value: number;
  label: string | null;
}

export interface StockByLot {
  lot_id: string;
  lot_number: string;
  status: LotStatus;
  total_kg: number;
  total_bags: number;
  owners: number;
}

export interface SlowStockItem {
  warehouse_type: WarehouseType;
  identifier: string;
  quantity_kg: number;
  last_movement_date: string | null;
  days_idle: number;
}

export interface DashboardAlert {
  alert_type: string;
  severity: "WARNING" | "INFO";
  message: string;
  reference_id: string | null;
}

export interface RecentShipment {
  id: string;
  shipment_number: string;
  shipment_date: string;
  buyer_id: string;
  status: ShipmentStatus;
  total_kg: number;
}

export const dashboardApi = {
  summary: () => apiClient.get<DashboardSummary>("/dashboard/summary"),
  fgChart: () => apiClient.get<{ production: ChartDataPoint[]; shipments: ChartDataPoint[] }>("/dashboard/finished-goods-chart"),
  stockByLot: () => apiClient.get<StockByLot[]>("/dashboard/stock-by-lot"),
  slowStock: () => apiClient.get<SlowStockItem[]>("/dashboard/slow-stock"),
  recentShipments: () => apiClient.get<RecentShipment[]>("/dashboard/recent-shipments"),
  alerts: () => apiClient.get<DashboardAlert[]>("/dashboard/alerts"),
};
