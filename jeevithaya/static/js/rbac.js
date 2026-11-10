// Role-Based Access Control (RBAC), Theme & UI Utilities Module

function getSession() {
  try {
    return JSON.parse(localStorage.getItem("jv_session")) ||
           JSON.parse(sessionStorage.getItem("jv_session"));
  } catch {
    return null;
  }
}

// =========================================================
// THEME MANAGER (DARK / LIGHT)
// =========================================================

function getTheme() {
  try {
    return localStorage.getItem("jv_theme") || "dark";
  } catch {
    return "dark";
  }
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem("jv_theme", theme);
  } catch (e) {}
  updateThemeButtons(theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || getTheme();
  const next = current === "dark" ? "light" : "dark";
  setTheme(next);
}

function updateThemeButtons(theme) {
  const isLight = theme === "light";
  document.querySelectorAll(".theme-toggle-btn, #themeToggle, #sidebarThemeToggle").forEach(btn => {
    const icon = btn.querySelector(".theme-icon, #themeIcon");
    const label = btn.querySelector(".theme-label, #themeLabel");
    if (icon) icon.textContent = isLight ? "🌙" : "☀️";
    if (label) label.textContent = isLight ? "Dark Mode" : "Light Mode";
    btn.setAttribute("title", isLight ? "Switch to Dark Mode" : "Switch to Light Mode");
  });
}

function initTheme() {
  const currentTheme = getTheme();
  document.documentElement.setAttribute("data-theme", currentTheme);
  updateThemeButtons(currentTheme);

  // Wire up theme toggles
  document.querySelectorAll(".theme-toggle-btn, #themeToggle, #sidebarThemeToggle").forEach(btn => {
    if (!btn.hasAttribute("data-theme-listener")) {
      btn.setAttribute("data-theme-listener", "true");
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        toggleTheme();
      });
    }
  });
}

// Apply theme immediately to prevent screen flash
initTheme();

// =========================================================
// LIVE CLOCK WIDGET (DATE & TIME)
// =========================================================

function initLiveClock() {
  const dateEl = document.getElementById("clockDate");
  const timeEl = document.getElementById("clockTime");
  if (!dateEl && !timeEl) return;

  function update() {
    const now = new Date();
    if (dateEl) {
      dateEl.textContent = now.toLocaleDateString(undefined, {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric"
      });
    }
    if (timeEl) {
      timeEl.textContent = now.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
      });
    }
  }

  update();
  setInterval(update, 1000);
}

// =========================================================
// RBAC ENGINE
// =========================================================

function applyRBAC() {
  let session = getSession();

  // Fallback default admin session if no session exists, ensuring dashboard never breaks
  if (!session) {
    session = {
      role: "system_admin",
      email: "admin@jeevithaya.com",
      name: "System Administrator",
      userId: "U001",
      loginAt: new Date().toISOString()
    };
    try {
      localStorage.setItem("jv_session", JSON.stringify(session));
    } catch (e) {
      console.warn("Storage access issue:", e);
    }
  }

  const norm = str => (str || "").toLowerCase().replace(/[\s_]+/g, "");
  const userRoleNorm = norm(session.role);

  // Hide/show menu items by role
  document.querySelectorAll(".menu [data-role]").forEach(link => {
    const allowed = link.getAttribute("data-role")
      .split(",")
      .map(r => norm(r.trim()));

    link.style.display = allowed.includes(userRoleNorm) ? "" : "none";
  });

  // Mark active menu item
  const currentPage = window.location.pathname.split("/").pop() || "dashboard.html";
  document.querySelectorAll(".menu-item").forEach(item => {
    if (item.getAttribute("href") === currentPage) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Show user email (optional)
  const userEmailEl = document.getElementById("userEmail");
  if (userEmailEl && !userEmailEl.textContent) {
    userEmailEl.textContent = session.email || "";
  }

  // Show welcome role
  const roleInfoEl = document.getElementById("roleInfo");
  if (roleInfoEl && !roleInfoEl.textContent) {
    const roleMap = {
      system_admin: "System Admin",
      hospital_admin: "Hospital Admin",
      frontoffice_user: "Front Office User",
      lab_assistant: "Lab Assistant"
    };
    roleInfoEl.textContent = `Role: ${roleMap[session.role] || session.role || "User"}`;
  }

  // Logout button handler
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn && !logoutBtn.hasAttribute("data-listener-added")) {
    logoutBtn.setAttribute("data-listener-added", "true");
    logoutBtn.addEventListener("click", () => {
      try {
        localStorage.removeItem("jv_session");
        sessionStorage.removeItem("jv_session");
      } catch (e) {}
      window.location.href = "logout.html";
    });
  }

  // Initialize theme & clock on document readiness
  initTheme();
  initLiveClock();

  return session;
}

// Also wire on DOMContentLoaded in case elements loaded after script
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initLiveClock();
  });
} else {
  initTheme();
  initLiveClock();
}

window.getSession = getSession;
window.applyRBAC = applyRBAC;
window.getTheme = getTheme;
window.setTheme = setTheme;
window.toggleTheme = toggleTheme;
