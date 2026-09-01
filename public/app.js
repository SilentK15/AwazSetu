/**
 * Civic Grievance Redressal Portal — Frontend Client Application
 * Zero Fake Data | Native Geolocation | Mapbox GL JS | Real-Time Status Resolution
 */

// State variables
let currentLanguage = 'en';
let activeView = 'citizen';
let activeLocMode = 'gps';
let selectedLat = 19.0760;
let selectedLon = 72.8777;
let grievancesData = [];
let mapboxMap = null;
let currentMarkers = [];

// Multilingual Dictionary
const UI_TRANSLATIONS = {
  en: {
    portal_title: "Civic Grievance Redressal Portal",
    portal_subtitle: "Report civic issues. Track resolution. Improve your neighbourhood.",
    eyebrow: "CITIZEN SERVICE PLATFORM",
    portal_status: "Portal Status",
    services_operational: "Services operational",
    nav_citizen: "Citizen Portal",
    nav_track: "Track Complaint",
    nav_dashboard: "Authority Dashboard",
    nav_how: "How It Works",
    hero_kicker: "CITIZEN GRIEVANCE SERVICE",
    hero_title: "Report a civic issue in a few simple steps.",
    hero_desc: "Submit a complaint with location and description. Intelligent AI routing directs the issue to the appropriate service team and merges duplicate reports.",
    point_1: "Multilingual complaint submission",
    point_2: "Similar complaint detection (400m)",
    point_3: "Transparent priority explanation (XAI)",
    step_1: "Issue",
    step_1_sub: "Describe problem",
    step_2: "Location",
    step_2_sub: "Pin affected area",
    step_3: "Analysis",
    step_3_sub: "AI verification",
    step_4: "Submit",
    step_4_sub: "Receive ticket ID",
    form_heading: "Describe the civic issue",
    lbl_desc: "What is the problem? *",
    lbl_cat: "Issue category",
    lbl_ward: "Administrative area / Ward *",
    btn_submit: "Submit Grievance →",
    loc_btn_gps: "📍 Use My Location (GPS)",
    loc_btn_preset: "🏢 Area / Landmark",
    loc_btn_map: "🗺️ Click on Map",
    loc_btn_manual: "🔢 Coordinates",
    detect_btn: "📍 Detect Location",
    kpi_total: "Total complaints",
    kpi_pending: "Pending review",
    kpi_high: "High / Critical",
    kpi_resolved: "Resolved",
    queue_title: "Needs attention",
    empty_records: "No complaints have been submitted yet.",
    empty_queue: "No unresolved complaints in queue.",
    dup_title: "Similar issues reported nearby",
    btn_resolve: "Mark as Resolved",
    btn_progress: "Mark In Progress",
    btn_pending: "Mark Pending",
  },
  hi: {
    portal_title: "नागरिक शिकायत निवारण पोर्टल",
    portal_subtitle: "नागरिक समस्याओं की रिपोर्ट करें। समाधान ट्रैक करें। अपने क्षेत्र को बेहतर बनाएं।",
    eyebrow: "नागरिक सेवा मंच",
    portal_status: "पोर्टल स्थिति",
    services_operational: "सेवाएं सक्रिय हैं",
    nav_citizen: "नागरिक पोर्टल",
    nav_track: "शिकायत ट्रैक करें",
    nav_dashboard: "अधिकारी डैशबोर्ड",
    nav_how: "यह कैसे काम करता है",
    hero_kicker: "नागरिक शिकायत सेवा",
    hero_title: "कुछ आसान चरणों में नागरिक समस्या की रिपोर्ट करें।",
    hero_desc: "स्थान और विवरण के साथ शिकायत दर्ज करें। AI सही विभाग को शिकायत भेजता है और 400 मीटर के भीतर डुप्लीकेट शिकायतों को रोकता है।",
    point_1: "बहुभाषी शिकायत दर्ज (हिंदी, मराठी, अंग्रेजी)",
    point_2: "समान शिकायत पहचान (400 मीटर)",
    point_3: "पारदर्शी प्राथमिकता स्पष्टीकरण (XAI)",
    step_1: "समस्या",
    step_1_sub: "विवरण लिखें",
    step_2: "स्थान",
    step_2_sub: "प्रभावित क्षेत्र",
    step_3: "विश्लेषण",
    step_3_sub: "AI सत्यापन",
    step_4: "जमा करें",
    step_4_sub: "टिकट ID प्राप्त करें",
    form_heading: "नागरिक समस्या का विवरण दें",
    lbl_desc: "समस्या क्या है? *",
    lbl_cat: "समस्या श्रेणी",
    lbl_ward: "प्रशासनिक क्षेत्र / वार्ड *",
    btn_submit: "शिकायत दर्ज करें →",
    loc_btn_gps: "📍 मेरा वर्तमान स्थान (GPS)",
    loc_btn_preset: "🏢 प्रसिद्ध स्थल",
    loc_btn_map: "🗺️ नक्शे पर चुनें",
    loc_btn_manual: "🔢 निर्देशांक",
    detect_btn: "📍 स्थान खोजें",
    kpi_total: "कुल शिकायतें",
    kpi_pending: "समीक्षा लंबित",
    kpi_high: "उच्च / गंभीर",
    kpi_resolved: "समाधानित",
    queue_title: "ध्यान देने योग्य",
    empty_records: "अभी तक कोई शिकायत दर्ज नहीं की गई है।",
    empty_queue: "कतार में कोई अनसुलझी शिकायत नहीं है।",
    dup_title: "निकट में पहले से दर्ज समान शिकायतें मिलीं",
    btn_resolve: "समाधानित चिह्नित करें",
    btn_progress: "प्रगति में चिह्नित करें",
    btn_pending: "लंबित चिह्नित करें",
  },
  mr: {
    portal_title: "नागरिक तक्रार निवारण पोर्टल",
    portal_subtitle: "नागरी समस्यांची नोंद करा. निवारणाचा मागोवा घ्या. आपला परिसर सुधारा.",
    eyebrow: "नागरिक सेवा मंच",
    portal_status: "पोर्टल स्थिती",
    services_operational: "सेवा कार्यरत आहेत",
    nav_citizen: "नागरिक पोर्टल",
    nav_track: "तक्रार ट्रॅक करा",
    nav_dashboard: "अधिकारी डॅशबोर्ड",
    nav_how: "कार्यप्रणाली",
    hero_kicker: "नागरिक तक्रार सेवा",
    hero_title: "काही सोप्या चरणांमध्ये नागरी समस्येची नोंद करा.",
    hero_desc: "स्थान आणि वर्णनासह तक्रार नोंदवा. AI संबंधित विभागाकडे तक्रार पाठवते आणि 400 मीटरच्या परिसरातील तक्रारींचे विलीनीकरण करते.",
    point_1: "मराठी, हिंदी आणि इंग्रजीत तक्रार नोंदणी",
    point_2: "समान तक्रार ओळख (400 मीटर)",
    point_3: "पारदर्शक प्राधान्य स्पष्टीकरण (XAI)",
    step_1: "समस्या",
    step_1_sub: "तपशील लिहा",
    step_2: "स्थान",
    step_2_sub: "प्रभावित क्षेत्र",
    step_3: "विश्लेषण",
    step_3_sub: "AI पडताळणी",
    step_4: "सादर करा",
    step_4_sub: "तिकीट ID मिळवा",
    form_heading: "नागरी समस्येचे वर्णन करा",
    lbl_desc: "नेमकी समस्या काय आहे? *",
    lbl_cat: "समस्या प्रवर्ग",
    lbl_ward: "प्रशासकीय प्रभाग *",
    btn_submit: "तक्रार सादर करा →",
    loc_btn_gps: "📍 माझे चालू स्थान (GPS)",
    loc_btn_preset: "🏢 प्रसिद्ध ठिकाण",
    loc_btn_map: "🗺️ नकाशावर निवडा",
    loc_btn_manual: "🔢 निर्देशक",
    detect_btn: "📍 स्थान मिळवा",
    kpi_total: "एकूण तक्रारी",
    kpi_pending: "प्रलंबित",
    kpi_high: "उच्च / गंभीर",
    kpi_resolved: "निवारण झालेले",
    queue_title: "तातडीने लक्ष द्या",
    empty_records: "अद्याप कोणतीही तक्रार नोंदवलेली नाही.",
    empty_queue: "रांगेत कोणतीही प्रलंबित तक्रार नाही.",
    dup_title: "जवळपास आधीच नोंदवलेली समान समस्या आढळली",
    btn_resolve: "निवारण झाले म्हणून चिन्हांकित करा",
    btn_progress: "प्रगतीपथावर चिन्हांकित करा",
    btn_pending: "प्रलंबित चिन्हांकित करा",
  }
};

