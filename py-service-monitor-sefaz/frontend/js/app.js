const form = document.getElementById("configForm");
const authForm = document.getElementById("authForm");
const alertContainer = document.getElementById("alertContainer");
const healthBadge = document.getElementById("healthBadge");
const historyTableBody = document.getElementById("historyTableBody");

async function apiFetch(url, options = {}) {
  const response = await fetch(url, options);

  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Sessao expirada.");
  }

  return response;
}

function showAlert(message, type = "success") {
  alertContainer.innerHTML = `
    <div class="alert alert-${type} alert-dismissible fade show shadow-sm" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;
}

function serializeForm() {
  return {
    url_sefaz: document.getElementById("url_sefaz").value.trim(),
    telegram_token: document.getElementById("telegram_token").value.trim(),
    telegram_chat_id: document.getElementById("telegram_chat_id").value.trim(),
    webhook_url: document.getElementById("webhook_url").value.trim(),
    check_interval_seconds: Number(
      document.getElementById("check_interval_seconds").value,
    ),
    request_timeout_seconds: Number(
      document.getElementById("request_timeout_seconds").value,
    ),
    monitor_enabled: document.getElementById("monitor_enabled").checked,
    telegram_enabled: document.getElementById("telegram_enabled").checked,
    webhook_enabled: document.getElementById("webhook_enabled").checked,
  };
}

function fillForm(config) {
  document.getElementById("url_sefaz").value = config.url_sefaz || "";
  document.getElementById("telegram_token").value = config.telegram_token || "";
  document.getElementById("telegram_chat_id").value =
    config.telegram_chat_id || "";
  document.getElementById("webhook_url").value = config.webhook_url || "";
  document.getElementById("check_interval_seconds").value =
    config.check_interval_seconds || 60;
  document.getElementById("request_timeout_seconds").value =
    config.request_timeout_seconds || 30;
  document.getElementById("monitor_enabled").checked = Boolean(
    config.monitor_enabled,
  );
  document.getElementById("telegram_enabled").checked = Boolean(
    config.telegram_enabled,
  );
  document.getElementById("webhook_enabled").checked = Boolean(
    config.webhook_enabled,
  );
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("pt-BR");
}

function renderStatus(status) {
  const lastResult = status.last_result;
  const indisponiveis = lastResult?.indisponiveis?.length || 0;

  document.getElementById("threadState").textContent = status.thread_alive
    ? "thread ativa"
    : "thread parada";
  document.getElementById("runningValue").textContent = status.running
    ? "sim"
    : "nao";
  document.getElementById("lastStartValue").textContent = formatDateTime(
    status.last_run_started_at,
  );
  document.getElementById("lastFinishValue").textContent = formatDateTime(
    status.last_run_finished_at,
  );
  document.getElementById("durationValue").textContent =
    status.last_duration_seconds ? `${status.last_duration_seconds}s` : "-";
  document.getElementById("lastErrorValue").textContent =
    status.last_error || "-";
  document.getElementById("lastResultValue").textContent = lastResult
    ? `${lastResult.message} (${indisponiveis} indisponibilidade(s))`
    : "-";
  document.getElementById("webhookValue").textContent = status.config
    ?.webhook_enabled
    ? "habilitado"
    : "desabilitado";

  const monitorEnabled = status.config?.monitor_enabled;
  healthBadge.textContent = monitorEnabled
    ? "monitor ativo"
    : "monitor pausado";
  healthBadge.classList.toggle("is-paused", !monitorEnabled);
}

async function loadConfig() {
  const response = await apiFetch("/api/config");
  const config = await response.json();
  fillForm(config);
}

async function loadStatus() {
  const response = await apiFetch("/api/status");
  const payload = await response.json();
  renderStatus(payload.status);
}

function renderHistory(alerts) {
  if (!alerts.length) {
    historyTableBody.innerHTML = `
      <tr>
        <td colspan="6" class="text-muted">Nenhum alerta registrado.</td>
      </tr>
    `;
    return;
  }

  historyTableBody.innerHTML = alerts
    .map(
      (alert) => `
        <tr>
          <td>${formatDateTime(alert.created_at)}</td>
          <td>${alert.channel}</td>
          <td>${alert.destination || "-"}</td>
          <td>${alert.success ? "enviado" : "falhou"}</td>
          <td>${alert.indisponiveis_count}</td>
          <td>${alert.error_message || "-"}</td>
        </tr>
      `,
    )
    .join("");
}

async function loadHistory() {
  const response = await apiFetch("/api/alerts?limit=20");
  const payload = await response.json();
  renderHistory(payload.alerts || []);
}

async function loadAuthSettings() {
  const response = await apiFetch("/api/auth/me");
  const payload = await response.json();
  document.getElementById("panelUsernameValue").textContent =
    payload.auth.panel_username;
  document.getElementById("new_username").value = payload.auth.panel_username;
}

async function postAction(endpoint, successMessage) {
  const response = await apiFetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || "Falha ao executar acao.");
  }

  showAlert(successMessage || payload.message, "success");
  await Promise.all([loadConfig(), loadStatus()]);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const response = await apiFetch("/api/config", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(serializeForm()),
    });

    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || "Falha ao salvar configuracao.");
    }

    fillForm(payload.config);
    showAlert("Configuracao salva com sucesso.", "success");
    await Promise.all([loadStatus(), loadHistory()]);
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const response = await apiFetch("/api/auth/credentials", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        current_password: document.getElementById("current_password").value,
        new_username: document.getElementById("new_username").value.trim(),
        new_password: document.getElementById("new_password").value,
      }),
    });

    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || "Falha ao atualizar credenciais.");
    }

    document.getElementById("current_password").value = "";
    document.getElementById("new_password").value = "";
    document.getElementById("panelUsernameValue").textContent =
      payload.auth.panel_username;
    showAlert("Credenciais atualizadas com sucesso.", "success");
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

document
  .getElementById("reloadConfigBtn")
  .addEventListener("click", async () => {
    try {
      await Promise.all([
        loadConfig(),
        loadStatus(),
        loadHistory(),
        loadAuthSettings(),
      ]);
      showAlert("Configuracao recarregada.", "secondary");
    } catch (error) {
      showAlert(error.message, "danger");
    }
  });

document.getElementById("runNowBtn").addEventListener("click", async () => {
  try {
    await postAction("/api/actions/run-now", "Execucao manual solicitada.");
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

document.getElementById("startBtn").addEventListener("click", async () => {
  try {
    await postAction("/api/actions/start", "Monitor ativado.");
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

document.getElementById("stopBtn").addEventListener("click", async () => {
  try {
    await postAction("/api/actions/stop", "Monitor pausado.");
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

document.getElementById("restartBtn").addEventListener("click", async () => {
  try {
    await postAction(
      "/api/actions/restart",
      "Reinicio solicitado. A interface pode ficar indisponivel por alguns segundos.",
    );
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  try {
    await apiFetch("/logout", { method: "POST" });
    window.location.href = "/login";
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

async function bootstrap() {
  try {
    await Promise.all([
      loadConfig(),
      loadStatus(),
      loadHistory(),
      loadAuthSettings(),
    ]);
  } catch (error) {
    showAlert(error.message, "danger");
  }
}

bootstrap();
setInterval(() => {
  Promise.all([loadStatus(), loadHistory()]).catch((error) => {
    showAlert(error.message, "danger");
  });
}, 5000);
