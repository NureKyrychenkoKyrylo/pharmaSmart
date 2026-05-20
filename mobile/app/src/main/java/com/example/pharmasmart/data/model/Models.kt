package com.example.pharmasmart.data.model

enum class AlertSeverity {
    CRITICAL,
    WARNING,
}

data class DashboardMetrics(
    val activeAlerts: Int,
    val onlinePharmacies: Int,
    val totalPharmacies: Int,
    val expiringBatches: Int,
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
