
function getSession(){
  try {
    return JSON.parse(localStorage.getItem("jv_session")) ||
           JSON.parse(sessionStorage.getItem("jv_session"));
  } catch {
    return null;
  }
}

function applyRBAC(){
  const session = getSession();

  // if no session -> show login message (avoid blank)
  if (!session) {
    document.body.innerHTML = `
      <div style="font-family:system-ui; padding:40px;">
        <h2>Session not found</h2>
        <p>Please login first.</p>
        <a href="login.html">Go to Login</a>
      </div>
    `;
    return null;
  }

  const norm = str => (str || "").toLowerCase().replace(/[\s_]+/g, "");
  const userRoleNorm = norm(session.role);

  // hide/show menu items by role
  document.querySelectorAll(".menu [data-role]").forEach(link => {
    const allowed = link.getAttribute("data-role")
      .split(",")
      .map(r => norm(r.trim()));

    // Check if user's role is in the allowed roles list
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

  // show user email (optional) - only if not already set by dashboard.js
  const userEmailEl = document.getElementById("userEmail");
  if (userEmailEl && !userEmailEl.textContent) {
    userEmailEl.textContent = session.email || "";
  }

  // show welcome role (optional) - only if not already set by dashboard.js
  const roleInfoEl = document.getElementById("roleInfo");
  if (roleInfoEl && !roleInfoEl.textContent) {
    roleInfoEl.textContent = `Role: ${role}`;
  }

  // logout - redirect to logout page
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn && !logoutBtn.hasAttribute("data-listener-added")) {
    logoutBtn.setAttribute("data-listener-added", "true");
    logoutBtn.addEventListener("click", () => {
      window.location.href = "logout.html";
    });
  }

  return session;
}