package com.example.pharmasmart

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.pharmasmart.data.BackendPharmaSmartRepository
import com.example.pharmasmart.data.SamplePharmaSmartRepository
import com.example.pharmasmart.data.model.AlertSeverity
import com.example.pharmasmart.data.model.DashboardMetrics
import com.example.pharmasmart.data.model.PharmacyAlert
import com.example.pharmasmart.data.model.PharmacySummary
import com.example.pharmasmart.data.model.UserProfile
import com.example.pharmasmart.data.model.UserRole
import com.example.pharmasmart.ui.theme.PharmasmartTheme
import kotlinx.coroutines.launch

private const val DEFAULT_BACKEND_URL = "https://pharmasmart-ej5n.onrender.com"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            PharmasmartTheme {
                PharmaSmartApp()
            }
        }
    }
}

private enum class AppDestination(val title: String) {
    Dashboard("Огляд"),
    Alerts("Тривоги"),
    Pharmacies("Аптеки"),
}

private enum class AlertFilter(val label: String) {
    All("Усі"),
    Critical("Критичні"),
    Warning("Попередження"),
}

private data class RemoteSnapshot(
    val token: String,
    val user: UserProfile,
    val metrics: DashboardMetrics,
    val alerts: List<PharmacyAlert>,
    val pharmacies: List<PharmacySummary>,
)

