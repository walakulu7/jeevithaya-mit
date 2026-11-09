const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect
}

const logoutBtn = document.getElementById("logoutBtn");
const form = document.getElementById("requestForm");
const tableBody = document.querySelector("#requestTable tbody");
const msg = document.getElementById("msg");
const search = document.getElementById("search");
const statusFilter = document.getElementById("statusFilter");

const KEY = "jv_requests";
let requestList = [];

function showMessage(text, isError = false) {
  if (!msg) return;
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => { msg.textContent = ""; }, 2500);
}

function newReqId() {
  const next = Math.floor(100 + Math.random() * 900);
  return "REQ" + next;
}

function urgencyClass(u) {
  if (u === "Critical") return "urgent";
  if (u === "Urgent") return "pending";
  return "done";
}

function statusClass(s) {
  if (s === "Pending") return "pending";
  if (s === "Rejected") return "urgent";
  return "done";
}

// Load Requests from Django Backend or Fallback
async function loadRequests() {
  try {
    if (window.requestAPI && typeof window.requestAPI.getAll === "function") {
      const data = await window.requestAPI.getAll();
      if (Array.isArray(data)) {
        requestList = data.map(r => ({
          requestId: r.RequestID || r.requestId,
          patientId: r.PatientID || r.patientId,
          hospitalId: r.HospitalID || r.hospitalId,
          requestDate: r.RequestDate || r.requestDate,
          bloodGroup: r.BloodGroup || r.bloodGroup,
          type: r.Type || r.type || "Blood",
          qty: r.Quantity || r.qty || 1,
          urgency: r.Urgency || r.urgency || "Normal",
          status: r.Status || r.status || "Pending",
        }));
        applyFilters();
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load requests from API, using fallback:", err);
  }

  // Fallback to local storage
  try {
    const local = JSON.parse(localStorage.getItem(KEY));
    if (local && local.length > 0) {
      requestList = local;
      applyFilters();
      return;
    }
  } catch {}

  requestList = [
    { requestId: "REQ101", patientId: "P001", hospitalId: 1, requestDate: new Date().toISOString().split('T')[0], bloodGroup: "O+", type: "Blood", qty: 2, urgency: "Critical", status: "Pending" },
    { requestId: "REQ102", patientId: "P002", hospitalId: 1, requestDate: new Date().toISOString().split('T')[0], bloodGroup: "A+", type: "Plasma", qty: 1, urgency: "Urgent", status: "Approved" }
  ];
  applyFilters();
}

function render(list) {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  if (!list || list.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:20px; color:#6b7280;">No requests found.</td></tr>`;
    return;
  }

  list.forEach((r, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>#${r.requestId}</strong></td>
      <td>${r.patientId}</td>
      <td>${r.hospitalId}</td>
      <td><span class="badge">${r.bloodGroup}</span></td>
      <td>${r.type}</td>
      <td>${r.qty}</td>
      <td class="status ${urgencyClass(r.urgency)}">${r.urgency}</td>
      <td class="status ${statusClass(r.status)}">${r.status}</td>
      <td>
        <select class="input input-mini" data-id="${r.requestId}" data-idx="${idx}">
          <option ${r.status === "Pending" ? "selected" : ""}>Pending</option>
          <option ${r.status === "Approved" ? "selected" : ""}>Approved</option>
          <option ${r.status === "Fulfilled" ? "selected" : ""}>Fulfilled</option>
          <option ${r.status === "Rejected" ? "selected" : ""}>Rejected</option>
        </select>
      </td>
      <td>
        <button class="btn-mini danger" data-id="${r.requestId}" data-del="${idx}">Delete</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

function applyFilters() {
  const q = search ? search.value.toLowerCase().trim() : "";
  const sf = statusFilter ? statusFilter.value : "";

  const filtered = requestList.filter(r => {
    const matchText =
      ("#" + r.requestId).toLowerCase().includes(q) ||
      (r.patientId && r.patientId.toLowerCase().includes(q));

    const matchStatus = !sf || r.status === sf;
    return matchText && matchStatus;
  });

  render(filtered);
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const requestId = newReqId();
    const patientId = document.getElementById("patientId").value.trim().toUpperCase();
    const hospitalId = document.getElementById("hospitalId").value.trim();
    const requestDate = document.getElementById("requestDate").value;
    const bloodGroup = document.getElementById("bloodGroup").value;
    const type = document.getElementById("type").value;
    const qty = document.getElementById("qty").value;
    const urgency = document.getElementById("urgency").value;
    const status = document.getElementById("status").value;

    if (!patientId || !hospitalId || !requestDate || !bloodGroup || !qty || !urgency || !status) {
      showMessage("Please fill required fields", true);
      return;
    }

    const payload = {
      RequestID: requestId,
      PatientID: patientId,
      HospitalID: parseInt(hospitalId) || 1,
      RequestDate: requestDate,
      BloodGroup: bloodGroup,
      Type: type,
      Quantity: parseInt(qty) || 1,
      Urgency: urgency,
      Status: status
    };

    try {
      if (window.requestAPI && typeof window.requestAPI.create === "function") {
        await window.requestAPI.create(payload);
        showMessage("Request saved to database! ✅");
      }
    } catch (err) {
      console.warn("API save error:", err);
      showMessage("Saved (Offline fallback): " + err.message, true);
    }

    requestList.unshift({
      requestId,
      patientId,
      hospitalId,
      requestDate,
      bloodGroup,
      type,
      qty,
      urgency,
      status
    });

    try {
      localStorage.setItem(KEY, JSON.stringify(requestList));
    } catch {}

    form.reset();
    document.getElementById("requestDate").valueAsDate = new Date();
    applyFilters();
  });
}

// Update status
document.getElementById("requestTable")?.addEventListener("change", async (e) => {
  const sel = e.target.closest("[data-id]");
  if (!sel) return;

  const reqId = sel.dataset.id;
  const newStatus = sel.value;

  try {
    if (window.requestAPI && typeof window.requestAPI.update === "function") {
      await window.requestAPI.update(reqId, { Status: newStatus });
    }
  } catch (err) {
    console.warn("API update error:", err);
  }

  const idx = Number(sel.dataset.idx);
  if (requestList[idx]) {
    requestList[idx].status = newStatus;
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(requestList));
  } catch {}

  applyFilters();
  showMessage("Status updated ✅");
});

// Delete
document.getElementById("requestTable")?.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;

  const reqId = btn.dataset.id;
  if (!confirm(`Are you sure you want to delete request #${reqId}?`)) return;

  try {
    if (window.requestAPI && typeof window.requestAPI.delete === "function") {
      await window.requestAPI.delete(reqId);
    }
  } catch (err) {
    console.warn("API delete error:", err);
  }

  const idx = Number(btn.dataset.del);
  if (requestList[idx]) {
    requestList.splice(idx, 1);
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(requestList));
  } catch {}

  applyFilters();
  showMessage("Request deleted");
});

if (search) search.addEventListener("input", applyFilters);
if (statusFilter) statusFilter.addEventListener("change", applyFilters);

const reqDateEl = document.getElementById("requestDate");
if (reqDateEl) reqDateEl.valueAsDate = new Date();

loadRequests();