const LANDMARK_COORDS = {
  "Dadar TT Circle": [19.0178, 72.8478],
  "Andheri Station (W)": [19.1197, 72.8464],
  "Bandra Bandstand": [19.0450, 72.8200],
  "Kurla LBS Road": [19.0726, 72.8793],
  "Borivali Station (W)": [19.2307, 72.8567],
  "Colaba Causeway": [18.9067, 72.8147]
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  const savedLang = localStorage.getItem('civic_lang') || 'en';
  setLanguage(savedLang);

  const descField = document.getElementById('description');
  if (descField) {
    descField.addEventListener('input', (e) => {
      document.getElementById('char-count').innerText = `${e.target.value.length} / 1000`;
    });
  }

  loadAllGrievances();
});

// Switch Language
function setLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem('civic_lang', lang);
  const t = UI_TRANSLATIONS[lang] || UI_TRANSLATIONS.en;

  document.getElementById('btn-lang-en').classList.toggle('lang-active', lang === 'en');
  document.getElementById('btn-lang-hi').classList.toggle('lang-active', lang === 'hi');
  document.getElementById('btn-lang-mr').classList.toggle('lang-active', lang === 'mr');

  document.getElementById('txt-portal-title').innerText = t.portal_title;
  document.getElementById('txt-portal-subtitle').innerText = t.portal_subtitle;
  document.getElementById('txt-eyebrow').innerText = t.eyebrow;
  document.getElementById('txt-portal-status').innerText = t.portal_status;
  document.getElementById('txt-services-op').innerText = t.services_operational;

  document.getElementById('nav-citizen').innerText = t.nav_citizen;
  document.getElementById('nav-track').innerText = t.nav_track;
  document.getElementById('nav-dashboard').innerText = t.nav_dashboard;
  document.getElementById('nav-how').innerText = t.nav_how;

  document.getElementById('txt-hero-kicker').innerText = t.hero_kicker;
  document.getElementById('txt-hero-title').innerText = t.hero_title;
  document.getElementById('txt-hero-desc').innerText = t.hero_desc;
  document.getElementById('txt-point-1').innerText = t.point_1;
  document.getElementById('txt-point-2').innerText = t.point_2;
  document.getElementById('txt-point-3').innerText = t.point_3;

  document.getElementById('txt-st-1').innerText = t.step_1;
  document.getElementById('txt-st-1-s').innerText = t.step_1_sub;
  document.getElementById('txt-st-2').innerText = t.step_2;
  document.getElementById('txt-st-2-s').innerText = t.step_2_sub;
  document.getElementById('txt-st-3').innerText = t.step_3;
  document.getElementById('txt-st-3-s').innerText = t.step_3_sub;
  document.getElementById('txt-st-4').innerText = t.step_4;
  document.getElementById('txt-st-4-s').innerText = t.step_4_sub;

  document.getElementById('txt-form-heading').innerText = t.form_heading;
  document.getElementById('lbl-desc').innerHTML = `${t.lbl_desc} <span>*</span>`;
  document.getElementById('lbl-cat').innerText = t.lbl_cat;
  document.getElementById('lbl-ward').innerHTML = `${t.lbl_ward} <span>*</span>`;
  document.getElementById('txt-submit-btn').innerText = t.btn_submit;

  document.getElementById('btn-loc-gps').innerText = t.loc_btn_gps;
  document.getElementById('btn-loc-preset').innerText = t.loc_btn_preset;
  document.getElementById('btn-loc-map').innerText = t.loc_btn_map;
  document.getElementById('btn-loc-manual').innerText = t.loc_btn_manual;
  document.getElementById('btn-trigger-gps').innerText = t.detect_btn;

  document.getElementById('kpi-lbl-total').innerText = t.kpi_total;
  document.getElementById('kpi-lbl-pending').innerText = t.kpi_pending;
  document.getElementById('kpi-lbl-high').innerText = t.kpi_high;
  document.getElementById('kpi-lbl-resolved').innerText = t.kpi_resolved;
  document.getElementById('txt-queue-title').innerText = t.queue_title;
}

