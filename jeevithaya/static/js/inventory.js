const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect
}

// DOM
const form = document.getElementById("invForm");
const tableBody = document.querySelector("#invTable tbody");
const msg = document.getElementById("msg");
const search = document.getElementById("search");
const statusFilter = document.getElementById("statusFilter");

const KEY = "jv_inventory";
let inventoryList = [];

function showMessage(text, isError = false) {
  if (!msg) return;
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => { msg.textContent = ""; }, 2500);
}

function newUnitId() {
  const next = Math.floor(1000 + Math.random() * 9000);
  return "U" + next;
}

function isExpired(expiry) {
  if (!expiry) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const ex = new Date(expiry);
  ex.setHours(0, 0, 0, 0);
  return ex < today;
}

function statusClass(s) {
  if (s === "Expired") return "urgent";
  if (s === "Reserved" || s === "Issued") return "pending";
  return "done";
}

// Load Inventory from Django Backend or Fallback
async function loadInventory() {
  try {
    if (window.inventoryAPI && typeof window.inventoryAPI.getAll === "function") {
      const data = await window.inventoryAPI.getAll();
      if (Array.isArray(data)) {
        inventoryList = data.map(item => ({
          unitId: item.UnitID || item.unitId,
          donationId: item.DonationID || item.donationId,
          donorId: item.DonorID || item.donorId,
          bloodbankId: item.BloodBankID || item.bloodbankId || 1,
          bloodGroup: item.BloodGroup || item.bloodGroup,
          type: item.Type || item.type || "Blood",
          qty: item.Quantity || item.qty || 1,
          batchNo: item.BatchNo || item.batchNo || "B-001",
          expiry: item.ExpiryDate || item.expiry,
          status: item.Status || item.status || "Available"
        }));
        applyFilters();
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load inventory from API, using fallback:", err);
  }

  // Fallback to local storage
  try {
    const local = JSON.parse(localStorage.getItem(KEY));
    if (local && local.length > 0) {
      inventoryList = local;
      applyFilters();
      return;
    }
  } catch {}

  // Default baseline sample units
  const now = new Date();
  const expFuture = new Date(now.getTime() + 25 * 86400000).toISOString().split('T')[0];
  inventoryList = [
    { unitId: "U0001", donationId: "DN001", donorId: "D001", bloodbankId: 1, bloodGroup: "O+", type: "Blood", qty: 1, batchNo: "B-101", expiry: expFuture, status: "Available" },
    { unitId: "U0002", donationId: "DN002", donorId: "D003", bloodbankId: 1, bloodGroup: "B-", type: "Plasma", qty: 2, batchNo: "B-102", expiry: expFuture, status: "Available" }
  ];
  applyFilters();
}

function render(rows) {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  if (!rows || rows.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:20px; color:#6b7280;">No inventory records found.</td></tr>`;
    return;
  }

  rows.forEach((row) => {
    const u = row.item;
    const realIdx = row.realIdx;

    const expired = isExpired(u.expiry);
    const finalStatus = expired ? "Expired" : u.status;

    const tr = document.createElement("tr");
    tr.className = expired ? "row-expired" : "";
    tr.innerHTML = `
      <td><strong>${u.unitId}</strong></td>
      <td>${u.donationId}</td>
      <td>${u.donorId}</td>
      <td>${u.bloodbankId}</td>
      <td><span class="badge">${u.bloodGroup}</span></td>
      <td>${u.type}</td>
      <td>${u.qty}</td>
      <td>${u.batchNo}</td>
      <td>${u.expiry}</td>
      <td class="status ${statusClass(finalStatus)}">${finalStatus}</td>
      <td>
        <select class="input input-mini" data-unitid="${u.unitId}" data-update="${realIdx}" ${expired ? "disabled" : ""}>
          <option ${u.status === "Available" ? "selected" : ""}>Available</option>
          <option ${u.status === "Reserved" ? "selected" : ""}>Reserved</option>
          <option ${u.status === "Issued" ? "selected" : ""}>Issued</option>
        </select>
        <button class="btn-mini danger" data-unitid="${u.unitId}" data-del="${realIdx}">Delete</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

function applyFilters() {
  const q = (search?.value || "").toLowerCase().trim();
  const sf = statusFilter?.value || "";

  const rows = inventoryList.map((item, realIdx) => ({ item, realIdx }));

  const filtered = rows.filter(({ item }) => {
    const expired = isExpired(item.expiry);
    const finalStatus = expired ? "Expired" : item.status;

    const matchText =
      (item.unitId && item.unitId.toLowerCase().includes(q)) ||
      (item.donorId && item.donorId.toLowerCase().includes(q)) ||
      (item.batchNo && item.batchNo.toLowerCase().includes(q));

    const matchStatus = !sf || finalStatus === sf;
    return matchText && matchStatus;
  });

  render(filtered);
}

// Add unit
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const unitId = newUnitId();
    const donationId = document.getElementById("donationId").value.trim().toUpperCase();
    const donorId = document.getElementById("donorId").value.trim().toUpperCase();
    const bloodbankId = document.getElementById("bloodbankId").value.trim();
    const bloodGroup = document.getElementById("bloodGroup").value;
    const type = document.getElementById("type").value;
    const qty = document.getElementById("qty").value;
    const batchNo = document.getElementById("batchNo").value.trim();
    const expiry = document.getElementById("expiry").value;
    const status = document.getElementById("status").value;

    if (!donationId || !donorId || !bloodbankId || !bloodGroup || !qty || !batchNo || !expiry) {
      showMessage("Please fill required fields", true);
      return;
    }

    const payload = {
      UnitID: unitId,
      DonationID: donationId,
      DonorID: donorId,
      BloodBankID: parseInt(bloodbankId) || 1,
      BloodGroup: bloodGroup,
      Type: type,
      Quantity: parseInt(qty) || 1,
      BatchNo: batchNo,
      ExpiryDate: expiry,
      Status: status
    };

    try {
      if (window.inventoryAPI && typeof window.inventoryAPI.create === "function") {
        await window.inventoryAPI.create(payload);
        showMessage("Unit saved to database! ✅");
      }
    } catch (err) {
      console.warn("API save error:", err);
      showMessage("Saved (Offline fallback): " + err.message, true);
    }

    inventoryList.unshift({
      unitId,
      donationId,
      donorId,
      bloodbankId,
      bloodGroup,
      type,
      qty,
      batchNo,
      expiry,
      status
    });

    try {
      localStorage.setItem(KEY, JSON.stringify(inventoryList));
    } catch {}

    form.reset();
    applyFilters();
  });
}

// Update status
document.getElementById("invTable")?.addEventListener("change", async (e) => {
  const sel = e.target.closest("[data-update]");
  if (!sel) return;

  const unitId = sel.dataset.unitid;
  const newStatus = sel.value;

  try {
    if (window.inventoryAPI && typeof window.inventoryAPI.update === "function") {
      await window.inventoryAPI.update(unitId, { Status: newStatus });
    }
  } catch (err) {
    console.warn("API update error:", err);
  }

  const realIdx = Number(sel.dataset.update);
  if (inventoryList[realIdx]) {
    inventoryList[realIdx].status = newStatus;
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(inventoryList));
  } catch {}

  applyFilters();
  showMessage("Status updated ✅");
});

// Delete
document.getElementById("invTable")?.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;

  const unitId = btn.dataset.unitid;
  if (!confirm(`Are you sure you want to delete unit ${unitId}?`)) return;

  try {
    if (window.inventoryAPI && typeof window.inventoryAPI.delete === "function") {
      await window.inventoryAPI.delete(unitId);
    }
  } catch (err) {
    console.warn("API delete error:", err);
  }

  const realIdx = Number(btn.dataset.del);
  if (inventoryList[realIdx]) {
    inventoryList.splice(realIdx, 1);
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(inventoryList));
  } catch {}

  applyFilters();
  showMessage("Unit deleted");
});

if (search) search.addEventListener("input", applyFilters);
if (statusFilter) statusFilter.addEventListener("change", applyFilters);

// Initial expiry default (30 days from now)
const d = new Date();
d.setDate(d.getDate() + 30);
const expiryEl = document.getElementById("expiry");
if (expiryEl) expiryEl.valueAsDate = d;

// Initial load
loadInventory();
