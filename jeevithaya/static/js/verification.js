const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect
}

const form = document.getElementById("verForm");
const tableBody = document.querySelector("#verTable tbody");
const msg = document.getElementById("msg");
const search = document.getElementById("search");

const unitIdEl = document.getElementById("unitId");
const donorIdEl = document.getElementById("donorId");
const verifiedByEl = document.getElementById("verifiedBy");
const dateEl = document.getElementById("date");
const resultEl = document.getElementById("result");
const commentEl = document.getElementById("comment");

const KEY = "jv_verifications";
let verificationsList = [];

function newVid() {
  const next = Math.floor(1000 + Math.random() * 9000);
  return "V" + next;
}

function showMessage(text, isError = false) {
  if (!msg) return;
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => msg.textContent = "", 2500);
}

async function loadVerifications() {
  try {
    if (window.verificationAPI && typeof window.verificationAPI.getAll === "function") {
      const data = await window.verificationAPI.getAll();
      if (Array.isArray(data)) {
        verificationsList = data.map(v => ({
          verificationId: v.VerificationID || v.verificationId,
          unitId: v.UnitID || v.unitId,
          donorId: v.DonorID || v.donorId,
          date: v.Date || v.date,
          verifiedBy: v.VerifiedBy || v.verifiedBy,
          result: v.OverallResult || v.result || "Passed",
          comment: v.Notes || v.comment || ""
        }));
        applySearch();
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load verifications from API, using fallback:", err);
  }

  try {
    const local = JSON.parse(localStorage.getItem(KEY));
    if (local && local.length > 0) {
      verificationsList = local;
      applySearch();
      return;
    }
  } catch {}

  verificationsList = [
    { verificationId: "V0001", unitId: "U0001", donorId: "D001", date: new Date().toISOString().split('T')[0], verifiedBy: "Dr. Saman", result: "Passed", comment: "All markers clear" },
    { verificationId: "V0002", unitId: "U0002", donorId: "D003", date: new Date().toISOString().split('T')[0], verifiedBy: "Dr. Kasun", result: "Passed", comment: "Normal" }
  ];
  applySearch();
}

function render(rows) {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  if (!rows || rows.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:#6b7280;">No verification records found.</td></tr>`;
    return;
  }

  rows.forEach(({ item, realIdx }) => {
    const isPassed = item.result === "Passed" || item.result === "Pass";
    const cls = isPassed ? "done" : "urgent";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${item.verificationId}</strong></td>
      <td>${item.unitId}</td>
      <td>${item.donorId}</td>
      <td>${item.date}</td>
      <td>${item.verifiedBy}</td>
      <td class="status ${cls}">${item.result}</td>
      <td>${item.comment || "-"}</td>
      <td><button class="btn-mini danger" data-id="${item.verificationId}" data-del="${realIdx}">Delete</button></td>
    `;
    tableBody.appendChild(tr);
  });
}

function applySearch() {
  const q = (search?.value || "").toLowerCase().trim();
  const rows = verificationsList.map((item, realIdx) => ({ item, realIdx }));

  const filtered = rows.filter(({ item }) =>
    (item.verificationId && item.verificationId.toLowerCase().includes(q)) ||
    (item.unitId && item.unitId.toLowerCase().includes(q)) ||
    (item.donorId && item.donorId.toLowerCase().includes(q)) ||
    (item.verifiedBy && item.verifiedBy.toLowerCase().includes(q))
  );

  render(filtered);
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const verificationId = newVid();
    const unitId = unitIdEl.value.trim().toUpperCase();
    const donorId = donorIdEl.value.trim().toUpperCase();
    const verifiedBy = verifiedByEl.value.trim();
    const date = dateEl.value;
    const result = resultEl.value;
    const comment = commentEl ? commentEl.value.trim() : "";

    if (!unitId || !donorId || !verifiedBy || !date || !result) {
      showMessage("Please fill required fields", true);
      return;
    }

    const payload = {
      VerificationID: verificationId,
      UnitID: unitId,
      DonorID: donorId,
      VerifiedBy: verifiedBy,
      Date: date,
      OverallResult: result,
      Notes: comment
    };

    try {
      if (window.verificationAPI && typeof window.verificationAPI.create === "function") {
        await window.verificationAPI.create(payload);
        showMessage("Verification saved to database! ✅");
      }
    } catch (err) {
      console.warn("API save error:", err);
      showMessage("Saved (Offline fallback): " + err.message, true);
    }

    verificationsList.unshift({
      verificationId,
      unitId,
      donorId,
      verifiedBy,
      date,
      result,
      comment
    });

    try {
      localStorage.setItem(KEY, JSON.stringify(verificationsList));
    } catch {}

    form.reset();
    if (dateEl) dateEl.valueAsDate = new Date();
    applySearch();
  });
}

document.getElementById("verTable")?.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;

  const verId = btn.dataset.id;
  if (!confirm(`Are you sure you want to delete verification ${verId}?`)) return;

  try {
    if (window.verificationAPI && typeof window.verificationAPI.delete === "function") {
      await window.verificationAPI.delete(verId);
    }
  } catch (err) {
    console.warn("API delete error:", err);
  }

  const realIdx = Number(btn.dataset.del);
  if (verificationsList[realIdx]) {
    verificationsList.splice(realIdx, 1);
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(verificationsList));
  } catch {}

  applySearch();
  showMessage("Deleted");
});

if (search) search.addEventListener("input", applySearch);
if (dateEl) dateEl.valueAsDate = new Date();

loadVerifications();