// Adjust font size for accessibility
function adjustFontSize(delta) {
  const current = parseFloat(window.getComputedStyle(document.body).fontSize) || 15;
  if (delta === 0) document.body.style.fontSize = '15px';
  else document.body.style.fontSize = `${Math.min(20, Math.max(12, current + delta))}px`;
}

// View switcher
function switchView(viewName) {
  activeView = viewName;
  document.getElementById('view-citizen').style.display = viewName === 'citizen' ? 'block' : 'none';
  document.getElementById('view-track').style.display = viewName === 'track' ? 'block' : 'none';
  document.getElementById('view-dashboard').style.display = viewName === 'dashboard' ? 'block' : 'none';
  document.getElementById('view-how').style.display = viewName === 'how' ? 'block' : 'none';

  document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${viewName}`);
  if (activeNav) activeNav.classList.add('active');

  if (viewName === 'dashboard') {
    setTimeout(initOrUpdateMap, 100);
  }
}

// Location Mode selector
function setLocMode(mode) {
  activeLocMode = mode;
  document.querySelectorAll('.loc-toggle-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById(`btn-loc-${mode}`).classList.add('active');

  document.getElementById('gps-action-box').style.display = mode === 'gps' ? 'flex' : 'none';
  document.getElementById('preset-select-box').style.display = mode === 'preset' ? 'block' : 'none';
  document.getElementById('manual-coords-box').style.display = mode === 'manual' ? 'grid' : 'none';

  if (mode === 'preset') onPresetChange();
}

function onPresetChange() {
  const sel = document.getElementById('preset-landmark-dropdown').value;
  const coords = LANDMARK_COORDS[sel] || [19.0178, 72.8478];
  selectedLat = coords[0];
  selectedLon = coords[1];
}

// Native HTML5 Geolocation API with robust error handling
function requestBrowserGPS() {
  const title = document.getElementById('gps-status-title');
  const display = document.getElementById('gps-coords-display');

  if (!navigator.geolocation) {
    title.innerText = "❌ Geolocation Unsupported";
    display.innerText = "Geolocation is not supported by your browser. Please choose Area / Landmark or enter coordinates.";
    return;
  }

  title.innerText = "⏳ Detecting location...";
  display.innerText = "Requesting device GPS permission from browser...";

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      selectedLat = pos.coords.latitude;
      selectedLon = pos.coords.longitude;
      title.innerText = "✅ GPS Coordinates Locked";
      display.innerText = `Latitude: ${selectedLat.toFixed(5)}, Longitude: ${selectedLon.toFixed(5)} (Accuracy: ${Math.round(pos.coords.accuracy)}m)`;
      document.getElementById('input-lat').value = selectedLat;
      document.getElementById('input-lon').value = selectedLon;
    },
    (err) => {
      let errText = "Unable to determine your location. Please select your location manually.";
      if (err.code === err.PERMISSION_DENIED) {
        errText = "Location permission was denied. Please allow location access or choose an area preset.";
      } else if (err.code === err.TIMEOUT) {
        errText = "Location request timed out. Please try again or choose an area preset.";
      }
      title.innerText = "⚠️ Location Unavailable";
      display.innerText = errText;
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
}

function onPhotoSelected(e) {
  const file = e.target.files[0];
  if (file) {
    document.getElementById('file-name-preview').innerText = `Attached: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  }
}

