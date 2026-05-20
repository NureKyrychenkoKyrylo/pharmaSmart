package com.example.pharmasmart.data

import com.example.pharmasmart.data.model.AlertSeverity
import com.example.pharmasmart.data.model.DashboardMetrics
import com.example.pharmasmart.data.model.IncidentHistoryEntry
import com.example.pharmasmart.data.model.PharmacyAlert
import com.example.pharmasmart.data.model.PharmacySummary
import com.example.pharmasmart.data.model.UserProfile
import com.example.pharmasmart.data.model.UserRole
import com.example.pharmasmart.network.PharmaSmartApiFactory
import retrofit2.HttpException
import java.io.IOException
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.temporal.ChronoUnit
import kotlin.math.roundToInt

class BackendPharmaSmartRepository(
    private val baseUrl: String,
) {
    private val api = PharmaSmartApiFactory.create(baseUrl)

    suspend fun login(email: String, password: String): String {
        return api.login(email, password).access_token
    }

    suspend fun getCurrentUser(token: String): UserProfile {
        val dto = api.getCurrentUser("Bearer $token")
        return UserProfile(
            id = dto.id,
            fullName = dto.full_name,
            email = dto.email,
            role = when (dto.role.lowercase()) {
                "admin" -> UserRole.ADMIN
                "manager" -> UserRole.MANAGER
                else -> UserRole.PHARMACIST
            },
            pharmacyId = dto.pharmacy_id,
        )
    }

    suspend fun getDashboardMetrics(token: String): DashboardMetrics {
        val dto = api.getDashboardStats("Bearer $token")
        return DashboardMetrics(
            activeAlerts = dto.active_alerts,
            onlinePharmacies = 0,
            totalPharmacies = 0,
            totalSalesOrders = dto.total_sales_orders,
            totalStaff = dto.total_staff,
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
                createdAt = dto.created_at,
                minutesAgo = calculateMinutesAgo(dto.created_at),
            )
        }
    }

    suspend fun getIncidentHistory(token: String): List<IncidentHistoryEntry> {
        return runCatching {
            api.getIncidentHistory("Bearer $token").map { dto ->
                IncidentHistoryEntry(
                    id = dto.id.toString(),
                    action = dto.action,
                    headline = dto.headline,
                    message = dto.message,
                    pharmacyName = dto.pharmacy_name ?: "Невідома аптека",
                    storageLocation = dto.storage_location_name ?: "Невідома локація",
                    deviceSerialNumber = dto.device_serial_number,
                    actorName = dto.actor_name ?: "Система",
                    createdAt = dto.created_at,
                    alertId = dto.alert_id?.toString(),
                )
            }
        }.recoverCatching { error ->
            if (error is HttpException && error.code() == 404) {
                emptyList()
            } else {
                throw error
            }
        }.getOrThrow()
    }

    suspend fun getPharmacies(token: String): List<PharmacySummary> {
        return api.getPharmacies("Bearer $token").map { dto ->
            PharmacySummary(
                id = dto.id.toString(),
                name = dto.name,
                address = dto.address,
                temperature = dto.latest_temperature ?: 0.0,
                humidity = (dto.latest_humidity ?: 0.0).roundToInt(),
                activeIncidents = dto.active_alerts,
                expiringBatches = 0,
            )
        }
    }

    suspend fun resolveAlert(token: String, alertId: String) {
        api.resolveAlert(alertId.toInt(), "Bearer $token")
    }

    suspend fun escalateAlert(token: String, alertId: String) {
        runCatching {
            api.escalateAlert(alertId.toInt(), "Bearer $token")
        }.getOrElse { error ->
            if (error is HttpException && error.code() == 404) {
                throw UnsupportedOperationException(
                    "Поточна версія сервера ще не підтримує ескалацію інцидентів. Потрібен повторний деплой backend."
                )
            }
            throw error
        }
    }

    private fun extractMedicineName(message: String): String {
        val quotedName = "«([^»]+)»".toRegex().find(message)?.groupValues?.getOrNull(1)
        if (!quotedName.isNullOrBlank()) {
            return quotedName
        }
        return message.substringAfter("Critical:", "")
            .substringBefore("->")
            .trim()
            .ifBlank { "Препарат" }
    }

    fun toUserMessage(error: Throwable): String {
        return when (error) {
            is HttpException -> when (error.code()) {
                401 -> "Невірний email або пароль."
                403 -> "У користувача недостатньо прав для цього розділу."
                404 -> "Backend не знайшов потрібний endpoint. Перевірте URL сервера."
                else -> "Сервер повернув помилку ${error.code()}."
            }
            is IOException -> "Не вдалося підключитися до backend. Перевірте інтернет або адресу сервера."
            is UnsupportedOperationException -> error.message ?: "Функція тимчасово недоступна на цьому сервері."
            else -> error.message ?: "Сталася невідома помилка."
        }
    }

    private fun calculateMinutesAgo(createdAt: String): Int {
        return runCatching {
            val created = parseApiDate(createdAt)
            val now = OffsetDateTime.now(ZoneOffset.UTC)
            ChronoUnit.MINUTES.between(created, now).toInt().coerceAtLeast(0)
        }.getOrDefault(0)
    }

    private fun parseApiDate(createdAt: String): OffsetDateTime {
        return runCatching { OffsetDateTime.parse(createdAt) }
            .getOrElse {
                LocalDateTime.parse(createdAt).atOffset(ZoneOffset.UTC)
            }
    }
}
