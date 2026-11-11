const session = applyRBAC();

const TAB_TITLES = {
  overview: "Executive Overview Report",
  inventory: "Inventory & Cold-Chain Expiry Report",
  requests: "Hospital Requests & Fulfillment Report",
  donations: "Donors & Collection Intake Report",
  verification: "Serological Verification & QC Audit Report",
  disposal: "Bio-Waste Disposal & Wastage Compliance Report",
};

const VALID_TABS = Object.keys(TAB_TITLES);
const BLOOD_GROUPS = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"];

const state = {
  activeTab: "overview",
  bundle: null,
};

// DOM elements
const rangeSel = document.getElementById("range");
const fromField = document.getElementById("fromField");
const toField = document.getElementById("toField");
const fromDateEl = document.getElementById("fromDate");
const toDateEl = document.getElementById("toDate");
const bloodGroupSel = document.getElementById("filterBloodGroup");
const typeSel = document.getElementById("filterType");
const searchEl = document.getElementById("reportSearch");
const resetBtn = document.getElementById("resetFiltersBtn");

const exportCsvBtn = document.getElementById("exportCsvBtn");
const exportBtn = document.getElementById("exportBtn");
const pdfReportBtn = document.getElementById("pdfReportBtn");
const pdfPackBtn = document.getElementById("pdfPackBtn");

function esc(val) {
  return String(val ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function emptyRow(tbodyId, colspan, text = "No records match the selected filters.") {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center; padding:16px; color:var(--text-muted);">${esc(text)}</td></tr>`;
}

function renderBarList(containerId, items, wideLabel = false) {
  const box = document.getElementById(containerId);
  if (!box) return;
  box.innerHTML = "";
  if (!items || items.length === 0) {
    box.innerHTML = `<p class="muted" style="margin:6px 0;">No data available for chart.</p>`;
    return;
  }
  const maxVal = Math.max(1, ...items.map(item => Number(item.value) || 0));
  items.forEach(item => {
    const val = Number(item.value) || 0;
    const width = Math.min(100, Math.round((val / maxVal) * 100));
    const row = document.createElement("div");
    row.className = `bar-row${wideLabel ? " wide-label" : ""}`;
    row.innerHTML = `
      <span class="bar-label">${esc(item.label)}</span>
      <div class="bar-track">
        <div class="bar-fill ${esc(item.tone || "")}" style="width:${width}%"></div>
      </div>
      <span class="bar-meta">${esc(item.meta ?? val)}</span>
    `;
    box.appendChild(row);
  });
}

function statusPill(text) {
  const clean = String(text || "").toLowerCase();
  let cls = "pending";
  if (["fulfilled", "passed", "available", "eligible", "healthy (> 30d)", "sufficient"].includes(clean)) {
    cls = "done";
  } else if (["rejected", "failed", "expired", "critical (<= 7d)", "critical", "not eligible", "contaminated", "shortage", "failed verification"].includes(clean)) {
    cls = "urgent";
  }
  return `<span class="status ${cls}">${esc(text)}</span>`;
}

function matchesSearch(obj, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  return Object.values(obj).some(v => String(v ?? "").toLowerCase().includes(q));
}

function getFilters() {
  const rangeVal = rangeSel ? rangeSel.value : "all";
  const params = {
    days: rangeVal === "custom" ? "all" : rangeVal,
    blood_group: bloodGroupSel ? bloodGroupSel.value : "all",
    item_type: typeSel ? typeSel.value : "all",
  };
  if (rangeVal === "custom") {
    if (fromDateEl?.value) params.from = fromDateEl.value;
    if (toDateEl?.value) params.to = toDateEl.value;
  }
  return params;
}

function syncCustomDateVisibility() {
  const isCustom = rangeSel?.value === "custom";
  if (fromField) fromField.style.display = isCustom ? "flex" : "none";
  if (toField) toField.style.display = isCustom ? "flex" : "none";
}

function updatePrintMetadata(mode = "active") {
  const f = getFilters();
  const periodLabel = rangeSel?.value === "custom"
    ? `${f.from || "..."} to ${f.to || "..."}`
    : (rangeSel?.options[rangeSel.selectedIndex]?.text || "All Time");
  const bgLabel = f.blood_group === "all" ? "All Groups" : f.blood_group;
  const typeLabel = f.item_type === "all" ? "All Components" : f.item_type;

  setText("printReportTitle", mode === "all" ? "Complete Executive Audit Report Pack" : TAB_TITLES[state.activeTab]);
  setText("printFilterSummary", `Period: ${periodLabel} | Blood Group: ${bgLabel} | Type: ${typeLabel}`);
  setText("printGeneratedAt", `Generated: ${new Date().toLocaleString()}`);
  setText("printPreparedBy", `Prepared by: ${session?.name || session?.email || "Authorized User"} (${session?.role || "Staff"})`);
  document.body.setAttribute("data-print-mode", mode);
}

function syncPdfLinks() {
  if (!window.reportAPI || typeof window.reportAPI.pdfUrl !== "function") return;
  const f = getFilters();
  const preparedBy = session?.name || session?.email || "System Administrator";
  if (pdfReportBtn) {
    pdfReportBtn.href = window.reportAPI.pdfUrl({
      type: state.activeTab,
      ...f,
      prepared_by: preparedBy,
    });
  }
  if (pdfPackBtn) {
    pdfPackBtn.href = window.reportAPI.pdfUrl({
      type: "all",
      ...f,
      prepared_by: preparedBy,
      download: "1",
    });
  }
}

function setActiveTab(tab, pushUrl = true) {
  if (!VALID_TABS.includes(tab)) tab = "overview";
  state.activeTab = tab;

  document.querySelectorAll(".report-tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.querySelectorAll(".report-panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === `panel-${tab}`);
  });

  syncPdfLinks();

  if (pushUrl) {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", tab);
      window.history.replaceState({}, "", url.toString());
    } catch {}
  }
}

