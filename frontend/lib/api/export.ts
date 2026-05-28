import { useAuthStore } from "@/lib/stores/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().accessToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function downloadBlob(url: string, filename: string): Promise<void> {
  const response = await fetch(url, { headers: authHeaders() });
  if (!response.ok) throw new Error(`Export failed: ${response.statusText}`);
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

function buildQs(params: Record<string, string | undefined>): string {
  const filtered = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined)) as Record<string, string>;
  const qs = new URLSearchParams(filtered).toString();
  return qs ? `?${qs}` : "";
}

export const exportApi = {
  stockReport: (params: { fmt?: string; warehouse_type?: string; as_of_date?: string }) => {
    const qs = buildQs({ fmt: params.fmt || "xlsx", warehouse_type: params.warehouse_type, as_of_date: params.as_of_date });
    return downloadBlob(`${API_BASE}/export/stock-report${qs}`, `stock-report.${params.fmt || "xlsx"}`);
  },

  shipments: (params: { fmt?: string; date_from?: string; date_to?: string; buyer_id?: string }) => {
    const qs = buildQs({ fmt: params.fmt || "xlsx", date_from: params.date_from, date_to: params.date_to, buyer_id: params.buyer_id });
    return downloadBlob(`${API_BASE}/export/shipments${qs}`, `shipments.${params.fmt || "xlsx"}`);
  },

  dailyReport: (reportId: string, fmt = "xlsx") => {
    return downloadBlob(`${API_BASE}/export/daily-report/${reportId}?fmt=${fmt}`, `daily-report.${fmt}`);
  },

  lotCard: (lotId: string, fmt = "xlsx") => {
    return downloadBlob(`${API_BASE}/export/lot-card/${lotId}?fmt=${fmt}`, `lot-card.${fmt}`);
  },

  wasteReport: (params: { fmt?: string; date_from?: string; date_to?: string }) => {
    const qs = buildQs({ fmt: params.fmt || "xlsx", date_from: params.date_from, date_to: params.date_to });
    return downloadBlob(`${API_BASE}/export/waste-report${qs}`, `waste-report.${params.fmt || "xlsx"}`);
  },

  auditLog: (params: { date_from?: string; date_to?: string; entity_type?: string }) => {
    const qs = buildQs({ fmt: "xlsx", date_from: params.date_from, date_to: params.date_to, entity_type: params.entity_type });
    return downloadBlob(`${API_BASE}/export/audit-log${qs}`, "audit-log.xlsx");
  },
};