// Base API URL
const API_BASE = window.location.port === '8080' ? '' : 'http://localhost:8080';

// REST API — Submit Grievance
async function submitGrievance() {
  const desc = document.getElementById('description').value.trim();
  const categoryHint = document.getElementById('category').value;
  const ward = document.getElementById('ward').value;

  if (!desc) {
    alert("Please enter a description for your grievance.");
    return;
  }

  if (activeLocMode === 'manual') {
    selectedLat = parseFloat(document.getElementById('input-lat').value) || selectedLat;
    selectedLon = parseFloat(document.getElementById('input-lon').value) || selectedLon;
  }

  const payload = {
    original_text: desc,
    category_hint: categoryHint,
    ward: ward,
    lat: selectedLat,
    lon: selectedLon,
    citizen_name: "Citizen",
    citizen_phone: "9820123456"
  };

  const submitBtn = document.getElementById('btn-submit-complaint');
  submitBtn.disabled = true;
  submitBtn.innerText = "Analyzing with SentenceTransformers...";

  try {
    const res = await fetch(`${API_BASE}/api/grievance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    submitBtn.disabled = false;
    submitBtn.innerText = "Submit Grievance →";

    if (result.success) {
      document.getElementById('description').value = '';
      document.getElementById('char-count').innerText = '0 / 1000';
      document.getElementById('file-name-preview').innerText = '';

      // Live AI Preview Card
      const preview = document.getElementById('live-ai-preview');
      preview.style.display = 'block';
      preview.innerHTML = `
        <div style="font-weight:700; color:#0b3c5d; margin-bottom:4px;">Ticket Created: #${result.data.id}</div>
        <div>Department: <b>${result.data.department}</b></div>
        <div>Priority: <b style="color:${getPriorityColor(result.data.priority)}">${result.data.priority}</b> (${result.data.severity_score}/100)</div>
        <div>Status: <b>${result.data.status}</b></div>
      `;

      // Duplicate alert
      const dupBanner = document.getElementById('duplicate-result-banner');
      if (result.data.is_duplicate === 1) {
        dupBanner.style.display = 'block';
        document.getElementById('dup-banner-text').innerText =
          `We found a matching complaint (Ticket #${result.data.parent_id}) within 400m. Your report has been merged as an upvote to elevate its resolution priority!`;
      } else {
        dupBanner.style.display = 'none';
      }

      // Update stepper to step 4
      document.getElementById('step-node-1').classList.add('active');
      document.getElementById('step-node-2').classList.add('active');
      document.getElementById('step-node-3').classList.add('active');
      document.getElementById('step-node-4').classList.add('active');

      loadAllGrievances();
    } else {
      alert(`Submission error: ${result.error}`);
    }
  } catch (err) {
    submitBtn.disabled = false;
    submitBtn.innerText = "Submit Grievance →";
    alert(`Server communication error: ${err.message}`);
  }
}