// Offline/localStorage fallback calculator in case backend API is unreachable
function loadLocal(key) {
  try { return JSON.parse(localStorage.getItem(key)) || []; }
  catch { return []; }
}

function buildOfflineBundle(filters) {
  const donors = loadLocal("jv_donors");
  const patients = loadLocal("jv_patients");
  const requests = loadLocal("jv_requests");
  const inventory = loadLocal("jv_inventory");
  const donations = loadLocal("jv_donations");
  const verifications = loadLocal("jv_verifications");
  const disposals = loadLocal("jv_disposals");

  const matchCommon = (bg, tp) => {
    if (filters.blood_group !== "all" && bg !== filters.blood_group) return false;
    if (filters.item_type !== "all" && tp !== filters.item_type) return false;
    return true;
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const invFiltered = inventory.filter(u => matchCommon(u.bloodGroup || u.BloodGroup, u.type || u.Type));
  const reqFiltered = requests.filter(r => matchCommon(r.bloodGroup || r.BloodGroup, r.type || r.Type));
  const donFiltered = donations.filter(d => matchCommon(d.bloodGroup || d.BloodGroup, d.type || d.Type));
  const donorsFiltered = donors.filter(d => filters.blood_group === "all" || (d.blood || d.BloodGroup) === filters.blood_group);

  const availUnits = invFiltered.filter(u => (u.status || u.Status) === "Available").reduce((s, u) => s + (parseInt(u.qty || u.Quantity, 10) || 1), 0);
  const reqFulfilled = reqFiltered.filter(r => (r.status || r.Status) === "Fulfilled").length;
  const verPassed = verifications.filter(v => (v.result || v.OverallResult) === "Passed").length;

  const supplyVsDemand = BLOOD_GROUPS.map(bg => {
    const available = invFiltered.filter(u => (u.bloodGroup || u.BloodGroup) === bg && (u.status || u.Status) === "Available").reduce((s, u) => s + (parseInt(u.qty || u.Quantity, 10) || 1), 0);
    const pendingDemand = reqFiltered.filter(r => (r.bloodGroup || r.BloodGroup) === bg && ["Pending", "Approved"].includes(r.status || r.Status)).reduce((s, r) => s + (parseInt(r.qty || r.Quantity, 10) || 1), 0);
    return { bloodGroup: bg, available, pendingDemand, gap: available - pendingDemand, shortage: available - pendingDemand < 0 };
  });

  return {
    overview: {
      summary: {
        totalDonors: donorsFiltered.length,
        totalPatients: patients.length,
        totalRequests: reqFiltered.length,
        pendingRequests: reqFiltered.filter(r => ["Pending", "Approved"].includes(r.status || r.Status)).length,
        fulfillmentRate: reqFiltered.length ? Math.round((reqFulfilled / reqFiltered.length) * 1000) / 10 : 0,
        availableUnits: availUnits,
        expiredUnits: invFiltered.filter(u => (u.status || u.Status) === "Expired").reduce((s, u) => s + (parseInt(u.qty || u.Quantity, 10) || 1), 0),
        expiringSoonUnits: 0,
        totalVerifications: verifications.length,
        verificationPassRate: verifications.length ? Math.round((verPassed / verifications.length) * 1000) / 10 : 0,
        totalDisposals: disposals.length,
        wastageRate: 0,
      },
      supplyVsDemand,
      criticalShortages: supplyVsDemand.filter(x => x.shortage),
      timeline: [],
    },
    inventory: {
      summary: { availableUnits: availUnits, reservedUnits: 0, expiringSoonUnits: 0, expiredUnits: 0 },
      componentMatrix: BLOOD_GROUPS.map(bg => ({ bloodGroup: bg, bloodUnits: 0, plasmaUnits: 0, totalAvailable: 0, reservedUnits: 0, expiredUnits: 0 })),
      statusBreakdown: [],
      expiryBuckets: [],
      ledger: invFiltered.map(u => ({
        unitId: u.unitId || u.UnitID,
        batchNo: u.batchNo || u.BatchNo || "-",
        bloodGroup: u.bloodGroup || u.BloodGroup,
        type: u.type || u.Type,
        quantity: u.qty || u.Quantity || 1,
        expiryDate: u.expiry || u.ExpiryDate || "-",
        expiryBucket: "-",
        status: u.status || u.Status,
      })),
    },
    requests: {
      summary: {
        totalRequests: reqFiltered.length,
        pendingRequests: reqFiltered.filter(r => (r.status || r.Status) === "Pending").length,
        approvedRequests: reqFiltered.filter(r => (r.status || r.Status) === "Approved").length,
        fulfilledRequests: reqFulfilled,
        criticalRequests: reqFiltered.filter(r => (r.urgency || r.Urgency) === "Critical").length,
        totalUnitsRequested: reqFiltered.reduce((s, r) => s + (parseInt(r.qty || r.Quantity, 10) || 1), 0),
        fulfillmentRate: reqFiltered.length ? Math.round((reqFulfilled / reqFiltered.length) * 1000) / 10 : 0,
      },
      statusBreakdown: [],
      urgencyBreakdown: [],
      hospitalBreakdown: [],
      ledger: reqFiltered.map(r => ({
        requestId: r.requestId || r.RequestID,
        patientName: r.patientId || r.PatientID || "-",
        hospitalId: r.hospitalId || r.HospitalID || "-",
        requestDate: r.requestDate || r.RequestDate || "-",
        bloodGroup: r.bloodGroup || r.BloodGroup,
        type: r.type || r.Type,
        quantity: r.qty || r.Quantity || 1,
        urgency: r.urgency || r.Urgency || "Normal",
        status: r.status || r.Status || "Pending",
        availableStock: 0,
        stockSufficient: false,
      })),
    },
    donations: {
      summary: {
        totalDonors: donorsFiltered.length,
        eligibleDonors: donorsFiltered.filter(d => (d.status || d.Status) === "Eligible").length,
        eligibilityRate: 0,
        totalDonations: donFiltered.length,
        totalUnitsCollected: donFiltered.reduce((s, d) => s + (parseInt(d.qty || d.Quantity, 10) || 1), 0),
        bloodUnits: 0,
        plasmaUnits: 0,
      },
      donorByBloodGroup: [],
      topDonors: [],
      ledger: donFiltered.map(d => ({
        donationId: d.donationId || d.DonationID,
        donorName: d.donorId || d.DonorID,
        date: d.date || d.Date,
        bloodGroup: d.bloodGroup || d.BloodGroup,
        type: d.type || d.Type,
        quantity: d.qty || d.Quantity || 1,
        bloodBankId: d.bloodBankId || d.BloodBankID || 1,
        status: d.status || d.Status || "Completed",
      })),
    },
    verification: {
      summary: { totalVerified: verifications.length, passedCount: verPassed, failedCount: verifications.length - verPassed, passRate: 0 },
      markerBreakdown: [],
      verifierBreakdown: [],
      ledger: verifications.map(v => ({
        verificationId: v.verificationId || v.VerificationID,
        unitId: v.unitId || v.UnitID,
        donorId: v.donorId || v.DonorID || "-",
        date: v.date || v.Date,
        verifiedBy: v.verifiedBy || v.VerifiedBy,
        hiv: v.hiv || v.HIV || "-",
        hepatitisB: v.hbv || v.HepatitisB || "-",
        hepatitisC: v.hcv || v.HepatitisC || "-",
        syphilis: v.syphilis || v.Syphilis || "-",
        overallResult: v.result || v.OverallResult,
        notes: v.notes || v.Notes || "",
      })),
    },
    disposal: {
      summary: { totalDisposals: disposals.length, totalUnitsDisposed: disposals.length, expiredReasonCount: 0, failedVerificationCount: 0, contaminatedCount: 0, damagedCount: 0 },
      reasonBreakdown: [],
      bloodGroupWastage: [],
      ledger: disposals.map(dp => ({
        disposalId: dp.disposalId || dp.DisposalID,
        unitId: dp.unitId || dp.UnitID,
        bloodGroup: "-",
        type: "-",
        quantity: 1,
        disposalDate: dp.date || dp.DisposalDate,
        reason: dp.reason || dp.Reason,
        disposedBy: dp.disposedBy || dp.DisposedBy || "-",
        notes: dp.notes || dp.Notes || "",
      })),
    },
  };
}

function renderOverview(ov, query) {
  if (!ov) return;
  const s = ov.summary || {};
  setText("ovFulfillmentRate", `${s.fulfillmentRate ?? 0}%`);
  setText("ovRequestsMeta", `${(s.totalRequests ?? 0) - (s.pendingRequests ?? 0)} closed of ${s.totalRequests ?? 0} requests`);
  setText("ovAvailableUnits", s.availableUnits ?? 0);
  setText("ovExpiryMeta", `${s.expiringSoonUnits ?? 0} expiring in 7 days`);
  setText("ovPassRate", `${s.verificationPassRate ?? 0}%`);
  setText("ovVerifMeta", `${s.totalVerifications ?? 0} verifications audited`);
  setText("ovWastageRate", `${s.wastageRate ?? 0}%`);
  setText("ovDisposalMeta", `${s.totalDisposals ?? 0} disposal records`);

  const alertBox = document.getElementById("shortageAlertBanner");
  if (alertBox) {
    const shortages = ov.criticalShortages || [];
    if (shortages.length > 0) {
      const summary = shortages.map(x => `${x.bloodGroup} (Avail ${x.available} / Demand ${x.pendingDemand})`).join(" • ");
      alertBox.innerHTML = `<div class="shortage-alert"><span>Stock Shortage Alert: ${esc(summary)}</span><span>Action Needed</span></div>`;
    } else {
      alertBox.innerHTML = "";
    }
  }

  renderBarList(
    "ovSupplyChart",
    (ov.supplyVsDemand || []).map(item => ({
      label: item.bloodGroup,
      value: item.available,
      tone: item.shortage ? "danger" : (item.pendingDemand > 0 ? "warn" : "success"),
      meta: `${item.available} avail / ${item.pendingDemand} demand`,
    }))
  );

  const snapBody = document.getElementById("ovSnapshotTable");
  if (snapBody) {
    const rows = [
      ["Registered Donors", s.totalDonors ?? 0],
      ["Enrolled Patients", s.totalPatients ?? 0],
      ["Open Requests (Pending/Approved)", s.pendingRequests ?? 0],
      ["Expired Units in Cold Storage", s.expiredUnits ?? 0],
      ["QC Verifications Logged", s.totalVerifications ?? 0],
      ["Bio-Waste Disposals Logged", s.totalDisposals ?? 0],
    ];
    snapBody.innerHTML = rows.map(([k, v]) => `<tr><td><strong>${esc(k)}</strong></td><td>${esc(v)}</td></tr>`).join("");
  }

  const timelineRows = (ov.timeline || []).filter(r => matchesSearch(r, query));
  const tlBody = document.getElementById("ovTimelineTable");
  if (!tlBody) return;
  if (timelineRows.length === 0) {
    emptyRow("ovTimelineTable", 5, "No audit activity in the selected period.");
    return;
  }
  tlBody.innerHTML = timelineRows.map(r => `
    <tr>
      <td><span class="badge">${esc(r.module)}</span></td>
      <td><strong>${esc(r.id)}</strong></td>
      <td>${esc(r.date)}</td>
      <td>${esc(r.bloodGroup)}</td>
      <td>${esc(r.summary)}</td>
    </tr>
  `).join("");
}

function renderInventoryReport(inv, query) {
  if (!inv) return;
  const s = inv.summary || {};
  setText("invAvail", s.availableUnits ?? 0);
  setText("invReserved", s.reservedUnits ?? 0);
  setText("invExpiring7", s.expiringSoonUnits ?? 0);
  setText("invExpired", s.expiredUnits ?? 0);

  const matBody = document.getElementById("invMatrixTable");
  if (matBody) {
    const matrix = inv.componentMatrix || [];
    if (matrix.length === 0) {
      emptyRow("invMatrixTable", 6);
    } else {
      matBody.innerHTML = matrix.map(row => `
        <tr>
          <td><strong>${esc(row.bloodGroup)}</strong></td>
          <td>${esc(row.bloodUnits)}</td>
          <td>${esc(row.plasmaUnits)}</td>
          <td><strong>${esc(row.totalAvailable)}</strong></td>
          <td>${esc(row.reservedUnits)}</td>
          <td>${esc(row.expiredUnits)}</td>
        </tr>
      `).join("");
    }
  }

  renderBarList(
    "invExpiryChart",
    (inv.expiryBuckets || []).map(b => ({
      label: b.bucket,
      value: b.units,
      tone: b.bucket.startsWith("Expired") || b.bucket.startsWith("Critical") ? "danger" : (b.bucket.startsWith("Warning") ? "warn" : "success"),
      meta: `${b.units} units`,
    })),
    true
  );

  const stBody = document.getElementById("invStatusTable");
  if (stBody) {
    const statuses = inv.statusBreakdown || [];
    stBody.innerHTML = statuses.length
      ? statuses.map(r => `<tr><td>${statusPill(r.status)}</td><td>${esc(r.records)}</td><td>${esc(r.units)}</td></tr>`).join("")
      : `<tr><td colspan="3" class="muted">No status breakdown</td></tr>`;
  }

  const ledger = (inv.ledger || []).filter(r => matchesSearch(r, query));
  setText("invLedgerCount", `${ledger.length} units`);
  const body = document.getElementById("invLedgerTable");
  if (!body) return;
  if (ledger.length === 0) {
    emptyRow("invLedgerTable", 8);
    return;
  }
  body.innerHTML = ledger.map(u => `
    <tr>
      <td><strong>${esc(u.unitId)}</strong></td>
      <td>${esc(u.batchNo)}</td>
      <td><span class="badge">${esc(u.bloodGroup)}</span></td>
      <td>${esc(u.type)}</td>
      <td>${esc(u.quantity)}</td>
      <td>${esc(u.expiryDate)}</td>
      <td>${statusPill(u.expiryBucket)}</td>
      <td>${statusPill(u.status)}</td>
    </tr>
  `).join("");
}

function renderRequestsReport(req, query) {
  if (!req) return;
  const s = req.summary || {};
  setText("reqTotal", s.totalRequests ?? 0);
  setText("reqUnitsMeta", `${s.totalUnitsRequested ?? 0} units requested`);
  setText("reqOpen", (s.pendingRequests ?? 0) + (s.approvedRequests ?? 0));
  setText("reqFulfilled", s.fulfilledRequests ?? 0);
  setText("reqRateMeta", `${s.fulfillmentRate ?? 0}% fulfillment rate`);
  setText("reqCritical", s.criticalRequests ?? 0);

  renderBarList(
    "reqStatusChart",
    (req.statusBreakdown || []).map(item => ({
      label: item.status,
      value: item.count,
      tone: item.status === "Fulfilled" ? "success" : (item.status === "Rejected" ? "danger" : "warn"),
      meta: `${item.count} (${item.units}u)`,
    })),
    true
  );

  const urgBody = document.getElementById("reqUrgencyTable");
  if (urgBody) {
    const rows = req.urgencyBreakdown || [];
    urgBody.innerHTML = rows.length
      ? rows.map(u => `<tr><td>${statusPill(u.urgency)}</td><td>${esc(u.count)}</td><td>${esc(u.openCount)}</td><td>${esc(u.units)}</td></tr>`).join("")
      : `<tr><td colspan="4" class="muted">No urgency data</td></tr>`;
  }

  const hospBody = document.getElementById("reqHospitalTable");
  if (hospBody) {
    const rows = req.hospitalBreakdown || [];
    if (rows.length === 0) {
      emptyRow("reqHospitalTable", 5);
    } else {
      hospBody.innerHTML = rows.map(h => `
        <tr>
          <td><strong>Hospital #${esc(h.hospitalId)}</strong></td>
          <td>${esc(h.totalRequests)}</td>
          <td>${esc(h.fulfilled)}</td>
          <td>${esc(h.open)}</td>
          <td>${esc(h.totalUnits)}</td>
        </tr>
      `).join("");
    }
  }

  const ledger = (req.ledger || []).filter(r => matchesSearch(r, query));
  setText("reqLedgerCount", `${ledger.length} requests`);
  const body = document.getElementById("reqLedgerTable");
  if (!body) return;
  if (ledger.length === 0) {
    emptyRow("reqLedgerTable", 9);
    return;
  }
  body.innerHTML = ledger.map(r => `
    <tr>
      <td><strong>${esc(r.requestId)}</strong></td>
      <td>${esc(r.patientName)}</td>
      <td>#${esc(r.hospitalId)}</td>
      <td>${esc(r.requestDate)}</td>
      <td><span class="badge">${esc(r.bloodGroup)}</span> ${esc(r.type)}</td>
      <td>${esc(r.quantity)}</td>
      <td>${statusPill(r.urgency)}</td>
      <td>${statusPill(r.status)}</td>
      <td>${r.status === "Fulfilled" ? statusPill("Fulfilled") : statusPill(r.stockSufficient ? "Sufficient" : "Shortage")}</td>
    </tr>
  `).join("");
}

function renderDonationsReport(don, query) {
  if (!don) return;
  const s = don.summary || {};
  setText("donTotalDonors", s.totalDonors ?? 0);
  setText("donEligMeta", `${s.eligibleDonors ?? 0} eligible (${s.eligibilityRate ?? 0}%)`);
  setText("donTotalDonations", s.totalDonations ?? 0);
  setText("donUnitsMeta", `${s.totalUnitsCollected ?? 0} units collected`);
  setText("donBloodUnits", s.bloodUnits ?? 0);
  setText("donPlasmaUnits", s.plasmaUnits ?? 0);

  const bgBody = document.getElementById("donBgTable");
  if (bgBody) {
    const rows = don.donorByBloodGroup || [];
    if (rows.length === 0) {
      emptyRow("donBgTable", 4);
    } else {
      bgBody.innerHTML = rows.map(r => `
        <tr>
          <td><strong>${esc(r.bloodGroup)}</strong></td>
          <td>${esc(r.eligible)}</td>
          <td>${esc(r.notEligible)}</td>
          <td><strong>${esc(r.total)}</strong></td>
        </tr>
      `).join("");
    }
  }

  const topBody = document.getElementById("donTopTable");
  if (topBody) {
    const rows = don.topDonors || [];
    if (rows.length === 0) {
      emptyRow("donTopTable", 5, "No donation sessions recorded in range.");
    } else {
      topBody.innerHTML = rows.map(d => `
        <tr>
          <td><strong>${esc(d.name)}</strong> <span class="muted">(${esc(d.donorId)})</span></td>
          <td><span class="badge">${esc(d.bloodGroup)}</span></td>
          <td>${esc(d.donations)}</td>
          <td>${esc(d.units)}</td>
          <td>${esc(d.lastDate)}</td>
        </tr>
      `).join("");
    }
  }

  const ledger = (don.ledger || []).filter(r => matchesSearch(r, query));
  setText("donLedgerCount", `${ledger.length} donations`);
  const body = document.getElementById("donLedgerTable");
  if (!body) return;
  if (ledger.length === 0) {
    emptyRow("donLedgerTable", 8);
    return;
  }
  body.innerHTML = ledger.map(d => `
    <tr>
      <td><strong>${esc(d.donationId)}</strong></td>
      <td>${esc(d.donorName)}</td>
      <td>${esc(d.date)}</td>
      <td><span class="badge">${esc(d.bloodGroup)}</span></td>
      <td>${esc(d.type)}</td>
      <td>${esc(d.quantity)}</td>
      <td>#${esc(d.bloodBankId)}</td>
      <td>${statusPill(d.status)}</td>
    </tr>
  `).join("");
}

function renderVerificationReport(ver, query) {
  if (!ver) return;
  const s = ver.summary || {};
  setText("verTotal", s.totalVerified ?? 0);
  setText("verPassed", s.passedCount ?? 0);
  setText("verFailed", s.failedCount ?? 0);
  setText("verPassRate", `${s.passRate ?? 0}%`);

  const mkBody = document.getElementById("verMarkerTable");
  if (mkBody) {
    const rows = ver.markerBreakdown || [];
    mkBody.innerHTML = rows.length
      ? rows.map(m => `<tr><td><strong>${esc(m.marker)}</strong></td><td>${esc(m.passed)}</td><td>${esc(m.failed)}</td></tr>`).join("")
      : `<tr><td colspan="3" class="muted">No marker data</td></tr>`;
  }

  const offBody = document.getElementById("verOfficerTable");
  if (offBody) {
    const rows = ver.verifierBreakdown || [];
    if (rows.length === 0) {
      emptyRow("verOfficerTable", 4);
    } else {
      offBody.innerHTML = rows.map(o => `
        <tr>
          <td><strong>${esc(o.verifiedBy)}</strong></td>
          <td>${esc(o.total)}</td>
          <td>${esc(o.passed)}</td>
          <td>${esc(o.failed)}</td>
        </tr>
      `).join("");
    }
  }

  const ledger = (ver.ledger || []).filter(r => matchesSearch(r, query));
  setText("verLedgerCount", `${ledger.length} records`);
  const body = document.getElementById("verLedgerTable");
  if (!body) return;
  if (ledger.length === 0) {
    emptyRow("verLedgerTable", 8);
    return;
  }
  body.innerHTML = ledger.map(v => `
    <tr>
      <td><strong>${esc(v.verificationId)}</strong></td>
      <td>${esc(v.unitId)}</td>
      <td>${esc(v.donorId)}</td>
      <td>${esc(v.date)}</td>
      <td>${esc(v.verifiedBy)}</td>
      <td>${esc(`${v.hiv} / ${v.hepatitisB} / ${v.hepatitisC} / ${v.syphilis}`)}</td>
      <td>${statusPill(v.overallResult)}</td>
      <td>${esc(v.notes || "-")}</td>
    </tr>
  `).join("");
}

function renderDisposalReport(disp, query) {
  if (!disp) return;
  const s = disp.summary || {};
  setText("dispTotal", s.totalDisposals ?? 0);
  setText("dispUnitsMeta", `${s.totalUnitsDisposed ?? 0} units disposed`);
  setText("dispExpired", s.expiredReasonCount ?? 0);
  setText("dispFailedVer", s.failedVerificationCount ?? 0);
  setText("dispOther", (s.contaminatedCount ?? 0) + (s.damagedCount ?? 0));

  renderBarList(
    "dispReasonChart",
    (disp.reasonBreakdown || []).map(r => ({
      label: r.reason,
      value: r.count,
      tone: r.reason === "Expired" ? "warn" : "danger",
      meta: `${r.count} (${r.sharePercent}%)`,
    })),
    true
  );

  const bgBody = document.getElementById("dispBgTable");
  if (bgBody) {
    const rows = disp.bloodGroupWastage || [];
    if (rows.length === 0) {
      emptyRow("dispBgTable", 3);
    } else {
      bgBody.innerHTML = rows.map(r => `
        <tr>
          <td><strong>${esc(r.bloodGroup)}</strong></td>
          <td>${esc(r.records)}</td>
          <td>${esc(r.units)}</td>
        </tr>
      `).join("");
    }
  }

  const ledger = (disp.ledger || []).filter(r => matchesSearch(r, query));
  setText("dispLedgerCount", `${ledger.length} records`);
  const body = document.getElementById("dispLedgerTable");
  if (!body) return;
  if (ledger.length === 0) {
    emptyRow("dispLedgerTable", 8);
    return;
  }
  body.innerHTML = ledger.map(dp => `
    <tr>
      <td><strong>${esc(dp.disposalId)}</strong></td>
      <td>${esc(dp.unitId)}</td>
      <td><span class="badge">${esc(dp.bloodGroup)}</span> ${esc(dp.type)}</td>
      <td>${esc(dp.quantity)}</td>
      <td>${esc(dp.disposalDate)}</td>
      <td>${statusPill(dp.reason)}</td>
      <td>${esc(dp.disposedBy)}</td>
      <td>${esc(dp.notes || "-")}</td>
    </tr>
  `).join("");
}

function renderAllPanels() {
  const b = state.bundle;
  if (!b) return;
  const query = searchEl ? searchEl.value.trim() : "";

  renderOverview(b.overview, query);
  renderInventoryReport(b.inventory, query);
  renderRequestsReport(b.requests, query);
  renderDonationsReport(b.donations, query);
  renderVerificationReport(b.verification, query);
  renderDisposalReport(b.disposal, query);
}

function getCsvDatasetForTab(tab) {
  const b = state.bundle || {};
  const q = searchEl ? searchEl.value.trim() : "";

  if (tab === "inventory") {
    const rows = (b.inventory?.ledger || []).filter(r => matchesSearch(r, q));
    return {
      headers: ["Unit ID", "Batch No", "Blood Group", "Type", "Quantity", "Expiry Date", "Days Remaining", "Shelf-Life Bucket", "Status"],
      rows: rows.map(r => [r.unitId, r.batchNo, r.bloodGroup, r.type, r.quantity, r.expiryDate, r.daysRemaining ?? "", r.expiryBucket, r.status]),
    };
  }
  if (tab === "requests") {
    const rows = (b.requests?.ledger || []).filter(r => matchesSearch(r, q));
    return {
      headers: ["Request ID", "Patient", "Hospital ID", "Date", "Blood Group", "Type", "Quantity", "Urgency", "Status", "Available Stock"],
      rows: rows.map(r => [r.requestId, r.patientName, r.hospitalId, r.requestDate, r.bloodGroup, r.type, r.quantity, r.urgency, r.status, r.availableStock]),
    };
  }
  if (tab === "donations") {
    const rows = (b.donations?.ledger || []).filter(r => matchesSearch(r, q));
    return {
      headers: ["Donation ID", "Donor", "Date", "Blood Group", "Type", "Quantity", "Blood Bank ID", "Status"],
      rows: rows.map(r => [r.donationId, r.donorName, r.date, r.bloodGroup, r.type, r.quantity, r.bloodBankId, r.status]),
    };
  }
  if (tab === "verification") {
    const rows = (b.verification?.ledger || []).filter(r => matchesSearch(r, q));
    return {
      headers: ["Verification ID", "Unit ID", "Donor ID", "Date", "Verified By", "HIV", "Hepatitis B", "Hepatitis C", "Syphilis", "Overall Result", "Notes"],
      rows: rows.map(r => [r.verificationId, r.unitId, r.donorId, r.date, r.verifiedBy, r.hiv, r.hepatitisB, r.hepatitisC, r.syphilis, r.overallResult, r.notes]),
    };
  }
  if (tab === "disposal") {
    const rows = (b.disposal?.ledger || []).filter(r => matchesSearch(r, q));
    return {
      headers: ["Disposal ID", "Unit ID", "Blood Group", "Type", "Quantity", "Disposal Date", "Reason", "Disposed By", "Notes"],
      rows: rows.map(r => [r.disposalId, r.unitId, r.bloodGroup, r.type, r.quantity, r.disposalDate, r.reason, r.disposedBy, r.notes]),
    };
  }
  const rows = (b.overview?.timeline || []).filter(r => matchesSearch(r, q));
  return {
    headers: ["Module", "Record ID", "Date", "Blood Group", "Summary"],
    rows: rows.map(r => [r.module, r.id, r.date, r.bloodGroup, r.summary]),
  };
}

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function loadReports() {
  const filters = getFilters();
  syncPdfLinks();
  try {
    if (window.reportAPI && typeof window.reportAPI.get === "function") {
      const res = await window.reportAPI.get({ type: "all", ...filters });
      if (res && res.reports) {
        state.bundle = res.reports;
        renderAllPanels();
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load backend /api/reports/, using offline fallback:", err);
  }

  state.bundle = buildOfflineBundle(filters);
  renderAllPanels();
}

// Event bindings
document.getElementById("reportTabs")?.addEventListener("click", (e) => {
  const btn = e.target.closest(".report-tab");
  if (!btn) return;
  setActiveTab(btn.dataset.tab);
});

[rangeSel, fromDateEl, toDateEl, bloodGroupSel, typeSel].forEach(el => {
  el?.addEventListener("change", () => {
    syncCustomDateVisibility();
    loadReports();
  });
});

searchEl?.addEventListener("input", renderAllPanels);

resetBtn?.addEventListener("click", () => {
  if (rangeSel) rangeSel.value = "all";
  if (fromDateEl) fromDateEl.value = "";
  if (toDateEl) toDateEl.value = "";
  if (bloodGroupSel) bloodGroupSel.value = "all";
  if (typeSel) typeSel.value = "all";
  if (searchEl) searchEl.value = "";
  syncCustomDateVisibility();
  loadReports();
});

exportCsvBtn?.addEventListener("click", () => {
  const { headers, rows } = getCsvDatasetForTab(state.activeTab);
  const escapeCsv = val => `"${String(val ?? "").replace(/"/g, '""')}"`;
  const lines = [
    [`Jeevithaya Blood & Plasma Bank - ${TAB_TITLES[state.activeTab]}`].map(escapeCsv).join(","),
    [`Generated: ${new Date().toISOString()}`, `Prepared by: ${session?.email || "Staff"}`].map(escapeCsv).join(","),
    headers.map(escapeCsv).join(","),
    ...rows.map(r => r.map(escapeCsv).join(",")),
  ];
  downloadFile(`jeevithaya_${state.activeTab}_report.csv`, lines.join("\n"), "text/csv;charset=utf-8;");
});

exportBtn?.addEventListener("click", () => {
  const payload = {
    reportTitle: TAB_TITLES[state.activeTab],
    exportedAt: new Date().toISOString(),
    preparedBy: session?.email || "Staff",
    filters: getFilters(),
    reports: state.bundle,
  };
  downloadFile(`jeevithaya_reports_bundle_${state.activeTab}.json`, JSON.stringify(payload, null, 2), "application/json");
});

// Initialize tab from URL if provided
try {
  const initialTab = new URLSearchParams(window.location.search).get("tab");
  if (initialTab && VALID_TABS.includes(initialTab)) {
    setActiveTab(initialTab, false);
  }
} catch {}

syncCustomDateVisibility();
syncPdfLinks();
loadReports();
