const form = document.getElementById("loginForm");
const msg = document.getElementById("msg");
const togglePwd = document.getElementById("togglePwd");
const passwordEl = document.getElementById("password");
const forgotLink = document.getElementById("forgotLink");

const USERS_KEY = "jv_users";

// Initialize default demo user profiles if they don't exist
function initializeDemoUsers() {
  const existingUsers = loadUsers();
  
  // Only initialize if no users exist
  if (existingUsers.length === 0) {
    const demoUsers = [
      {
        userId: "U001",
        name: "System Administrator",
        email: "admin@jeevithaya.com",
        role: "system_admin",
        password: "admin123"
      },
      {
        userId: "U002",
        name: "Hospital Administrator",
        email: "hospital@jeevithaya.com",
        role: "hospital_admin",
        password: "hospital123"
      },
      {
        userId: "U003",
        name: "Front Office User",
        email: "frontoffice@jeevithaya.com",
        role: "frontoffice_user",
        password: "front123"
      },
      {
        userId: "U004",
        name: "Lab Assistant",
        email: "lab@jeevithaya.com",
        role: "lab_assistant",
        password: "lab123"
      }
    ];
    
    saveUsers(demoUsers);
    console.log("Demo users initialized");
  }
}

function loadUsers() {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY)) || [];
  } catch {
    return [];
  }
}

function saveUsers(list) {
  localStorage.setItem(USERS_KEY, JSON.stringify(list));
}

// Initialize demo users on page load
initializeDemoUsers();

togglePwd.addEventListener("click", () => {
  const isPwd = passwordEl.type === "password";
  passwordEl.type = isPwd ? "text" : "password";
  togglePwd.textContent = isPwd ? "Hide" : "Show";
});

forgotLink.addEventListener("click", (e) => {
  e.preventDefault();
  const users = loadUsers();
  if (users.length > 0) {
    msg.className = "msg err";
    msg.textContent = "Contact your system administrator for password reset.";
  } else {
    msg.className = "msg err";
    msg.textContent = "Demo mode: password is 1234 🙂";
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const role = document.querySelector('input[name="role"]:checked')?.value;
  const email = document.getElementById("email").value.trim().toLowerCase();
  const password = passwordEl.value.trim();
  const remember = document.getElementById("remember").checked;

  if (!email) return showError("Please enter email.");
  if (!password) return showError("Please enter password.");

  // Try authenticating via Django Backend API first
  if (window.authAPI && typeof window.authAPI.login === "function") {
    try {
      const response = await window.authAPI.login(email, password, role);
      if (response && response.user) {
        const u = response.user;
        const session = {
          role: u.Role,
          email: u.Email,
          name: u.Name,
          userId: u.UserID,
          loginAt: new Date().toISOString()
        };

        if (remember) {
          localStorage.setItem("jv_session", JSON.stringify(session));
        } else {
          sessionStorage.setItem("jv_session", JSON.stringify(session));
        }

        showOk("Login success! Redirecting...");
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 600);
        return;
      }
    } catch (apiErr) {
      console.warn("Backend login attempt:", apiErr.message);
      // If error is invalid credentials, show error directly
      if (apiErr.message && !apiErr.message.includes("Failed to fetch") && !apiErr.message.includes("NetworkError")) {
        return showError(apiErr.message);
      }
    }
  }

  // Fallback to local demo users if API server is offline
  const users = loadUsers();
  const user = users.find(
    u => u.email.toLowerCase() === email && 
         u.role === role && 
         u.password === password
  );

  if (!user) {
    if (users.length === 0 && password === "1234") {
      const session = {
        role,
        email,
        name: role.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase()),
        loginAt: new Date().toISOString()
      };

      if (remember) {
        localStorage.setItem("jv_session", JSON.stringify(session));
      } else {
        sessionStorage.setItem("jv_session", JSON.stringify(session));
      }

      showOk("Login success! Redirecting...");
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 600);
      return;
    }
    return showError("Invalid email, password, or role combination.");
  }

  // Save session with user details
  const session = {
    role: user.role,
    email: user.email,
    name: user.name,
    userId: user.userId,
    loginAt: new Date().toISOString()
  };

  if (remember) {
    localStorage.setItem("jv_session", JSON.stringify(session));
  } else {
    sessionStorage.setItem("jv_session", JSON.stringify(session));
  }

  showOk("Login success! Redirecting...");

  setTimeout(() => {
    window.location.href = "dashboard.html";
  }, 600);
});

function showError(text){
  msg.className = "msg err";
  msg.textContent = text;
}
function showOk(text){
  msg.className = "msg ok";
  msg.textContent = text;
}