// REST API — Fetch All Grievances & Render
async function loadAllGrievances() {
  try {
    const res = await fetch(`${API_BASE}/api/grievances`);
    const data = await res.json();
    grievancesData = data.records || [];
    renderCitizenTickets();
    renderAuthorityDashboard();
  } catch (e) {
    console.error("Error loading grievances:", e);
  }
}

function renderCitizenTickets() {
  const container = document.getElementById('citizen-tickets-container');
  if (!container) return;

  const t = UI_TRANSLATIONS[currentLanguage] || UI_TRANSLATIONS.en;

  if (grievancesData.length === 0) {
    container.innerHTML = `
      <div class="empty-state-box">
        <h4 style="color:#0b3c5d; margin:0 0 4px 0;">${t.empty_records}</h4>
        <p style="margin:0;">Submit a complaint in the Citizen Portal to track its live resolution progress.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = grievancesData.map(item => {
    const statusClass = item.status === 'Resolved' ? 'resolved' : (item.status === 'In Progress' ? 'progress' : 'pending');
    const color = getPriorityColor(item.priority);
    const dupTag = item.is_duplicate === 1 ? `<span style="color:#a15c00; font-size:11px;">[Merged into #${item.parent_id}]</span>` : '';

    return `
      <div class="card" style="padding:16px 20px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div>
            <span style="font-weight:800; color:#0b3c5d; font-size:1.05rem;">#${item.id}</span>
            &nbsp;·&nbsp; <b>${item.department}</b> ${dupTag}
            &nbsp;·&nbsp; <span style="font-size:0.8rem; color:#5f6b76;">Area: ${item.ward}</span>
          </div>
          <div>
            <span class="status-badge ${statusClass}">${item.status}</span>
            &nbsp;
            <span style="color:${color}; font-weight:700; font-size:11px; border:1px solid ${color}; padding:2px 8px; border-radius:4px;">
              ${item.priority} (${item.severity_score}/100)
            </span>
          </div>
        </div>
        <div style="color:#17202a; font-size:0.9rem; margin-bottom:8px;">
          "${escapeHtml(item.original_text)}"
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#5f6b76;">
          <span>Reported: ${item.created_at ? item.created_at.substring(0, 16).replace('T', ' ') : 'Just now'}</span>
          <span>Community Confirmations: <b>${item.upvotes}</b></span>
        </div>
      </div>
    `;
  }).join('');
}

