package com.example.pharmasmart.network

data class LoginResponse(
    val access_token: String,
    val token_type: String,
)

data class CurrentUserDto(
    val id: Int,
    val email: String,
    val full_name: String,
    val role: String,
    val pharmacy_id: Int?,
    val is_active: Boolean,
)

data class DashboardStatsDto(
    val pharmacy_filter: String,
    val total_sales_orders: Int,
    val total_revenue: Double,
    val active_alerts: Int,
    val total_staff: Int,
)

data class ActiveAlertDto(
    val id: Int,
    val device_id: Int,
    val severity: String,
    val message: String,
    val is_resolved: Boolean,
    val created_at: String,
    val pharmacy_name: String?,
    val storage_location_name: String?,
    val device_serial_number: String?,
    val latest_temperature: Double?,
    val latest_humidity: Double?,
)

data class IncidentHistoryDto(
    val id: Int,
    val action: String,
    val headline: String,
    val message: String,
    val created_at: String,
    val pharmacy_name: String?,
    val storage_location_name: String?,
    val device_serial_number: String?,
    val actor_name: String?,
    val alert_id: Int?,
)

data class StorageLocationDto(
    val id: Int,
    val pharmacy_id: Int,
    val name: String,
    val description: String?,
    val is_refrigerated: Boolean,
)

data class PharmacyDto(
    val id: Int,
    val name: String,
    val address: String,
    val license_number: String,
    val license_expiry_date: String?,
    val phone: String?,
    val active_alerts: Int = 0,
    val latest_temperature: Double? = null,
    val latest_humidity: Double? = null,
    val storage_locations: List<StorageLocationDto> = emptyList(),
)
