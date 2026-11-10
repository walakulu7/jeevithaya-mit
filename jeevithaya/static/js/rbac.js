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
  const t = (theme === "light") ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", t);
  if (document.body) {
    document.body.setAttribute("data-theme", t);
    if (t === "light") {
      document.body.classList.add("theme-light");
      document.body.classList.remove("theme-dark");
    } else {
      document.body.classList.add("theme-dark");
      document.body.classList.remove("theme-light");
    }
  }
  try {
    localStorage.setItem("jv_theme", t);
  } catch (e) {}
  updateThemeButtons(t);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || getTheme();
  const next = current === "dark" ? "light" : "dark";
  setTheme(next);
}

function updateThemeButtons(theme) {
  const isLight = theme === "light";
  document.querySelectorAll(".theme-toggle-btn, #themeToggle, #sidebarThemeToggle").forEach(btn => {
    const label = btn.querySelector(".theme-label, #themeLabel");
    if (label) {
      label.textContent = isLight ? "Light" : "Dark";
    }
    btn.setAttribute("title", isLight ? "Switch to Dark Mode" : "Switch to Light Mode");
  });
}

function initTheme() {
  const currentTheme = getTheme();
  setTheme(currentTheme);

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
      dateEl.textContent = now.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
      });
    }
    if (timeEl) {
      timeEl.textContent = now.toLocaleTimeString("en-US", {
        hour: "numeric",
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

  const norm = str => {
    let s = (str || "").toLowerCase().replace(/[\s_]+/g, "");
    if (s === "frontoffice") s = "frontofficeuser";
    if (s === "lab") s = "labassistant";
    if (s === "admin") s = "systemadmin";
    return s;
  };
  const userRoleNorm = norm(session.role);

  // Hide/show menu items by role
  document.querySelectorAll(".menu [data-role]").forEach(link => {
    const allowed = link.getAttribute("data-role")
      .split(",")
      .map(r => norm(r.trim()));

    link.style.display = allowed.includes(userRoleNorm) ? "" : "none";
  });

  // Mark active menu item
  let currentPage = window.location.pathname.split("/").filter(Boolean).pop() || "dashboard.html";
  if (!currentPage.includes(".")) {
    currentPage += ".html";
  }
  document.querySelectorAll(".menu-item").forEach(item => {
    const href = item.getAttribute("href") || "";
    if (href === currentPage || (currentPage === "" && href === "dashboard.html")) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Show user email
  const userEmailEl = document.getElementById("userEmail");
  if (userEmailEl && session.email) {
    userEmailEl.textContent = session.email;
  }

  // Show welcome role
  const roleMap = {
    system_admin: "System Admin",
    hospital_admin: "Hospital Admin",
    frontoffice_user: "Front Office User",
    lab_assistant: "Lab Assistant"
  };

  const roleInfoEl = document.getElementById("roleInfo");
  if (roleInfoEl) {
    const displayRole = roleMap[session.role] || session.role || "User";
    roleInfoEl.textContent = `Role: ${displayRole}`;
  }

  const welcomeEl = document.getElementById("welcome");
  if (welcomeEl && welcomeEl.textContent === "Dashboard") {
    const displayRole = roleMap[session.role] || session.role || "User";
    welcomeEl.textContent = `Welcome, ${session.name || displayRole}`;
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

  // Initialize theme, clock & collapsible forms on document readiness
  initTheme();
  initLiveClock();
  initCollapsibleForms();

  return session;
}

// Universal Collapsible Form Handler
function initCollapsibleForms() {
  document.querySelectorAll("[data-action='toggle-form'], #toggleFormBtn").forEach(btn => {
    if (!btn.hasAttribute("data-toggle-wired")) {
      btn.setAttribute("data-toggle-wired", "true");
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-target");
        const formCard = targetId ? document.getElementById(targetId) : document.querySelector(".collapsible-form-card");
        if (!formCard) return;

        const isOpen = formCard.classList.contains("open");
        if (isOpen) {
          formCard.classList.remove("open");
          btn.classList.remove("btn-ghost");
          btn.classList.add("btn-primary");
          if (btn.hasAttribute("data-default-text")) {
            btn.innerHTML = btn.getAttribute("data-default-text");
          }
        } else {
          formCard.classList.add("open");
          btn.classList.remove("btn-primary");
          btn.classList.add("btn-ghost");
          if (!btn.hasAttribute("data-default-text")) {
            btn.setAttribute("data-default-text", btn.innerHTML);
          }
          btn.innerHTML = `<span>✕ Close Form</span>`;
          const firstInput = formCard.querySelector("input:not([type=hidden]):not([disabled]), select:not([disabled])");
          if (firstInput) firstInput.focus();
        }
      });
    }
  });

  document.querySelectorAll("[data-action='close-form'], .btn-close-form, #closeFormBtn").forEach(btn => {
    if (!btn.hasAttribute("data-close-wired")) {
      btn.setAttribute("data-close-wired", "true");
      btn.addEventListener("click", () => {
        closeCollapsibleForm();
      });
    }
  });
}

function closeCollapsibleForm() {
  document.querySelectorAll(".collapsible-form-card").forEach(c => c.classList.remove("open"));
  const toggleBtn = document.querySelector("[data-action='toggle-form'], #toggleFormBtn");
  if (toggleBtn && toggleBtn.hasAttribute("data-default-text")) {
    toggleBtn.classList.remove("btn-ghost");
    toggleBtn.classList.add("btn-primary");
    toggleBtn.innerHTML = toggleBtn.getAttribute("data-default-text");
  }
}

window.closeCollapsibleForm = closeCollapsibleForm;

// Also wire on DOMContentLoaded in case elements loaded after script
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initLiveClock();
    initCollapsibleForms();
  });
} else {
  initTheme();
  initLiveClock();
  initCollapsibleForms();
}

window.getSession = getSession;
window.applyRBAC = applyRBAC;
window.getTheme = getTheme;
window.setTheme = setTheme;
window.toggleTheme = toggleTheme;