function renderAuthorityDashboard() {
  const total = grievancesData.length;
  const pending = grievancesData.filter(g => g.status === 'Pending').length;
  const high = grievancesData.filter(g => (g.priority === 'Critical' || g.priority === 'High') && g.status !== 'Resolved').length;
  const resolved = grievancesData.filter(g => g.status === 'Resolved').length;
  const duplicates = grievancesData.filter(g => g.is_duplicate === 1).length;
  const upvotes = grievancesData.reduce((acc, g) => acc + (g.upvotes || 0), 0);

  document.getElementById('kpi-total-val').innerText = total;
  document.getElementById('kpi-pending-val').innerText = pending;
  document.getElementById('kpi-high-val').innerText = high;
  document.getElementById('kpi-resolved-val').innerText = resolved;

  const resRate = total > 0 ? ((resolved / total) * 100).toFixed(1) : 0;
  document.getElementById('kpi-res-rate').innerText = `${resRate}% resolution rate`;

  const dupRate = total > 0 ? ((duplicates / total) * 100).toFixed(1) : 0;
  document.getElementById('analytics-dup-reduction').innerText = `${dupRate}%`;
  document.getElementById('analytics-upvote-count').innerText = upvotes;

  // Render Priority Queue List
  const queueContainer = document.getElementById('admin-queue-list');
  if (queueContainer) {
    const unresolved = grievancesData
      .filter(g => g.status !== 'Resolved')
      .sort((a, b) => b.severity_score - a.severity_score)
      .slice(0, 6);

    const t = UI_TRANSLATIONS[currentLanguage] || UI_TRANSLATIONS.en;

    if (unresolved.length === 0) {
      queueContainer.innerHTML = `
        <div class="empty-state-box" style="padding:20px;">
          ${t.empty_queue}
        </div>
      `;
    } else {
      queueContainer.innerHTML = unresolved.map(item => {
        const pClass = item.priority.toLowerCase();
        const sClass = item.status === 'In Progress' ? 'progress' : 'pending';
        return `
          <div class="queue-item">
            <div class="queue-priority ${pClass}">${item.priority}</div>
            <div class="queue-copy" onclick="openTicketModal('${item.id}')">
              <strong>${item.department} (${item.ward})</strong>
              <span>#${item.id} · "${escapeHtml(item.text_en.substring(0, 40))}..."</span>
            </div>
            <button class="status-badge ${sClass}" onclick="openTicketModal('${item.id}')">${item.status}</button>
          </div>
        `;
      }).join('');
    }
  }

  // Update map markers
  if (mapboxMap) {
    initOrUpdateMap();
  }
}

function applyAdminFilters() {
  renderAuthorityDashboard();
}

// Modal Detail View & Lifecycle State Management
function openTicketModal(ticketId) {
  const item = grievancesData.find(g => g.id === ticketId);
  if (!item) return;

  const modal = document.getElementById('ticket-modal');
  const title = document.getElementById('modal-ticket-id');
  const content = document.getElementById('modal-content');

  const color = getPriorityColor(item.priority);
  title.innerText = `Ticket #${item.id} — ${item.department}`;

  content.innerHTML = `
    <div style="font-size:12px; margin-bottom:14px;">
      <div style="margin-bottom:6px;"><strong>Status:</strong> <span class="status-badge ${item.status === 'Resolved' ? 'resolved' : (item.status === 'In Progress' ? 'progress' : 'pending')}">${item.status}</span></div>
      <div style="margin-bottom:6px;"><strong>Priority:</strong> <span style="color:${color}; font-weight:700;">${item.priority}</span> (${item.severity_score}/100 Urgency Score)</div>
      <div style="margin-bottom:6px;"><strong>Administrative Area:</strong> ${item.ward} (Coordinates: ${item.lat.toFixed(5)}, ${item.lon.toFixed(5)})</div>
      <div style="margin-bottom:6px;"><strong>Language Detected:</strong> ${item.detected_lang.toUpperCase()}</div>
      <div style="margin-bottom:8px;"><strong>Citizen Description:</strong> <i>"${escapeHtml(item.original_text)}"</i></div>
      <div style="margin-bottom:12px; background:#f8fafc; padding:8px; border-radius:4px; border:1px solid #e2e8f0;">
        <strong>Normalized English:</strong> "${escapeHtml(item.text_en)}"
      </div>

      <div style="background:#edf3f7; padding:10px; border-radius:4px; margin-bottom:14px;">
        <strong style="color:#0b3c5d;">Explainable AI (XAI) Model Breakdown:</strong>
        <pre style="white-space:pre-wrap; font-family:inherit; font-size:11px; margin:4px 0 0 0; color:#334155;">${escapeHtml(item.xai_department)}\n\n${escapeHtml(item.xai_priority)}</pre>
      </div>

      <div style="border-top:1px solid #e2e8f0; padding-top:12px; display:flex; gap:8px; justify-content:flex-end;">
        <button class="outline-btn" style="color:#a4262c;" onclick="updateTicketStatus('${item.id}', 'Pending')">Mark Pending</button>
        <button class="outline-btn" style="color:#0b3c5d;" onclick="updateTicketStatus('${item.id}', 'In Progress')">Mark In Progress</button>
        <button class="primary-btn" style="background:#167044; border-color:#167044;" onclick="updateTicketStatus('${item.id}', 'Resolved')">✓ Mark as Resolved</button>
      </div>
    </div>
  `;

  modal.style.display = 'flex';
}

