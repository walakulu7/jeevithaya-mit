const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect
}

const logoutBtn = document.getElementById("logoutBtn");
const rangeSel = document.getElementById("range");
const exportBtn = document.getElementById("exportBtn");

// Keys used in local storage
const K = {
  donors: "jv_donors",
  patients: "jv_patients",
  requests: "jv_requests",
  inventory: "jv_inventory",
  donations: "jv_donations",
  verifications: "jv_verifications",
  disposals: "jv_disposals"
};

let store = {
  donors: [],
  patients: [],
  requests: [],
  inventory: [],
  donations: [],
  verifications: [],
  disposals: []
};

function loadLocal(key) {
  try { return JSON.parse(localStorage.getItem(key)) || []; }
  catch { return []; }
}

function daysAgo(n) {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - n);
  return d;
}

function inRange(dateStr, days) {
  if (days === "all" || !dateStr) return true;
  const dt = new Date(dateStr);
  return dt >= daysAgo(Number(days));
}

function isExpired(exp) {
  if (!exp) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const ex = new Date(exp);
  ex.setHours(0, 0, 0, 0);
  return ex < today;
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function row2(tbodyId, c1, c2) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><strong>${c1}</strong></td><td>${c2}</td>`;
  tbody.appendChild(tr);
}

// Fetch all live data from Django MySQL backend
async function fetchLiveData() {
  try {
    const [d, p, r, i, dn, v, dp] = await Promise.allSettled([
      window.donorAPI?.getAll(),
      window.patientAPI?.getAll(),
      window.requestAPI?.getAll(),
      window.inventoryAPI?.getAll(),
      window.donationAPI?.getAll(),
      window.verificationAPI?.getAll(),
      window.disposalAPI?.getAll(),
    ]);

    if (d.status === "fulfilled" && Array.isArray(d.value)) {
      store.donors = d.value.map(x => ({ id: x.DonorID || x.id, name: x.Name || x.name, blood: x.BloodGroup, status: x.Status }));
      localStorage.setItem(K.donors, JSON.stringify(store.donors));
    } else {
      store.donors = loadLocal(K.donors);
    }

    if (p.status === "fulfilled" && Array.isArray(p.value)) {
      store.patients = p.value.map(x => ({ patientId: x.PatientID, name: x.Name, bloodGroup: x.BloodGroup, urgency: x.Urgency }));
      localStorage.setItem(K.patients, JSON.stringify(store.patients));
    } else {
      store.patients = loadLocal(K.patients);
    }

    if (r.status === "fulfilled" && Array.isArray(r.value)) {
      store.requests = r.value.map(x => ({ requestId: x.RequestID, bloodGroup: x.BloodGroup, type: x.Type, qty: x.Quantity, status: x.Status, urgency: x.Urgency, requestDate: x.RequestDate }));
      localStorage.setItem(K.requests, JSON.stringify(store.requests));
    } else {
      store.requests = loadLocal(K.requests);
    }

    if (i.status === "fulfilled" && Array.isArray(i.value)) {
      store.inventory = i.value.map(x => ({ unitId: x.UnitID, bloodGroup: x.BloodGroup, type: x.Type, qty: x.Quantity, expiry: x.ExpiryDate, status: x.Status }));
      localStorage.setItem(K.inventory, JSON.stringify(store.inventory));
    } else {
      store.inventory = loadLocal(K.inventory);
    }

    if (dn.status === "fulfilled" && Array.isArray(dn.value)) {
      store.donations = dn.value.map(x => ({ donationId: x.DonationID, donorId: x.DonorID, bloodGroup: x.BloodGroup, type: x.Type, qty: x.Quantity, date: x.Date }));
      localStorage.setItem(K.donations, JSON.stringify(store.donations));
    } else {
      store.donations = loadLocal(K.donations);
    }

    if (v.status === "fulfilled" && Array.isArray(v.value)) {
      store.verifications = v.value.map(x => ({ verificationId: x.VerificationID, unitId: x.UnitID, result: x.OverallResult, verifiedBy: x.VerifiedBy, date: x.Date }));
      localStorage.setItem(K.verifications, JSON.stringify(store.verifications));
    } else {
      store.verifications = loadLocal(K.verifications);
    }

    if (dp.status === "fulfilled" && Array.isArray(dp.value)) {
      store.disposals = dp.value.map(x => ({ disposalId: x.DisposalID, unitId: x.UnitID, reason: x.Reason, date: x.DisposalDate }));
      localStorage.setItem(K.disposals, JSON.stringify(store.disposals));
    } else {
      store.disposals = loadLocal(K.disposals);
    }

  } catch (err) {
    console.warn("Could not fetch reports from backend API, using local storage:", err);
    Object.keys(K).forEach(k => {
      store[k] = loadLocal(K[k]);
    });
  }

  render();
}

function render() {
  const days = rangeSel ? rangeSel.value : "all";

  const donors = store.donors;
  const patients = store.patients;
  const requestsAll = store.requests;
  const inventoryAll = store.inventory;
  const donationsAll = store.donations;
  const verAll = store.verifications;
  const disAll = store.disposals;

  // Filter transactions by selected date range
  const requests = requestsAll.filter(r => inRange(r.requestDate || r.date, days));
  const donations = donationsAll.filter(d => inRange(d.date, days));
  const verifications = verAll.filter(v => inRange(v.date, days));
  const disposals = disAll.filter(d => inRange(d.date || d.DisposalDate, days));
  const inventory = inventoryAll;

  // Summary Metrics
  setText("rDonors", donors.length);
  setText("rPatients", patients.length);
  setText("rRequests", requests.length);
  setText("rPending", requests.filter(r => r.status === "Pending").length);

  setText("rUnits", inventory.length);
  setText("rExpired", inventory.filter(u => isExpired(u.expiry) || u.status === "Expired").length);
  setText("rVerifications", verifications.length);
  setText("rDisposals", disposals.length);

  // Requests by Status Table
  const statusBody = document.getElementById("statusTable");
  if (statusBody) {
    statusBody.innerHTML = "";
    const statuses = ["Pending", "Approved", "Fulfilled", "Rejected"];
    statuses.forEach(s => row2("statusTable", s, requests.filter(r => r.status === s).length));
  }

  // Inventory by Blood Group Table
  const bloodBody = document.getElementById("bloodTable");
  if (bloodBody) {
    bloodBody.innerHTML = "";
    const groups = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"];
    groups.forEach(bg => {
      const count = inventory
        .filter(u => u.bloodGroup === bg && u.status === "Available")
        .reduce((sum, item) => sum + (parseInt(item.qty) || 1), 0);
      row2("bloodTable", bg, count);
    });
  }

  // Recent Activity Feed
  const activity = [];
  requests.slice().reverse().forEach(r => activity.push({
    type: "Request",
    id: r.requestId ? ("REQ" + r.requestId).replace("REQREQ", "REQ") : (r.requestId || ""),
    date: r.requestDate || "",
    details: `${r.bloodGroup || ""} ${r.type || "Blood"} | ${r.status || "Pending"}`
  }));

  donations.slice().reverse().forEach(d => activity.push({
    type: "Donation",
    id: d.donationId,
    date: d.date,
    details: `Donor: ${d.donorId} | ${d.bloodGroup} ${d.type} | Qty: ${d.qty}`
  }));

  verifications.slice().reverse().forEach(v => activity.push({
    type: "Verification",
    id: v.verificationId,
    date: v.date,
    details: `Unit: ${v.unitId} | ${v.result} | By: ${v.verifiedBy}`
  }));

  activity.sort((a, b) => (new Date(b.date) - new Date(a.date)));
  const actBody = document.getElementById("activityTable");
  if (actBody) {
    actBody.innerHTML = "";
    if (activity.length === 0) {
      actBody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:16px; color:#6b7280;">No transactions in this period.</td></tr>`;
    } else {
      activity.slice(0, 10).forEach(a => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><strong>${a.type}</strong></td><td>${a.id}</td><td>${a.date}</td><td>${a.details}</td>`;
        actBody.appendChild(tr);
      });
    }
  }

  // Export JSON Report
  if (exportBtn) {
    exportBtn.onclick = () => {
      const data = {
        exportedAt: new Date().toISOString(),
        dateRange: days,
        donors,
        patients,
        requests: requestsAll,
        inventory: inventoryAll,
        donations: donationsAll,
        verifications: verAll,
        disposals: disAll
      };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `jeevithaya_audit_report_${days}_days.json`;
      a.click();
      URL.revokeObjectURL(url);
    };
  }

  // Export CSV Report
  const exportCsvBtn = document.getElementById("exportCsvBtn");
  if (exportCsvBtn) {
    exportCsvBtn.onclick = () => {
      let csv = "Type,ID,Date,Details\n";
      activity.forEach(row => {
        const cleanDetails = (row.details || "").replace(/"/g, '""');
        csv += `"${row.type}","${row.id}","${row.date}","${cleanDetails}"\n`;
      });
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `jeevithaya_activity_${days}_days.csv`;
      a.click();
      URL.revokeObjectURL(url);
    };
  }

  // Print Report
  const printBtn = document.getElementById("printBtn");
  if (printBtn) {
    printBtn.onclick = () => {
      window.print();
    };
  }
}

if (rangeSel) rangeSel.addEventListener("change", render);

// Initial Load
fetchLiveData();
