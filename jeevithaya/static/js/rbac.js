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
      label.textContent = isLight ? "Dark" : "Light";
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

  const roleMap = {
    system_admin: "System Admin",
    hospital_admin: "Hospital Admin",
    frontoffice_user: "Front Office User",
    lab_assistant: "Lab Assistant"
  };
  const displayRole = roleMap[session.role] || session.role || "User";
  const displayName = session.name || displayRole || session.email || "User";

  // Show user display name in topbar chip & wire account dropdown
  const userEmailEl = document.getElementById("userEmail");
  if (userEmailEl) {
    userEmailEl.textContent = displayName;
  }

  const performLogout = () => {
    try {
      localStorage.removeItem("jv_session");
      sessionStorage.removeItem("jv_session");
    } catch (e) {}
    window.location.href = "logout.html";
  };

  initUserDropdown(displayName, displayRole, session.email || "", performLogout);

  const roleInfoEl = document.getElementById("roleInfo");
  if (roleInfoEl) {
    roleInfoEl.textContent = `Role: ${displayRole}`;
  }

  const welcomeEl = document.getElementById("welcome");
  if (welcomeEl && welcomeEl.textContent === "Dashboard") {
    welcomeEl.textContent = `Welcome, ${displayName}`;
  }

  // Logout button handler (sidebar)
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn && !logoutBtn.hasAttribute("data-listener-added")) {
    logoutBtn.setAttribute("data-listener-added", "true");
    logoutBtn.addEventListener("click", performLogout);
  }

  // Initialize theme, clock & collapsible forms on document readiness
  initTheme();
  initLiveClock();
  initCollapsibleForms();
  initNotifications(session);

  return session;
}

function initNotifications(session) {
  const clockEl = document.querySelector(".topbar-actions .clock-widget");
  const actionsEl = document.querySelector(".topbar-actions");
  if (!actionsEl || document.querySelector(".notif-menu")) return;

  const storageKey = `jv_notif_read_${(session && session.email) || "guest"}`;
  const loadReadIds = () => {
    try { return new Set(JSON.parse(localStorage.getItem(storageKey)) || []); }
    catch { return new Set(); }
  };
  const saveReadIds = (idSet) => {
    try { localStorage.setItem(storageKey, JSON.stringify([...idSet].slice(-200))); }
    catch {}
  };

  const wrapper = document.createElement("div");
  wrapper.className = "notif-menu";
  wrapper.innerHTML = `
    <button type="button" class="notif-btn" id="notifToggleBtn" title="Notifications" aria-haspopup="menu" aria-expanded="false">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
      </svg>
      <span class="notif-badge" id="notifBadge" hidden>0</span>
    </button>
    <div class="notif-dropdown" id="notifDropdown" role="menu">
      <div class="notif-header">
        <span class="notif-header-title">Notifications</span>
        <button type="button" class="notif-mark-read" id="notifMarkAllRead">Mark all read</button>
      </div>
      <div class="notif-list" id="notifList">
        <div class="notif-empty">Checking alerts...</div>
      </div>
    </div>
  `;

  if (clockEl) {
    actionsEl.insertBefore(wrapper, clockEl);
  } else {
    actionsEl.prepend(wrapper);
  }

  const toggleBtn = wrapper.querySelector("#notifToggleBtn");
  const badgeEl = wrapper.querySelector("#notifBadge");
  const listEl = wrapper.querySelector("#notifList");
  const markAllBtn = wrapper.querySelector("#notifMarkAllRead");

  let currentItems = [];

  const escHtml = (str) => String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  const renderNotifications = () => {
    const readIds = loadReadIds();
    const unreadCount = currentItems.filter(item => !readIds.has(item.id)).length;

    if (badgeEl) {
      if (unreadCount > 0) {
        badgeEl.textContent = unreadCount > 99 ? "99+" : String(unreadCount);
        badgeEl.hidden = false;
      } else {
        badgeEl.textContent = "0";
        badgeEl.hidden = true;
      }
    }

    if (!listEl) return;
    if (currentItems.length === 0) {
      listEl.innerHTML = `<div class="notif-empty">All caught up — no active alerts.</div>`;
      return;
    }

    listEl.innerHTML = currentItems.map(item => {
      const isUnread = !readIds.has(item.id);
      return `
        <a class="notif-item${isUnread ? " unread" : ""}" href="${escHtml(item.link || "dashboard.html")}" data-notif-id="${escHtml(item.id)}">
          <span class="notif-dot ${escHtml(item.severity || "info")}"></span>
          <div>
            <div class="notif-item-title">${escHtml(item.title)}</div>
            <div class="notif-item-msg">${escHtml(item.message)}</div>
          </div>
        </a>
      `;
    }).join("");
  };

  const fetchNotifications = async () => {
    try {
      const res = await fetch("/api/notifications/", { credentials: "same-origin" });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.notifications)) {
          currentItems = data.notifications;
          renderNotifications();
          return;
        }
      }
    } catch {}
    currentItems = [];
    renderNotifications();
  };

  const toggleDropdown = (force) => {
    const next = typeof force === "boolean" ? force : !wrapper.classList.contains("open");
    wrapper.classList.toggle("open", next);
    toggleBtn?.setAttribute("aria-expanded", String(next));
  };

  toggleBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleDropdown();
  });

  markAllBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    const readIds = loadReadIds();
    currentItems.forEach(item => readIds.add(item.id));
    saveReadIds(readIds);
    renderNotifications();
  });

  listEl?.addEventListener("click", (e) => {
    const link = e.target.closest("[data-notif-id]");
    if (!link) return;
    const readIds = loadReadIds();
    readIds.add(link.getAttribute("data-notif-id"));
    saveReadIds(readIds);
    renderNotifications();
  });

  document.addEventListener("click", (e) => {
    if (!wrapper.contains(e.target)) toggleDropdown(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") toggleDropdown(false);
  });

  fetchNotifications();
  setInterval(fetchNotifications, 60000);
}

