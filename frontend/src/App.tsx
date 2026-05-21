import { ReactNode, useEffect, useState } from "react";
import { api, toUserMessage } from "./api";
import type {
  ActiveAlert,
  AuditLog,
  Batch,
  DashboardStats,
  IncidentHistoryEntry,
  IoTDevice,
  Medicine,
  Pharmacy,
  Sale,
  StorageLocation,
  User,
  UserRole,
} from "./types";

type ViewKey =
  | "dashboard"
  | "alerts"
  | "history"
  | "pharmacies"
  | "locations"
  | "devices"
  | "inventory"
  | "sales"
  | "staff"
  | "audit";

type Notice = {
  tone: "success" | "error";
  text: string;
};

const SESSION_KEY = "pharmasmart-web-token";

const navByRole: Record<UserRole, Array<{ key: ViewKey; label: string }>> = {
  admin: [
    { key: "dashboard", label: "Огляд" },
    { key: "alerts", label: "Тривоги" },
    { key: "history", label: "Журнал інцидентів" },
    { key: "pharmacies", label: "Аптеки" },
    { key: "locations", label: "Місця зберігання" },
    { key: "devices", label: "Датчики" },
    { key: "inventory", label: "Склад" },
    { key: "sales", label: "Продажі" },
    { key: "staff", label: "Співробітники" },
    { key: "audit", label: "Аудит" },
  ],
  manager: [
    { key: "dashboard", label: "Огляд" },
    { key: "alerts", label: "Тривоги" },
    { key: "history", label: "Журнал інцидентів" },
    { key: "pharmacies", label: "Моя аптека" },
    { key: "locations", label: "Місця зберігання" },
    { key: "devices", label: "Датчики" },
    { key: "inventory", label: "Склад" },
    { key: "sales", label: "Продажі" },
    { key: "staff", label: "Співробітники" },
  ],
  pharmacist: [
    { key: "alerts", label: "Тривоги" },
    { key: "history", label: "Журнал інцидентів" },
    { key: "pharmacies", label: "Моя аптека" },
    { key: "inventory", label: "Склад" },
    { key: "sales", label: "Продажі" },
  ],
};

