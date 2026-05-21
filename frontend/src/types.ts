export type UserRole = "admin" | "manager" | "pharmacist";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  pharmacy_id: number | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface DashboardStats {
  pharmacy_filter: number | "All Network";
  total_sales_orders: number;
  total_revenue: number;
  active_alerts: number;
  total_staff: number;
}

export interface StorageLocation {
  id: number;
  pharmacy_id: number;
  name: string;
  description: string | null;
  is_refrigerated: boolean;
}

export interface Pharmacy {
  id: number;
  name: string;
  address: string;
  license_number: string;
  license_expiry_date: string | null;
  phone: string | null;
  created_at: string;
  active_alerts: number;
  latest_temperature: number | null;
  latest_humidity: number | null;
  storage_locations: StorageLocation[];
}

export interface Medicine {
  id: number;
  name: string;
  manufacturer: string | null;
  description: string | null;
  min_temperature: number;
  max_temperature: number;
  min_humidity: number;
  max_humidity: number;
  is_prescription: boolean;
  requires_smart_lock: boolean;
  created_at: string;
}

export interface Batch {
  id: number;
  medicine_id: number;
  storage_location_id: number;
  batch_number: string;
  initial_quantity: number;
  current_quantity: number;
  expiration_date: string;
  arrival_date: string;
}

export interface IoTDevice {
  id: number;
  serial_number: string;
  device_type: string;
  status: string;
  storage_location_id: number | null;
  last_seen: string | null;
}

export interface ActiveAlert {
  id: number;
  device_id: number;
  severity: string;
  message: string;
  is_resolved: boolean;
  created_at: string;
  pharmacy_name: string | null;
  storage_location_name: string | null;
  device_serial_number: string | null;
  latest_temperature: number | null;
  latest_humidity: number | null;
}

export interface IncidentHistoryEntry {
  id: number;
  action: string;
  headline: string;
  message: string;
  created_at: string;
  pharmacy_name: string | null;
  storage_location_name: string | null;
  device_serial_number: string | null;
  actor_name: string | null;
  alert_id: number | null;
}

export interface SaleItem {
  id: number;
  batch_id: number;
  quantity: number;
  price_at_moment: number;
}

export interface Sale {
  id: number;
  pharmacy_id: number;
  seller_id: number | null;
  total_amount: number;
  status: string;
  created_at: string;
  items: SaleItem[];
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  details: unknown;
  created_at: string;
}

export interface CreateUserPayload {
  email: string;
  full_name: string;
  role: UserRole;
  pharmacy_id: number | null;
  is_active: boolean;
  password: string;
}

export interface CreatePharmacyPayload {
  name: string;
  address: string;
  license_number: string;
  license_expiry_date: string | null;
  phone: string | null;
}

export interface CreateLocationPayload {
  name: string;
  description: string | null;
  is_refrigerated: boolean;
  pharmacy_id: number;
}

export interface CreateMedicinePayload {
  name: string;
  manufacturer: string | null;
  description: string | null;
  min_temperature: number;
  max_temperature: number;
  min_humidity: number;
  max_humidity: number;
  is_prescription: boolean;
  requires_smart_lock: boolean;
}

export interface CreateBatchPayload {
  batch_number: string;
  initial_quantity: number;
  current_quantity: number;
  expiration_date: string;
  medicine_id: number;
  storage_location_id: number;
}

export interface DisposeBatchPayload {
  batch_id: number;
  quantity: number;
  reason: string;
}

export interface CreateDevicePayload {
  serial_number: string;
  device_type: string;
  status: string;
  storage_location_id: number;
}

export interface CreateSaleItemPayload {
  batch_id: number;
  quantity: number;
  price_per_unit: number;
}

export interface CreateSalePayload {
  items: CreateSaleItemPayload[];
}
