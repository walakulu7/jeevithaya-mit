// Apply RBAC and get session
const session = applyRBAC();
if (!session) return;

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

if (userEmailEl) userEmailEl.textContent = session.email || "";
if (roleInfoEl) roleInfoEl.textContent = "Role: " + (roleMap[session.role] || session.role || "User");
if (welcomeEl) {
  const userName = session.name || session.email?.split("@")[0] || "User";
  welcomeEl.textContent = `Welcome, ${userName}`;
}

// Display user profile information
function displayUserProfile() {
  const profileNameEl = document.getElementById("profileName");
  const profileUserIdEl = document.getElementById("profileUserId");
  const profileEmailEl = document.getElementById("profileEmail");
  const profileRoleEl = document.getElementById("profileRole");

  if (profileNameEl) profileNameEl.textContent = session.name || "Not set";
  if (profileUserIdEl) profileUserIdEl.textContent = session.userId || "N/A";
  if (profileEmailEl) profileEmailEl.textContent = session.email || "Not set";
  if (profileRoleEl) profileRoleEl.textContent = roleMap[session.role] || session.role || "Not set";
}

displayUserProfile();

// Update statistics from API (with local fallback)
async function updateStats() {
  const donorCountEl = document.getElementById("donorCount");
  const requestCountEl = document.getElementById("requestCount");
  const unitCountEl = document.getElementById("unitCount");
  const urgentCountEl = document.getElementById("urgentCount");

  try {
    if (window.dashboardAPI && typeof window.dashboardAPI.getStats === "function") {
      const stats = await window.dashboardAPI.getStats();
      if (donorCountEl) donorCountEl.textContent = stats.donorCount || 0;
      if (requestCountEl) requestCountEl.textContent = stats.requestCount || 0;
      if (unitCountEl) unitCountEl.textContent = stats.unitCount || 0;
      if (urgentCountEl) urgentCountEl.textContent = stats.urgentCount || 0;
      return;
    }
  } catch (error) {
    console.warn('API stats unavailable, computing from local fallback:', error);
  }

  // Fallback: compute from localStorage if backend is offline
  try {
    const donors = JSON.parse(localStorage.getItem("jv_donors")) || [];
    const requests = JSON.parse(localStorage.getItem("jv_requests")) || [];
    const inventory = JSON.parse(localStorage.getItem("jv_inventory")) || [];

    const activeRequests = requests.filter(r => r.status === "Pending" || r.status === "Approved");
    const urgentRequests = activeRequests.filter(r => r.urgency === "Urgent" || r.urgency === "Critical");
    const totalUnits = inventory
      .filter(i => (i.status || "Available") === "Available")
      .reduce((sum, item) => sum + (parseInt(item.quantity) || 1), 0);

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
    const requests = await requestAPI.getAll();
    
    // Sort by request ID (most recent first) and take top 5
    const recent = requests
      .sort((a, b) => {
        const aId = parseInt(a.RequestID?.replace("REQ", "") || 0);
        const bId = parseInt(b.RequestID?.replace("REQ", "") || 0);
        return bId - aId;
      })
      .slice(0, 5);

    if (recent.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 20px; color: var(--muted);">
            No recent requests
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = recent.map(req => {
      const statusClass = getStatusClass(req.Status);
      const requestId = req.RequestID || "N/A";
      const bloodGroup = req.BloodGroup || "N/A";
      const type = req.Type || "Blood";
      const quantity = req.Quantity || 1;
      
      return `
        <tr>
          <td>#${requestId}</td>
          <td>${bloodGroup}</td>
          <td>${type}</td>
          <td>${quantity} ${quantity === 1 ? "Unit" : "Units"}</td>
          <td class="status ${statusClass}">${req.Status || "Pending"}</td>
        </tr>
      `;
    }).join("");
  } catch (error) {
    console.error('Error loading requests:', error);
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; padding: 20px; color: var(--muted);">
          Error loading requests
        </td>
      </tr>
    `;
  }
}

function getStatusClass(status) {
  if (!status) return "pending";
  status = status.toLowerCase();
  if (status === "fulfilled" || status === "completed") return "done";
  if (status === "urgent" || status === "critical") return "urgent";
  return "pending";
}

// Initialize dashboard
updateStats();
displayRecentRequests();

// Refresh stats every 30 seconds (optional)
setInterval(() => {
  updateStats();
  displayRecentRequests();
}, 30000);