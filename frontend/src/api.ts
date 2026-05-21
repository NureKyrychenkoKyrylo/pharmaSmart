import type {
  ActiveAlert,
  AuditLog,
  Batch,
  CreateBatchPayload,
  CreateDevicePayload,
  CreateLocationPayload,
  CreateMedicinePayload,
  CreatePharmacyPayload,
  CreateSalePayload,
  CreateUserPayload,
  DashboardStats,
  DisposeBatchPayload,
  IncidentHistoryEntry,
  IoTDevice,
  Medicine,
  Pharmacy,
  Sale,
  StorageLocation,
  TokenResponse,
  User,
} from "./types";

const DEFAULT_BASE_URL = "https://pharmasmart-ej5n.onrender.com";

type RequestOptions = {
  method?: string;
  token?: string | null;
  body?: unknown;
  form?: URLSearchParams;
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) || DEFAULT_BASE_URL;
  const headers: Record<string, string> = {};

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  if (options.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  }

  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${baseUrl}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.form ?? (options.body ? JSON.stringify(options.body) : undefined),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string };
      detail = data.detail ?? detail;
    } catch {
      // noop
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  login(email: string, password: string) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      form,
    });
  },

  me(token: string) {
    return request<User>("/auth/me", { token });
  },

  getDashboardStats(token: string, pharmacyId?: number) {
    const query = pharmacyId ? `?pharmacy_id=${pharmacyId}` : "";
    return request<DashboardStats>(`/admin/dashboard-stats${query}`, { token });
  },

  getAlerts(token: string, pharmacyId?: number) {
    const query = pharmacyId ? `?pharmacy_id=${pharmacyId}` : "";
    return request<ActiveAlert[]>(`/iot/alerts${query}`, { token });
  },

  resolveAlert(token: string, alertId: number) {
    return request<{ status: string }>(`/iot/alerts/${alertId}/resolve`, {
      method: "PUT",
      token,
    });
  },

  escalateAlert(token: string, alertId: number) {
    return request<{ status: string }>(`/iot/alerts/${alertId}/escalate`, {
      method: "PUT",
      token,
    });
  },

  getIncidentHistory(token: string, pharmacyId?: number, limit = 100) {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    if (pharmacyId) {
      params.set("pharmacy_id", String(pharmacyId));
    }
    return request<IncidentHistoryEntry[]>(`/iot/incidents/history?${params.toString()}`, { token });
  },

  getPharmacies(token: string) {
    return request<Pharmacy[]>("/pharmacies/", { token });
  },

  createPharmacy(token: string, payload: CreatePharmacyPayload) {
    return request<Pharmacy>("/pharmacies/", {
      method: "POST",
      token,
      body: payload,
    });
  },

  deletePharmacy(token: string, pharmacyId: number) {
    return request<void>(`/pharmacies/${pharmacyId}`, {
      method: "DELETE",
      token,
    });
  },

  getLocations(token: string, pharmacyId?: number) {
    const query = pharmacyId ? `?pharmacy_id=${pharmacyId}` : "";
    return request<StorageLocation[]>(`/pharmacies/locations${query}`, { token });
  },

  createLocation(token: string, payload: CreateLocationPayload) {
    return request<StorageLocation>("/pharmacies/locations", {
      method: "POST",
      token,
      body: payload,
    });
  },

  deleteLocation(token: string, locationId: number) {
    return request<void>(`/pharmacies/locations/${locationId}`, {
      method: "DELETE",
      token,
    });
  },

  getMedicines(token: string) {
    return request<Medicine[]>("/inventory/medicines", { token });
  },

  createMedicine(token: string, payload: CreateMedicinePayload) {
    return request<Medicine>("/inventory/medicines", {
      method: "POST",
      token,
      body: payload,
    });
  },

  deleteMedicine(token: string, medicineId: number) {
    return request<void>(`/inventory/medicines/${medicineId}`, {
      method: "DELETE",
      token,
    });
  },

  getBatches(token: string, pharmacyId?: number) {
    const query = pharmacyId ? `?pharmacy_id=${pharmacyId}` : "";
    return request<Batch[]>(`/inventory/batches${query}`, { token });
  },

  createBatch(token: string, payload: CreateBatchPayload) {
    return request<Batch>("/inventory/batches", {
      method: "POST",
      token,
      body: payload,
    });
  },

  deleteBatch(token: string, batchId: number) {
    return request<void>(`/inventory/batches/${batchId}`, {
      method: "DELETE",
      token,
    });
  },

  getExpiredBatches(token: string, daysToExpire: number, pharmacyId?: number) {
    const params = new URLSearchParams();
    params.set("days_to_expire", String(daysToExpire));
    if (pharmacyId) {
      params.set("pharmacy_id", String(pharmacyId));
    }
    return request<Batch[]>(`/inventory/expired?${params.toString()}`, { token });
  },

  disposeBatch(token: string, payload: DisposeBatchPayload) {
    return request<{ message: string; remaining_quantity: number }>("/inventory/dispose", {
      method: "POST",
      token,
      body: payload,
    });
  },

  getDevices(token: string, pharmacyId?: number) {
    const query = pharmacyId ? `?pharmacy_id=${pharmacyId}` : "";
    return request<IoTDevice[]>(`/iot/devices${query}`, { token });
  },

  createDevice(token: string, payload: CreateDevicePayload) {
    return request<IoTDevice>("/iot/devices", {
      method: "POST",
      token,
      body: payload,
    });
  },

  deleteDevice(token: string, deviceId: number) {
    return request<void>(`/iot/devices/${deviceId}`, {
      method: "DELETE",
      token,
    });
  },

  getSales(token: string, pharmacyId?: number) {
    const params = new URLSearchParams();
    params.set("limit", "100");
    if (pharmacyId) {
      params.set("pharmacy_id", String(pharmacyId));
    }
    return request<Sale[]>(`/sales/?${params.toString()}`, { token });
  },

  getSale(token: string, saleId: number) {
    return request<Sale>(`/sales/${saleId}`, { token });
  },

  createSale(token: string, payload: CreateSalePayload) {
    return request<Sale>("/sales/", {
      method: "POST",
      token,
      body: payload,
    });
  },

  getUsers(token: string, pharmacyId?: number) {
    const query = pharmacyId ? `?pharmacy_id=${pharmacyId}` : "";
    return request<User[]>(`/auth/users${query}`, { token });
  },

  createUser(token: string, payload: CreateUserPayload) {
    return request<User>("/auth/users", {
      method: "POST",
      token,
      body: payload,
    });
  },

  deleteUser(token: string, userId: number) {
    return request<void>(`/auth/users/${userId}`, {
      method: "DELETE",
      token,
    });
  },

  getAuditLogs(token: string, limit = 100) {
    return request<AuditLog[]>(`/admin/audit-logs?limit=${limit}`, { token });
  },
};

export function toUserMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 400:
        return error.detail || "Сервер відхилив запит.";
      case 401:
        return "Невірний email або пароль.";
      case 403:
        return "У вас недостатньо прав для цієї дії.";
      case 404:
        return "Потрібний endpoint або запис не знайдено на сервері.";
      default:
        return error.detail || `Сервер повернув помилку ${error.status}.`;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Сталася невідома помилка.";
}