function closeModal() {
  document.getElementById('ticket-modal').style.display = 'none';
}

// REST API — Update Status (Persistent Real-Time Commit)
async function updateTicketStatus(ticketId, newStatus) {
  if (newStatus === 'Resolved' && !confirm("Confirm marking this complaint as Resolved?")) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: ticketId, status: newStatus })
    });

    const result = await res.json();
    if (result.success) {
      closeModal();
      await loadAllGrievances();
    } else {
      alert(`Error updating status: ${result.error}`);
    }
  } catch (err) {
    alert(`Communication error: ${err.message}`);
  }
}

// Mapbox GL JS Integration (Mumbai coordinates & real points)
function initOrUpdateMap() {
  const container = document.getElementById('mapbox-container');
  if (!container) return;

  const mumbaiCenter = [72.8777, 19.0760];

  if (!mapboxMap) {
    mapboxgl.accessToken = window.MAPBOX_TOKEN || '';
    mapboxMap = new mapboxgl.Map({
      container: 'mapbox-container',
      style: 'mapbox://styles/mapbox/light-v11',
      center: mumbaiCenter,
      zoom: 11
    });

    mapboxMap.addControl(new mapboxgl.NavigationControl(), 'top-right');
  }

  // Clear previous markers
  currentMarkers.forEach(m => m.remove());
  currentMarkers = [];

  // Add real complaint markers only
  grievancesData.forEach(item => {
    const color = getPriorityColor(item.priority);
    const el = document.createElement('div');
    el.style.width = '14px';
    el.style.height = '14px';
    el.style.borderRadius = '50%';
    el.style.backgroundColor = color;
    el.style.border = '2px solid #ffffff';
    el.style.cursor = 'pointer';
    el.style.boxShadow = '0 2px 5px rgba(0,0,0,0.3)';

    const popupHtml = `
      <div style="font-family:sans-serif; font-size:12px; min-width:180px;">
        <h4 style="margin:0 0 4px; color:#0b3c5d;">${item.department}</h4>
        <div>Ticket: <b>#${item.id}</b></div>
        <div>Priority: <b style="color:${color};">${item.priority}</b> (${item.severity_score}/100)</div>
        <div>Area: <b>${item.ward}</b> | Status: <b>${item.status}</b></div>
        <div style="margin-top:6px; font-size:11px; color:#5f6b76; background:#f8fafc; padding:4px; border-radius:4px;">
          "${escapeHtml(item.text_en.substring(0, 70))}..."
        </div>
      </div>
    `;

    const marker = new mapboxgl.Marker(el)
      .setLngLat([item.lon, item.lat])
      .setPopup(new mapboxgl.Popup().setHTML(popupHtml))
      .addTo(mapboxMap);

    currentMarkers.push(marker);
  });
}

function getPriorityColor(priority) {
  if (priority === 'Critical') return '#dc2626';
  if (priority === 'High') return '#ea580c';
  if (priority === 'Medium') return '#ca8a04';
  return '#16a34a';
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, tag => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[tag] || tag));
}
