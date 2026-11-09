// Role-Based Access Control (RBAC) Module

function getSession() {
  try {
    return JSON.parse(localStorage.getItem("jv_session")) ||
           JSON.parse(sessionStorage.getItem("jv_session"));
  } catch {
    return null;
  }
}

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

  return session;
}

window.getSession = getSession;
window.applyRBAC = applyRBAC;
