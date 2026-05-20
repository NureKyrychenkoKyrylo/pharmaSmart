package com.example.pharmasmart.data

import com.example.pharmasmart.data.model.AlertSeverity
import com.example.pharmasmart.data.model.DashboardMetrics
import com.example.pharmasmart.data.model.PharmacyAlert
import com.example.pharmasmart.data.model.PharmacySummary
import com.example.pharmasmart.network.PharmaSmartApiFactory
import kotlin.math.roundToInt

class BackendPharmaSmartRepository(
    private val baseUrl: String,
) {
    private val api = PharmaSmartApiFactory.create(baseUrl)

    suspend fun login(email: String, password: String): String {
        return api.login(email, password).access_token
    }

    suspend fun getDashboardMetrics(token: String): DashboardMetrics {
        val dto = api.getDashboardStats("Bearer $token")
        return DashboardMetrics(
            activeAlerts = dto.active_alerts,
            onlinePharmacies = 0,
            totalPharmacies = 0,
            expiringBatches = 0,
            revenueToday = "₴${dto.total_revenue.roundToInt()}",
        )
    }

    suspend fun getAlerts(token: String): List<PharmacyAlert> {
        return api.getAlerts("Bearer $token").map { dto ->
            PharmacyAlert(
                id = dto.id.toString(),
                title = when (dto.severity.lowercase()) {
                    "critical" -> "Критичний інцидент"
                    else -> "Попередження системи"
                },
                message = dto.message,
                severity = if (dto.severity.lowercase() == "critical") {
                    AlertSeverity.CRITICAL
                } else {
                    AlertSeverity.WARNING
                },
                pharmacyName = dto.pharmacy_name ?: "Невідома аптека",
                storageLocation = dto.storage_location_name ?: "Невідома локація",
                affectedMedicine = extractMedicineName(dto.message),
                temperature = dto.latest_temperature ?: 0.0,
                humidity = (dto.latest_humidity ?: 0.0).roundToInt(),
                minutesAgo = 0,
            )
        }
    }

    suspend fun getPharmacies(token: String): List<PharmacySummary> {
        return api.getPharmacies("Bearer $token").map { dto ->
            PharmacySummary(
                id = dto.id.toString(),
                name = dto.name,
                address = dto.address,
                temperature = 0.0,
                humidity = 0,
                activeIncidents = 0,
                expiringBatches = 0,
            )
        }
    }

    private fun extractMedicineName(message: String): String {
        return message.substringAfter("Critical:", "")
            .substringBefore("->")
            .trim()
            .ifBlank { "Препарат" }
    }
}
