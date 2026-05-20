package com.example.pharmasmart.data

import com.example.pharmasmart.data.model.AlertSeverity
import com.example.pharmasmart.data.model.DashboardMetrics
import com.example.pharmasmart.data.model.PharmacyAlert
import com.example.pharmasmart.data.model.PharmacySummary

class SamplePharmaSmartRepository {
    fun getDashboardMetrics(): DashboardMetrics = DashboardMetrics(
        activeAlerts = 4,
        onlinePharmacies = 5,
        totalPharmacies = 6,
        expiringBatches = 11,
        revenueToday = "₴48 250",
    )

    fun getAlerts(): List<PharmacyAlert> = listOf(
        PharmacyAlert(
            id = "alt-001",
            title = "Перегрів холодильного модуля",
            message = "Температура перевищила допустиму межу для термолабільних препаратів.",
            severity = AlertSeverity.CRITICAL,
            pharmacyName = "Аптека №12",
            storageLocation = "Холодильник A-1",
            affectedMedicine = "Інсулін",
            temperature = 9.4,
            humidity = 68,
            minutesAgo = 6,
        ),
        PharmacyAlert(
            id = "alt-002",
            title = "Нестабільна вологість",
            message = "Зафіксовано повторювані коливання вологості в зоні зберігання.",
            severity = AlertSeverity.WARNING,
            pharmacyName = "Аптека №7",
            storageLocation = "Склад B-2",
            affectedMedicine = "Вакцини",
            temperature = 4.8,
            humidity = 71,
            minutesAgo = 18,
        ),
        PharmacyAlert(
            id = "alt-003",
            title = "Ризик псування партії",
            message = "Після аварійного відключення живлення сенсор зафіксував тривале відхилення.",
            severity = AlertSeverity.CRITICAL,
            pharmacyName = "Аптека №3",
            storageLocation = "Холодильна камера C-4",
            affectedMedicine = "Адреналін",
            temperature = 10.1,
            humidity = 62,
            minutesAgo = 31,
        ),
        PharmacyAlert(
            id = "alt-004",
            title = "Понижений заряд датчика",
            message = "Рівень заряду сенсора наближається до критичного, потрібна перевірка.",
            severity = AlertSeverity.WARNING,
            pharmacyName = "Аптека №5",
            storageLocation = "Холодильник D-2",
            affectedMedicine = "Антибіотики",
            temperature = 5.1,
            humidity = 60,
            minutesAgo = 47,
        ),
    )

    fun getPharmacies(): List<PharmacySummary> = listOf(
        PharmacySummary(
            id = "ph-12",
            name = "Аптека №12",
            address = "Харків, вул. Науки, 14",
            temperature = 9.4,
            humidity = 68,
            activeIncidents = 2,
            expiringBatches = 4,
        ),
        PharmacySummary(
            id = "ph-07",
            name = "Аптека №7",
            address = "Харків, вул. Клочківська, 88",
            temperature = 4.8,
            humidity = 71,
            activeIncidents = 1,
            expiringBatches = 3,
        ),
        PharmacySummary(
            id = "ph-03",
            name = "Аптека №3",
            address = "Харків, просп. Героїв Харкова, 120",
            temperature = 10.1,
            humidity = 62,
            activeIncidents = 1,
            expiringBatches = 2,
        ),
        PharmacySummary(
            id = "ph-05",
            name = "Аптека №5",
            address = "Харків, вул. Сумська, 51",
            temperature = 5.1,
            humidity = 60,
            activeIncidents = 0,
            expiringBatches = 2,
        ),
    )
}
