function getSession(){
  try {
    return JSON.parse(localStorage.getItem("jv_session")) ||
           JSON.parse(sessionStorage.getItem("jv_session"));
  } catch { return null; }
}

const session = getSession();
if (!session) {
  document.body.innerHTML = `
    <div style="font-family:system-ui; padding:40px;">
      <h2>Session not found</h2>
      <p>Please login first.</p>
      <a href="login.html">Go to Login</a>
    </div>
  `;
} else {

  const logoutBtn = document.getElementById("logoutBtn");
  const rangeSel = document.getElementById("range");
  const exportBtn = document.getElementById("exportBtn");

  logoutBtn.addEventListener("click", () => {
    window.location.href = "logout.html";
  });

  // Keys used in your pages
  const K = {
    donors: "jv_donors",         // if you don't store donors yet, will show 0
    patients: "jv_patients",
    requests: "jv_requests",
    inventory: "jv_inventory",
    donations: "jv_donations",
    verifications: "jv_verifications",
    disposals: "jv_disposals"
  };

  function load(key){
    try { return JSON.parse(localStorage.getItem(key)) || []; }
    catch { return []; }
  }

  function daysAgo(n){
    const d = new Date();
    d.setHours(0,0,0,0);
    d.setDate(d.getDate() - n);
    return d;
  }

  function inRange(dateStr, days){
    if (days === "all") return true;
    const dt = new Date(dateStr);
    return dt >= daysAgo(Number(days));
  }

  function isExpired(exp){
    const today = new Date(); today.setHours(0,0,0,0);
    const ex = new Date(exp); ex.setHours(0,0,0,0);
    return ex < today;
  }

  function setText(id, val){
    document.getElementById(id).textContent = val;
  }

  function row2(tbodyId, c1, c2){
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${c1}</td><td>${c2}</td>`;
    document.getElementById(tbodyId).appendChild(tr);
  }

  function render(){
    const days = rangeSel.value;

    const donors = load(K.donors);
    const patients = load(K.patients);
    const requestsAll = load(K.requests);
    const inventoryAll = load(K.inventory);
    const donationsAll = load(K.donations);
    const verAll = load(K.verifications);
    const disAll = load(K.disposals);

    // date filtering for transactions
    const requests = requestsAll.filter(r => inRange(r.requestDate || r.date, days));
    const donations = donationsAll.filter(d => inRange(d.date, days));
    const verifications = verAll.filter(v => inRange(v.date, days));
    const disposals = disAll.filter(d => inRange(d.date, days));
    const inventory = inventoryAll; // inventory is current state (not by date)

    setText("rDonors", donors.length);
    setText("rPatients", patients.length);
    setText("rRequests", requests.length);
    setText("rPending", requests.filter(r => r.status === "Pending").length);

    setText("rUnits", inventory.length);
    setText("rExpired", inventory.filter(u => isExpired(u.expiry)).length);
    setText("rVerifications", verifications.length);
    setText("rDisposals", disposals.length);

    // Requests by Status
    const statusBody = document.getElementById("statusTable");
    statusBody.innerHTML = "";
    const statuses = ["Pending","Approved","Fulfilled","Rejected"];
    statuses.forEach(s => row2("statusTable", s, requests.filter(r => r.status === s).length));

    // Inventory by Blood Group
    const bloodBody = document.getElementById("bloodTable");
    bloodBody.innerHTML = "";
    const groups = ["O+","O-","A+","A-","B+","B-","AB+","AB-"];
    groups.forEach(bg => row2("bloodTable", bg, inventory.filter(u => u.bloodGroup === bg).length));

    // Recent Activity (latest 10)
    const activity = [];
    requests.slice().reverse().forEach(r => activity.push({
      type: "Request",
      id: r.requestId ? ("REQ" + r.requestId).replace("REQREQ","REQ") : (r.requestId || ""),
      date: r.requestDate || "",
      details: `${r.bloodGroup} ${r.type} | ${r.qty} | ${r.status}`
    }));

    donations.slice().reverse().forEach(d => activity.push({
      type: "Donation",
      id: d.donationId,
      date: d.date,
      details: `${d.donorId} | ${d.bloodGroup} ${d.type} | ${d.qty}`
    }));

    verifications.slice().reverse().forEach(v => activity.push({
      type: "Verification",
      id: v.verificationId,
      date: v.date,
      details: `${v.unitId} | ${v.result} | ${v.verifiedBy}`
    }));

    activity.sort((a,b) => (new Date(b.date) - new Date(a.date)));
    const actBody = document.getElementById("activityTable");
    actBody.innerHTML = "";
    activity.slice(0,10).forEach(a => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${a.type}</td><td>${a.id}</td><td>${a.date}</td><td>${a.details}</td>`;
      actBody.appendChild(tr);
    });

    // export
    exportBtn.onclick = () => {
      const data = {
        donors, patients,
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
      a.download = "jeevithaya_reports_export.json";
      a.click();
      URL.revokeObjectURL(url);
    };
  }

  rangeSel.addEventListener("change", render);
  render();
}