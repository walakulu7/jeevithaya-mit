const session = applyRBAC() || {};

const form = document.getElementById("profileForm");
const msg = document.getElementById("msg");

const nameEl = document.getElementById("name");
const emailEl = document.getElementById("email");
const roleEl = document.getElementById("role");
const passEl = document.getElementById("password");

const USERS_KEY = "jv_users";

function loadUsers(){
  try { return JSON.parse(localStorage.getItem(USERS_KEY)) || []; }
  catch { return []; }
}

function saveUsers(list){
  localStorage.setItem(USERS_KEY, JSON.stringify(list));
}

function populateProfileFields(profile){
  if (!profile) return;
  const nameVal = profile.name || profile.Name || "";
  const emailVal = profile.email || profile.Email || "";
  if (nameEl) nameEl.value = nameVal;
  if (emailEl) emailEl.value = emailVal;
  if (roleEl) roleEl.value = profile.role || profile.Role || "";

  const userEmailEl = document.getElementById("userEmail");
  if (userEmailEl && (nameVal || emailVal)) {
    userEmailEl.textContent = nameVal || emailVal;
  }
  const dropdownNameEl = document.getElementById("dropdownUserName");
  if (dropdownNameEl && nameVal) {
    dropdownNameEl.textContent = nameVal;
  }
}

async function syncCurrentProfile(){
  // Populate immediately from active session
  populateProfileFields(session);

  // Refresh from backend session if authenticated
  if (window.authAPI && typeof window.authAPI.me === "function") {
    try {
      const res = await window.authAPI.me();
      const user = res && res.user ? res.user : null;
      if (user) {
        session.userId = user.UserID ?? session.userId;
        session.name = user.Name || session.name;
        session.email = user.Email || session.email;
        session.role = user.Role || session.role;
        populateProfileFields(session);
        try {
          localStorage.setItem("jv_session", JSON.stringify(session));
        } catch {}
      }
    } catch {
      // Fallback to local session when no server cookie session is active
    }
  }
}

syncCurrentProfile();

function showMessage(text, isError=false){
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => msg.textContent = "", 1500);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const newName = nameEl.value.trim();
  const newPass = passEl.value.trim();

  if (!newName) {
    showMessage("Name is required.", true);
    return;
  }

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
  populateProfileFields(session);
  try {
    localStorage.setItem("jv_session", JSON.stringify(session));
  } catch {}

  passEl.value = "";
  showMessage("Profile updated ✅");
});