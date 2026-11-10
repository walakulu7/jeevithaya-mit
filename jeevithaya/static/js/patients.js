const logoutBtn = document.getElementById("logoutBtn");
const form = document.getElementById("patientForm");
const tableBody = document.querySelector("#patientTable tbody");
const msg = document.getElementById("msg");
const search = document.getElementById("search");

const session = applyRBAC();
if (!session) {
  // applyRBAC handles redirection
}

const KEY = "jv_patients";
let patients = [];

function showMessage(text, isError = false) {
  if (!msg) return;
  msg.className = "msg " + (isError ? "err" : "ok");
  msg.textContent = text;
  setTimeout(() => { msg.textContent = ""; }, 2500);
}

function newId() {
  const next = Math.floor(100 + Math.random() * 900);
  return "P" + next;
}

// Load patients from Django backend or fallback
async function loadPatients() {
  try {
    if (window.patientAPI && typeof window.patientAPI.getAll === "function") {
      const data = await window.patientAPI.getAll();
      if (Array.isArray(data)) {
        patients = data.map(p => ({
          patientId: p.PatientID || p.patientId,
          name: p.Name || p.name,
          hospitalId: p.HospitalID || p.hospitalId,
          bloodGroup: p.BloodGroup || p.bloodGroup,
          type: p.Type || p.type || "Blood",
          urgency: p.Urgency || p.urgency || "Normal",
          contact: p.Contact || p.contact,
          dob: p.DateOfBirth || p.dob,
          age: p.Age || p.age,
          gender: p.Gender || p.gender,
          address: p.Address || p.address,
        }));
        render(patients);
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load patients from API, checking local storage:", err);
  }

  // Fallback to local storage
  try {
    const local = JSON.parse(localStorage.getItem(KEY)) || [];
    if (local.length > 0) {
      patients = local;
      render(patients);
      return;
    }
  } catch {}

  patients = [
    { patientId: "P001", name: "Kamal Perera", hospitalId: 1, bloodGroup: "O+", type: "Blood", urgency: "Critical", contact: "0712345678" },
    { patientId: "P002", name: "Nimal Silva", hospitalId: 1, bloodGroup: "A+", type: "Plasma", urgency: "Urgent", contact: "0778901234" }
  ];
  render(patients);
}

function render(list) {
  if (!tableBody) return;
  tableBody.innerHTML = "";

  if (!list || list.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:#6b7280;">No patients found.</td></tr>`;
    return;
  }

  list.forEach((p) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${p.patientId}</strong></td>
      <td>${p.name}</td>
      <td>${p.hospitalId}</td>
      <td><span class="badge">${p.bloodGroup}</span></td>
      <td>${p.type}</td>
      <td class="status ${p.urgency === "Critical" ? "urgent" : (p.urgency === "Urgent" ? "pending" : "done")}">
        ${p.urgency}
      </td>
      <td>${p.contact}</td>
      <td>
        <button class="btn-mini danger" data-id="${p.patientId}">Delete</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });

  tableBody.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", () => deletePatient(btn.getAttribute("data-id")));
  });
}

function applySearch() {
  const q = search ? search.value.toLowerCase().trim() : "";
  const filtered = patients.filter(p =>
    (p.name && p.name.toLowerCase().includes(q)) ||
    (p.contact && String(p.contact).includes(q)) ||
    (p.patientId && p.patientId.toLowerCase().includes(q))
  );
  render(filtered);
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const patientId = newId();
    const hospitalId = document.getElementById("hospitalId").value.trim();
    const name = document.getElementById("name").value.trim();
    const dob = document.getElementById("dob")?.value || "";
    const age = document.getElementById("age")?.value || "";
    const gender = document.getElementById("gender")?.value || "";
    const contact = document.getElementById("contact").value.trim();
    const address = document.getElementById("address")?.value.trim() || "";
    const bloodGroup = document.getElementById("bloodGroup")?.value || "";
    const type = document.getElementById("type")?.value || "Blood";
    const urgency = document.getElementById("urgency")?.value || "Normal";

    if (!hospitalId || !name || !contact || !bloodGroup) {
      showMessage("Please fill all required fields", true);
      return;
    }

    const payload = {
      PatientID: patientId,
      HospitalID: parseInt(hospitalId) || 1,
      Name: name,
      DateOfBirth: dob || null,
      Age: age ? parseInt(age) : null,
      Gender: gender,
      Contact: contact,
      Address: address,
      BloodGroup: bloodGroup,
      Type: type,
      Urgency: urgency,
    };

    try {
      if (window.patientAPI && typeof window.patientAPI.create === "function") {
        await window.patientAPI.create(payload);
        showMessage("Patient saved to database! ✅");
      }
    } catch (err) {
      console.warn("API save error:", err);
      showMessage("Saved (Offline fallback): " + err.message, true);
    }

    patients.unshift({
      patientId,
      hospitalId,
      name,
      dob,
      age,
      gender,
      contact,
      address,
      bloodGroup,
      type,
      urgency,
    });

    try {
      localStorage.setItem(KEY, JSON.stringify(patients));
    } catch {}

    form.reset();
    applySearch();
    if (window.closeCollapsibleForm) window.closeCollapsibleForm();
  });
}

async function deletePatient(patientId) {
  if (!confirm(`Are you sure you want to delete patient ${patientId}?`)) return;

  try {
    if (window.patientAPI && typeof window.patientAPI.delete === "function") {
      await window.patientAPI.delete(patientId);
    }
  } catch (err) {
    console.warn("API delete error:", err);
  }

  patients = patients.filter(p => p.patientId !== patientId);
  try {
    localStorage.setItem(KEY, JSON.stringify(patients));
  } catch {}

  applySearch();
  showMessage(`Patient ${patientId} deleted.`);
}

if (search) search.addEventListener("input", applySearch);

// Initial load
loadPatients();
