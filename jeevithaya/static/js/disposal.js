const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirect
}

const form = document.getElementById("disForm");
const tableBody = document.querySelector("#disTable tbody");
const msg = document.getElementById("msg");
const search = document.getElementById("search");

const unitIdEl = document.getElementById("unitId");
const donorIdEl = document.getElementById("donorId");
const verificationIdEl = document.getElementById("verificationId");
const disposedByEl = document.getElementById("disposedBy");
const dateEl = document.getElementById("date");
const reasonEl = document.getElementById("reason");

const KEY = "jv_disposals";
let disposalsList = [];

function newDid() {
  const next = Math.floor(1000 + Math.random() * 9000);
  return "DISP" + next;
}

function showMessage(text, isError = false) {
  if (!msg) return;
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => msg.textContent = "", 2500);
}

async function loadDisposals() {
  try {
    if (window.disposalAPI && typeof window.disposalAPI.getAll === "function") {
      const data = await window.disposalAPI.getAll();
      if (Array.isArray(data)) {
        disposalsList = data.map(d => ({
          disposalId: d.DisposalID || d.disposalId,
          unitId: d.UnitID || d.unitId,
          donorId: d.DonorID || d.donorId || "-",
          verificationId: d.VerificationID || d.verificationId || "-",
          date: d.DisposalDate || d.date,
          reason: d.Reason || d.reason,
          disposedBy: d.DisposedBy || d.disposedBy
        }));
        render(disposalsList);
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load disposals from API, using fallback:", err);
  }

  try {
    const local = JSON.parse(localStorage.getItem(KEY));
    if (local && local.length > 0) {
      disposalsList = local;
      render(disposalsList);
      return;
    }
  } catch {}

  disposalsList = [
    { disposalId: "DISP1001", unitId: "U0099", donorId: "D002", verificationId: "V0010", date: new Date().toISOString().split('T')[0], reason: "Expired", disposedBy: "Lab Tech" }
  ];
  render(disposalsList);
}

function render(list) {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  if (!list || list.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:#6b7280;">No disposal records found.</td></tr>`;
    return;
  }

  list.forEach((d, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${d.disposalId}</strong></td>
      <td>${d.unitId}</td>
      <td>${d.donorId || "-"}</td>
      <td>${d.verificationId || "-"}</td>
      <td>${d.date}</td>
      <td class="status urgent">${d.reason}</td>
      <td>${d.disposedBy}</td>
      <td><button class="btn-mini danger" data-id="${d.disposalId}" data-del="${i}">Delete</button></td>
    `;
    tableBody.appendChild(tr);
  });
}

function applySearch() {
  const q = (search?.value || "").toLowerCase().trim();
  const filtered = disposalsList.filter(d =>
    (d.disposalId && d.disposalId.toLowerCase().includes(q)) ||
    (d.unitId && d.unitId.toLowerCase().includes(q)) ||
    (d.reason && d.reason.toLowerCase().includes(q)) ||
    (d.disposedBy && d.disposedBy.toLowerCase().includes(q))
  );
  render(filtered);
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const disposalId = newDid();
    const unitId = unitIdEl.value.trim().toUpperCase();
    const donorId = donorIdEl ? donorIdEl.value.trim().toUpperCase() : "-";
    const verificationId = verificationIdEl ? verificationIdEl.value.trim().toUpperCase() : "-";
    const disposedBy = disposedByEl.value.trim();
    const date = dateEl.value;
    const reason = reasonEl.value;

    if (!unitId || !disposedBy || !date || !reason) {
      showMessage("Please fill required fields", true);
      return;
    }

    const payload = {
      DisposalID: disposalId,
      UnitID: unitId,
      DisposalDate: date,
      Reason: reason,
      DisposedBy: disposedBy,
      Notes: `Donor: ${donorId}, Ver: ${verificationId}`
    };

    try {
      if (window.disposalAPI && typeof window.disposalAPI.create === "function") {
        await window.disposalAPI.create(payload);
        showMessage("Disposal recorded in database! ✅");
      }
    } catch (err) {
      console.warn("API save error:", err);
      showMessage("Recorded (Offline fallback): " + err.message, true);
    }

    disposalsList.unshift({
      disposalId,
      unitId,
      donorId,
      verificationId,
      date,
      reason,
      disposedBy
    });

    try {
      localStorage.setItem(KEY, JSON.stringify(disposalsList));
    } catch {}

    form.reset();
    if (dateEl) dateEl.valueAsDate = new Date();
    applySearch();
    if (window.closeCollapsibleForm) window.closeCollapsibleForm();
  });
}

document.getElementById("disTable")?.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del]");
  if (!btn) return;

  const dispId = btn.dataset.id;
  if (!confirm(`Are you sure you want to delete disposal ${dispId}?`)) return;

  try {
    if (window.disposalAPI && typeof window.disposalAPI.delete === "function") {
      await window.disposalAPI.delete(dispId);
    }
  } catch (err) {
    console.warn("API delete error:", err);
  }

  const i = Number(btn.dataset.del);
  if (disposalsList[i]) {
    disposalsList.splice(i, 1);
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(disposalsList));
  } catch {}

  applySearch();
  showMessage("Deleted");
});

if (search) search.addEventListener("input", applySearch);
if (dateEl) dateEl.valueAsDate = new Date();

loadDisposals();
