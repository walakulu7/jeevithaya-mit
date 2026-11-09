// Apply RBAC and get session
const session = applyRBAC() || {};

// Role mapping for display
const roleMap = {
  system_admin: "System Admin",
  hospital_admin: "Hospital Admin",
  frontoffice_user: "Front Office User",
  lab_assistant: "Lab Assistant"
};

// Display user information in topbar
const userEmailEl = document.getElementById("userEmail");
const roleInfoEl = document.getElementById("roleInfo");
const welcomeEl = document.getElementById("welcome");

function updateHeaderAndProfile(user) {
  const email = user.email || user.Email || "admin@jeevithaya.com";
  const rawRole = user.role || user.Role || "system_admin";
  const name = user.name || user.Name || email.split("@")[0] || "User";
  const userId = user.userId || user.UserID || "U001";
  const formattedRole = roleMap[rawRole] || rawRole || "System Admin";

  if (userEmailEl) userEmailEl.textContent = email;
  if (roleInfoEl) roleInfoEl.textContent = `Role: ${formattedRole}`;
  if (welcomeEl) welcomeEl.textContent = `Welcome, ${name}`;

  const profileNameEl = document.getElementById("profileName");
  const profileUserIdEl = document.getElementById("profileUserId");
  const profileEmailEl = document.getElementById("profileEmail");
  const profileRoleEl = document.getElementById("profileRole");

  if (profileNameEl) profileNameEl.textContent = name;
  if (profileUserIdEl) profileUserIdEl.textContent = typeof userId === 'number' ? `U${String(userId).padStart(3, '0')}` : userId;
  if (profileEmailEl) profileEmailEl.textContent = email;
  if (profileRoleEl) profileRoleEl.textContent = formattedRole;
}

// Initial display from local session
updateHeaderAndProfile(session);

// Also try loading current authenticated user from backend session
if (window.authAPI && typeof window.authAPI.me === "function") {
  window.authAPI.me()
    .then(res => {
      if (res && res.user) {
        updateHeaderAndProfile(res.user);
      }
    })
    .catch(() => {});
}

// Update statistics from API
async function updateStats() {
  const donorCountEl = document.getElementById("donorCount");
  const requestCountEl = document.getElementById("requestCount");
  const unitCountEl = document.getElementById("unitCount");
  const urgentCountEl = document.getElementById("urgentCount");

  try {
    const api = window.dashboardAPI || dashboardAPI;
    if (api && typeof api.getStats === "function") {
      const stats = await api.getStats();
      if (stats) {
        if (donorCountEl) donorCountEl.textContent = stats.donorCount ?? 0;
        if (requestCountEl) requestCountEl.textContent = stats.requestCount ?? 0;
        if (unitCountEl) unitCountEl.textContent = stats.unitCount ?? 0;
        if (urgentCountEl) urgentCountEl.textContent = stats.urgentCount ?? 0;
        return;
      }
    }
  } catch (error) {
    console.warn('API stats unavailable, computing fallback:', error);
  }

  // Fallback: compute from localStorage if API is unavailable
  try {
    const donors = JSON.parse(localStorage.getItem("jv_donors")) || [];
    const requests = JSON.parse(localStorage.getItem("jv_requests")) || [];
    const inventory = JSON.parse(localStorage.getItem("jv_inventory")) || [];

    const activeRequests = requests.filter(r => r.status === "Pending" || r.status === "Approved");
    const urgentRequests = activeRequests.filter(r => r.urgency === "Urgent" || r.urgency === "Critical");
    const totalUnits = inventory
      .filter(i => (i.status || "Available") === "Available")
      .reduce((sum, item) => sum + (parseInt(item.qty || item.quantity) || 1), 0);

    if (donorCountEl) donorCountEl.textContent = donors.length;
    if (requestCountEl) requestCountEl.textContent = activeRequests.length;
    if (unitCountEl) unitCountEl.textContent = totalUnits;
    if (urgentCountEl) urgentCountEl.textContent = urgentRequests.length;
  } catch {
    if (donorCountEl) donorCountEl.textContent = "0";
    if (requestCountEl) requestCountEl.textContent = "0";
    if (unitCountEl) unitCountEl.textContent = "0";
    if (urgentCountEl) urgentCountEl.textContent = "0";
  }
}

// Display recent requests from API
async function displayRecentRequests() {
  const tbody = document.getElementById("recentRequestsBody");
  if (!tbody) return;

  try {
    const api = window.requestAPI || requestAPI;
    const requests = await api.getAll();

    if (!Array.isArray(requests) || requests.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 20px; color: var(--muted);">
            No recent requests
          </td>
        </tr>
      `;
      return;
    }

    // Sort by request ID (most recent first) and take top 5
    const recent = requests
      .sort((a, b) => {
        const aId = parseInt(String(a.RequestID || a.requestId || "").replace(/\D/g, "") || 0);
        const bId = parseInt(String(b.RequestID || b.requestId || "").replace(/\D/g, "") || 0);
        return bId - aId;
      })
      .slice(0, 5);

    tbody.innerHTML = recent.map(req => {
      const status = req.Status || req.status || "Pending";
      const statusClass = getStatusClass(status);
      const rawId = req.RequestID || req.requestId || "N/A";
      const requestId = String(rawId).startsWith("REQ") ? rawId : `#REQ${rawId}`;
      const bloodGroup = req.BloodGroup || req.bloodGroup || "N/A";
      const type = req.Type || req.type || "Blood";
      const quantity = req.Quantity || req.qty || 1;

      return `
        <tr>
          <td><strong>${requestId}</strong></td>
          <td><span class="badge">${bloodGroup}</span></td>
          <td>${type}</td>
          <td>${quantity} ${quantity === 1 ? "Unit" : "Units"}</td>
          <td class="status ${statusClass}">${status}</td>
        </tr>
      `;
    }).join("");

  } catch (error) {
    console.warn('Error loading recent requests:', error);
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; padding: 20px; color: var(--muted);">
          No recent requests
        </td>
      </tr>
    `;
  }
}

function getStatusClass(status) {
  if (!status) return "pending";
  const s = String(status).toLowerCase();
  if (s === "fulfilled" || s === "completed" || s === "approved") return "done";
  if (s === "urgent" || s === "critical" || s === "rejected") return "urgent";
  return "pending";
}

// Initialize dashboard immediately
updateStats();
displayRecentRequests();

// Auto-refresh stats every 15 seconds
setInterval(() => {
  updateStats();
  displayRecentRequests();
}, 15000);