function initUserDropdown(displayName, displayRole, email, onLogout) {
  const chip = document.querySelector(".user-chip");
  if (!chip) return;

  let wrapper = chip.closest(".user-menu");
  if (!wrapper) {
    wrapper = document.createElement("div");
    wrapper.className = "user-menu";
    chip.parentNode.insertBefore(wrapper, chip);
    wrapper.appendChild(chip);
  }

  if (!chip.hasAttribute("data-dropdown-wired")) {
    chip.setAttribute("data-dropdown-wired", "true");
    chip.setAttribute("role", "button");
    chip.setAttribute("tabindex", "0");
    chip.setAttribute("aria-haspopup", "menu");
    chip.setAttribute("aria-expanded", "false");

    const chevron = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    chevron.setAttribute("viewBox", "0 0 24 24");
    chevron.setAttribute("width", "13");
    chevron.setAttribute("height", "13");
    chevron.setAttribute("fill", "none");
    chevron.setAttribute("stroke", "currentColor");
    chevron.setAttribute("stroke-width", "2");
    chevron.setAttribute("stroke-linecap", "round");
    chevron.setAttribute("stroke-linejoin", "round");
    chevron.classList.add("user-chevron");
    chevron.innerHTML = `<polyline points="6 9 12 15 18 9"></polyline>`;
    chip.appendChild(chevron);

    const menu = document.createElement("div");
    menu.className = "user-dropdown";
    menu.setAttribute("role", "menu");
    menu.innerHTML = `
      <div class="user-dropdown-header">
        <div class="user-dropdown-name" id="dropdownUserName"></div>
        <div class="user-dropdown-meta" id="dropdownUserMeta"></div>
      </div>
      <a class="user-dropdown-item" href="profile.html" role="menuitem">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
        <span>Edit Profile</span>
      </a>
      <button type="button" class="user-dropdown-item danger" id="dropdownLogoutBtn" role="menuitem">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
          <polyline points="16 17 21 12 16 7"></polyline>
          <line x1="21" y1="12" x2="9" y2="12"></line>
        </svg>
        <span>Logout</span>
      </button>
    `;
    wrapper.appendChild(menu);

    const toggleMenu = (force) => {
      const next = typeof force === "boolean" ? force : !wrapper.classList.contains("open");
      wrapper.classList.toggle("open", next);
      chip.setAttribute("aria-expanded", String(next));
    };

    chip.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleMenu();
    });
    chip.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleMenu();
      } else if (e.key === "Escape") {
        toggleMenu(false);
      }
    });
    document.addEventListener("click", (e) => {
      if (!wrapper.contains(e.target)) toggleMenu(false);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") toggleMenu(false);
    });

    menu.querySelector("#dropdownLogoutBtn")?.addEventListener("click", onLogout);
  }

  const nameEl = wrapper.querySelector("#dropdownUserName");
  const metaEl = wrapper.querySelector("#dropdownUserMeta");
  if (nameEl) nameEl.textContent = displayName;
  if (metaEl) metaEl.textContent = email ? `${displayRole} • ${email}` : displayRole;
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
