const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect
}

const userRole = (session?.role || "").toLowerCase().replace(/[\s_]+/g, "");
if (userRole !== "systemadmin") {
  document.body.innerHTML = `
    <div style="padding:40px;font-family:system-ui">
      <h2>Access Denied</h2>
      <p>Only System Admin can manage system users.</p>
      <a href="dashboard.html">Back to Dashboard</a>
    </div>
  `;
}

const form = document.getElementById("userForm");
const formCard = document.getElementById("userFormCard");
const formTitle = document.getElementById("formTitle");
const submitBtn = document.getElementById("submitBtn");
const tableBody = document.querySelector("#userTable tbody");
const msg = document.getElementById("msg");
const tableMsg = document.getElementById("tableMsg");
const toggleFormBtn = document.getElementById("toggleFormBtn");

const KEY = "jv_users";
let userList = [];
let editingIndex = null;

function showMessage(text, isError = false, target = msg) {
  const el = target || msg;
  if (!el) return;
  el.className = "msg " + (isError ? "err" : "ok");
  el.textContent = text;
  setTimeout(() => { el.textContent = ""; }, 2500);
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function normalizeRole(role) {
  const clean = String(role || "").trim().toLowerCase().replace(/[\s_]+/g, "");
  if (clean === "systemadmin") return "system_admin";
  if (clean === "hospitaladmin") return "hospital_admin";
  if (clean === "frontoffice" || clean === "frontofficeuser") return "frontoffice_user";
  if (clean === "labassistant") return "lab_assistant";
  return role || "";
}

function getNumericId(rawId) {
  const digits = String(rawId ?? "").replace(/\D/g, "");
  return digits ? parseInt(digits, 10) : null;
}

function persistLocalUsers() {
  try {
    localStorage.setItem(KEY, JSON.stringify(userList));
  } catch {}
}

function isSelfUser(u) {
  if (!session || !u) return false;
  if (session.userId && String(session.userId) === String(u.userId)) return true;
  if (session.email && u.email && session.email.toLowerCase() === u.email.toLowerCase()) return true;
  return false;
}

function openFormCard() {
  if (!formCard) return;
  formCard.classList.add("open");
  if (toggleFormBtn) {
    toggleFormBtn.classList.remove("btn-primary");
    toggleFormBtn.classList.add("btn-ghost");
    if (!toggleFormBtn.hasAttribute("data-default-text")) {
      toggleFormBtn.setAttribute("data-default-text", toggleFormBtn.innerHTML);
    }
    toggleFormBtn.innerHTML = `<span>✕ Close Form</span>`;
  }
  formCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function resetFormMode() {
  editingIndex = null;
  if (form) form.reset();
  if (form?.status) form.status.value = "Active";
  if (form?.password) {
    form.password.required = true;
    form.password.placeholder = "";
  }
  if (formTitle) formTitle.textContent = "Create New User";
  if (submitBtn) submitBtn.textContent = "Create User";
}

function startEditUser(index) {
  const user = userList[index];
  if (!user || !form) return;

  editingIndex = index;
  form.name.value = user.name || "";
  form.email.value = user.email || "";
  form.role.value = normalizeRole(user.role);
  if (form.status) form.status.value = user.status === "Inactive" ? "Inactive" : "Active";
  form.password.value = "";
  form.password.required = false;
  form.password.placeholder = "Leave blank to keep current password";

  if (formTitle) formTitle.textContent = `Edit User (${user.userId})`;
  if (submitBtn) submitBtn.textContent = "Update User";

  openFormCard();
  form.name.focus();
}

async function loadUsers() {
  try {
    if (window.userAPI && typeof window.userAPI.getAll === "function") {
      const data = await window.userAPI.getAll();
      if (Array.isArray(data) && data.length > 0) {
        userList = data.map(u => ({
          userId: u.UserID || u.userId,
          name: u.Name || u.name,
          email: u.Email || u.email,
          role: u.Role || u.role,
          status: u.Status || u.status || "Active",
        }));
        persistLocalUsers();
        render();
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load users from API, using fallback:", err);
  }

  try {
    const local = JSON.parse(localStorage.getItem(KEY));
    if (local && local.length > 0) {
      userList = local.map(u => ({
        ...u,
        status: u.status || u.Status || "Active",
      }));
      render();
      return;
    }
  } catch {}

  userList = [
    { userId: 1, name: "System Administrator", email: "admin@jeevithaya.com", role: "system_admin", status: "Active" },
    { userId: 2, name: "Hospital Administrator", email: "hospital@jeevithaya.com", role: "hospital_admin", status: "Active" },
    { userId: 3, name: "Front Office User", email: "frontoffice@jeevithaya.com", role: "frontoffice_user", status: "Active" },
    { userId: 4, name: "Lab Assistant", email: "lab@jeevithaya.com", role: "lab_assistant", status: "Active" }
  ];
  render();
}

function render() {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  userList.forEach((u, i) => {
    const isActive = (u.status || "Active") !== "Inactive";
    const statusLabel = isActive ? "Active" : "Inactive";
    const statusClass = isActive ? "done" : "urgent";
    const toggleBtnClass = isActive ? "warn" : "success";
    const toggleBtnText = isActive ? "Deactivate" : "Activate";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escapeHtml(u.userId)}</strong></td>
      <td>${escapeHtml(u.name)}</td>
      <td>${escapeHtml(u.email)}</td>
      <td><span class="badge">${escapeHtml(u.role)}</span></td>
      <td><span class="status ${statusClass}">${statusLabel}</span></td>
      <td>
        <div class="action-group">
          <button type="button" class="btn-mini" data-edit="${i}">Edit</button>
          <button type="button" class="btn-mini ${toggleBtnClass}" data-toggle-status="${i}">${toggleBtnText}</button>
          <button type="button" class="btn-mini danger" data-id="${escapeHtml(u.userId)}" data-del="${i}">Delete</button>
        </div>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

// Reset form state whenever form card closes or "+ Add New User" opens it fresh
document.querySelectorAll("[data-action='close-form'], .btn-close-form").forEach(btn => {
  btn.addEventListener("click", resetFormMode);
});
toggleFormBtn?.addEventListener("click", () => {
  if (!formCard?.classList.contains("open")) {
    resetFormMode();
  }
});

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = form.name.value.trim();
    const email = form.email.value.trim().toLowerCase();
    const role = form.role.value;
    const status = form.status ? form.status.value : "Active";
    const password = form.password.value;
    const isEdit = editingIndex !== null;

    if (!name || !email || !role || (!isEdit && !password)) {
      showMessage("Please fill all required fields", true);
      return;
    }

    if (isEdit) {
      const target = userList[editingIndex];
      if (!target) {
        resetFormMode();
        return;
      }

      if (isSelfUser(target) && status === "Inactive") {
        showMessage("Cannot deactivate your own active account.", true);
        return;
      }

      const payload = {
        Name: name,
        Email: email,
        Role: role,
        Status: status
      };
      if (password.trim()) {
        payload.Password = password.trim();
      }

      const numId = getNumericId(target.userId);
      try {
        if (numId && window.userAPI && typeof window.userAPI.update === "function") {
          const updated = await window.userAPI.update(numId, payload);
          target.userId = updated?.UserID || target.userId;
        }
        showMessage("User updated! ✅", false, tableMsg);
      } catch (err) {
        console.warn("API user update error:", err);
        showMessage("Update failed: " + err.message, true);
        return;
      }

      target.name = name;
      target.email = email;
      target.role = role;
      target.status = status;

      if (isSelfUser(target)) {
        session.name = name;
        session.email = email;
        session.role = role;
        try { localStorage.setItem("jv_session", JSON.stringify(session)); } catch {}
      }

      persistLocalUsers();
      render();
      resetFormMode();
      if (window.closeCollapsibleForm) window.closeCollapsibleForm();
      return;
    }

    const payload = {
      Name: name,
      Email: email,
      Role: role,
      Status: status,
      Password: password,
      HospitalID: 1
    };

    let newId = "U" + Math.floor(100 + Math.random() * 900);

    try {
      if (window.userAPI && typeof window.userAPI.create === "function") {
        const res = await window.userAPI.create(payload);
        if (res && res.UserID) newId = res.UserID;
        showMessage("User account created! ✅", false, tableMsg);
      }
    } catch (err) {
      console.warn("API user save error:", err);
      showMessage("User created (Offline fallback): " + err.message, true);
    }

    userList.push({
      userId: newId,
      name,
      email,
      role,
      status
    });

    persistLocalUsers();
    render();
    resetFormMode();
    if (window.closeCollapsibleForm) window.closeCollapsibleForm();
  });
}

document.getElementById("userTable")?.addEventListener("click", async (e) => {
  const editBtn = e.target.closest("[data-edit]");
  if (editBtn) {
    startEditUser(Number(editBtn.dataset.edit));
    return;
  }

  const toggleBtn = e.target.closest("[data-toggle-status]");
  if (toggleBtn) {
    const i = Number(toggleBtn.dataset.toggleStatus);
    const user = userList[i];
    if (!user) return;

    const currentStatus = user.status === "Inactive" ? "Inactive" : "Active";
    const nextStatus = currentStatus === "Active" ? "Inactive" : "Active";

    if (nextStatus === "Inactive" && isSelfUser(user)) {
      showMessage("Cannot deactivate your own active account.", true, tableMsg);
      return;
    }

    const numId = getNumericId(user.userId);
    try {
      if (numId && window.userAPI && typeof window.userAPI.update === "function") {
        await window.userAPI.update(numId, { Status: nextStatus });
      }
    } catch (err) {
      console.warn("API status update error:", err);
      showMessage("Status update failed: " + err.message, true, tableMsg);
      return;
    }

    user.status = nextStatus;
    persistLocalUsers();
    render();
    showMessage(`User marked as ${nextStatus}`, false, tableMsg);
    return;
  }

  const delBtn = e.target.closest("[data-del]");
  if (!delBtn) return;

  const i = Number(delBtn.dataset.del);
  const user = userList[i];
  if (user && isSelfUser(user)) {
    showMessage("Cannot delete your own active account.", true, tableMsg);
    return;
  }

  const rawId = delBtn.dataset.id;
  const numId = getNumericId(rawId);

  if (!confirm(`Are you sure you want to delete user ${rawId}?`)) return;

  try {
    if (numId && window.userAPI && typeof window.userAPI.delete === "function") {
      await window.userAPI.delete(numId);
    }
  } catch (err) {
    console.warn("API delete user error:", err);
  }

  if (userList[i]) {
    userList.splice(i, 1);
  }
  persistLocalUsers();
  render();
  showMessage("User deleted", false, tableMsg);
});

loadUsers();
