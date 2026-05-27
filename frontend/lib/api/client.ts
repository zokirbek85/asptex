import { useAuthStore } from "@/lib/stores/auth";
import type { ApiError } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export class ApiException extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public field?: string
  ) {
    super(message);
    this.name = "ApiException";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }

  let errorBody: ApiError;
  try {
    errorBody = await response.json();
  } catch {
    errorBody = { detail: response.statusText, code: "HTTP_ERROR" };
  }

  // 401: clear auth and redirect to login
  if (response.status === 401) {
    useAuthStore.getState().clearAuth();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  throw new ApiException(
    response.status,
    errorBody.code,
    errorBody.detail,
    errorBody.field
  );
}

function getHeaders(withAuth = true): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (withAuth) {
    const token = useAuthStore.getState().accessToken;
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export const apiClient = {
  async get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    let url = `${API_BASE}${path}`;
    if (params) {
      const filtered = Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== undefined)
      ) as Record<string, string>;
      const qs = new URLSearchParams(filtered as Record<string, string>).toString();
      if (qs) url += `?${qs}`;
    }
    const response = await fetch(url, { headers: getHeaders() });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body?: unknown, withAuth = true): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: getHeaders(withAuth),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "PUT",
      headers: getHeaders(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "PATCH",
      headers: getHeaders(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    return handleResponse<T>(response);
  },
};
