const session = applyRBAC() || {};

const form = document.getElementById("profileForm");
const msg = document.getElementById("msg");

const nameEl = document.getElementById("name");
const emailEl = document.getElementById("email");
const roleEl = document.getElementById("role");
const passEl = document.getElementById("password");

// load session data
nameEl.value = session.name || "";
emailEl.value = session.email || "";
roleEl.value = session.role || "";

const USERS_KEY = "jv_users";

function loadUsers(){
  try { return JSON.parse(localStorage.getItem(USERS_KEY)) || []; }
  catch { return []; }
}

function saveUsers(list){
  localStorage.setItem(USERS_KEY, JSON.stringify(list));
}

function showMessage(text, isError=false){
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => msg.textContent = "", 1500);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const newName = nameEl.value.trim();
  const newPass = passEl.value.trim();

  // Try updating on backend API
  if (session.userId && window.userAPI && typeof window.userAPI.update === "function") {
    try {
      const updateData = { Name: newName };
      if (newPass) updateData.Password = newPass;
      await window.userAPI.update(session.userId, updateData);
    } catch (apiErr) {
      console.warn("Backend profile update failed:", apiErr);
    }
  }

  const list = loadUsers();
  const idx = list.findIndex(u => u.email === session.email);

  if (idx !== -1) {
    list[idx].name = newName;
    if (newPass) list[idx].password = newPass;
    saveUsers(list);
  }

  // update session also
  session.name = newName;
  try {
    localStorage.setItem("jv_session", JSON.stringify(session));
  } catch {}

  passEl.value = "";
  showMessage("Profile updated ✅");
});
});