const root = document.getElementById("root");
const yearLabel = document.getElementById("year");

const STORAGE_BASE_KEY = "referral_admin_base";
const STORAGE_LIMIT_KEY = "referral_admin_limit";

const state = {
  authenticated: false,
  baseUrl: localStorage.getItem(STORAGE_BASE_KEY) || "",
  limit: parseInt(localStorage.getItem(STORAGE_LIMIT_KEY) || "50", 10),
};

function setBaseUrl(url) {
  state.baseUrl = url;
  if (url) localStorage.setItem(STORAGE_BASE_KEY, url);
}

function setLimit(limit) {
  state.limit = limit;
  localStorage.setItem(STORAGE_LIMIT_KEY, String(limit));
}

function apiUrl(path) {
  const base = state.baseUrl?.trim() || "";
  const normalized = base ? base.replace(/\/$/, "") : "";
  return `${normalized}${path}`;
}

function showMessage(text) {
  alert(text);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    throw new Error("Не авторизован. Зайдите заново.");
  }

  if (!response.ok) {
    let details = "Ошибка запроса.";
    try {
      const data = await response.json();
      details = data.detail || JSON.stringify(data);
    } catch {
      details = await response.text();
    }
    throw new Error(details);
  }

  if (response.status === 204) return null;
  return response.json();
}

function renderLogin() {
  root.innerHTML = `
    <section class="card">
      <h2>Вход в админ-панель</h2>
      <form id="login-form">
        <label for="admin-id">Telegram ID</label>
        <input type="text" id="admin-id" placeholder="Введите ID" inputmode="numeric" pattern="\\d*" required>

        <label for="password">Пароль</label>
        <div class="password-input">
          <input type="password" id="password" placeholder="Введите пароль" required>
          <button type="button" class="password-toggle" data-target="password">Показать</button>
        </div>

        <label for="base-url">Базовый URL (необязательно)</label>
        <input type="text" id="base-url" placeholder="https://yourdomain.com" value="${state.baseUrl}">

        <button type="submit">Войти</button>
      </form>
      <p class="hint">Данные берутся из окружения бота: ADMIN_USER_ID / ADMIN_PASSWORD. После входа ставится cookie-сессия.</p>
    </section>
  `;

  document.querySelectorAll(".password-toggle").forEach((btn) => {
    const target = document.getElementById(btn.dataset.target);
    btn.addEventListener("click", () => {
      const hidden = target.type === "password";
      target.type = hidden ? "text" : "password";
      btn.textContent = hidden ? "Скрыть" : "Показать";
    });
  });

  const form = document.getElementById("login-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const adminId = form.querySelector("#admin-id").value.trim();
    const password = form.querySelector("#password").value.trim();
    const base = form.querySelector("#base-url").value.trim();
    if (base) setBaseUrl(base);

    if (!adminId || !password) {
      showMessage("Заполните логин и пароль.");
      return;
    }

    try {
      const body = new URLSearchParams();
      body.append("user_id", adminId);
      body.append("password", password);
      await fetch(apiUrl("/admin/login"), {
        method: "POST",
        body,
        credentials: "include",
      });
      state.authenticated = true;
      renderPanel();
    } catch (err) {
      showMessage(err.message);
    }
  });
}