@Composable
fun PharmaSmartApp(modifier: Modifier = Modifier) {
    val sampleRepository = remember { SamplePharmaSmartRepository() }
    val scope = rememberCoroutineScope()

    var isLoggedIn by rememberSaveable { mutableStateOf(false) }
    var isLoading by rememberSaveable { mutableStateOf(false) }
    var currentDestination by rememberSaveable { mutableStateOf(AppDestination.Dashboard) }
    var selectedAlertId by rememberSaveable { mutableStateOf<String?>(null) }
    var authToken by rememberSaveable { mutableStateOf<String?>(null) }
    var currentUser by remember { mutableStateOf<UserProfile?>(null) }
    var serverUrl by rememberSaveable { mutableStateOf(DEFAULT_BACKEND_URL) }
    var loginError by rememberSaveable { mutableStateOf<String?>(null) }
    var screenMessage by rememberSaveable { mutableStateOf<String?>(null) }

    var alerts by remember { mutableStateOf(sampleRepository.getAlerts()) }
    var pharmacies by remember { mutableStateOf(sampleRepository.getPharmacies()) }
    var metrics by remember { mutableStateOf(sampleRepository.getDashboardMetrics()) }

    fun applySnapshot(snapshot: RemoteSnapshot) {
        val enrichedPharmacies = snapshot.pharmacies.map { pharmacy ->
            val pharmacyAlerts = snapshot.alerts.filter { it.pharmacyName == pharmacy.name }
            pharmacy.copy(
                activeIncidents = pharmacyAlerts.size,
                temperature = pharmacyAlerts.firstOrNull { it.temperature != 0.0 }?.temperature ?: pharmacy.temperature,
                humidity = pharmacyAlerts.firstOrNull { it.humidity != 0 }?.humidity ?: pharmacy.humidity,
            )
        }

        authToken = snapshot.token
        currentUser = snapshot.user
        alerts = snapshot.alerts
        pharmacies = enrichedPharmacies
        metrics = snapshot.metrics.copy(
            onlinePharmacies = enrichedPharmacies.size,
            totalPharmacies = enrichedPharmacies.size,
        )
    }

    fun logout() {
        isLoggedIn = false
        isLoading = false
        authToken = null
        currentUser = null
        selectedAlertId = null
        currentDestination = AppDestination.Dashboard
        loginError = null
        screenMessage = null
        alerts = sampleRepository.getAlerts()
        pharmacies = sampleRepository.getPharmacies()
        metrics = sampleRepository.getDashboardMetrics()
    }

    Surface(
        modifier = modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        if (!isLoggedIn) {
            LoginScreen(
                serverUrl = serverUrl,
                isLoading = isLoading,
                errorMessage = loginError,
                onServerUrlChange = {
                    serverUrl = it
                    loginError = null
                },
                onLogin = { email, password ->
                    if (email.isBlank() || password.isBlank()) {
                        loginError = "Вкажіть email і пароль."
                        return@LoginScreen
                    }

                    val normalizedUrl = serverUrl.trim().ifBlank { DEFAULT_BACKEND_URL }
                    isLoading = true
                    loginError = null

                    scope.launch {
                        val repository = BackendPharmaSmartRepository(normalizedUrl)
                        runCatching {
                            val token = repository.login(email.trim(), password)
                            val user = repository.getCurrentUser(token)
                            val fetchedAlerts = repository.getAlerts(token)
                            val fetchedPharmacies = repository.getPharmacies(token)
                            val fetchedMetrics = if (user.role == UserRole.PHARMACIST) {
                                DashboardMetrics(
                                    activeAlerts = fetchedAlerts.size,
                                    onlinePharmacies = 0,
                                    totalPharmacies = 0,
                                    totalSalesOrders = 0,
                                    totalStaff = 0,
                                    revenueToday = "—",
                                )
                            } else {
                                repository.getDashboardMetrics(token)
                            }
                            RemoteSnapshot(
                                token = token,
                                user = user,
                                metrics = fetchedMetrics,
                                alerts = fetchedAlerts,
                                pharmacies = fetchedPharmacies,
                            )
                        }.onSuccess { snapshot ->
                            serverUrl = normalizedUrl
                            applySnapshot(snapshot)
                            currentDestination = if (snapshot.user.role == UserRole.PHARMACIST) {
                                AppDestination.Alerts
                            } else {
                                AppDestination.Dashboard
                            }
                            isLoggedIn = true
                            screenMessage = null
                        }.onFailure { error ->
                            loginError = repository.toUserMessage(error)
                        }
                        isLoading = false
                    }
                },
            )
            return@Surface
        }

        val selectedAlert = alerts.firstOrNull { it.id == selectedAlertId }

        Scaffold(
            topBar = {
                AppTopBar(
                    title = selectedAlert?.let { "Інцидент" } ?: currentDestination.title,
                    onBack = if (selectedAlert != null) ({ selectedAlertId = null }) else null,
                    user = currentUser,
                    isRefreshing = isLoading,
                    onRefresh = if (selectedAlert == null && authToken != null) ({
                        val token = authToken ?: return@AppTopBar
                        isLoading = true
                        screenMessage = null
                        scope.launch {
                            val repository = BackendPharmaSmartRepository(serverUrl)
                            runCatching {
                                val user = currentUser ?: repository.getCurrentUser(token)
                                RemoteSnapshot(
                                    token = token,
                                    user = user,
                                    metrics = if (user.role == UserRole.PHARMACIST) {
                                        DashboardMetrics(
                                            activeAlerts = alerts.size,
                                            onlinePharmacies = 0,
                                            totalPharmacies = 0,
                                            totalSalesOrders = 0,
                                            totalStaff = 0,
                                            revenueToday = "—",
                                        )
                                    } else {
                                        repository.getDashboardMetrics(token)
                                    },
                                    alerts = repository.getAlerts(token),
                                    pharmacies = repository.getPharmacies(token),
                                )
                            }.onSuccess { snapshot ->
                                applySnapshot(snapshot)
                                if (selectedAlertId != null && alerts.none { it.id == selectedAlertId }) {
                                    selectedAlertId = null
                                }
                            }.onFailure { error ->
                                screenMessage = repository.toUserMessage(error)
                            }
                            isLoading = false
                        }
                    }) else null,
                    onLogout = { logout() },
                )
            },
            bottomBar = {
                if (selectedAlert == null) {
                    AppBottomBar(
                        currentDestination = currentDestination,
                        userRole = currentUser?.role ?: UserRole.MANAGER,
                        onSelect = { currentDestination = it },
                    )
                }
            },
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            ) {
                when {
                    selectedAlert != null -> AlertDetailsScreen(
                        alert = selectedAlert,
                        userRole = currentUser?.role,
                        onResolve = if (authToken != null && currentUser?.role != UserRole.PHARMACIST) ({
                            val token = authToken ?: return@AlertDetailsScreen
                            isLoading = true
                            scope.launch {
                                val repository = BackendPharmaSmartRepository(serverUrl)
                                runCatching {
                                    repository.resolveAlert(token, selectedAlert.id)
                                    repository.getAlerts(token)
                                }.onSuccess { fetchedAlerts ->
                                    alerts = fetchedAlerts
                                    selectedAlertId = null
                                    screenMessage = "Інцидент успішно закрито."
                                }.onFailure { error ->
                                    screenMessage = repository.toUserMessage(error)
                                }
                                isLoading = false
                            }
                        }) else null,
                        modifier = Modifier.fillMaxSize(),
                    )

                    currentDestination == AppDestination.Dashboard && currentUser?.role != UserRole.PHARMACIST -> DashboardScreen(
                        metrics = metrics,
                        topAlerts = alerts.take(3),
                        message = screenMessage,
                        user = currentUser,
                        onAlertClick = { selectedAlertId = it.id },
                        modifier = Modifier.fillMaxSize(),
                    )

                    currentDestination == AppDestination.Alerts -> AlertsScreen(
                        alerts = alerts,
                        message = screenMessage,
                        user = currentUser,
                        onAlertClick = { selectedAlertId = it.id },
                        modifier = Modifier.fillMaxSize(),
                    )

                    currentDestination == AppDestination.Pharmacies -> PharmaciesScreen(
                        pharmacies = pharmacies,
                        message = screenMessage,
                        user = currentUser,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun AppPreview() {
    PharmasmartTheme {
        PharmaSmartApp()
    }
}

@Composable
private fun LoginScreen(
    serverUrl: String,
    isLoading: Boolean,
    errorMessage: String?,
    onServerUrlChange: (String) -> Unit,
    onLogin: (String, String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var email by rememberSaveable { mutableStateOf("manager@pharmasmart.ua") }
    var password by rememberSaveable { mutableStateOf("pharma123") }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surfaceContainerLowest)
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(28.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp),
            ) {
                BrandHeader()
                Text(
                    text = "Мобільний центр керування аптечною мережею",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedTextField(
                    value = serverUrl,
                    onValueChange = onServerUrlChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Server URL") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                )
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Email") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Пароль") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    visualTransformation = PasswordVisualTransformation(),
                )
                if (errorMessage != null) {
                    InlineMessage(
                        message = errorMessage,
                        isError = true,
                    )
                }
                Button(
                    onClick = { onLogin(email, password) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    enabled = !isLoading,
                ) {
                    if (isLoading) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(18.dp),
                                color = MaterialTheme.colorScheme.onPrimary,
                                strokeWidth = 2.dp,
                            )
                            Text("Підключення...")
                        }
                    } else {
                        Text("Увійти до системи")
                    }
                }
                Text(
                    text = "За замовчуванням використовується hosted backend на Render. Для локальної розробки можна вказати свій URL.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun BrandHeader() {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Box(
            modifier = Modifier
                .size(56.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(MaterialTheme.colorScheme.primaryContainer),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = "P",
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                fontWeight = FontWeight.Bold,
            )
        }
        Column {
            Text(
                text = "PharmaSmart",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "IoT-моніторинг аптек",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AppTopBar(
    title: String,
    onBack: (() -> Unit)?,
    user: UserProfile?,
    isRefreshing: Boolean,
    onRefresh: (() -> Unit)?,
    onLogout: () -> Unit,
) {
    TopAppBar(
        title = {
            Column {
                Text(
                    text = title,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (user != null) {
                    Text(
                        text = "${user.fullName} • ${user.role.displayName()}",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        },
        navigationIcon = {
            if (onBack != null) {
                TextButton(onClick = onBack) {
                    Text("Назад")
                }
            }
        },
        actions = {
            if (onBack == null) {
                if (onRefresh != null) {
                    TextButton(onClick = onRefresh, enabled = !isRefreshing) {
                        if (isRefreshing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = MaterialTheme.colorScheme.primary,
                                strokeWidth = 2.dp,
                            )
                        } else {
                            Text("Оновити")
                        }
                    }
                }
                TextButton(onClick = onLogout) {
                    Text("Вийти")
                }
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    )
}

@Composable
private fun AppBottomBar(
    currentDestination: AppDestination,
    userRole: UserRole,
    onSelect: (AppDestination) -> Unit,
) {
    val destinations = if (userRole == UserRole.PHARMACIST) {
        listOf(AppDestination.Alerts, AppDestination.Pharmacies)
    } else {
        AppDestination.entries.toList()
    }
    NavigationBar {
        destinations.forEach { destination ->
            NavigationBarItem(
                selected = destination == currentDestination,
                onClick = { onSelect(destination) },
                icon = {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(
                                if (destination == currentDestination) {
                                    MaterialTheme.colorScheme.primary
                                } else {
                                    MaterialTheme.colorScheme.outline
                                },
                            ),
                    )
                },
                label = { Text(destination.title) },
            )
        }
    }
}

@Composable
private fun DashboardScreen(
    metrics: DashboardMetrics,
    topAlerts: List<PharmacyAlert>,
    message: String?,
    user: UserProfile?,
    onAlertClick: (PharmacyAlert) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = if (user?.role == UserRole.ADMIN) "Мережа під контролем" else "Оперативна зведенка",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "Оперативна інформація щодо аптек, датчиків та інцидентів зберігання.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            MetricsGrid(metrics = metrics)
        }
        if (message != null) {
            item {
                InlineMessage(message = message)
            }
        }
        item {
            SectionTitle(
                title = "Критичні події",
                subtitle = "Останні події, які потребують реакції керівника або завідувача.",
            )
        }
        if (topAlerts.isEmpty()) {
            item {
                EmptyStateCard(
                    title = "Активних тривог немає",
                    subtitle = "Система не зафіксувала критичних подій у доступних аптеках.",
                )
            }
        } else {
            items(topAlerts, key = { it.id }) { alert ->
                AlertCard(alert = alert, onClick = { onAlertClick(alert) })
            }
        }
        item {
            Spacer(modifier = Modifier.height(12.dp))
        }
    }
}

@Composable
private fun MetricsGrid(metrics: DashboardMetrics) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            MetricCard(
                title = "Активні тривоги",
                value = metrics.activeAlerts.toString(),
                modifier = Modifier.weight(1f),
                accentColor = MaterialTheme.colorScheme.errorContainer,
            )
            MetricCard(
                title = "Аптеки",
                value = "${metrics.onlinePharmacies}/${metrics.totalPharmacies}",
                modifier = Modifier.weight(1f),
                accentColor = MaterialTheme.colorScheme.primaryContainer,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            MetricCard(
                title = "Замовлення",
                value = metrics.totalSalesOrders.toString(),
                modifier = Modifier.weight(1f),
                accentColor = MaterialTheme.colorScheme.secondaryContainer,
            )
            MetricCard(
                title = "Персонал",
                value = metrics.totalStaff.toString(),
                modifier = Modifier.weight(1f),
                accentColor = MaterialTheme.colorScheme.tertiaryContainer,
            )
        }
        MetricCard(
            title = "Виторг",
            value = metrics.revenueToday,
            modifier = Modifier.fillMaxWidth(),
            accentColor = MaterialTheme.colorScheme.surfaceContainerHigh,
        )
    }
}

@Composable
private fun MetricCard(
    title: String,
    value: String,
    modifier: Modifier = Modifier,
    accentColor: Color,
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = accentColor),
        shape = RoundedCornerShape(24.dp),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Text(
                text = value,
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}

@Composable
private fun AlertsScreen(
    alerts: List<PharmacyAlert>,
    message: String?,
    user: UserProfile?,
    onAlertClick: (PharmacyAlert) -> Unit,
    modifier: Modifier = Modifier,
) {
    var filter by rememberSaveable { mutableStateOf(AlertFilter.All) }
    val filteredAlerts = alerts.filter { alert ->
        when (filter) {
            AlertFilter.All -> true
            AlertFilter.Critical -> alert.severity == AlertSeverity.CRITICAL
            AlertFilter.Warning -> alert.severity == AlertSeverity.WARNING
        }
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            SectionTitle(
                title = "Моніторинг інцидентів",
                subtitle = if (user?.role == UserRole.PHARMACIST) {
                    "Інциденти, що стосуються вашої аптеки."
                } else {
                    "Список актуальних відхилень температури та вологості в місцях зберігання."
                },
            )
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AlertFilter.entries.forEach { option ->
                    FilterChip(
                        selected = option == filter,
                        onClick = { filter = option },
                        label = { Text(option.label) },
                    )
                }
            }
        }
        if (message != null) {
            item {
                InlineMessage(message = message)
            }
        }
        if (filteredAlerts.isEmpty()) {
            item {
                EmptyStateCard(
                    title = "Немає інцидентів для цього фільтра",
                    subtitle = "Спробуйте змінити фільтр або оновити дані з сервера.",
                )
            }
        } else {
            items(filteredAlerts, key = { it.id }) { alert ->
                AlertCard(alert = alert, onClick = { onAlertClick(alert) })
            }
        }
        item {
            Spacer(modifier = Modifier.height(12.dp))
        }
    }
}

@Composable
private fun AlertCard(
    alert: PharmacyAlert,
    onClick: () -> Unit,
) {
    val severityColor = when (alert.severity) {
        AlertSeverity.CRITICAL -> MaterialTheme.colorScheme.errorContainer
        AlertSeverity.WARNING -> MaterialTheme.colorScheme.secondaryContainer
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = alert.title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                Spacer(modifier = Modifier.width(12.dp))
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(severityColor)
                        .padding(horizontal = 10.dp, vertical = 6.dp),
                ) {
                    Text(
                        text = if (alert.severity == AlertSeverity.CRITICAL) "Критично" else "Увага",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Text(
                text = "${alert.pharmacyName} • ${alert.storageLocation}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = alert.message,
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                text = if (alert.temperature == 0.0 && alert.humidity == 0) {
                    "Дані сенсора тимчасово недоступні"
                } else {
                    "Температура ${alert.temperature}°C • Вологість ${alert.humidity}%"
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = "${alert.minutesAgo} хв тому",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
            )
        }
    }
}

@Composable
private fun AlertDetailsScreen(
    alert: PharmacyAlert,
    userRole: UserRole?,
    onResolve: (() -> Unit)?,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = alert.title,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "${alert.pharmacyName} • ${alert.storageLocation}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            DetailCard(
                title = "Опис інциденту",
                lines = listOf(
                    alert.message,
                    "Час виникнення: ${alert.minutesAgo} хв тому",
                    if (alert.temperature == 0.0 && alert.humidity == 0) {
                        "Поточні показники: сенсорні дані недоступні"
                    } else {
                        "Поточні показники: ${alert.temperature}°C / ${alert.humidity}%"
                    },
                ),
            )
        }
        item {
            DetailCard(
                title = "Рекомендовані дії",
                lines = listOf(
                    "1. Перевірити стан холодильного обладнання.",
                    "2. Оцінити ризик для партій препарату ${alert.affectedMedicine}.",
                    "3. Зафіксувати результат перевірки в журналі інцидентів.",
                ),
            )
        }
        item {
            if (userRole == UserRole.PHARMACIST) {
                InlineMessage(
                    message = "Фармацевт може переглядати інцидент та передавати інформацію завідувачу або адміністратору.",
                )
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Button(
                        onClick = { onResolve?.invoke() },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(16.dp),
                    ) {
                        Text("Закрити інцидент")
                    }
                    OutlinedButton(
                        onClick = {},
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(16.dp),
                    ) {
                        Text("Ескалувати")
                    }
                }
            }
        }
        item {
            Spacer(modifier = Modifier.height(12.dp))
        }
    }
}

@Composable
private fun DetailCard(
    title: String,
    lines: List<String>,
) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            lines.forEach { line ->
                Text(
                    text = line,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun PharmaciesScreen(
    pharmacies: List<PharmacySummary>,
    message: String?,
    user: UserProfile?,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            SectionTitle(
                title = "Аптечна мережа",
                subtitle = if (user?.role == UserRole.PHARMACIST) {
                    "Інформація щодо аптеки, до якої прив'язаний користувач."
                } else {
                    "Зведена інформація щодо об'єктів, сенсорів і ризиків по кожній аптеці."
                },
            )
        }
        if (message != null) {
            item {
                InlineMessage(message = message)
            }
        }
        if (pharmacies.isEmpty()) {
            item {
                EmptyStateCard(
                    title = "Аптеки не знайдені",
                    subtitle = "Користувач не прив'язаний до аптеки або сервер ще не має даних.",
                )
            }
        } else {
            items(pharmacies, key = { it.id }) { pharmacy ->
                PharmacyCard(pharmacy = pharmacy)
            }
        }
        item {
            Spacer(modifier = Modifier.height(12.dp))
        }
    }
}

@Composable
private fun PharmacyCard(pharmacy: PharmacySummary) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = pharmacy.name,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = pharmacy.address,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                CompactMetric(
                    label = "T",
                    value = if (pharmacy.temperature == 0.0) "--" else "${pharmacy.temperature}°C",
                )
                CompactMetric(
                    label = "H",
                    value = if (pharmacy.humidity == 0) "--" else "${pharmacy.humidity}%",
                )
                CompactMetric(
                    label = "Інциденти",
                    value = pharmacy.activeIncidents.toString(),
                )
            }
            Text(
                text = "Партій із ризиком списання: ${pharmacy.expiringBatches}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun CompactMetric(label: String, value: String) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surfaceContainerHigh)
            .padding(horizontal = 12.dp, vertical = 10.dp),
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun SectionTitle(
    title: String,
    subtitle: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = subtitle,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun InlineMessage(
    message: String,
    isError: Boolean = false,
) {
    val containerColor = if (isError) {
        MaterialTheme.colorScheme.errorContainer
    } else {
        MaterialTheme.colorScheme.secondaryContainer
    }
    val textColor = if (isError) {
        MaterialTheme.colorScheme.onErrorContainer
    } else {
        MaterialTheme.colorScheme.onSecondaryContainer
    }

    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = containerColor),
    ) {
        Text(
            text = message,
            modifier = Modifier.padding(16.dp),
            style = MaterialTheme.typography.bodyMedium,
            color = textColor,
        )
    }
}

@Composable
private fun EmptyStateCard(
    title: String,
    subtitle: String,
) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private fun UserRole.displayName(): String = when (this) {
    UserRole.ADMIN -> "Адміністратор"
    UserRole.MANAGER -> "Завідувач"
    UserRole.PHARMACIST -> "Фармацевт"
}
