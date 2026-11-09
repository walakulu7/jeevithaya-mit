// Donor Management
const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect or session error
}

let donors = [];

const tableBody = document.querySelector("#donorTable tbody");
const bloodFilter = document.getElementById("bloodFilter");
const eligibilityFilter = document.getElementById("eligibilityFilter");
const searchInput = document.getElementById("searchInput");
const donorForm = document.getElementById("donorForm");
const donorMsg = document.getElementById("donorMsg");

function showMsg(text, isError = false) {
  if (!donorMsg) return;
  donorMsg.className = "msg " + (isError ? "err" : "ok");
  donorMsg.textContent = text;
  setTimeout(() => { donorMsg.textContent = ""; }, 2500);
}

// Generate unique Donor ID if needed
function generateDonorId() {
  const num = Math.floor(1000 + Math.random() * 9000);
  return `D${num}`;
}

// Fetch donors from Django API or fallback
async function loadDonors() {
  try {
    if (window.donorAPI && typeof window.donorAPI.getAll === "function") {
      const data = await window.donorAPI.getAll();
      if (Array.isArray(data)) {
        donors = data.map(d => ({
          id: d.DonorID || d.id,
          name: d.Name || d.name,
          blood: d.BloodGroup || d.blood,
          phone: d.Phone || d.phone,
          status: d.Status || d.status || "Eligible",
        }));
        renderTable(donors);
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load from API, checking local storage:", err);
  }

  // Fallback to local storage or defaults
  try {
    const local = JSON.parse(localStorage.getItem("jv_donors"));
    if (local && local.length > 0) {
      donors = local;
      renderTable(donors);
      return;
    }
  } catch {}

  // Baseline mock data if empty
  donors = [
    { id: "D001", name: "Charith K", blood: "O+", phone: "0777678678", status: "Eligible" },
    { id: "D002", name: "Vithuran", blood: "A+", phone: "0711123123", status: "Not Eligible" },
    { id: "D003", name: "Sula", blood: "B-", phone: "0755123123", status: "Eligible" },
    { id: "D004", name: "Walakulu", blood: "AB+", phone: "0788123123", status: "Eligible" }
  ];
  renderTable(donors);
}

function renderTable(data) {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  if (!data || data.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:#6b7280;">No donors found.</td></tr>`;
    return;
  }

  data.forEach(d => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${d.id}</strong></td>
      <td>${d.name}</td>
      <td><span class="badge">${d.blood}</span></td>
      <td>${d.phone}</td>
      <td>
        <span class="${d.status === "Eligible" ? "status done" : "status urgent"}">
          ${d.status}
        </span>
      </td>
      <td>
        <button class="btn-mini danger" data-id="${d.id}">Delete</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });

  // Attach delete handlers
  tableBody.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", () => deleteDonor(btn.getAttribute("data-id")));
  });
}

function applyFilters() {
  const blood = bloodFilter ? bloodFilter.value : "";
  const status = eligibilityFilter ? eligibilityFilter.value : "";
  const search = searchInput ? searchInput.value.toLowerCase().trim() : "";

  const filtered = donors.filter(d =>
    (!blood || d.blood === blood) &&
    (!status || d.status === status) &&
    (!search || d.name.toLowerCase().includes(search) || d.phone.includes(search) || d.id.toLowerCase().includes(search))
  );

  renderTable(filtered);
}

// Add Donor form submission
if (donorForm) {
  donorForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("donorName").value.trim();
    const blood = document.getElementById("donorBloodGroup").value;
    const phone = document.getElementById("donorPhone").value.trim();
    const status = document.getElementById("donorStatus").value;
    const email = document.getElementById("donorEmail")?.value.trim() || "";
    const gender = document.getElementById("donorGender")?.value || "";

    const donorId = generateDonorId();

    const payload = {
      DonorID: donorId,
      Name: name,
      BloodGroup: blood,
      Phone: phone,
      Status: status,
      Email: email,
      Gender: gender,
    };

    try {
      if (window.donorAPI && typeof window.donorAPI.create === "function") {
        await window.donorAPI.create(payload);
        showMsg("Donor registered successfully in database!");
      }
    } catch (err) {
      console.warn("API save error, saving locally:", err);
      showMsg("Registered (Offline fallback): " + err.message, true);
    }

    // Add to current in-memory list & update UI
    donors.unshift({
      id: donorId,
      name,
      blood,
      phone,
      status
    });

    try {
      localStorage.setItem("jv_donors", JSON.stringify(donors));
    } catch {}

    donorForm.reset();
    applyFilters();
  });
}

// Delete Donor
async function deleteDonor(donorId) {
  if (!confirm(`Are you sure you want to delete donor ${donorId}?`)) return;

  try {
    if (window.donorAPI && typeof window.donorAPI.delete === "function") {
      await window.donorAPI.delete(donorId);
    }
  } catch (err) {
    console.warn("API delete error:", err);
  }

  donors = donors.filter(d => d.id !== donorId);
  try {
    localStorage.setItem("jv_donors", JSON.stringify(donors));
  } catch {}

  applyFilters();
  showMsg(`Donor ${donorId} deleted.`);
}

if (bloodFilter) bloodFilter.addEventListener("change", applyFilters);
if (eligibilityFilter) eligibilityFilter.addEventListener("change", applyFilters);
if (searchInput) searchInput.addEventListener("input", applyFilters);

// Initial load
loadDonors();