const emptyDashboard: DashboardStats = {
  pharmacy_filter: "All Network",
  total_sales_orders: 0,
  total_revenue: 0,
  active_alerts: 0,
  total_staff: 0,
};

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(SESSION_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [view, setView] = useState<ViewKey>("dashboard");
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);

  const [pharmacyFilterId, setPharmacyFilterId] = useState<number | "">("");
  const [dashboard, setDashboard] = useState<DashboardStats>(emptyDashboard);
  const [pharmacies, setPharmacies] = useState<Pharmacy[]>([]);
  const [locations, setLocations] = useState<StorageLocation[]>([]);
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [expiredBatches, setExpiredBatches] = useState<Batch[]>([]);
  const [alerts, setAlerts] = useState<ActiveAlert[]>([]);
  const [history, setHistory] = useState<IncidentHistoryEntry[]>([]);
  const [sales, setSales] = useState<Sale[]>([]);
  const [selectedSale, setSelectedSale] = useState<Sale | null>(null);
  const [staff, setStaff] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [historyLimit, setHistoryLimit] = useState(100);
  const [expiredDays, setExpiredDays] = useState(30);

  const activePharmacyFilter = user?.role === "admin" && pharmacyFilterId !== "" ? pharmacyFilterId : undefined;

  useEffect(() => {
    if (!token) {
      return;
    }
    void bootstrap(token);
  }, []);

  useEffect(() => {
    if (!token || !user) {
      return;
    }
    if (user.role === "admin" || user.role === "manager") {
      if (view === "dashboard") {
        void loadDashboard(token, user);
      }
    }
    if (view === "alerts") {
      void loadAlerts(token);
    }
    if (view === "history") {
      void loadHistory(token);
    }
    if (view === "pharmacies") {
      void loadPharmacies(token);
    }
    if (view === "locations") {
      void loadLocations(token);
    }
    if (view === "devices") {
      void loadDevices(token);
    }
    if (view === "inventory") {
      void loadInventory(token);
    }
    if (view === "sales") {
      void loadSales(token);
    }
    if (view === "staff" && user.role !== "pharmacist") {
      void loadStaff(token);
    }
    if (view === "audit" && user.role === "admin") {
      void loadAudit(token);
    }
  }, [view, pharmacyFilterId]);

  async function withTask<T>(label: string, task: () => Promise<T>): Promise<T | undefined> {
    setBusyLabel(label);
    try {
      return await task();
    } catch (error) {
      setNotice({ tone: "error", text: toUserMessage(error) });
      return undefined;
    } finally {
      setBusyLabel(null);
    }
  }

  async function bootstrap(sessionToken: string) {
    await withTask("Завантаження сесії", async () => {
      const currentUser = await api.me(sessionToken);
      setUser(currentUser);
      setView(currentUser.role === "pharmacist" ? "alerts" : "dashboard");
      await Promise.all([
        loadPharmacies(sessionToken, false),
        loadAlerts(sessionToken, false),
        loadHistory(sessionToken, false),
        currentUser.role !== "pharmacist" ? loadDashboard(sessionToken, currentUser, false) : Promise.resolve(),
      ]);
    });
  }

  function storeToken(sessionToken: string | null) {
    setToken(sessionToken);
    if (sessionToken) {
      localStorage.setItem(SESSION_KEY, sessionToken);
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
  }

  function resetSession() {
    storeToken(null);
    setUser(null);
    setLoginError(null);
    setPharmacyFilterId("");
    setDashboard(emptyDashboard);
    setPharmacies([]);
    setLocations([]);
    setDevices([]);
    setMedicines([]);
    setBatches([]);
    setExpiredBatches([]);
    setAlerts([]);
    setHistory([]);
    setSales([]);
    setSelectedSale(null);
    setStaff([]);
    setAuditLogs([]);
    setView("dashboard");
  }

  async function handleLogin(email: string, password: string) {
    setLoginError(null);
    const result = await withTask("Вхід", async () => {
      const login = await api.login(email, password);
      storeToken(login.access_token);
      await bootstrap(login.access_token);
      setNotice({ tone: "success", text: "Вхід виконано успішно." });
      return true;
    });
    if (result !== true) {
      setLoginError("Не вдалося виконати вхід. Перевір дані або доступність backend.");
    }
  }

  async function loadDashboard(sessionToken: string, currentUser = user, showBusy = true) {
    if (!currentUser || currentUser.role === "pharmacist") {
      return;
    }
    const runner = () => api.getDashboardStats(sessionToken, activePharmacyFilter);
    const data = showBusy ? await withTask("Оновлення дашборду", runner) : await runner().catch(() => undefined);
    if (data) {
      setDashboard(data);
    }
  }

  async function loadPharmacies(sessionToken: string, showBusy = true) {
    const runner = () => api.getPharmacies(sessionToken);
    const data = showBusy ? await withTask("Оновлення аптек", runner) : await runner().catch(() => undefined);
    if (data) {
      setPharmacies(data);
    }
  }

  async function loadLocations(sessionToken: string, showBusy = true) {
    const runner = () => api.getLocations(sessionToken, activePharmacyFilter);
    const data = showBusy ? await withTask("Оновлення локацій", runner) : await runner().catch(() => undefined);
    if (data) {
      setLocations(data);
    }
  }

  async function loadDevices(sessionToken: string, showBusy = true) {
    const runner = () => api.getDevices(sessionToken, activePharmacyFilter);
    const data = showBusy ? await withTask("Оновлення датчиків", runner) : await runner().catch(() => undefined);
    if (data) {
      setDevices(data);
    }
  }

  async function loadAlerts(sessionToken: string, showBusy = true) {
    const runner = () => api.getAlerts(sessionToken, activePharmacyFilter);
    const data = showBusy ? await withTask("Оновлення тривог", runner) : await runner().catch(() => undefined);
    if (data) {
      setAlerts(data);
    }
  }

  async function loadHistory(sessionToken: string, showBusy = true) {
    const runner = () => api.getIncidentHistory(sessionToken, activePharmacyFilter, historyLimit);
    const data = showBusy ? await withTask("Оновлення журналу", runner) : await runner().catch(() => undefined);
    if (data) {
      setHistory(data);
    }
  }

  async function loadInventory(sessionToken: string) {
    await withTask("Оновлення складу", async () => {
      const [medicineData, batchData, expiredData] = await Promise.all([
        api.getMedicines(sessionToken),
        api.getBatches(sessionToken, activePharmacyFilter),
        api.getExpiredBatches(sessionToken, expiredDays, activePharmacyFilter),
      ]);
      setMedicines(medicineData);
      setBatches(batchData);
      setExpiredBatches(expiredData);
    });
  }

  async function loadSales(sessionToken: string, saleToSelect?: number) {
    await withTask("Оновлення продажів", async () => {
      const list = await api.getSales(sessionToken, activePharmacyFilter);
      setSales(list);
      if (saleToSelect) {
        const full = await api.getSale(sessionToken, saleToSelect);
        setSelectedSale(full);
      }
    });
  }

  async function loadStaff(sessionToken: string) {
    const data = await withTask("Оновлення співробітників", () => api.getUsers(sessionToken, activePharmacyFilter));
    if (data) {
      setStaff(data);
    }
  }

  async function loadAudit(sessionToken: string) {
    const data = await withTask("Оновлення аудиту", () => api.getAuditLogs(sessionToken));
    if (data) {
      setAuditLogs(data);
    }
  }

  async function refreshCurrentView() {
    if (!token || !user) {
      return;
    }

    switch (view) {
      case "dashboard":
        await Promise.all([loadDashboard(token, user), loadAlerts(token, false), loadPharmacies(token, false)]);
        break;
      case "alerts":
        await loadAlerts(token);
        break;
      case "history":
        await loadHistory(token);
        break;
      case "pharmacies":
        await loadPharmacies(token);
        break;
      case "locations":
        await loadLocations(token);
        break;
      case "devices":
        await loadDevices(token);
        break;
      case "inventory":
        await loadInventory(token);
        break;
      case "sales":
        await loadSales(token, selectedSale?.id);
        break;
      case "staff":
        await loadStaff(token);
        break;
      case "audit":
        await loadAudit(token);
        break;
    }
  }

  if (!user || !token) {
    return (
      <LoginScreen
        busyLabel={busyLabel}
        error={loginError}
        onLogin={handleLogin}
      />
    );
  }

  const canManagePharmacies = user.role === "admin";
  const canManageLocations = user.role === "admin" || user.role === "manager";
  const canManageDevices = user.role === "admin" || user.role === "manager";
  const canManageMedicines = user.role === "admin";
  const canManageBatches = user.role === "admin" || user.role === "manager";
  const canManageStaff = user.role === "admin" || user.role === "manager";
  const canResolveAlerts = user.role !== "pharmacist";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-card">
          <div className="brand-mark">P</div>
          <div>
            <h1>PharmaSmart</h1>
            <p>Веб-панель керування аптечною мережею</p>
          </div>
        </div>

        <div className="user-card">
          <strong>{user.full_name}</strong>
          <span>{roleLabel(user.role)}</span>
          <small>{user.email}</small>
        </div>

        <nav className="nav-list">
          {navByRole[user.role].map((item) => (
            <button
              key={item.key}
              className={item.key === view ? "nav-item nav-item--active" : "nav-item"}
              onClick={() => setView(item.key)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>

        <button
          className="ghost-button danger-button"
          type="button"
          onClick={resetSession}
        >
          Вийти
        </button>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <h2>{navByRole[user.role].find((item) => item.key === view)?.label ?? "PharmaSmart"}</h2>
            <p>{viewSubtitle(view, user.role)}</p>
          </div>
          <div className="topbar-actions">
            {user.role === "admin" && pharmacies.length > 0 ? (
              <select
                className="select-field"
                value={pharmacyFilterId}
                onChange={(event) => {
                  const value = event.target.value;
                  setPharmacyFilterId(value ? Number(value) : "");
                }}
              >
                <option value="">Уся мережа</option>
                {pharmacies.map((pharmacy) => (
                  <option key={pharmacy.id} value={pharmacy.id}>
                    {pharmacy.name}
                  </option>
                ))}
              </select>
            ) : null}
            <button className="primary-button" type="button" onClick={() => void refreshCurrentView()}>
              Оновити
            </button>
          </div>
        </header>

        {notice ? (
          <div className={notice.tone === "success" ? "notice notice--success" : "notice notice--error"}>
            <span>{notice.text}</span>
            <button type="button" onClick={() => setNotice(null)}>
              Закрити
            </button>
          </div>
        ) : null}

        {busyLabel ? <div className="busy-banner">{busyLabel}...</div> : null}

        {view === "dashboard" ? (
          <DashboardPage dashboard={dashboard} alerts={alerts.slice(0, 4)} />
        ) : null}

        {view === "alerts" ? (
          <AlertsPage
            alerts={alerts}
            canResolve={canResolveAlerts}
            onResolve={async (alertId) => {
              await withTask("Закриття інциденту", async () => {
                await api.resolveAlert(token, alertId);
                await Promise.all([loadAlerts(token, false), loadHistory(token, false), loadDashboard(token, user, false)]);
                setNotice({ tone: "success", text: "Інцидент закрито." });
              });
            }}
            onEscalate={async (alertId) => {
              await withTask("Ескалація інциденту", async () => {
                await api.escalateAlert(token, alertId);
                await Promise.all([loadAlerts(token, false), loadHistory(token, false), loadDashboard(token, user, false)]);
                setNotice({ tone: "success", text: "Інцидент ескальовано й оновлено до критичного рівня." });
              });
            }}
          />
        ) : null}

        {view === "history" ? (
          <HistoryPage
            entries={history}
            historyLimit={historyLimit}
            onLimitChange={(value) => setHistoryLimit(value)}
            onReload={() => void loadHistory(token)}
          />
        ) : null}

        {view === "pharmacies" ? (
          <PharmaciesPage
            pharmacies={pharmacies}
            canManage={canManagePharmacies}
            onCreate={async (payload) => {
              await withTask("Створення аптеки", async () => {
                await api.createPharmacy(token, payload);
                await loadPharmacies(token, false);
                setNotice({ tone: "success", text: "Аптеку створено." });
              });
            }}
            onDelete={async (pharmacyId) => {
              if (!window.confirm("Видалити аптеку?")) {
                return;
              }
              await withTask("Видалення аптеки", async () => {
                await api.deletePharmacy(token, pharmacyId);
                await loadPharmacies(token, false);
                setNotice({ tone: "success", text: "Аптеку видалено." });
              });
            }}
          />
        ) : null}

        {view === "locations" ? (
          <LocationsPage
            locations={locations}
            pharmacies={pharmacies}
            canManage={canManageLocations}
            currentUser={user}
            onCreate={async (payload) => {
              await withTask("Створення локації", async () => {
                await api.createLocation(token, payload);
                await loadLocations(token, false);
                setNotice({ tone: "success", text: "Місце зберігання створено." });
              });
            }}
            onDelete={async (locationId) => {
              if (!window.confirm("Видалити місце зберігання?")) {
                return;
              }
              await withTask("Видалення локації", async () => {
                await api.deleteLocation(token, locationId);
                await loadLocations(token, false);
                setNotice({ tone: "success", text: "Локацію видалено." });
              });
            }}
          />
        ) : null}

        {view === "devices" ? (
          <DevicesPage
            devices={devices}
            locations={locations}
            canManage={canManageDevices}
            currentUser={user}
            onCreate={async (payload) => {
              await withTask("Реєстрація датчика", async () => {
                await api.createDevice(token, payload);
                await loadDevices(token, false);
                setNotice({ tone: "success", text: "Датчик зареєстровано." });
              });
            }}
            onDelete={async (deviceId) => {
              if (!window.confirm("Видалити датчик?")) {
                return;
              }
              await withTask("Видалення датчика", async () => {
                await api.deleteDevice(token, deviceId);
                await loadDevices(token, false);
                setNotice({ tone: "success", text: "Датчик видалено." });
              });
            }}
          />
        ) : null}

        {view === "inventory" ? (
          <InventoryPage
            currentUser={user}
            medicines={medicines}
            batches={batches}
            expiredBatches={expiredBatches}
            locations={locations}
            canManageMedicines={canManageMedicines}
            canManageBatches={canManageBatches}
            expiredDays={expiredDays}
            onExpiredDaysChange={setExpiredDays}
            onReloadExpired={() => void loadInventory(token)}
            onCreateMedicine={async (payload) => {
              await withTask("Створення ліків", async () => {
                await api.createMedicine(token, payload);
                await loadInventory(token);
                setNotice({ tone: "success", text: "Нову позицію додано до довідника." });
              });
            }}
            onDeleteMedicine={async (medicineId) => {
              if (!window.confirm("Видалити ліки з довідника?")) {
                return;
              }
              await withTask("Видалення ліків", async () => {
                await api.deleteMedicine(token, medicineId);
                await loadInventory(token);
                setNotice({ tone: "success", text: "Позицію видалено з довідника." });
              });
            }}
            onCreateBatch={async (payload) => {
              await withTask("Створення партії", async () => {
                await api.createBatch(token, payload);
                await loadInventory(token);
                setNotice({ tone: "success", text: "Партію додано на склад." });
              });
            }}
            onDeleteBatch={async (batchId) => {
              if (!window.confirm("Видалити партію?")) {
                return;
              }
              await withTask("Видалення партії", async () => {
                await api.deleteBatch(token, batchId);
                await loadInventory(token);
                setNotice({ tone: "success", text: "Партію видалено." });
              });
            }}
            onDispose={async (payload) => {
              await withTask("Списання партії", async () => {
                await api.disposeBatch(token, payload);
                await loadInventory(token);
                setNotice({ tone: "success", text: "Списання проведено." });
              });
            }}
          />
        ) : null}

        {view === "sales" ? (
          <SalesPage
            currentUser={user}
            sales={sales}
            batches={batches}
            selectedSale={selectedSale}
            onSelectSale={async (saleId) => {
              await withTask("Завантаження чека", async () => {
                const sale = await api.getSale(token, saleId);
                setSelectedSale(sale);
              });
            }}
            onCreateSale={async (payload) => {
              await withTask("Оформлення продажу", async () => {
                const sale = await api.createSale(token, payload);
                await loadSales(token, sale.id);
                await loadInventory(token);
                setNotice({ tone: "success", text: "Продаж оформлено." });
              });
            }}
          />
        ) : null}

        {view === "staff" ? (
          <StaffPage
            currentUser={user}
            staff={staff}
            pharmacies={pharmacies}
            canManage={canManageStaff}
            onCreate={async (payload) => {
              await withTask("Створення співробітника", async () => {
                await api.createUser(token, payload);
                await loadStaff(token);
                await loadDashboard(token, user, false);
                setNotice({ tone: "success", text: "Співробітника створено." });
              });
            }}
            onDelete={async (userId) => {
              if (!window.confirm("Видалити співробітника?")) {
                return;
              }
              await withTask("Видалення співробітника", async () => {
                await api.deleteUser(token, userId);
                await loadStaff(token);
                await loadDashboard(token, user, false);
                setNotice({ tone: "success", text: "Співробітника видалено." });
              });
            }}
          />
        ) : null}

        {view === "audit" ? (
          <AuditPage logs={auditLogs} />
        ) : null}
      </main>
    </div>
  );
}

function LoginScreen(props: {
  busyLabel: string | null;
  error: string | null;
  onLogin: (email: string, password: string) => Promise<void>;
}) {
  const [email, setEmail] = useState("manager@pharmasmart.ua");
  const [password, setPassword] = useState("pharma123");

  return (
    <div className="login-screen">
      <form
        className="login-card"
        onSubmit={(event) => {
          event.preventDefault();
          void props.onLogin(email, password);
        }}
      >
        <div className="brand-card brand-card--login">
          <div className="brand-mark">P</div>
          <div>
            <h1>PharmaSmart</h1>
            <p>Єдина веб-панель для адміністрації, завідувачів і фармацевтів</p>
          </div>
        </div>

        <label className="field-block">
          <span>Email</span>
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        </label>

        <label className="field-block">
          <span>Пароль</span>
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
        </label>

        {props.error ? <div className="notice notice--error">{props.error}</div> : null}

        <button className="primary-button primary-button--wide" type="submit">
          {props.busyLabel ? `${props.busyLabel}...` : "Увійти до системи"}
        </button>

        <p className="support-text">
          Локально фронт запускається через `npm run dev`, а backend-адресу можна змінити через `VITE_API_BASE_URL`.
        </p>
      </form>
    </div>
  );
}

function DashboardPage(props: { dashboard: DashboardStats; alerts: ActiveAlert[] }) {
  return (
    <div className="page-grid">
      <section className="metrics-grid">
        <MetricCard title="Активні тривоги" value={String(props.dashboard.active_alerts)} tone="danger" />
        <MetricCard title="Продажі" value={String(props.dashboard.total_sales_orders)} />
        <MetricCard title="Персонал" value={String(props.dashboard.total_staff)} />
        <MetricCard title="Виторг" value={`₴${props.dashboard.total_revenue.toFixed(0)}`} />
      </section>

      <Panel title="Ключові інциденти" subtitle="Те, що потребує уваги прямо зараз.">
        <div className="list-stack">
          {props.alerts.length === 0 ? <EmptyState text="Активних інцидентів зараз немає." /> : null}
          {props.alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      </Panel>
    </div>
  );
}

function AlertsPage(props: {
  alerts: ActiveAlert[];
  canResolve: boolean;
  onResolve: (alertId: number) => Promise<void>;
  onEscalate: (alertId: number) => Promise<void>;
}) {
  const [filter, setFilter] = useState<"all" | "warning" | "critical">("all");
  const [query, setQuery] = useState("");

  const filtered = props.alerts.filter((alert) => {
    const matchesSeverity = filter === "all" || alert.severity === filter;
    const haystack = `${alert.message} ${alert.pharmacy_name ?? ""} ${alert.storage_location_name ?? ""}`.toLowerCase();
    return matchesSeverity && haystack.includes(query.toLowerCase());
  });

  return (
    <div className="page-grid">
      <Panel title="Активні тривоги" subtitle="Поточні відхилення температури та вологості.">
        <div className="toolbar">
          <div className="chip-group">
            {[
              { key: "all", label: "Усі" },
              { key: "warning", label: "Попередження" },
              { key: "critical", label: "Критичні" },
            ].map((item) => (
              <button
                key={item.key}
                type="button"
                className={filter === item.key ? "chip chip--active" : "chip"}
                onClick={() => setFilter(item.key as "all" | "warning" | "critical")}
              >
                {item.label}
              </button>
            ))}
          </div>
          <input
            className="search-field"
            placeholder="Пошук по аптеці або причині"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>

        <div className="list-stack">
          {filtered.length === 0 ? <EmptyState text="Інцидентів для цього фільтра не знайдено." /> : null}
          {filtered.map((alert) => (
            <div key={alert.id} className="card card--alert">
              <div className="card-row">
                <div>
                  <strong>{alert.severity === "critical" ? "Критичний інцидент" : "Попередження"}</strong>
                  <p>{alert.pharmacy_name ?? "Невідома аптека"} • {alert.storage_location_name ?? "Невідома локація"}</p>
                </div>
                <span className={alert.severity === "critical" ? "pill pill--danger" : "pill pill--warn"}>
                  {alert.severity === "critical" ? "Критично" : "Увага"}
                </span>
              </div>
              <p>{alert.message}</p>
              <div className="card-meta">
                <span>{formatSensorState(alert.latest_temperature, alert.latest_humidity)}</span>
                <span>{relativeTime(alert.created_at)}</span>
              </div>
              {props.canResolve ? (
                <div className="action-row">
                  <button className="secondary-button" type="button" onClick={() => void props.onResolve(alert.id)}>
                    Закрити
                  </button>
                  <button className="primary-button" type="button" onClick={() => void props.onEscalate(alert.id)}>
                    Ескалувати
                  </button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function HistoryPage(props: {
  entries: IncidentHistoryEntry[];
  historyLimit: number;
  onLimitChange: (value: number) => void;
  onReload: () => void;
}) {
  return (
    <Panel title="Журнал інцидентів" subtitle="Створення, оновлення, ескалація і закриття інцидентів.">
      <div className="toolbar">
        <label className="inline-field">
          <span>Показати записів</span>
          <input
            type="number"
            min={10}
            max={500}
            value={props.historyLimit}
            onChange={(event) => props.onLimitChange(Number(event.target.value))}
          />
        </label>
        <button className="secondary-button" type="button" onClick={props.onReload}>
          Оновити журнал
        </button>
      </div>
      <div className="list-stack">
        {props.entries.length === 0 ? <EmptyState text="Журнал поки що порожній." /> : null}
        {props.entries.map((entry) => (
          <details key={entry.id} className="card">
            <summary className="summary-row">
              <div>
                <strong>{entry.headline}</strong>
                <p>{entry.pharmacy_name ?? "Невідома аптека"} • {entry.storage_location_name ?? "Невідома локація"}</p>
              </div>
              <span>{relativeTime(entry.created_at)}</span>
            </summary>
            <p>{entry.message}</p>
            <div className="card-meta">
              <span>Виконавець: {entry.actor_name ?? "Система"}</span>
              <span>{formatDateTime(entry.created_at)}</span>
            </div>
          </details>
        ))}
      </div>
    </Panel>
  );
}

function PharmaciesPage(props: {
  pharmacies: Pharmacy[];
  canManage: boolean;
  onCreate: (payload: {
    name: string;
    address: string;
    license_number: string;
    license_expiry_date: string | null;
    phone: string | null;
  }) => Promise<void>;
  onDelete: (pharmacyId: number) => Promise<void>;
}) {
  const [form, setForm] = useState({
    name: "",
    address: "",
    license_number: "",
    license_expiry_date: "",
    phone: "",
  });

  return (
    <div className="page-grid">
      {props.canManage ? (
        <Panel title="Нова аптека" subtitle="Створення нового об'єкта мережі.">
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void props.onCreate({
                ...form,
                license_expiry_date: form.license_expiry_date || null,
                phone: form.phone || null,
              });
            }}
          >
            <input placeholder="Назва" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            <input placeholder="Адреса" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} required />
            <input placeholder="Ліцензія" value={form.license_number} onChange={(event) => setForm({ ...form, license_number: event.target.value })} required />
            <input type="date" value={form.license_expiry_date} onChange={(event) => setForm({ ...form, license_expiry_date: event.target.value })} />
            <input placeholder="Телефон" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
            <button className="primary-button" type="submit">Створити аптеку</button>
          </form>
        </Panel>
      ) : null}

      <Panel title="Список аптек" subtitle="Поточний стан аптек та останні показники сенсорів.">
        <div className="list-stack">
          {props.pharmacies.map((pharmacy) => (
            <div key={pharmacy.id} className="card">
              <div className="card-row">
                <div>
                  <strong>{pharmacy.name}</strong>
                  <p>{pharmacy.address}</p>
                </div>
                <span className={pharmacy.active_alerts > 0 ? "pill pill--warn" : "pill pill--ok"}>
                  {pharmacy.active_alerts > 0 ? `${pharmacy.active_alerts} інцид.` : "Стабільно"}
                </span>
              </div>
              <div className="card-meta">
                <span>{formatSensorState(pharmacy.latest_temperature, pharmacy.latest_humidity)}</span>
                <span>Локацій: {pharmacy.storage_locations.length}</span>
              </div>
              <div className="card-meta">
                <span>Ліцензія: {pharmacy.license_number}</span>
                <span>{pharmacy.license_expiry_date ? `До ${pharmacy.license_expiry_date}` : "Дата не вказана"}</span>
              </div>
              {props.canManage ? (
                <div className="action-row">
                  <button className="ghost-button" type="button" onClick={() => void props.onDelete(pharmacy.id)}>
                    Видалити
                  </button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function LocationsPage(props: {
  locations: StorageLocation[];
  pharmacies: Pharmacy[];
  currentUser: User;
  canManage: boolean;
  onCreate: (payload: {
    name: string;
    description: string | null;
    is_refrigerated: boolean;
    pharmacy_id: number;
  }) => Promise<void>;
  onDelete: (locationId: number) => Promise<void>;
}) {
  const defaultPharmacyId = props.currentUser.pharmacy_id ?? props.pharmacies[0]?.id ?? 0;
  const [form, setForm] = useState({
    name: "",
    description: "",
    is_refrigerated: true,
    pharmacy_id: defaultPharmacyId,
  });

  return (
    <div className="page-grid">
      {props.canManage ? (
        <Panel title="Нове місце зберігання" subtitle="Холодильник, зона або інша складська точка.">
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void props.onCreate({
                name: form.name,
                description: form.description || null,
                is_refrigerated: form.is_refrigerated,
                pharmacy_id: form.pharmacy_id,
              });
            }}
          >
            <input placeholder="Назва локації" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            <input placeholder="Опис" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
            <select value={form.pharmacy_id} onChange={(event) => setForm({ ...form, pharmacy_id: Number(event.target.value) })}>
              {props.pharmacies
                .filter((item) => props.currentUser.role === "admin" || item.id === props.currentUser.pharmacy_id)
                .map((pharmacy) => (
                  <option key={pharmacy.id} value={pharmacy.id}>
                    {pharmacy.name}
                  </option>
                ))}
            </select>
            <label className="checkbox-field">
              <input type="checkbox" checked={form.is_refrigerated} onChange={(event) => setForm({ ...form, is_refrigerated: event.target.checked })} />
              <span>Потрібне холодильне зберігання</span>
            </label>
            <button className="primary-button" type="submit">Створити локацію</button>
          </form>
        </Panel>
      ) : null}

      <Panel title="Локації" subtitle="Усі місця зберігання, доступні поточному користувачу.">
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Назва</th>
                <th>Аптека</th>
                <th>Тип</th>
                {props.canManage ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {props.locations.map((location) => (
                <tr key={location.id}>
                  <td>{location.id}</td>
                  <td>{location.name}</td>
                  <td>{props.pharmacies.find((item) => item.id === location.pharmacy_id)?.name ?? location.pharmacy_id}</td>
                  <td>{location.is_refrigerated ? "Холодильник" : "Полиця / зона"}</td>
                  {props.canManage ? (
                    <td className="table-actions">
                      <button type="button" onClick={() => void props.onDelete(location.id)}>Видалити</button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function DevicesPage(props: {
  devices: IoTDevice[];
  locations: StorageLocation[];
  currentUser: User;
  canManage: boolean;
  onCreate: (payload: {
    serial_number: string;
    device_type: string;
    status: string;
    storage_location_id: number;
  }) => Promise<void>;
  onDelete: (deviceId: number) => Promise<void>;
}) {
  const [form, setForm] = useState({
    serial_number: "",
    device_type: "sensor",
    status: "active",
    storage_location_id: props.locations[0]?.id ?? 0,
  });

  return (
    <div className="page-grid">
      {props.canManage ? (
        <Panel title="Новий датчик" subtitle="Реєстрація IoT-пристрою для конкретної локації.">
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void props.onCreate(form);
            }}
          >
            <input placeholder="Серійний номер" value={form.serial_number} onChange={(event) => setForm({ ...form, serial_number: event.target.value })} required />
            <select value={form.device_type} onChange={(event) => setForm({ ...form, device_type: event.target.value })}>
              <option value="sensor">sensor</option>
              <option value="smart_lock">smart_lock</option>
            </select>
            <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
              <option value="active">active</option>
              <option value="maintenance">maintenance</option>
              <option value="offline">offline</option>
            </select>
            <select value={form.storage_location_id} onChange={(event) => setForm({ ...form, storage_location_id: Number(event.target.value) })}>
              {props.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  #{location.id} {location.name}
                </option>
              ))}
            </select>
            <button className="primary-button" type="submit">Зареєструвати датчик</button>
          </form>
        </Panel>
      ) : null}

      <Panel title="Список датчиків" subtitle="Стан усіх доступних пристроїв.">
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Серійний номер</th>
                <th>Тип</th>
                <th>Статус</th>
                <th>Локація</th>
                {props.canManage ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {props.devices.map((device) => (
                <tr key={device.id}>
                  <td>{device.id}</td>
                  <td>{device.serial_number}</td>
                  <td>{device.device_type}</td>
                  <td>{device.status}</td>
                  <td>{props.locations.find((item) => item.id === device.storage_location_id)?.name ?? "Не прив'язано"}</td>
                  {props.canManage ? (
                    <td className="table-actions">
                      <button type="button" onClick={() => void props.onDelete(device.id)}>Видалити</button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function InventoryPage(props: {
  currentUser: User;
  medicines: Medicine[];
  batches: Batch[];
  expiredBatches: Batch[];
  locations: StorageLocation[];
  canManageMedicines: boolean;
  canManageBatches: boolean;
  expiredDays: number;
  onExpiredDaysChange: (value: number) => void;
  onReloadExpired: () => void;
  onCreateMedicine: (payload: {
    name: string;
    manufacturer: string | null;
    description: string | null;
    min_temperature: number;
    max_temperature: number;
    min_humidity: number;
    max_humidity: number;
    is_prescription: boolean;
    requires_smart_lock: boolean;
  }) => Promise<void>;
  onDeleteMedicine: (medicineId: number) => Promise<void>;
  onCreateBatch: (payload: {
    batch_number: string;
    initial_quantity: number;
    current_quantity: number;
    expiration_date: string;
    medicine_id: number;
    storage_location_id: number;
  }) => Promise<void>;
  onDeleteBatch: (batchId: number) => Promise<void>;
  onDispose: (payload: { batch_id: number; quantity: number; reason: string }) => Promise<void>;
}) {
  const [medicineForm, setMedicineForm] = useState({
    name: "",
    manufacturer: "",
    description: "",
    min_temperature: 2,
    max_temperature: 8,
    min_humidity: 45,
    max_humidity: 65,
    is_prescription: false,
    requires_smart_lock: false,
  });
  const [batchForm, setBatchForm] = useState({
    batch_number: "",
    initial_quantity: 100,
    current_quantity: 100,
    expiration_date: "",
    medicine_id: props.medicines[0]?.id ?? 0,
    storage_location_id: props.locations[0]?.id ?? 0,
  });
  const [disposeForm, setDisposeForm] = useState({
    batch_id: props.batches[0]?.id ?? 0,
    quantity: 1,
    reason: "Expired",
  });

  return (
    <div className="page-grid">
      <Panel title="Довідник ліків" subtitle="Глобальний каталог номенклатури та умови зберігання.">
        {props.canManageMedicines ? (
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void props.onCreateMedicine({
                ...medicineForm,
                manufacturer: medicineForm.manufacturer || null,
                description: medicineForm.description || null,
              });
            }}
          >
            <input placeholder="Назва" value={medicineForm.name} onChange={(event) => setMedicineForm({ ...medicineForm, name: event.target.value })} required />
            <input placeholder="Виробник" value={medicineForm.manufacturer} onChange={(event) => setMedicineForm({ ...medicineForm, manufacturer: event.target.value })} />
            <input placeholder="Опис" value={medicineForm.description} onChange={(event) => setMedicineForm({ ...medicineForm, description: event.target.value })} />
            <input type="number" step="0.1" value={medicineForm.min_temperature} onChange={(event) => setMedicineForm({ ...medicineForm, min_temperature: Number(event.target.value) })} />
            <input type="number" step="0.1" value={medicineForm.max_temperature} onChange={(event) => setMedicineForm({ ...medicineForm, max_temperature: Number(event.target.value) })} />
            <input type="number" step="0.1" value={medicineForm.min_humidity} onChange={(event) => setMedicineForm({ ...medicineForm, min_humidity: Number(event.target.value) })} />
            <input type="number" step="0.1" value={medicineForm.max_humidity} onChange={(event) => setMedicineForm({ ...medicineForm, max_humidity: Number(event.target.value) })} />
            <label className="checkbox-field">
              <input type="checkbox" checked={medicineForm.is_prescription} onChange={(event) => setMedicineForm({ ...medicineForm, is_prescription: event.target.checked })} />
              <span>Рецептурний препарат</span>
            </label>
            <label className="checkbox-field">
              <input type="checkbox" checked={medicineForm.requires_smart_lock} onChange={(event) => setMedicineForm({ ...medicineForm, requires_smart_lock: event.target.checked })} />
              <span>Потрібен smart lock</span>
            </label>
            <button className="primary-button" type="submit">Додати ліки</button>
          </form>
        ) : null}

        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Назва</th>
                <th>Темп.</th>
                <th>Вологість</th>
                {props.canManageMedicines ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {props.medicines.map((medicine) => (
                <tr key={medicine.id}>
                  <td>{medicine.id}</td>
                  <td>{medicine.name}</td>
                  <td>{medicine.min_temperature}..{medicine.max_temperature}°C</td>
                  <td>{medicine.min_humidity}..{medicine.max_humidity}%</td>
                  {props.canManageMedicines ? (
                    <td className="table-actions">
                      <button type="button" onClick={() => void props.onDeleteMedicine(medicine.id)}>Видалити</button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Партії на складі" subtitle="Управління надходженням і списанням товару.">
        {props.canManageBatches ? (
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void props.onCreateBatch(batchForm);
            }}
          >
            <input placeholder="Номер партії" value={batchForm.batch_number} onChange={(event) => setBatchForm({ ...batchForm, batch_number: event.target.value })} required />
            <select value={batchForm.medicine_id} onChange={(event) => setBatchForm({ ...batchForm, medicine_id: Number(event.target.value) })}>
              {props.medicines.map((medicine) => (
                <option key={medicine.id} value={medicine.id}>
                  {medicine.name}
                </option>
              ))}
            </select>
            <select value={batchForm.storage_location_id} onChange={(event) => setBatchForm({ ...batchForm, storage_location_id: Number(event.target.value) })}>
              {props.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name}
                </option>
              ))}
            </select>
            <input type="number" min={1} value={batchForm.initial_quantity} onChange={(event) => setBatchForm({ ...batchForm, initial_quantity: Number(event.target.value) })} />
            <input type="number" min={1} value={batchForm.current_quantity} onChange={(event) => setBatchForm({ ...batchForm, current_quantity: Number(event.target.value) })} />
            <input type="date" value={batchForm.expiration_date} onChange={(event) => setBatchForm({ ...batchForm, expiration_date: event.target.value })} required />
            <button className="primary-button" type="submit">Додати партію</button>
          </form>
        ) : null}

        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Партія</th>
                <th>Ліки</th>
                <th>Залишок</th>
                <th>Термін</th>
                {props.canManageBatches ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {props.batches.map((batch) => (
                <tr key={batch.id}>
                  <td>{batch.id}</td>
                  <td>{batch.batch_number}</td>
                  <td>{props.medicines.find((medicine) => medicine.id === batch.medicine_id)?.name ?? batch.medicine_id}</td>
                  <td>{batch.current_quantity} / {batch.initial_quantity}</td>
                  <td>{batch.expiration_date}</td>
                  {props.canManageBatches ? (
                    <td className="table-actions">
                      <button type="button" onClick={() => void props.onDeleteBatch(batch.id)}>Видалити</button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {props.canManageBatches ? (
          <form
            className="form-grid compact-form"
            onSubmit={(event) => {
              event.preventDefault();
              void props.onDispose(disposeForm);
            }}
          >
            <h4>Списання партії</h4>
            <select value={disposeForm.batch_id} onChange={(event) => setDisposeForm({ ...disposeForm, batch_id: Number(event.target.value) })}>
              {props.batches.map((batch) => (
                <option key={batch.id} value={batch.id}>
                  #{batch.id} {batch.batch_number}
                </option>
              ))}
            </select>
            <input type="number" min={1} value={disposeForm.quantity} onChange={(event) => setDisposeForm({ ...disposeForm, quantity: Number(event.target.value) })} />
            <input placeholder="Причина" value={disposeForm.reason} onChange={(event) => setDisposeForm({ ...disposeForm, reason: event.target.value })} />
            <button className="secondary-button" type="submit">Списати</button>
          </form>
        ) : null}
      </Panel>

      <Panel title="Партії під контролем терміну" subtitle="Пошук прострочених або близьких до завершення партій.">
        <div className="toolbar">
          <label className="inline-field">
            <span>Днів до завершення</span>
            <input type="number" min={0} value={props.expiredDays} onChange={(event) => props.onExpiredDaysChange(Number(event.target.value))} />
          </label>
          <button className="secondary-button" type="button" onClick={props.onReloadExpired}>
            Оновити вибірку
          </button>
        </div>

        <div className="list-stack">
          {props.expiredBatches.length === 0 ? <EmptyState text="Немає прострочених або ризикових партій." /> : null}
          {props.expiredBatches.map((batch) => (
            <div key={batch.id} className="card">
              <strong>{batch.batch_number}</strong>
              <div className="card-meta">
                <span>Ліки: {props.medicines.find((medicine) => medicine.id === batch.medicine_id)?.name ?? batch.medicine_id}</span>
                <span>Термін: {batch.expiration_date}</span>
              </div>
              <div className="card-meta">
                <span>Залишок: {batch.current_quantity}</span>
                <span>Локація: {props.locations.find((location) => location.id === batch.storage_location_id)?.name ?? batch.storage_location_id}</span>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function SalesPage(props: {
  currentUser: User;
  sales: Sale[];
  batches: Batch[];
  selectedSale: Sale | null;
  onSelectSale: (saleId: number) => Promise<void>;
  onCreateSale: (payload: { items: Array<{ batch_id: number; quantity: number; price_per_unit: number }> }) => Promise<void>;
}) {
  const [items, setItems] = useState<Array<{ batch_id: number; quantity: number; price_per_unit: number }>>([
    { batch_id: props.batches[0]?.id ?? 0, quantity: 1, price_per_unit: 100 },
  ]);

  return (
    <div className="page-grid">
      <Panel title="Оформлення продажу" subtitle="Створи чек на основі доступних партій.">
        <form
          className="list-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void props.onCreateSale({ items });
          }}
        >
          {items.map((item, index) => (
            <div key={`${item.batch_id}-${index}`} className="form-grid form-grid--compact">
              <select
                value={item.batch_id}
                onChange={(event) => {
                  const next = [...items];
                  next[index] = { ...next[index], batch_id: Number(event.target.value) };
                  setItems(next);
                }}
              >
                {props.batches.map((batch) => (
                  <option key={batch.id} value={batch.id}>
                    #{batch.id} {batch.batch_number} • залишок {batch.current_quantity}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                value={item.quantity}
                onChange={(event) => {
                  const next = [...items];
                  next[index] = { ...next[index], quantity: Number(event.target.value) };
                  setItems(next);
                }}
              />
              <input
                type="number"
                min={1}
                value={item.price_per_unit}
                onChange={(event) => {
                  const next = [...items];
                  next[index] = { ...next[index], price_per_unit: Number(event.target.value) };
                  setItems(next);
                }}
              />
              <button
                className="ghost-button"
                type="button"
                onClick={() => setItems(items.filter((_, itemIndex) => itemIndex !== index))}
              >
                Прибрати
              </button>
            </div>
          ))}
          <div className="action-row">
            <button
              className="secondary-button"
              type="button"
              onClick={() => setItems([...items, { batch_id: props.batches[0]?.id ?? 0, quantity: 1, price_per_unit: 100 }])}
            >
              Додати позицію
            </button>
            <button className="primary-button" type="submit">
              Оформити продаж
            </button>
          </div>
        </form>
      </Panel>

      <Panel title="Історія продажів" subtitle="Останні чеки та повні деталі вибраного продажу.">
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Час</th>
                <th>Сума</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {props.sales.map((sale) => (
                <tr key={sale.id} onClick={() => void props.onSelectSale(sale.id)}>
                  <td>#{sale.id}</td>
                  <td>{formatDateTime(sale.created_at)}</td>
                  <td>₴{sale.total_amount.toFixed(0)}</td>
                  <td>{sale.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {props.selectedSale ? (
          <div className="card">
            <strong>Чек #{props.selectedSale.id}</strong>
            <div className="card-meta">
              <span>{formatDateTime(props.selectedSale.created_at)}</span>
              <span>Сума: ₴{props.selectedSale.total_amount.toFixed(2)}</span>
            </div>
            <ul className="item-list">
              {props.selectedSale.items.map((item) => (
                <li key={item.id}>
                  Партія #{item.batch_id}: {item.quantity} од. по ₴{item.price_at_moment}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <EmptyState text="Натисни на чек, щоб побачити його деталі." />
        )}
      </Panel>
    </div>
  );
}

function StaffPage(props: {
  currentUser: User;
  staff: User[];
  pharmacies: Pharmacy[];
  canManage: boolean;
  onCreate: (payload: {
    email: string;
    full_name: string;
    role: UserRole;
    pharmacy_id: number | null;
    is_active: boolean;
    password: string;
  }) => Promise<void>;
  onDelete: (userId: number) => Promise<void>;
}) {
  const [form, setForm] = useState<{
    email: string;
    full_name: string;
    role: UserRole;
    pharmacy_id: number | null;
    is_active: boolean;
    password: string;
  }>({
    email: "",
    full_name: "",
    role: props.currentUser.role === "manager" ? ("pharmacist" as UserRole) : ("manager" as UserRole),
    pharmacy_id: props.currentUser.pharmacy_id ?? props.pharmacies[0]?.id ?? null,
    is_active: true,
    password: "",
  });

  return (
    <div className="page-grid">
      {props.canManage ? (
        <Panel title="Новий співробітник" subtitle="Адмін створює будь-які ролі, менеджер тільки фармацевтів своєї аптеки.">
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void props.onCreate(form);
            }}
          >
            <input placeholder="ПІБ" value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} required />
            <input placeholder="Email" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />
            <input placeholder="Пароль" type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required />
            <select
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value as UserRole })}
              disabled={props.currentUser.role === "manager"}
            >
              {props.currentUser.role === "admin" ? (
                <>
                  <option value="manager">manager</option>
                  <option value="pharmacist">pharmacist</option>
                  <option value="admin">admin</option>
                </>
              ) : (
                <option value="pharmacist">pharmacist</option>
              )}
            </select>
            <select
              value={form.pharmacy_id ?? ""}
              onChange={(event) => setForm({ ...form, pharmacy_id: event.target.value ? Number(event.target.value) : null })}
              disabled={props.currentUser.role === "manager"}
            >
              {props.pharmacies
                .filter((pharmacy) => props.currentUser.role === "admin" || pharmacy.id === props.currentUser.pharmacy_id)
                .map((pharmacy) => (
                  <option key={pharmacy.id} value={pharmacy.id}>
                    {pharmacy.name}
                  </option>
                ))}
            </select>
            <label className="checkbox-field">
              <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
              <span>Активний користувач</span>
            </label>
            <button className="primary-button" type="submit">Створити співробітника</button>
          </form>
        </Panel>
      ) : null}

      <Panel title="Список співробітників" subtitle="Користувачі, доступні поточній ролі.">
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>ПІБ</th>
                <th>Роль</th>
                <th>Email</th>
                {props.canManage ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {props.staff.map((staffUser) => (
                <tr key={staffUser.id}>
                  <td>{staffUser.id}</td>
                  <td>{staffUser.full_name}</td>
                  <td>{roleLabel(staffUser.role)}</td>
                  <td>{staffUser.email}</td>
                  {props.canManage ? (
                    <td className="table-actions">
                      <button type="button" onClick={() => void props.onDelete(staffUser.id)}>Видалити</button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function AuditPage(props: { logs: AuditLog[] }) {
  return (
    <Panel title="Журнал аудиту" subtitle="Останні дії системи та користувачів.">
      <div className="list-stack">
        {props.logs.map((log) => (
          <details key={log.id} className="card">
            <summary className="summary-row">
              <div>
                <strong>{log.action}</strong>
                <p>User ID: {log.user_id ?? "system"}</p>
              </div>
              <span>{formatDateTime(log.created_at)}</span>
            </summary>
            <pre className="preformatted">{JSON.stringify(log.details, null, 2)}</pre>
          </details>
        ))}
      </div>
    </Panel>
  );
}

function Panel(props: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h3>{props.title}</h3>
          <p>{props.subtitle}</p>
        </div>
      </div>
      {props.children}
    </section>
  );
}

function MetricCard(props: { title: string; value: string; tone?: "danger" }) {
  return (
    <div className={props.tone === "danger" ? "metric-card metric-card--danger" : "metric-card"}>
      <span>{props.title}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function AlertCard(props: { alert: ActiveAlert }) {
  return (
    <div className="card card--alert">
      <div className="card-row">
        <strong>{props.alert.pharmacy_name ?? "Невідома аптека"}</strong>
        <span className={props.alert.severity === "critical" ? "pill pill--danger" : "pill pill--warn"}>
          {props.alert.severity === "critical" ? "Критично" : "Попередження"}
        </span>
      </div>
      <p>{props.alert.message}</p>
      <div className="card-meta">
        <span>{props.alert.storage_location_name ?? "Невідома локація"}</span>
        <span>{relativeTime(props.alert.created_at)}</span>
      </div>
    </div>
  );
}

function EmptyState(props: { text: string }) {
  return <div className="empty-state">{props.text}</div>;
}

function roleLabel(role: UserRole) {
  switch (role) {
    case "admin":
      return "Адміністратор";
    case "manager":
      return "Завідувач";
    case "pharmacist":
      return "Фармацевт";
  }
}

function viewSubtitle(view: ViewKey, role: UserRole) {
  if (view === "dashboard") {
    return role === "admin"
      ? "Мережевий стан аптек, персоналу та продажів."
      : "Оперативна зведенка по вашій аптеці.";
  }
  if (view === "alerts") {
    return "Контроль відхилень температури та вологості.";
  }
  if (view === "history") {
    return "Історія всіх інцидентів і змін стану.";
  }
  if (view === "pharmacies") {
    return role === "admin" ? "Усі аптеки мережі." : "Інформація по вашій аптеці.";
  }
  if (view === "locations") {
    return "Керування холодильниками й місцями зберігання.";
  }
  if (view === "devices") {
    return "IoT-пристрої та їх прив'язка до локацій.";
  }
  if (view === "inventory") {
    return "Ліки, партії, списання та контроль терміну дії.";
  }
  if (view === "sales") {
    return "Оформлення чеків і перегляд історії продажів.";
  }
  if (view === "staff") {
    return "Створення та контроль співробітників.";
  }
  return "Журнал системних подій і дій користувачів.";
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("uk-UA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function relativeTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 1) {
    return "щойно";
  }
  if (minutes < 60) {
    return `${minutes} хв тому`;
  }
  if (minutes < 1440) {
    return `${Math.floor(minutes / 60)} год тому`;
  }
  return `${Math.floor(minutes / 1440)} дн тому`;
}

function formatSensorState(temperature: number | null, humidity: number | null) {
  if (temperature == null && humidity == null) {
    return "Сенсорні дані недоступні";
  }
  return `Температура ${temperature ?? "—"}°C • Вологість ${humidity ?? "—"}%`;
}
