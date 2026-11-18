const form = document.getElementById("loginForm");
const msg = document.getElementById("msg");
const togglePwd = document.getElementById("togglePwd");
const passwordEl = document.getElementById("password");
const forgotLink = document.getElementById("forgotLink");

// Remove demo credentials that older versions cached in the browser
try { localStorage.removeItem("jv_users"); } catch (e) {}

togglePwd.addEventListener("click", () => {
  const isPwd = passwordEl.type === "password";
  passwordEl.type = isPwd ? "text" : "password";
  togglePwd.textContent = isPwd ? "Hide" : "Show";
});

forgotLink.addEventListener("click", (e) => {
  e.preventDefault();
  msg.className = "msg err";
  msg.textContent = "Contact your system administrator for password reset.";
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("email").value.trim().toLowerCase();
  const password = passwordEl.value.trim();
  const remember = document.getElementById("remember").checked;

  if (!email) return showError("Please enter your email.");
  if (!password) return showError("Please enter your password.");

  // Authentication happens only on the server; the browser keeps display info
  try {
    const response = await window.authAPI.login(email, password);
    const u = response && response.user;
    if (!u) return showError("Login failed. Please try again.");

    const session = {
      role: u.Role,
      email: u.Email,
      name: u.Name,
      userId: u.UserID,
      loginAt: new Date().toISOString()
    };
    const store = remember ? localStorage : sessionStorage;
    store.setItem("jv_session", JSON.stringify(session));

    showOk(`Welcome back, ${u.Name || "User"}! Redirecting...`);
    setTimeout(() => {
      window.location.href = "dashboard.html";
    }, 500);
  } catch (apiErr) {
    console.warn("Login failed:", apiErr.message);
    if (apiErr.message && (apiErr.message.includes("Failed to fetch") || apiErr.message.includes("NetworkError"))) {
      return showError("Cannot reach the server. Check your connection and try again.");
    }
    showError(apiErr.message || "Invalid email or password.");
  }
});

function showError(text){
  msg.className = "msg err";
  msg.textContent = text;
}
function showOk(text){
  msg.className = "msg ok";
  msg.textContent = text;
}

// Quick Demo Account Click Handler
document.querySelectorAll(".demo-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    const email = chip.getAttribute("data-email");
    const pwd = chip.getAttribute("data-pwd");
    const emailInput = document.getElementById("email");
    const pwdInput = document.getElementById("password");
    if (emailInput && email) emailInput.value = email;
    if (pwdInput && pwd) pwdInput.value = pwd;

    // Visual feedback
    chip.style.borderColor = "var(--primary)";
    setTimeout(() => {
      chip.style.borderColor = "";
    }, 400);

    // Focus submit button
    const submitBtn = form.querySelector("button[type='submit']");
    if (submitBtn) submitBtn.focus();
  });
});
