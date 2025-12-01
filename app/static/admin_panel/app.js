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
      <div class="panel-header">
        <h2>Панель управления</h2>
        <button class="secondary" id="logout-btn">Выйти</button>
      </div>
      <div class="panel-block">
        <div class="controls">
          <div>
            <label for="base-url">Базовый URL</label>
            <input type="text" id="base-url" value="${state.baseUrl}" placeholder="https://yourdomain.com">
          </div>
          <div>
            <label for="limit">Лимит записей</label>
            <input type="number" id="limit" min="1" max="500" value="${state.limit}">
          </div>
        </div>
        <div class="panel-header">
          <h3>Заявки</h3>
          <button id="load-subs">Обновить</button>
        </div>
        <div id="subs-status" class="muted"></div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Пользователь</th>
                <th>Банк</th>
                <th>Комментарий</th>
                <th>Статус</th>
                <th>Создано</th>
              </tr>
            </thead>
            <tbody id="subs-body"></tbody>
          </table>
        </div>
      </div>

      <div class="panel-block">
        <div class="panel-header">
          <h3>Последние действия</h3>
          <button class="secondary" id="load-actions">Обновить</button>
        </div>
        <div id="actions-status" class="muted"></div>
        <ul id="actions-list" class="logs"></ul>
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

  document.getElementById("load-subs").addEventListener("click", loadSubmissions);
  document.getElementById("load-actions").addEventListener("click", loadActions);

  loadSubmissions();
  loadActions();
}

async function loadSubmissions() {
  const status = document.getElementById("subs-status");
  const body = document.getElementById("subs-body");
  status.textContent = "Загружаю...";
  body.innerHTML = "";
  try {
    const data = await apiFetch(`/submissions?limit=${state.limit}`);
    status.textContent = `Заявок: ${data.items.length}`;
    data.items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${item.id}</td>
        <td>${item.username || item.user_id || "—"}</td>
        <td>${item.bank}</td>
        <td>${item.comment || "—"}</td>
        <td><span class="pill">${item.status}</span></td>
        <td>${item.created_at}</td>
      `;
      body.appendChild(tr);
    });
  } catch (err) {
    status.textContent = err.message;
  }
}

async function loadActions() {
  const status = document.getElementById("actions-status");
  const list = document.getElementById("actions-list");
  status.textContent = "Загружаю...";
  list.innerHTML = "";
  try {
    const data = await apiFetch(`/actions?limit=${state.limit}`);
    status.textContent = `Событий: ${data.items.length}`;
    data.items.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `${item.created_at} — ${item.action} — user: ${item.username || item.user_id || "—"} — details: ${JSON.stringify(item.details || {})}`;
      list.appendChild(li);
    });
  } catch (err) {
    status.textContent = err.message;
  }
}

yearLabel.textContent = new Date().getFullYear();

renderLogin();
