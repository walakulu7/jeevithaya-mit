const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect
}

const form = document.getElementById("donationForm");
const tableBody = document.querySelector("#donationTable tbody");
const search = document.getElementById("search");

const donorIdEl = document.getElementById("donorId");
const dateEl = document.getElementById("date");
const bloodGroupEl = document.getElementById("bloodGroup");
const typeEl = document.getElementById("type");
const qtyEl = document.getElementById("qty");
const conductedByEl = document.getElementById("conductedBy");

const KEY = "jv_donations";
let donationsList = [];

function newDonationId() {
  const next = Math.floor(100 + Math.random() * 900);
  return "DN" + next;
}

async function loadDonations() {
  try {
    if (window.donationAPI && typeof window.donationAPI.getAll === "function") {
      const data = await window.donationAPI.getAll();
      if (Array.isArray(data)) {
        donationsList = data.map(d => ({
          donationId: d.DonationID || d.donationId,
          donorId: d.DonorID || d.donorId,
          date: d.Date || d.date,
          bloodGroup: d.BloodGroup || d.bloodGroup,
          type: d.Type || d.type || "Blood",
          qty: d.Quantity || d.qty || 1,
          bloodbankId: d.BloodBankID || 1,
          conductedBy: d.ConductedBy || d.conductedBy || "Lab Staff"
        }));
        render(donationsList);
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load donations from API, using fallback:", err);
  }

  try {
    const local = JSON.parse(localStorage.getItem(KEY));
    if (local && local.length > 0) {
      donationsList = local;
      render(donationsList);
      return;
    }
  } catch {}

  donationsList = [
    { donationId: "DN101", donorId: "D001", date: new Date().toISOString().split('T')[0], bloodGroup: "O+", type: "Blood", qty: 1, conductedBy: "Dr. Saman" },
    { donationId: "DN102", donorId: "D003", date: new Date().toISOString().split('T')[0], bloodGroup: "B-", type: "Plasma", qty: 2, conductedBy: "Dr. Kasun" }
  ];
  render(donationsList);
}

function render(list) {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  if (!list || list.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:#6b7280;">No donations recorded.</td></tr>`;
    return;
  }

  list.forEach((d, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${d.donationId}</strong></td>
      <td>${d.donorId}</td>
      <td>${d.date}</td>
      <td><span class="badge">${d.bloodGroup}</span></td>
      <td>${d.type}</td>
      <td>${d.qty}</td>
      <td>${d.conductedBy}</td>
      <td><button class="btn-mini danger" data-id="${d.donationId}" data-del="${i}">Delete</button></td>
    `;
    tableBody.appendChild(tr);
  });
}

function applySearch() {
  const q = search ? search.value.toLowerCase().trim() : "";
  const filtered = donationsList.filter(d =>
    d.donationId.toLowerCase().includes(q) ||
    d.donorId.toLowerCase().includes(q) ||
    d.conductedBy.toLowerCase().includes(q)
  );
  render(filtered);
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const donationId = newDonationId();
    const donorId = donorIdEl.value.trim().toUpperCase();
    const date = dateEl.value;
    const bloodGroup = bloodGroupEl.value;
    const type = typeEl.value;
    const qty = qtyEl.value;
    const conductedBy = conductedByEl ? conductedByEl.value.trim() : "Lab Staff";

    if (!donorId || !date || !bloodGroup || !qty) {
      alert("Please fill required fields");
      return;
    }

    const payload = {
      DonationID: donationId,
      DonorID: donorId,
      Date: date,
      BloodGroup: bloodGroup,
      Type: type,
      Quantity: parseInt(qty) || 1,
      BloodBankID: 1,
      Status: "Pending"
    };

    try {
      if (window.donationAPI && typeof window.donationAPI.create === "function") {
        await window.donationAPI.create(payload);
      }
    } catch (err) {
      console.warn("API save error:", err);
    }

    donationsList.unshift({
      donationId,
      donorId,
      date,
      bloodGroup,
      type,
      qty,
      conductedBy
    });

    try {
      localStorage.setItem(KEY, JSON.stringify(donationsList));
    } catch {}

    form.reset();
    if (dateEl) dateEl.valueAsDate = new Date();
    applySearch();
    if (window.closeCollapsibleForm) window.closeCollapsibleForm();
  });
}

document.getElementById("donationTable")?.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;

  const donationId = btn.dataset.id;
  if (!confirm(`Are you sure you want to delete donation ${donationId}?`)) return;

  try {
    if (window.donationAPI && typeof window.donationAPI.delete === "function") {
      await window.donationAPI.delete(donationId);
    }
  } catch (err) {
    console.warn("API delete error:", err);
  }

  const i = Number(btn.dataset.del);
  if (donationsList[i]) {
    donationsList.splice(i, 1);
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(donationsList));
  } catch {}

  applySearch();
});

if (search) search.addEventListener("input", applySearch);
if (dateEl) dateEl.valueAsDate = new Date();

loadDonations();
