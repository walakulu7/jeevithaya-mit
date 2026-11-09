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
const tableBody = document.querySelector("#userTable tbody");
const msg = document.getElementById("msg");

const KEY = "jv_users";
let userList = [];

function showMessage(text, isError = false) {
  if (!msg) return;
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => msg.textContent = "", 2500);
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
        }));
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
      userList = local;
      render();
      return;
    }
  } catch {}

  userList = [
    { userId: "U001", name: "System Administrator", email: "admin@jeevithaya.com", role: "system_admin" },
    { userId: "U002", name: "Hospital Administrator", email: "hospital@jeevithaya.com", role: "hospital_admin" },
    { userId: "U003", name: "Front Office User", email: "frontoffice@jeevithaya.com", role: "frontoffice_user" },
    { userId: "U004", name: "Lab Assistant", email: "lab@jeevithaya.com", role: "lab_assistant" }
  ];
  render();
}

function render() {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  userList.forEach((u, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${u.userId}</strong></td>
      <td>${u.name}</td>
      <td>${u.email}</td>
      <td><span class="badge">${u.role}</span></td>
      <td>
        <button class="btn-mini danger" data-id="${u.userId}" data-del="${i}">Delete</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = form.name.value.trim();
    const email = form.email.value.trim().toLowerCase();
    const role = form.role.value;
    const password = form.password.value;

    if (!name || !email || !role || !password) {
      showMessage("Please fill all fields", true);
      return;
    }

    const payload = {
      Name: name,
      Email: email,
      Role: role,
      Password: password,
      HospitalID: 1
    };

    let newId = "U" + Math.floor(100 + Math.random() * 900);

    try {
      if (window.userAPI && typeof window.userAPI.create === "function") {
        const res = await window.userAPI.create(payload);
        if (res && res.UserID) newId = "U" + res.UserID;
        showMessage("User account created in database! ✅");
      }
    } catch (err) {
      console.warn("API user save error:", err);
      showMessage("User created (Offline fallback): " + err.message, true);
    }

    userList.push({
      userId: newId,
      name,
      email,
      role
    });

    try {
      localStorage.setItem(KEY, JSON.stringify(userList));
    } catch {}

    render();
    form.reset();
  });
}

document.getElementById("userTable")?.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;

  const rawId = btn.dataset.id;
  const numId = parseInt(rawId.replace(/\D/g, "")) || null;

  if (!confirm(`Are you sure you want to delete user ${rawId}?`)) return;

  try {
    if (numId && window.userAPI && typeof window.userAPI.delete === "function") {
      await window.userAPI.delete(numId);
    }
  } catch (err) {
    console.warn("API delete user error:", err);
  }

  const i = Number(btn.dataset.del);
  if (userList[i]) {
    userList.splice(i, 1);
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(userList));
  } catch {}

  render();
  showMessage("User deleted");
});

loadUsers();
