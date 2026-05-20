package com.example.pharmasmart.data.model

enum class AlertSeverity {
    CRITICAL,
    WARNING,
}

enum class UserRole {
    ADMIN,
    MANAGER,
    PHARMACIST,
}

data class UserProfile(
    val id: Int,
    val fullName: String,
    val email: String,
    val role: UserRole,
    val pharmacyId: Int?,
)

data class DashboardMetrics(
    val activeAlerts: Int,
    val onlinePharmacies: Int,
    val totalPharmacies: Int,
    val totalSalesOrders: Int,
    val totalStaff: Int,
    val revenueToday: String,
)

data class PharmacyAlert(
    val id: String,
    val title: String,
    val message: String,
    val severity: AlertSeverity,
    val pharmacyName: String,
    val storageLocation: String,
    val affectedMedicine: String,
    val temperature: Double,
    val humidity: Int,
    val minutesAgo: Int,
)

data class PharmacySummary(
    val id: String,
    val name: String,
    val address: String,
    val temperature: Double,
    val humidity: Int,
    val activeIncidents: Int,
    val expiringBatches: Int,
)