function renderPanel() {
  root.innerHTML = `
    <section class="card">
      <div class="panel-header top-bar">
        <div>
          <h2>Панель управления</h2>
          <p class="muted small">Бот и веб-админка</p>
        </div>
        <button class="secondary" id="logout-btn">Выйти</button>
      </div>

      <div class="summary-grid panel-block">
        <div>
          <div class="panel-header">
            <h3>Пользователи</h3>
            <button class="secondary" id="refresh-all">Обновить</button>
          </div>
          <div class="stats-row">
            <div class="stat-card">
              <div class="stat-label">ВСЕГО</div>
              <div class="stat-value" id="stat-users-all">—</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">ЗА НЕДЕЛЮ</div>
              <div class="stat-value" id="stat-users-week">—</div>
            </div>
          </div>
        </div>
        <div class="settings">
          <label for="base-url">Базовый URL</label>
          <input type="text" id="base-url" value="${state.baseUrl}" placeholder="https://yourdomain.com">
          <label for="limit">Лимит записей</label>
          <input type="number" id="limit" min="1" max="500" value="${state.limit}">
        </div>
      </div>

      <div class="panel-block">
        <div class="panel-header">
          <h3>Вопросы админам</h3>
          <button class="secondary" id="load-questions">Обновить</button>
        </div>
        <div id="questions-status" class="muted"></div>
        <div class="cards-grid" id="questions-cards"></div>
      </div>

      <div class="panel-block">
        <div class="panel-header">
          <h3>Отчеты (карты)</h3>
          <button class="secondary" id="load-reports">Обновить</button>
        </div>
        <div id="reports-status" class="muted"></div>
        <div class="cards-grid" id="reports-cards"></div>
      </div>

      <div class="panel-block">
        <div class="panel-header">
          <h3>Добавить карту</h3>
        </div>
        <form id="card-form">
          <label for="card-title">Название карты</label>
          <input type="text" id="card-title" placeholder="Например, Карта Альфа" required>
          <label for="card-payout">Выплата</label>
          <input type="text" id="card-payout" placeholder="Например, 500 ₽" required>
          <label for="card-note">Комментарий</label>
          <textarea id="card-note" rows="2" placeholder="Доп. условия (необязательно)"></textarea>
          <button type="submit">Добавить задание</button>
          <div id="card-status" class="muted"></div>
        </form>
      </div>

      <div class="panel-block">
        <div class="panel-header">
          <h3>Рассылка всем пользователям</h3>
        </div>
        <div id="broadcast-status" class="muted"></div>
        <form id="broadcast-form">
          <label for="broadcast-message">Текст рассылки</label>
          <textarea id="broadcast-message" rows="3" placeholder="Введите текст"></textarea>
          <button type="submit">Отправить</button>
        </form>
      </div>
    </section>
  `;

  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      await fetch(apiUrl("/admin/logout"), { method: "GET", credentials: "include" });
    } catch {
      // ignore
    } finally {
      state.authenticated = false;
      renderLogin();
    }
  });

  document.getElementById("base-url").addEventListener("change", (e) => {
    setBaseUrl(e.target.value.trim());
  });
  document.getElementById("limit").addEventListener("change", (e) => {
    const n = parseInt(e.target.value, 10) || 50;
    setLimit(n);
  });

  document.getElementById("refresh-all").addEventListener("click", () => {
    loadSubmissions();
    loadActions();
    loadQuestions();
    loadReports();
  });
  document.getElementById("load-questions").addEventListener("click", loadQuestions);
  document.getElementById("load-reports").addEventListener("click", loadReports);
  document.getElementById("broadcast-form").addEventListener("submit", handleBroadcast);
  document.getElementById("card-form").addEventListener("submit", handleAddCard);

  loadSubmissions();
  loadActions();
  loadQuestions();
  loadReports();
}

async function loadSubmissions() {
  const statusUsersAll = document.getElementById("stat-users-all");
  const statusUsersWeek = document.getElementById("stat-users-week");
  statusUsersAll.textContent = "—";
  statusUsersWeek.textContent = "—";
  try {
    const data = await apiFetch(`/submissions?limit=${state.limit}`);
    const uniqueUsers = new Set(data.items.map((i) => i.user_id).filter(Boolean));
    statusUsersAll.textContent = uniqueUsers.size || "0";

    const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    const weekUsers = new Set(
      data.items
        .filter((i) => Date.parse(i.created_at) >= weekAgo)
        .map((i) => i.user_id)
        .filter(Boolean)
    );
    statusUsersWeek.textContent = weekUsers.size || "0";
  } catch (err) {
    statusUsersAll.textContent = "Ошибка";
    statusUsersWeek.textContent = "Ошибка";
  }
}

async function loadActions() {
  try {
    const data = await apiFetch(`/actions?limit=${state.limit}`);
    // можно отрисовать при необходимости
  } catch (err) {
    // ignore
  }
}

async function loadQuestions() {
  const status = document.getElementById("questions-status");
  const container = document.getElementById("questions-cards");
  status.textContent = "Загружаю...";
  container.innerHTML = "";
  try {
    const data = await apiFetch(`/questions?limit=${state.limit}`);
    const items = (data.items || []).filter((i) => (i.message || "").trim().length >= 5);
    status.textContent = `Вопросов: ${items.length}`;
    if (!items.length) {
      container.innerHTML = `<p class="muted">Нет вопросов.</p>`;
      return;
    }
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "mini-card";
      card.innerHTML = `
        <div class="mini-title">#${item.id} · ${item.username || item.user_id || "—"}</div>
        <div class="mini-body">${item.message || "—"}</div>
        <div class="mini-meta">
          <span>${item.created_at}</span>
          <span>${item.file_id || ""}</span>
        </div>
        <div class="mini-actions">
          <button data-id="${item.id}" class="secondary reply-question">Ответить</button>
          <button data-id="${item.id}" class="danger reject-question">Отклонить</button>
        </div>
      `;
      container.appendChild(card);
    });
    container.querySelectorAll(".reply-question").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.dataset.id;
        const text = prompt("Введите ответ пользователю:");
        if (!text) return;
        try {
          await apiFetch(`/questions/${id}/reply`, {
            method: "POST",
            body: JSON.stringify({ message: text }),
          });
          showMessage("Ответ отправлен.");
          loadActions();
        } catch (err) {
          showMessage(err.message);
        }
      });
    });
    container.querySelectorAll(".reject-question").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.dataset.id;
        if (!confirm("Отклонить вопрос и убрать из списка?")) return;
        try {
          await apiFetch(`/questions/${id}/reject`, { method: "POST" });
          e.target.closest(".mini-card").remove();
          showMessage("Отклонено.");
          loadActions();
        } catch (err) {
          showMessage(err.message);
        }
      });
    });
  } catch (err) {
    status.textContent = err.message;
  }
}

async function loadReports() {
  const status = document.getElementById("reports-status");
  const container = document.getElementById("reports-cards");
  status.textContent = "Загружаю...";
  container.innerHTML = "";
  try {
    const data = await apiFetch(`/reports?limit=${state.limit}`);
    status.textContent = `Отчетов: ${data.items.length}`;
    if (!data.items.length) {
      container.innerHTML = `<p class="muted">Нет отчетов.</p>`;
      return;
    }
    data.items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "mini-card";
      card.innerHTML = `
        <div class="mini-title">#${item.id} · ${item.username || item.user_id || "—"}</div>
        <div class="mini-body">${item.message || "—"}</div>
        <div class="mini-meta">
          <span>${item.created_at}</span>
          <span>${item.file_id || ""}</span>
        </div>
        <div class="mini-actions">
          <button data-id="${item.id}" class="secondary reply-report">Ответить</button>
        </div>
      `;
      container.appendChild(card);
    });
    container.querySelectorAll(".reply-report").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.dataset.id;
        const text = prompt("Введите ответ по отчету:");
        if (!text) return;
        try {
          await apiFetch(`/reports/${id}/reply`, {
            method: "POST",
            body: JSON.stringify({ message: text }),
          });
          showMessage("Ответ отправлен.");
          loadActions();
        } catch (err) {
          showMessage(err.message);
        }
      });
    });
  } catch (err) {
    status.textContent = err.message;
  }
}

async function handleAddCard(event) {
  event.preventDefault();
  const title = document.getElementById("card-title").value.trim();
  const payout = document.getElementById("card-payout").value.trim();
  const note = document.getElementById("card-note").value.trim();
  const status = document.getElementById("card-status");
  if (!title || !payout) {
    showMessage("Укажите название и выплату.");
    return;
  }
  status.textContent = "Сохраняю...";
  try {
    await apiFetch("/cards", {
      method: "POST",
      body: JSON.stringify({ title, payout, note }),
    });
    status.textContent = "Сохранено.";
    document.getElementById("card-form").reset();
  } catch (err) {
    status.textContent = err.message;
    showMessage(err.message);
  }
}

async function handleBroadcast(event) {
  event.preventDefault();
  const textarea = document.getElementById("broadcast-message");
  const status = document.getElementById("broadcast-status");
  const text = textarea.value.trim();
  if (!text) {
    showMessage("Введите текст рассылки.");
    return;
  }
  status.textContent = "Отправляю...";
  try {
    const data = await apiFetch("/broadcast", {
      method: "POST",
      body: JSON.stringify({ message: text }),
    });
    status.textContent = `Отправлено: ${data.sent}, ошибок: ${data.failed}`;
    showMessage("Рассылка завершена.");
    textarea.value = "";
  } catch (err) {
    status.textContent = err.message;
    showMessage(err.message);
  }
}

yearLabel.textContent = new Date().getFullYear();

renderLogin();
