/**
 * AwazSetu Civic Grievance Redressal Portal — Frontend Application
 * Leaflet.js Mapping + Location Autocomplete + Role-based Auth & Personal Tracking
 */

// ─── Application State ───
let currentUser = null;   // { id, role, username, full_name }
let userRole = null;      // "citizen" | "admin"
let activeView = 'citizen';
let selectedLat = 19.0760;
let selectedLon = 72.8777;
let grievancesData = [];

// Leaflet Map Instances
let citizenMap = null;
let citizenMarker = null;
let adminMap = null;
let adminMarkersLayer = null;

const API_BASE = '';

// ═══════════════════════════════════════════════════════════════════════
// MULTILINGUAL LOCALIZATION (i18n) DICTIONARY: EN, HI, MR
// ═══════════════════════════════════════════════════════════════════════
let currentSiteLang = localStorage.getItem('awazsetu_site_lang') || 'en';
let currentModalTicketId = null;

const I18N = {
  en: {
    langLabel: "Language",
    kickerSecure: "SECURE SIGN-IN",
    portalTitle: "Sign in to AwazSetu",
    portalSubtitle: "Choose your account type to access the civic portal.",
    roleCitizen: "Citizen",
    roleAuthority: "Authority",
    tabLogin: "Log In",
    tabRegister: "New Registration",
    citizenLoginDesc: "Log in with your registered 10-digit Indian mobile number (+91).",
    lblMobile: "🇮🇳 Indian Mobile Number (+91)",
    phMobile: "e.g. 9820012345",
    lblPassword: "Password",
    phPassword: "Enter password",
    btnCitizenLogin: "Log In as Citizen",
    citizenRegDesc: "Create a verified citizen account for complaint tracking and status notifications.",
    lblName: "Full Name",
    phName: "e.g. Ramesh Kumar",
    lblConfirmPassword: "Confirm Password",
    phConfirmPassword: "Confirm your password",
    btnCitizenRegister: "Register Citizen Account",
    officerNoticeTitle: "Official Municipal Officer Access",
    officerNoticeDesc: "Select your assigned department and log in with your municipal credential ID.",
    lblAssignedDept: "Assigned Municipal Department",
    lblOfficerUser: "Officer Username / ID",
    phOfficerUser: "Enter officer username",
    btnLogIn: "Log In",
    lblFullName: "Full Name",
    phFullName: "Enter your full name",
    phMinPassword: "Min. 4 characters",
    btnCreateAccount: "Create Account",
    officerLoginDesc: "Authorized Municipal Officer Login. Select your department to access your operational console.",
    lblSelectDept: "Select Municipal Department",
    deptAccountsKicker: "Department Accounts:",
    pwdHint: "Password: admin123",
    secPolicyTitle: "Internal Governance Policy",
    secPolicyDesc: "Municipal Officer accounts are issued directly by Corporation IT Administration. Public self-registration is permanently disabled for security.",
    hdrDept: "🏢 Dept:",
    optAllDepts: "All Departments (Central)",
    optRoads: "Roads & Infrastructure",
    optWater: "Water Supply",
    optPower: "Electricity/Power",
    optWaste: "Waste Management",
    optHealth: "Public Health",
    optLoginRoads: "🛣️ Roads & Infrastructure (Potholes, Roadways, Asphalt)",
    optLoginWater: "💧 Water Supply & Sewerage (Pipelines, Leaks)",
    optLoginPower: "⚡ Electricity & Power (Streetlights, Wiring)",
    optLoginWaste: "🗑️ Solid Waste Management (Garbage, Dumps)",
    optLoginHealth: "🏥 Public Health & Sanitation (Sewage, Hazards)",
    optLoginAll: "🏛️ All Departments (Central Municipal Administration)",
    chipRoads: "🛣️ Roads",
    chipWater: "💧 Water",
    chipPower: "⚡ Power",
    chipWaste: "🗑️ Waste",
    chipHealth: "🏥 Health",
    chipAll: "🏛️ Commissioner",
    authFooter: "© 2026 AwazSetu Municipal Governance Platform",
    emergencyText: "Emergency: 112",
    btnLogout: "Log Out",
    citizenHeroTitle: "Citizen Grievance Portal",
    citizenHeroSubtitle: "Submit civic issues, infrastructure concerns, or public service failures directly for municipal redressal.",
    slaKicker: "SLA GUARANTEE",
    slaTitle: "48-Hour Resolution Window",
    dupBannerTitle: "Similar complaint found nearby",
    dupBannerText: "Your report has been merged with an existing complaint to speed up resolution.",
    btnViewInTracking: "View in Tracking",
    sec1Title: "1. SELECT ISSUE CATEGORY",
    catAutoTitle: "🤖 Auto-Detect",
    catAutoSub: "AI routes from description",
    catRoadsTitle: "Roads & Potholes",
    catRoadsSub: "Asphalt, cracks, sinking",
    catWaterTitle: "Water Supply",
    catWaterSub: "Leakage, contamination",
    catPowerTitle: "Street Lighting",
    catPowerSub: "Dark poles, flickering",
    catWasteTitle: "Sanitation & Waste",
    catWasteSub: "Garbage dump, overflow",
    sec2Title: "2. DESCRIBE THE PROBLEM",
    voiceBtnText: "Voice Dictate",
    phDescription: "Describe what happened, the exact location details, and any urgency factors... (or tap 'Voice Dictate' to speak)",
    voiceListening: "Listening... Speak clearly",
    btnVoiceStop: "Stop & Keep Text",
    sec3Title: "3. INCIDENT LOCATION",
    phLocation: "Type area, society, landmark (e.g. Vardhaman Vatika)...",
    btnDetectGps: "📍 Detect GPS",
    mapHint: "Click anywhere on the map to pin location",
    sec4Title: "4. ATTACH PHOTO (OPTIONAL)",
    uploadHeadline: "Click or drag photo here",
    uploadSub: "Supports JPEG, PNG up to 10MB",
    btnBrowseFiles: "Browse File",
    txtSubmitBtn: "Submit Grievance",
    routingTitle: "Complaint Routing",
    routingDesc: "Your report is automatically categorized and dispatched to the designated civic department while checking for nearby duplicates.",
    lblCoverageRadius: "Coverage Radius",
    valCoverageRadius: "400m Proximity",
    lblLanguages: "Languages",
    privacyTitle: "Your Privacy Matters",
    privacyText: "Only information needed to resolve the grievance is collected. Avoid sharing passwords or confidential personal information.",
    badgeSecure: "Secure & Verified",
    trackTicketsTitle: "Track Complaints",
    trackTicketsSubtitle: "Real-time status updates from the municipal grievance database.",
    btnRefresh: "↻ Refresh",
    deptKicker: "AUTHORITY OPERATIONS",
    deptTitle: "Service Operations Dashboard",
    deptSubtitle: "Monitor grievance volume, department queues, incident map and resolution progress.",
    kpiTotal: "Total Complaints",
    kpiPending: "Pending Review",
    kpiHigh: "High / Critical",
    kpiResolved: "Resolved",
    headingActiveMap: "Active Complaints Map",
    headingPriorityQueue: "Priority Queue",
    lblDupMerged: "Duplicate Merged",
    lblAvgResponse: "Avg Response",
    lblIssueClusters: "Issue Clusters",
    lblCitizenConfirms: "Citizen Confirmations",
    modalTicketTitle: "Ticket Details",
    footerText: "© 2026 AwazSetu Municipal Governance Platform. All rights reserved.",
    navCitizen: "Citizen Portal",
    navTrackCitizen: "Track My Complaints",
    navDashboard: "Authority Dashboard",
    navTrackAdmin: "Track Complaints",
    statusPending: "Pending",
    statusInProgress: "In Progress",
    statusResolved: "Resolved",
    statusReopened: "Reopened",
    statusWaitingConfirmation: "Waiting for Citizen's Confirmation",
    upvoteAffectsMe: "👍 Affects Me Too",
    upvoteSupported: "✓ Supported (+1)",
    upvoteEndorsements: "👍 Endorsements",
    slaActive: "⏱️ SLA Active",
    slaBreached: "🚨 Breached",
    slaHoursLeft: "left (Urgent)",
    slaHoursRemaining: "remaining",
    noComplaintsFiled: "No Complaints Filed Yet",
    noComplaintsDesc: "You can only track complaints that were filed from your registered account (+91 {phone}). Use the Citizen Portal to submit an issue and track its resolution progress here.",
    btnReportIssue: "Report a Civic Issue",
    noComplaintsDept: "No Complaints in {dept}",
    noComplaintsDeptDesc: "There are currently no open or pending complaints assigned to {dept}.",
    noComplaintsSystem: "No complaints in the system.",
    reportedAgo: "Reported",
    anonymousUser: "Anonymous Citizen",
    evidenceBefore: "Before: Citizen Evidence",
    evidenceAfter: "After: Field Resolution Proof",
    clickFullSize: "Click to inspect full size",
    verifiedRepair: "✓ Verified On-Site Repair",
    pendingProof: "Field crew resolution photo (Pending work completion)",
    officerNote: "✓ Field Officer Note:",
    resolvedAt: "Resolved at:",
    confirmQuestion: "Did the municipal authority fix this issue?",
    confirmDesc: "Please inspect the before & after evidence. If the issue is fixed on the ground, tap 'Confirm Resolved' to close and permanently remove this ticket. If not resolved, tap 'Reopen Ticket'.",
    btnConfirmResolved: "✓ Confirm Resolved (Close & Remove)",
    btnReopenTicket: "↺ Reopen Ticket",
    resolutionConfirmed: "✓ Resolution Confirmed",
    resolutionConfirmedDesc: "You verified that this complaint was resolved satisfactorily.",
    ticketReopened: "↺ Ticket Reopened",
    adminWaitingNotice: "⏳ Waiting for Citizen's Confirmation: Field work and completion photo have been submitted. Awaiting citizen verification to close and remove this ticket.",
    ticketDeletedNotice: "✓ Resolution confirmed! Ticket #{id} has been verified and permanently removed from active complaints.",
    workOrderTitle: "🛠️ Field Work Order & Resolution Action",
    resPhotoLabel: "Upload \"After\" Resolution Photo Proof (Camera/File) *Required to Resolve:",
    workRemarks: "Work Completion Remarks:",
    workRemarksPh: "e.g. Patched 3 potholes with 20kg cold-mix asphalt",
    btnMarkPending: "Mark Pending",
    btnMarkProgress: "Mark In Progress",
    btnResolvePhoto: "✓ Submit Work for Citizen Confirmation",
    logInToDept: "Log In to {dept}"
  },
  hi: {
    langLabel: "भाषा",
    kickerSecure: "सुरक्षित साइन-इन",
    portalTitle: "आवाज़सेतु में लॉगिन करें",
    portalSubtitle: "नागरिक पोर्टल पर जाने के लिए अपना खाता प्रकार चुनें।",
    roleCitizen: "नागरिक",
    roleAuthority: "अधिकारी / प्रशासन",
    tabLogin: "लॉग इन",
    tabRegister: "नया पंजीकरण",
    citizenLoginDesc: "अपने 10-अंकों के पंजीकृत मोबाइल नंबर (+91) से लॉगिन करें।",
    lblMobile: "🇮🇳 मोबाइल नंबर (+91)",
    phMobile: "उदा. 9820012345",
    lblPassword: "पासवर्ड",
    phPassword: "पासवर्ड दर्ज करें",
    btnCitizenLogin: "नागरिक के रूप में लॉगिन करें",
    citizenRegDesc: "शिकायत ट्रैकिंग और स्थिति सूचनाओं के लिए एक सत्यापित नागरिक खाता बनाएं।",
    lblName: "पूरा नाम",
    phName: "उदा. रमेश कुमार",
    lblConfirmPassword: "पासवर्ड की पुष्टि करें",
    phConfirmPassword: "पासवर्ड पुनः दर्ज करें",
    btnCitizenRegister: "नागरिक खाता पंजीकृत करें",
    officerNoticeTitle: "आधिकारिक नगर पालिका अधिकारी लॉगिन",
    officerNoticeDesc: "अपने आवंटित विभाग का चयन करें और अपने क्रेडेंशियल के साथ लॉगिन करें।",
    lblAssignedDept: "आवंटित नगर पालिका विभाग",
    lblOfficerUser: "अधिकारी यूज़रनेम / आईडी",
    phOfficerUser: "अधिकारी यूज़रनेम दर्ज करें",
    btnLogIn: "लॉग इन",
    lblFullName: "पूरा नाम",
    phFullName: "अपना पूरा नाम दर्ज करें",
    phMinPassword: "न्यूनतम 4 वर्ण",
    btnCreateAccount: "खाता बनाएं",
    officerLoginDesc: "अधिकृत नगर पालिका अधिकारी लॉगिन। अपने परिचालन कंसोल तक पहुंचने के लिए अपने विभाग का चयन करें।",
    lblSelectDept: "नगर पालिका विभाग चुनें",
    deptAccountsKicker: "विभागीय खाते:",
    pwdHint: "पासवर्ड: admin123",
    secPolicyTitle: "आंतरिक शासन नीति",
    secPolicyDesc: "अधिकारी खाते सीधे आईटी प्रशासन द्वारा जारी किए जाते हैं। सुरक्षा के लिए सार्वजनिक स्व-पंजीकरण बंद है।",
    hdrDept: "🏢 विभाग:",
    optAllDepts: "सभी विभाग (केंद्रीय)",
    optRoads: "सड़क एवं अवसंरचना",
    optWater: "जल आपूर्ति",
    optPower: "विद्युत / ऊर्जा",
    optWaste: "ठोस कचरा प्रबंधन",
    optHealth: "सार्वजनिक स्वास्थ्य",
    optLoginRoads: "🛣️ सड़कें और बुनियादी ढांचा (गड्ढे, सड़कें, डामर)",
    optLoginWater: "💧 जल आपूर्ति एवं सीवरेज (पाइपलाइन, रिसाव)",
    optLoginPower: "⚡ बिजली और ऊर्जा (स्ट्रीट लाइट, वायरिंग)",
    optLoginWaste: "🗑️ ठोस कचरा प्रबंधन (कचरा, डंप)",
    optLoginHealth: "🏥 सार्वजनिक स्वास्थ्य एवं स्वच्छता (सीवेज, खतरे)",
    optLoginAll: "🏛️ सभी विभाग (केंद्रीय नगर निगम प्रशासन)",
    chipRoads: "🛣️ सड़कें",
    chipWater: "💧 पानी",
    chipPower: "⚡ बिजली",
    chipWaste: "🗑️ कचरा",
    chipHealth: "🏥 स्वास्थ्य",
    chipAll: "🏛️ आयुक्त",
    authFooter: "© 2026 आवाज़सेतु नगर निगम सुशासन मंच",
    emergencyText: "आपातकालीन: 112",
    btnLogout: "लॉग आउट",
    citizenHeroTitle: "नागरिक शिकायत निवारण पोर्टल",
    citizenHeroSubtitle: "नागरिक समस्याओं, बुनियादी ढांचे की चिंताओं या सेवा विफलताओं को सीधे नगर निगम निवारण के लिए दर्ज करें।",
    slaKicker: "एसएलए गारंटी",
    slaTitle: "48-घंटे के भीतर समाधान",
    dupBannerTitle: "पास में समान शिकायत मिली",
    dupBannerText: "समाधान में तेजी लाने के लिए आपकी रिपोर्ट को मौजूदा शिकायत के साथ जोड़ दिया गया है।",
    btnViewInTracking: "ट्रैकिंग में देखें",
    sec1Title: "1. शिकायत श्रेणी चुनें",
    catAutoTitle: "🤖 स्वचालित (AI)",
    catAutoSub: "विवरण से AI तय करेगा",
    catRoadsTitle: "सड़क एवं गड्ढे",
    catRoadsSub: "डामर, गड्ढे, दरारें",
    catWaterTitle: "जल आपूर्ति",
    catWaterSub: "लीकेज, गंदा पानी, कमी",
    catPowerTitle: "स्ट्रीट लाइट व बिजली",
    catPowerSub: "बंद लाइट, लटके तार",
    catWasteTitle: "कचरा व स्वच्छता",
    catWasteSub: "कचरे का ढेर, दुर्गंध",
    sec2Title: "2. समस्या का विवरण दें",
    voiceBtnText: "आवाज से बोलें",
    phDescription: "क्या हुआ, सटीक स्थान और कोई भी तात्कालिकता बताएं... (या 'आवाज से बोलें' दबाएं)",
    voiceListening: "सुन रहे हैं... स्पष्ट रूप से बोलें",
    btnVoiceStop: "रोकें और टेक्स्ट रखें",
    sec3Title: "3. घटना स्थल",
    phLocation: "इलाका, सोसायटी या लैंडमार्क लिखें (उदा. वर्धमान वाटिका)...",
    btnDetectGps: "📍 जीपीएस से खोजें",
    mapHint: "स्थान चुनने के लिए मैप पर कहीं भी क्लिक करें",
    sec4Title: "4. फोटो संलग्न करें (वैकल्पिक)",
    uploadHeadline: "फोटो खींचें या यहाँ ड्रैग करें",
    uploadSub: "JPEG, PNG 10MB तक समर्थित",
    btnBrowseFiles: "फ़ाइल चुनें",
    txtSubmitBtn: "शिकायत दर्ज करें",
    routingTitle: "शिकायत रूटिंग",
    routingDesc: "आपकी रिपोर्ट स्वचालित रूप से वर्गीकृत होकर संबंधित विभाग को भेजी जाती है और आसपास की प्रतियों की जाँच करती है।",
    lblCoverageRadius: "कवरेज दायरा",
    valCoverageRadius: "400 मी. निकटता",
    lblLanguages: "भाषाएं",
    privacyTitle: "आपकी गोपनीयता महत्वपूर्ण है",
    privacyText: "केवल शिकायत निवारण के लिए आवश्यक जानकारी ही एकत्र की जाती है। व्यक्तिगत पासवर्ड साझा न करें।",
    badgeSecure: "सुरक्षित एवं सत्यापित",
    trackTicketsTitle: "शिकायतों की स्थिति",
    trackTicketsSubtitle: "नगर निगम डेटाबेस से वास्तविक समय की स्थिति।",
    btnRefresh: "↻ रीफ्रेश करें",
    deptKicker: "प्रशासन संचालन",
    deptTitle: "सेवा संचालन डैशबोर्ड",
    deptSubtitle: "शिकायत मात्रा, विभागीय कतार, मानचित्र और निवारण प्रगति की निगरानी करें।",
    kpiTotal: "कुल शिकायतें",
    kpiPending: "लंबित समीक्षा",
    kpiHigh: "गंभीर / उच्च प्राथमिकता",
    kpiResolved: "समाधान हुआ",
    headingActiveMap: "सक्रिय शिकायत मानचित्र",
    headingPriorityQueue: "प्राथमिकता कतार",
    lblDupMerged: "समान शिकायतें मर्ज",
    lblAvgResponse: "औसत प्रतिक्रिया",
    lblIssueClusters: "समस्या क्लस्टर",
    lblCitizenConfirms: "नागरिक पुष्टि",
    modalTicketTitle: "शिकायत विवरण",
    footerText: "© 2026 आवाज़सेतु नगर निगम शासन मंच। सर्वाधिकार सुरक्षित।",
    navCitizen: "नागरिक पोर्टल",
    navTrackCitizen: "मेरी शिकायतें ट्रैक करें",
    navDashboard: "अधिकारी डैशबोर्ड",
    navTrackAll: "शिकायतें ट्रैक करें",
    statusPending: "लंबित",
    statusInProgress: "प्रगति पर",
    statusResolved: "हल किया गया",
    statusReopened: "पुनः खोला गया",
    statusWaitingConfirmation: "नागरिक पुष्टि की प्रतीक्षा",
    upvoteAffectsMe: "👍 यह मुझे भी प्रभावित करता है",
    upvoteSupported: "✓ आपके द्वारा समर्थित (+1)",
    upvoteEndorsements: "👍 समर्थन",
    slaActive: "⏱️ एसएलए सक्रिय",
    slaBreached: "🚨 समय सीमा पार",
    slaHoursLeft: "घंटे शेष (अति-आवश्यक)",
    slaHoursRemaining: "घंटे शेष",
    noComplaintsFiled: "अभी तक कोई शिकायत दर्ज नहीं की गई",
    noComplaintsDesc: "आप केवल अपने पंजीकृत खाते (+91 {phone}) से दर्ज शिकायतों को ही ट्रैक कर सकते हैं।",
    btnReportIssue: "नागरिक समस्या दर्ज करें",
    noComplaintsDept: "{dept} में कोई खुली शिकायत नहीं है",
    noComplaintsDeptDesc: "वर्तमान में {dept} के लिए कोई खुली या लंबित शिकायत नहीं है।",
    noComplaintsSystem: "सिस्टम में कोई शिकायत नहीं है।",
    reportedAgo: "दर्ज की गई",
    anonymousUser: "नागरिक",
    evidenceBefore: "कार्य से पहले: नागरिक साक्ष्य",
    evidenceAfter: "कार्य के बाद: फील्ड समाधान साक्ष्य",
    clickFullSize: "पूरा आकार देखने के लिए क्लिक करें",
    verifiedRepair: "✓ सत्यापित जमीनी मरम्मत",
    pendingProof: "फील्ड क्रू समाधान फोटो (कार्य प्रगति पर)",
    officerNote: "✓ फील्ड अधिकारी टिप्पणी:",
    resolvedAt: "समाधान का समय:",
    confirmQuestion: "क्या नगर निगम प्रशासन ने इस समस्या का समाधान किया?",
    confirmDesc: "कृपया कार्य से पहले और बाद के फोटो साक्ष्य देखें। यदि समस्या का समाधान हो गया है, तो इसे बंद करने और हटाने के लिए 'समाधान की पुष्टि करें' दबाएं। अन्यथा 'टिकट पुनः खोलें' दबाएं।",
    btnConfirmResolved: "✓ समाधान की पुष्टि करें (बंद और हटाएं)",
    btnReopenTicket: "↺ टिकट पुनः खोलें",
    resolutionConfirmed: "✓ समाधान की पुष्टि की गई",
    resolutionConfirmedDesc: "आपने पुष्टि की है कि यह शिकायत संतोषजनक रूप से हल हो गई है।",
    ticketReopened: "↺ टिकट पुनः खोला गया",
    adminWaitingNotice: "⏳ नागरिक पुष्टि की प्रतीक्षा: कार्य का फोटो प्रमाण अपलोड किया गया है। नागरिक द्वारा सत्यापन की प्रतीक्षा है।",
    ticketDeletedNotice: "✓ समाधान की पुष्टि हो गई! टिकट #{id} का सत्यापन हो गया और सक्रिय शिकायतों से हटा दिया गया।",
    workOrderTitle: "🛠️ फील्ड वर्क ऑर्डर एवं समाधान कार्रवाई",
    resPhotoLabel: "समाधान फोटो प्रमाण अपलोड करें (कैमरा/फ़ाइल) *अनिवार्य:",
    workRemarks: "कार्य पूर्णता टिप्पणी:",
    workRemarksPh: "उदा. गड्ढे को 20 किग्रा कोल्ड-मिक्स डामर से भर दिया गया",
    btnMarkPending: "लंबित रखें",
    btnMarkProgress: "प्रगति पर करें",
    btnResolvePhoto: "✓ कार्य पूर्ण कर नागरिक पुष्टि हेतु भेजें",
    logInToDept: "{dept} में लॉग इन करें"
  },
  mr: {
    langLabel: "भाषा",
    kickerSecure: "सुरक्षित साइन-इन",
    portalTitle: "आवाजसेतू मध्ये लॉगिन करा",
    portalSubtitle: "नागरी पोर्टलवर जाण्यासाठी आपले खाते निवडा.",
    roleCitizen: "नागरिक",
    roleAuthority: "अधिकारी / प्रशासन",
    tabLogin: "लॉग इन",
    tabRegister: "नवीन नोंदणी",
    citizenLoginDesc: "आपल्या नोंदणीकृत 10-अंकी मोबाइल क्रमांकाने (+91) लॉगिन करा.",
    lblMobile: "🇮🇳 मोबाइल क्रमांक (+91)",
    phMobile: "उदा. 9820012345",
    lblPassword: "पासवर्ड",
    phPassword: "पासवर्ड टाका",
    btnCitizenLogin: "नागरिक म्हणून लॉगिन करा",
    citizenRegDesc: "तक्रार ट्रॅकिंग आणि स्थिती सूचनांसाठी नागरिक खाते तयार करा.",
    lblName: "पूर्ण नाव",
    phName: "उदा. रमेश कुमार",
    lblConfirmPassword: "पासवर्डची खात्री करा",
    phConfirmPassword: "पासवर्ड पुन्हा टाका",
    btnCitizenRegister: "नागरिक खाते नोंदणी करा",
    officerNoticeTitle: "अधिकृत महापालिका अधिकारी प्रवेश",
    officerNoticeDesc: "आपला नियुक्त विभाग निवडा आणि आपल्या अधिकृत क्रेडेंशियल्सने लॉगिन करा.",
    lblAssignedDept: "नियुक्त महापालिका विभाग",
    lblOfficerUser: "अधिकारी युझरनेम / आयडी",
    phOfficerUser: "अधिकारी युझरनेम टाका",
    btnLogIn: "लॉग इन",
    lblFullName: "पूर्ण नाव",
    phFullName: "आपले पूर्ण नाव टाका",
    phMinPassword: "किमान 4 वर्ण",
    btnCreateAccount: "खाते तयार करा",
    officerLoginDesc: "अधिकृत महापालिका अधिकारी प्रवेश. आपल्या कार्य प्रणालीत जाण्यासाठी आपला विभाग निवडा.",
    lblSelectDept: "महापालिका विभाग निवडा",
    deptAccountsKicker: "विभागीय खाती:",
    pwdHint: "पासवर्ड: admin123",
    secPolicyTitle: "अंतर्गत शासन धोरण",
    secPolicyDesc: "अधिकारी खाती थेट महापालिका आयटी प्रशासनाकडून दिली जातात. सुरक्षेसाठी सार्वजनिक नोंदणी बंद आहे.",
    hdrDept: "🏢 विभाग:",
    optAllDepts: "सर्व विभाग (मध्यवर्ती)",
    optRoads: "रस्ते व पायाभूत सुविधा",
    optWater: "पाणी पुरवठा",
    optPower: "वीज / ऊर्जा",
    optWaste: "कचरा व्यवस्थापन",
    optHealth: "सार्वजनिक आरोग्य",
    optLoginRoads: "🛣️ रस्ते आणि पायाभूत सुविधा (खड्डे, रस्ते, डांबरीकरण)",
    optLoginWater: "💧 पाणी पुरवठा आणि सांडपाणी (पाईपलाईन, गळती)",
    optLoginPower: "⚡ वीज आणि ऊर्जा (पथदिवे, वायरिंग)",
    optLoginWaste: "🗑️ घनकचरा व्यवस्थापन (कचरा, डंप)",
    optLoginHealth: "🏥 सार्वजनिक आरोग्य आणि स्वच्छता (सांडपाणी, धोके)",
    optLoginAll: "🏛️ सर्व विभाग (मध्यवर्ती महानगरपालिका प्रशासन)",
    chipRoads: "🛣️ रस्ते",
    chipWater: "💧 पाणी",
    chipPower: "⚡ वीज",
    chipWaste: "🗑️ कचरा",
    chipHealth: "🏥 आरोग्य",
    chipAll: "🏛️ आयुक्त",
    authFooter: "© 2026 आवाजसेतू महानगरपालिका प्रशासन व्यासपीठ",
    emergencyText: "आपत्कालीन: 112",
    btnLogout: "लॉग आउट",
    citizenHeroTitle: "नागरिक तक्रार निवारण पोर्टल",
    citizenHeroSubtitle: "नागरी समस्या, पायाभूत सुविधांच्या तक्रारी किंवा सेवा त्रुटी थेट महापालिका निवारणासाठी नोंदवा.",
    slaKicker: "हमी कालावधी (SLA)",
    slaTitle: "48 तासांत निवारण",
    dupBannerTitle: "जवळच अशीच तक्रार आढळली",
    dupBannerText: "निवारण जलद होण्यासाठी आपली तक्रार अस्तित्वातील तक्रारीशी जोडली गेली आहे.",
    btnViewInTracking: "ट्रॅकिंगमध्ये पहा",
    sec1Title: "1. तक्रार वर्गवारी निवडा",
    catAutoTitle: "🤖 स्वयंचलित (AI)",
    catAutoSub: "वर्णनावरून AI ठरवेल",
    catRoadsTitle: "रस्ते व खड्डे",
    catRoadsSub: "डांबर, खड्डे, भेगा",
    catWaterTitle: "पाणी पुरवठा",
    catWaterSub: "गळती, दूषित पाणी",
    catPowerTitle: "पथदिवे व वीज",
    catPowerSub: "बंद दिवे, तुटलेली वायर",
    catWasteTitle: "कचरा व स्वच्छता",
    catWasteSub: "कचऱ्याचे ढीग, अस्वच्छता",
    sec2Title: "2. समस्येचे वर्णन करा",
    voiceBtnText: "आवाजाने बोला",
    phDescription: "काय घडले, नेमके ठिकाण आणि तातडीचे मुद्दे लिहा... (किंवा 'आवाजाने बोला' वर दाबा)",
    voiceListening: "ऐकत आहे... स्पष्टपणे बोला",
    btnVoiceStop: "थांबवा आणि मजकूर ठेवा",
    sec3Title: "3. घटना स्थळ",
    phLocation: "परिसर, इमारत किंवा लँडमार्क टाइप करा (उदा. वर्धमान वाटिका)...",
    btnDetectGps: "📍 जीपीएस शोधा",
    mapHint: "ठिकाण निवडण्यासाठी नकाशावर कुठेही क्लिक करा",
    sec4Title: "4. फोटो जोडा (पर्यायी)",
    uploadHeadline: "फोटो काढा किंवा येथे ड्रॅग करा",
    uploadSub: "JPEG, PNG 10MB पर्यंत चालेल",
    btnBrowseFiles: "फाइल निवडा",
    txtSubmitBtn: "तक्रार दाखल करा",
    routingTitle: "तक्रार विभागणी",
    routingDesc: "आपली तक्रार स्वयंचलितपणे वर्गीकृत करून संबंधित विभागाकडे पाठवली जाते आणि जवळच्या इतर तक्रारींची तपासणी केली जाते.",
    lblCoverageRadius: "कव्हरेज क्षेत्र",
    valCoverageRadius: "400 मी. परिसर",
    lblLanguages: "भाषा",
    privacyTitle: "आपली गोपनीयता महत्त्वाची आहे",
    privacyText: "फक्त तक्रार निवारणासाठी लागणारी माहिती गोळा केली जाते. कृपया वैयक्तिक पासवर्ड शेअर करू नका.",
    badgeSecure: "सुरक्षित व पडताळणीकृत",
    trackTicketsTitle: "तक्रारींची स्थिती",
    trackTicketsSubtitle: "महापालिका डेटाबेसमधून थेट स्थिती अपडेट.",
    btnRefresh: "↻ रिफ्रेश करा",
    deptKicker: "प्रशासन कामकाज",
    deptTitle: "सेवा संचालन डॅशबोर्ड",
    deptSubtitle: "तक्रारींचे प्रमाण, विभाग रांगा, नकाशा आणि निवारण प्रगतीचे निरीक्षण करा.",
    kpiTotal: "एकूण तक्रारी",
    kpiPending: "प्रलंबित पुनरावलोकन",
    kpiHigh: "गंभीर / उच्च प्राधान्य",
    kpiResolved: "निवारण झाले",
    headingActiveMap: "सक्रिय तक्रारींचा नकाशा",
    headingPriorityQueue: "प्राधान्य रांग",
    lblDupMerged: "समान तक्रारी विलीन",
    lblAvgResponse: "सरासरी प्रतिसाद वेळ",
    lblIssueClusters: "समस्या क्लस्टर्स",
    lblCitizenConfirms: "नागरिक पुष्टी",
    modalTicketTitle: "तक्रार तपशील",
    footerText: "© 2026 आवाजसेतू महापालिका शासन मंच. सर्व हक्क राखीव.",
    navCitizen: "नागरिक पोर्टल",
    navTrackCitizen: "माझ्या तक्रारी ट्रॅक करा",
    navDashboard: "अधिकारी डॅशबोर्ड",
    navTrackAll: "तक्रारी ट्रॅक करा",
    statusPending: "प्रलंबित",
    statusInProgress: "प्रगतीपथावर",
    statusResolved: "निवारण झाले",
    statusReopened: "पुन्हा उघडले",
    statusWaitingConfirmation: "नागरिकांच्या पुष्टीकरणाची प्रतीक्षा",
    upvoteAffectsMe: "👍 मलाही याचा त्रास होतोय",
    upvoteSupported: "✓ आपण पुष्टी केली (+1)",
    upvoteEndorsements: "👍 समर्थन",
    slaActive: "⏱️ हमी वेळ सुरू",
    slaBreached: "🚨 मुदत ओलांडली",
    slaHoursLeft: "तास शिल्लक (तातडीचे)",
    slaHoursRemaining: "तास शिल्लक",
    noComplaintsFiled: "अद्याप कोणतीही तक्रार दाखल नाही",
    noComplaintsDesc: "आपण फक्त आपल्या नोंदणीकृत खात्यावरून (+91 {phone}) दाखल केलेल्या तक्रारी ट्रॅक करू शकता.",
    btnReportIssue: "नागरी समस्या नोंदवा",
    noComplaintsDept: "{dept} मध्ये कोणतीही तक्रार नाही",
    noComplaintsDeptDesc: "सध्या {dept} विभागासाठी कोणतीही प्रलंबित तक्रार नाही.",
    noComplaintsSystem: "सिस्टममध्ये कोणतीही तक्रार नाही.",
    reportedAgo: "नोंदणी तारीख",
    anonymousUser: "नागरिक",
    evidenceBefore: "कामापूर्वी: नागरिकांचा पुरावा",
    evidenceAfter: "कामानंतर: निवारणाचा फोटो पुरावा",
    clickFullSize: "मोठा फोटो पाहण्यासाठी क्लिक करा",
    verifiedRepair: "✓ प्रत्यक्ष काम पूर्ण",
    pendingProof: "कर्मचाऱ्यांचा कामाचा फोटो (काम प्रलंबित)",
    officerNote: "✓ अधिकारी टिप्पणी:",
    resolvedAt: "निवारणाची वेळ:",
    confirmQuestion: "महापालिका प्रशासनाने ही समस्या सोडवली का?",
    confirmDesc: "कृपया आधी आणि नंतरचा फोटो पुरावा तपासा. समस्या सुटली असल्यास हे तिकीट बंद करून हटवण्यासाठी 'निवारणाची खात्री करा' दाबा. न सुटल्यास 'पुन्हा उघडा' दाबा.",
    btnConfirmResolved: "✓ निवारणाची खात्री करा (बंद करा आणि हटवा)",
    btnReopenTicket: "↺ तक्रार पुन्हा उघडा",
    resolutionConfirmed: "✓ निवारणाची पुष्टी झाली",
    resolutionConfirmedDesc: "आपण खात्री केली आहे की ही तक्रार योग्य रीतीने सोडवली गेली आहे.",
    ticketReopened: "↺ तक्रार पुन्हा उघडली",
    adminWaitingNotice: "⏳ नागरिकांच्या पुष्टीकरणाची प्रतीक्षा: दुरुस्तीचा फोटो पुरावा अपलोड केला आहे. नागरिकांच्या पडताळणीची प्रतीक्षा आहे.",
    ticketDeletedNotice: "✓ निवारणाची पुष्टी झाली! तिकीट #{id} चे प्रमाणीकरण झाले आणि सक्रिय तक्रारींमधून काढून टाकण्यात आले.",
    workOrderTitle: "🛠️ कार्य आदेश व निवारण कृती",
    resPhotoLabel: "निवारणाचा फोटो पुरावा अपलोड करा (कॅमेरा/फाइल) *आवश्यक:",
    workRemarks: "काम पूर्ण झाल्याची टिप्पणी:",
    workRemarksPh: "उदा. डांबराने खड्डा बुजवला व रस्ता दुरुस्त केला",
    btnMarkPending: "प्रलंबित करा",
    btnMarkProgress: "प्रगतीपथावर करा",
    btnResolvePhoto: "✓ काम पूर्ण करून नागरिकांच्या पुष्टीकरणासाठी पाठवा",
    logInToDept: "{dept} मध्ये लॉगिन करा"
  }
};

function t(key, fallback = '') {
  const dict = I18N[currentSiteLang] || I18N['en'];
  return dict[key] || (I18N['en'] && I18N['en'][key]) || fallback;
}

function getLocalizedDeptName(dept) {
  const map = {
    'Roads & Infrastructure': { hi: 'सड़क एवं अवसंरचना', mr: 'रस्ते व पायाभूत सुविधा' },
    'Water Supply': { hi: 'जल आपूर्ति', mr: 'पाणी पुरवठा' },
    'Electricity/Power': { hi: 'विद्युत एवं ऊर्जा', mr: 'वीज व ऊर्जा' },
    'Waste Management': { hi: 'ठोस कचरा प्रबंधन', mr: 'कचरा व्यवस्थापन' },
    'Public Health': { hi: 'सार्वजनिक स्वास्थ्य', mr: 'सार्वजनिक आरोग्य' },
    'All': { hi: 'सभी विभाग', mr: 'सर्व विभाग' }
  };
  if (map[dept] && map[dept][currentSiteLang]) {
    return map[dept][currentSiteLang];
  }
  return dept;
}

function getLocalizedStatus(status) {
  if (status === 'Waiting for Citizen Confirmation' || status === 'Awaiting Citizen Confirmation') {
    return t('statusWaitingConfirmation', "Waiting for Citizen's Confirmation");
  }
  if (status === 'Resolved') return t('statusResolved', 'Resolved');
  if (status === 'In Progress') return t('statusInProgress', 'In Progress');
  if (status === 'Reopened') return t('statusReopened', 'Reopened');
  return t('statusPending', 'Pending');
}

function switchSiteLanguage(lang) {
  if (!['en', 'hi', 'mr'].includes(lang)) lang = 'en';
  currentSiteLang = lang;
  localStorage.setItem('awazsetu_site_lang', lang);

  // 1. Update language pills in both auth screen and app header
  document.querySelectorAll('.site-lang-pill').forEach(pill => {
    const pillLang = pill.getAttribute('data-site-lang');
    if (pillLang === lang) {
      pill.classList.add('active');
    } else {
      pill.classList.remove('active');
    }
  });

  // 2. Synchronize voice dictation language default
  const targetDictationLang = lang === 'hi' ? 'hi-IN' : (lang === 'mr' ? 'mr-IN' : 'en-IN');
  setDictationLanguage(targetDictationLang);

  // 3. Update all static elements with [data-i18n]
  const dict = I18N[lang] || I18N['en'];
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) {
      el.innerText = dict[key];
    }
  });

  // 4. Update all input/textarea placeholders with [data-i18n-ph]
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const key = el.getAttribute('data-i18n-ph');
    if (dict[key]) {
      el.placeholder = dict[key];
    }
  });

  // 5. Dynamic department login button & account labels
  const adminDeptSel = document.getElementById('admin-login-dept');
  if (adminDeptSel) {
    onAdminDeptSelectChange(adminDeptSel.value);
  }

  // 6. Navigation pills
  renderNav();

  // 7. Dynamic department headings and view content
  updateDepartmentHeadings();
  renderCitizenTickets();
  renderAuthorityDashboard();

  // 8. If ticket modal is currently open, refresh it with new language
  const modal = document.getElementById('ticket-modal');
  if (modal && modal.style.display !== 'none' && currentModalTicketId) {
    openTicketModal(currentModalTicketId);
  }
}




// ─── Initialization ───
document.addEventListener('DOMContentLoaded', () => {
  // Initialize site language from storage or default
  switchSiteLanguage(currentSiteLang);

  // Check saved session
  const saved = sessionStorage.getItem('awazsetu_user');
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      currentUser = parsed;
      userRole = parsed.role;
      enterApp();
    } catch (e) { /* ignore */ }
  }

  // Character counter
  const descField = document.getElementById('description');
  if (descField) {
    descField.addEventListener('input', (e) => {
      document.getElementById('char-count').innerText = `${e.target.value.length}/500 chars`;
    });
  }

  // Location Autocomplete with debounced geocode search
  const locInput = document.getElementById('incident-location-text');
  const suggestionsBox = document.getElementById('location-suggestions');
  let geocodeDebounceTimer = null;

  if (locInput && suggestionsBox) {
    locInput.addEventListener('input', (e) => {
      const q = e.target.value.trim();
      clearTimeout(geocodeDebounceTimer);
      if (q.length < 2) {
        suggestionsBox.style.display = 'none';
        suggestionsBox.innerHTML = '';
        return;
      }
      geocodeDebounceTimer = setTimeout(() => {
        fetchLocationSuggestions(q);
      }, 250);
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (!locInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
        suggestionsBox.style.display = 'none';
      }
    });

    locInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        suggestionsBox.style.display = 'none';
      }
    });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// LOCATION AUTOCOMPLETE (Suggestions Dropdown)
// ═══════════════════════════════════════════════════════════════════════
async function fetchLocationSuggestions(query) {
  const box = document.getElementById('location-suggestions');
  if (!box) return;

  try {
    const res = await fetch(`${API_BASE}/api/geocode?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    const results = data.results || [];

    if (results.length === 0) {
      box.style.display = 'none';
      box.innerHTML = '';
      return;
    }

    box.innerHTML = results.map((item) => {
      const parts = item.display_name.split(',');
      const primary = parts[0].trim();
      const secondary = parts.slice(1).join(',').trim();
      const safePrimary = escapeHtml(primary).replace(/'/g, "\\'");
      return `
        <div class="suggestion-item" onclick="selectLocationSuggestion(${item.lat}, ${item.lon}, '${safePrimary}')">
          <span class="suggestion-pin">📍</span>
          <div class="suggestion-texts">
            <span class="suggestion-primary">${escapeHtml(primary)}</span>
            <span class="suggestion-secondary">${escapeHtml(secondary)}</span>
          </div>
        </div>
      `;
    }).join('');
    box.style.display = 'block';
  } catch (err) {
    box.style.display = 'none';
  }
}

let selectedPlaceName = '';

function selectLocationSuggestion(lat, lon, placeName) {
  const input = document.getElementById('incident-location-text');
  const box = document.getElementById('location-suggestions');
  if (input) input.value = placeName;
  if (box) box.style.display = 'none';
  selectedPlaceName = placeName;

  updateSelectedLocation(lat, lon);
  if (citizenMap && citizenMarker) {
    citizenMap.setView([lat, lon], 16);
    citizenMarker.setLatLng([lat, lon]);
    citizenMarker.bindPopup(`<b>📍 ${placeName}</b>`).openPopup();
  }
}

// ═══════════════════════════════════════════════════════════════════════
// AUTHENTICATION LOGIC
// ═══════════════════════════════════════════════════════════════════════
function switchAuthRole(role) {
  document.getElementById('tab-citizen-role').classList.toggle('active', role === 'citizen');
  document.getElementById('tab-admin-role').classList.toggle('active', role === 'admin');
  document.getElementById('auth-citizen-panel').style.display = role === 'citizen' ? 'block' : 'none';
  document.getElementById('auth-admin-panel').style.display = role === 'admin' ? 'block' : 'none';
}

function switchAuthSubTab(panel, tab) {
  if (panel === 'citizen') {
    document.getElementById('tab-citizen-login').classList.toggle('active', tab === 'login');
    document.getElementById('tab-citizen-register').classList.toggle('active', tab === 'register');
    document.getElementById('citizen-login-form').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('citizen-register-form').style.display = tab === 'register' ? 'block' : 'none';
  }
}

async function citizenLogin() {
  const phone = document.getElementById('citizen-login-phone').value.trim();
  const password = document.getElementById('citizen-login-password').value;
  const errEl = document.getElementById('citizen-login-error');
  errEl.innerText = '';

  if (!phone || !password) { errEl.innerText = 'Please fill in all fields.'; return; }

  const cleanPhone = phone.replace(/\s|-|\+91/g, '').replace(/^0+/, '');
  try {
    const res = await fetch(`${API_BASE}/api/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: 'citizen', username: cleanPhone, password })
    });
    const data = await res.json();
    if (data.success) {
      currentUser = data.user;
      userRole = 'citizen';
      sessionStorage.setItem('awazsetu_user', JSON.stringify(data.user));
      enterApp();
    } else {
      errEl.innerText = data.error || 'Login failed.';
    }
  } catch (e) { errEl.innerText = 'Server connection error. Is the server running?'; }
}

async function citizenRegister() {
  const name = document.getElementById('citizen-reg-name').value.trim();
  const phone = document.getElementById('citizen-reg-phone').value.trim();
  const pw1 = document.getElementById('citizen-reg-password').value;
  const pw2 = document.getElementById('citizen-reg-confirm').value;
  const errEl = document.getElementById('citizen-reg-error');
  const successEl = document.getElementById('citizen-reg-success');
  errEl.innerText = ''; successEl.innerText = '';

  if (!name || !phone || !pw1 || !pw2) { errEl.innerText = 'Please fill in all fields.'; return; }
  if (pw1 !== pw2) { errEl.innerText = 'Passwords do not match.'; return; }

  try {
    const res = await fetch(`${API_BASE}/api/register`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: name, phone, password: pw1 })
    });
    const data = await res.json();
    if (data.success) {
      successEl.innerText = '✓ Account created! You can now log in.';
      document.getElementById('citizen-reg-name').value = '';
      document.getElementById('citizen-reg-phone').value = '';
      document.getElementById('citizen-reg-password').value = '';
      document.getElementById('citizen-reg-confirm').value = '';
    } else {
      errEl.innerText = data.error || 'Registration failed.';
    }
  } catch (e) { errEl.innerText = 'Server connection error.'; }
}



function onAdminDeptSelectChange(dept) {
  const btn = document.getElementById('btn-officer-login-submit');
  const localizedDept = getLocalizedDeptName(dept);
  if (btn) {
    if (currentSiteLang === 'hi') {
      btn.innerText = dept === 'All' ? 'केंद्रीय प्रशासन में लॉग इन करें' : `${localizedDept} में लॉग इन करें`;
    } else if (currentSiteLang === 'mr') {
      btn.innerText = dept === 'All' ? 'मध्यवर्ती प्रशासनात लॉगिन करा' : `${localizedDept} मध्ये लॉगिन करा`;
    } else {
      btn.innerText = dept === 'All' ? 'Log In to Central Administration' : `Log In to ${dept}`;
    }
  }

  const defaultUsernames = {
    'Roads & Infrastructure': 'roads_admin',
    'Water Supply': 'water_admin',
    'Electricity/Power': 'power_admin',
    'Waste Management': 'waste_admin',
    'Public Health': 'health_admin',
    'All': 'admin'
  };

  const uInput = document.getElementById('admin-login-username');
  if (uInput && defaultUsernames[dept]) {
    uInput.value = defaultUsernames[dept];
  }

  const chipMap = {
    'Roads & Infrastructure': 'chip-roads',
    'Water Supply': 'chip-water',
    'Electricity/Power': 'chip-power',
    'Waste Management': 'chip-waste',
    'Public Health': 'chip-health',
    'All': 'chip-all'
  };
  document.querySelectorAll('.btn-dept-chip').forEach(c => c.classList.remove('active'));
  const activeChip = document.getElementById(chipMap[dept]);
  if (activeChip) activeChip.classList.add('active');
}

function quickFillOfficer(dept, username) {
  const sel = document.getElementById('admin-login-dept');
  if (sel) sel.value = dept;
  const uInput = document.getElementById('admin-login-username');
  if (uInput) uInput.value = username;
  const pInput = document.getElementById('admin-login-password');
  if (pInput) pInput.value = 'admin123';
  onAdminDeptSelectChange(dept);
}



async function adminLogin() {
  const dept = document.getElementById('admin-login-dept') ? document.getElementById('admin-login-dept').value : 'All';
  const username = document.getElementById('admin-login-username').value.trim();
  const password = document.getElementById('admin-login-password').value;
  const errEl = document.getElementById('admin-login-error');
  if (errEl) errEl.innerText = '';

  if (!username || !password) {
    if (errEl) errEl.innerText = 'Please fill in all fields.';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: 'admin', username, password, department: dept })
    });
    const data = await res.json();
    if (data.success) {
      currentUser = data.user;
      userRole = 'admin';
      sessionStorage.setItem('awazsetu_user', JSON.stringify(data.user));

      const assignedDept = data.user.department || dept || 'All';
      currentAdminDepartment = assignedDept;
      sessionStorage.setItem('awazsetu_admin_dept', assignedDept);

      enterApp();
    } else {
      if (errEl) errEl.innerText = data.error || 'Login failed.';
    }
  } catch (e) {
    if (errEl) errEl.innerText = 'Server connection error.';
  }
}

let currentAdminDepartment = sessionStorage.getItem('awazsetu_admin_dept') || 'All';

function switchAdminDepartment(dept) {
  currentAdminDepartment = dept || 'All';
  sessionStorage.setItem('awazsetu_admin_dept', currentAdminDepartment);

  const headerSel = document.getElementById('global-admin-dept-select');
  const dashSel = document.getElementById('filter-department');
  if (headerSel) headerSel.value = currentAdminDepartment;
  if (dashSel) dashSel.value = currentAdminDepartment;

  updateDepartmentHeadings();
  renderAuthorityDashboard();
  renderCitizenTickets();
}

function updateDepartmentHeadings() {
  const kicker = document.getElementById('dashboard-dept-kicker');
  const dashTitle = document.getElementById('dashboard-dept-title');
  const dashSub = document.getElementById('dashboard-dept-subtitle');
  const trackTitle = document.getElementById('track-tickets-title');
  const trackSub = document.getElementById('track-tickets-subtitle');

  const deptKey = currentAdminDepartment || 'All';
  const isHi = currentSiteLang === 'hi';
  const isMr = currentSiteLang === 'mr';

  if (userRole === 'admin') {
    if (deptKey === 'All') {
      if (kicker) kicker.innerText = isHi ? 'केंद्रीय नगर निगम संचालन' : (isMr ? 'मध्यवर्ती महापालिका कामकाज' : 'CENTRAL MUNICIPAL OPERATIONS');
      if (dashTitle) dashTitle.innerText = isHi ? 'केंद्रीय संचालन डैशबोर्ड' : (isMr ? 'मध्यवर्ती संचालन डॅशबोर्ड' : 'Central Operations Dashboard');
      if (dashSub) dashSub.innerText = isHi ? 'समेकित शिकायत मात्रा, नगरपालिका कतार, मानचित्र और समाधान प्रगति।' : (isMr ? 'एकत्रित तक्रारींचे प्रमाण, विभाग रांगा, नकाशा आणि निवारण प्रगती.' : 'Consolidated grievance volume, municipal queues, incident map and resolution progress.');
      if (trackTitle) trackTitle.innerText = isHi ? 'शिकायतें ट्रैक करें — सभी विभाग' : (isMr ? 'तक्रारींचा मागोवा — सर्व विभाग' : 'Track Complaints — All Departments');
      if (trackSub) trackSub.innerText = isHi ? 'सभी नगरपालिका विभागों की सभी शिकायतों का पूरा रजिस्टर।' : (isMr ? 'सर्व महापालिका विभागांमधील सर्व तक्रारींची संपूर्ण नोंद.' : 'Complete register of all civic complaints across all municipal departments.');
    } else {
      const localizedDept = getLocalizedDeptName(deptKey);
      if (kicker) kicker.innerText = isHi ? `${localizedDept.toUpperCase()} विभाग` : (isMr ? `${localizedDept.toUpperCase()} विभाग` : `${deptKey.toUpperCase()} DEPARTMENT`);
      if (dashTitle) dashTitle.innerText = isHi ? `${localizedDept} संचालन पोर्टल` : (isMr ? `${localizedDept} संचालन पोर्टल` : `${deptKey} Operations Portal`);
      if (dashSub) dashSub.innerText = isHi ? `${localizedDept} के लिए समर्पित परिचालन नियंत्रण, प्राथमिकता समीक्षा और मानचित्र।` : (isMr ? `${localizedDept} साठी समर्पित नियंत्रण, प्राधान्य पुनरावलोकन आणि नकाशा.` : `Dedicated operational control, priority triage, and incident map for ${deptKey}.`);
      if (trackTitle) trackTitle.innerText = isHi ? `शिकायतें — ${localizedDept}` : (isMr ? `तक्रारी — ${localizedDept}` : `Track Complaints — ${deptKey}`);
      if (trackSub) trackSub.innerText = isHi ? `केवल ${localizedDept} को भेजी गई शिकायतें दिखाई जा रही हैं।` : (isMr ? `केवळ ${localizedDept} कडे वर्ग केलेल्या तक्रारी दाखवत आहे.` : `Showing complaints strictly routed to ${deptKey}.`);
    }
  } else {
    if (trackTitle) trackTitle.innerText = t('trackTicketsTitle', 'Track My Complaints');
    if (trackSub) trackSub.innerText = isHi ? 'आपके पंजीकृत खाते द्वारा दर्ज की गई शिकायतों की वास्तविक समय स्थिति।' : (isMr ? 'आपल्या नोंदणीकृत खात्यावरून दाखल केलेल्या तक्रारींची थेट स्थिती.' : 'Real-time status updates for complaints submitted by your registered account.');
  }
}

function renderNav() {
  const nav = document.getElementById('main-nav');
  if (!nav) return;
  nav.innerHTML = '';
  if (userRole === 'citizen') {
    nav.innerHTML = `
      <button class="nav-pill ${activeView === 'citizen' ? 'active' : ''}" id="nav-citizen" onclick="switchView('citizen')">${t('navCitizen', 'Citizen Portal')}</button>
      <button class="nav-pill ${activeView === 'track' ? 'active' : ''}" id="nav-track" onclick="switchView('track')">${t('navTrackCitizen', 'Track My Complaints')}</button>
    `;
  } else if (userRole === 'admin') {
    nav.innerHTML = `
      <button class="nav-pill ${activeView === 'dashboard' ? 'active' : ''}" id="nav-dashboard" onclick="switchView('dashboard')">${t('navDashboard', 'Authority Dashboard')}</button>
      <button class="nav-pill ${activeView === 'track' ? 'active' : ''}" id="nav-track" onclick="switchView('track')">${t('navTrackAdmin', 'Track Complaints')}</button>
    `;
  }
}

function logoutUser() {
  currentUser = null;
  userRole = null;
  sessionStorage.removeItem('awazsetu_user');
  sessionStorage.removeItem('awazsetu_admin_dept');
  const deptSwitcher = document.getElementById('admin-dept-header-selector');
  if (deptSwitcher) deptSwitcher.style.display = 'none';
  document.getElementById('app-shell').style.display = 'none';
  document.getElementById('auth-screen').style.display = 'flex';
}

// ─── Enter App after Login ───
function enterApp() {
  document.getElementById('auth-screen').style.display = 'none';
  document.getElementById('app-shell').style.display = 'block';

  // Display user info
  const nameDisplay = document.getElementById('user-name-display');
  const roleTag = document.getElementById('user-role-tag');
  if (nameDisplay) nameDisplay.innerText = currentUser.full_name || currentUser.username || 'User';
  
  if (userRole === 'admin') {
    const userDept = (currentUser && currentUser.department) ? currentUser.department : (sessionStorage.getItem('awazsetu_admin_dept') || 'All');
    currentAdminDepartment = userDept;
    sessionStorage.setItem('awazsetu_admin_dept', currentAdminDepartment);

    if (roleTag) {
      const isHi = currentSiteLang === 'hi';
      const isMr = currentSiteLang === 'mr';
      if (currentAdminDepartment !== 'All') {
        const locDept = getLocalizedDeptName(currentAdminDepartment);
        roleTag.innerText = isHi ? `${locDept} अधिकारी` : (isMr ? `${locDept} अधिकारी` : `${currentAdminDepartment} Officer`);
      } else {
        roleTag.innerText = isHi ? 'केंद्रीय प्राधिकरण' : (isMr ? 'मध्यवर्ती प्राधिकरण' : 'Central Authority');
      }
      roleTag.className = 'role-tag role-admin';
    }

    const headerSel = document.getElementById('global-admin-dept-select');
    const dashSel = document.getElementById('filter-department');
    if (headerSel) headerSel.value = currentAdminDepartment;
    if (dashSel) dashSel.value = currentAdminDepartment;
  } else {
    if (roleTag) {
      roleTag.innerText = t('roleCitizen', 'Citizen');
      roleTag.className = 'role-tag role-citizen';
    }
  }

  // Show department switcher for admin
  const deptSwitcher = document.getElementById('admin-dept-header-selector');
  if (deptSwitcher) {
    deptSwitcher.style.display = userRole === 'admin' ? 'flex' : 'none';
  }

  updateDepartmentHeadings();

  // Build navigation based on role
  if (userRole === 'citizen') {
    activeView = 'citizen';
    renderNav();
    switchView('citizen');
  } else {
    activeView = 'dashboard';
    renderNav();
    switchView('dashboard');
  }

  loadAllGrievances();
}

// ═══════════════════════════════════════════════════════════════════════
// VIEW SWITCHER
// ═══════════════════════════════════════════════════════════════════════
function switchView(viewName) {
  activeView = viewName;
  document.querySelectorAll('.view-container').forEach(v => { v.classList.remove('active'); v.style.display = 'none'; });
  const target = document.getElementById(`view-${viewName}`);
  if (target) { target.style.display = 'block'; target.classList.add('active'); }
  document.querySelectorAll('.nav-pill').forEach(p => p.classList.remove('active'));
  const pill = document.getElementById(`nav-${viewName}`);
  if (pill) pill.classList.add('active');

  // Trigger map resize so tiles render properly when tab becomes visible
  if (viewName === 'citizen') {
    setTimeout(initCitizenMap, 80);
  } else if (viewName === 'dashboard') {
    setTimeout(initOrUpdateAdminMap, 80);
  } else if (viewName === 'track') {
    renderCitizenTickets();
  }
}

// ═══════════════════════════════════════════════════════════════════════
// LEAFLET MAPS: CITIZEN PINPOINT & AUTHORITY GIS
// ═══════════════════════════════════════════════════════════════════════

// 1. Citizen Map (interactive pin drop)
function initCitizenMap() {
  const container = document.getElementById('citizen-map');
  if (!container) return;

  if (!citizenMap) {
    citizenMap = L.map('citizen-map', { zoomControl: true }).setView([selectedLat, selectedLon], 13);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(citizenMap);

    // Draggable marker
    citizenMarker = L.marker([selectedLat, selectedLon], { draggable: true }).addTo(citizenMap);
    citizenMarker.bindPopup("<b>Incident Location</b><br>Drag pin or click map to move.").openPopup();

    citizenMarker.on('dragend', (e) => {
      const pos = e.target.getLatLng();
      updateSelectedLocation(pos.lat, pos.lng);
    });

    citizenMap.on('click', (e) => {
      citizenMarker.setLatLng(e.latlng);
      updateSelectedLocation(e.latlng.lat, e.latlng.lng);
    });
  } else {
    citizenMap.invalidateSize();
  }
}

function updateSelectedLocation(lat, lon) {
  selectedLat = lat;
  selectedLon = lon;
  const preview = document.getElementById('citizen-coords-preview');
  if (preview) {
    preview.innerText = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
  }
}

function requestBrowserGPS() {
  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your browser.");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      updateSelectedLocation(pos.coords.latitude, pos.coords.longitude);
      if (citizenMap && citizenMarker) {
        citizenMap.setView([pos.coords.latitude, pos.coords.longitude], 15);
        citizenMarker.setLatLng([pos.coords.latitude, pos.coords.longitude]);
        citizenMarker.bindPopup("<b>📍 GPS Location Locked</b>").openPopup();
      }
    },
    (err) => {
      alert("Unable to acquire GPS location. Please click on the map to place your pin.");
    },
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

// 2. Authority Map (Live complaints heatmap / marker cluster)
function initOrUpdateAdminMap() {
  const container = document.getElementById('admin-map');
  if (!container) return;

  if (!adminMap) {
    adminMap = L.map('admin-map', { zoomControl: true }).setView([19.0760, 72.8777], 11);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(adminMap);
    adminMarkersLayer = L.layerGroup().addTo(adminMap);
  }

  adminMap.invalidateSize();
  if (!adminMarkersLayer) return;

  adminMarkersLayer.clearLayers();

  const deptFilter = currentAdminDepartment || 'All';
  let filtered = grievancesData;
  if (deptFilter !== 'All') {
    filtered = filtered.filter(g => g.department === deptFilter);
  }

  const bounds = [];
  filtered.forEach(item => {
    if (!item.lat || !item.lon) return;
    const color = getPriorityColor(item.priority);
    const radius = item.priority === 'Critical' ? 10 : (item.priority === 'High' ? 8 : 6);

    const circle = L.circleMarker([item.lat, item.lon], {
      radius: radius,
      fillColor: color,
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85
    });

    const mapUrl = `https://www.google.com/maps/search/?api=1&query=${item.lat},${item.lon}`;
    const popupHtml = `
      <div style="font-family:sans-serif; min-width:180px;">
        <div style="font-size:0.75rem; font-weight:800; color:#2563eb; margin-bottom:2px;">#${item.id}</div>
        <strong style="font-size:0.85rem; color:#0f172a; display:block;">${escapeHtml(item.department)}</strong>
        <p style="font-size:0.75rem; color:#475569; margin:4px 0;">"${escapeHtml((item.text_en || item.original_text).substring(0, 70))}..."</p>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.72rem; margin-top:6px; border-top:1px solid #e2e8f0; padding-top:4px;">
          <span style="color:${color}; font-weight:800;">${item.priority} (${item.severity_score}/100)</span>
          <span style="font-weight:700; color:#334155;">${item.status}</span>
        </div>
        <div style="margin-top:6px; border-top:1px solid #e2e8f0; padding-top:6px; display:flex; justify-content:space-between; align-items:center; gap:6px;">
          <a href="${mapUrl}" target="_blank" rel="noopener noreferrer" style="font-size:0.72rem; color:#2563eb; font-weight:700; text-decoration:none;">📍 Maps ↗</a>
          <button onclick="openTicketModal('${item.id}')" style="background:#0f172a; color:#fff; border:none; padding:3px 8px; border-radius:4px; font-size:0.72rem; font-weight:700; cursor:pointer;">View Details</button>
        </div>
      </div>
    `;
    circle.bindPopup(popupHtml);
    circle.addTo(adminMarkersLayer);
    bounds.push([item.lat, item.lon]);
  });

  if (bounds.length > 0 && adminMap) {
    adminMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 });
  }
}

// ═══════════════════════════════════════════════════════════════════════
// FORM LOGIC & SUBMISSION
// ═══════════════════════════════════════════════════════════════════════
let selectedImageBase64 = null;

function selectCategoryCard(cardEl, catValue) {
  document.querySelectorAll('.cat-card').forEach(c => c.classList.remove('active'));
  cardEl.classList.add('active');
  const sel = document.getElementById('category');
  if (sel) sel.value = catValue;
}

function onPhotoSelected(e) {
  const file = e.target.files[0];
  const label = document.getElementById('file-name-preview');
  if (!file) {
    selectedImageBase64 = null;
    if (label) label.innerHTML = '';
    return;
  }
  const reader = new FileReader();
  reader.onload = function(evt) {
    selectedImageBase64 = evt.target.result;
    if (label) {
      label.innerHTML = `
        <div style="margin-top:8px; display:flex; align-items:center; gap:10px; background:#f8fafc; padding:8px 12px; border-radius:8px; border:1px solid #cbd5e1;">
          <img src="${selectedImageBase64}" style="width:44px; height:44px; object-fit:cover; border-radius:6px; border:1px solid #94a3b8;" alt="Preview" />
          <div style="flex:1;">
            <span style="font-weight:700; color:#0f172a; font-size:0.78rem; display:block;">✓ ${escapeHtml(file.name)}</span>
            <span style="color:#64748b; font-size:0.7rem;">${(file.size / 1024).toFixed(1)} KB (Attached to report)</span>
          </div>
          <button type="button" onclick="clearPhotoSelection()" style="background:transparent; border:none; color:#ef4444; font-weight:800; font-size:0.9rem; cursor:pointer;" title="Remove photo">✕</button>
        </div>
      `;
    }
  };
  reader.readAsDataURL(file);
}

function clearPhotoSelection() {
  selectedImageBase64 = null;
  const input = document.getElementById('photo-upload');
  if (input) input.value = '';
  const label = document.getElementById('file-name-preview');
  if (label) label.innerHTML = '';
}

async function submitGrievance() {
  const desc = (document.getElementById('description').value || '').trim();
  const cat = document.getElementById('category') ? document.getElementById('category').value : 'Auto-Detect';
  const locInput = document.getElementById('incident-location-text');
  const locText = locInput ? locInput.value.trim() : '';

  if (!desc) { alert("Please describe the issue."); return; }

  const btn = document.getElementById('btn-submit-complaint');
  const btnText = document.getElementById('txt-submit-btn');
  if (btn) btn.disabled = true;
  if (btnText) btnText.innerText = "Processing...";

  let finalLat = selectedLat;
  let finalLon = selectedLon;
  let finalWard = locText || selectedPlaceName || '';

  // If user typed a location but didn't pick from autocomplete, and coordinates are still default Kurla, geocode it
  if (locText && (Math.abs(selectedLat - 19.0760) < 0.0001 && Math.abs(selectedLon - 72.8777) < 0.0001)) {
    try {
      const geoRes = await fetch(`${API_BASE}/api/geocode?q=${encodeURIComponent(locText)}`);
      const geoData = await geoRes.json();
      if (geoData.results && geoData.results.length > 0) {
        finalLat = geoData.results[0].lat;
        finalLon = geoData.results[0].lon;
        updateSelectedLocation(finalLat, finalLon);
      }
    } catch (e) {
      console.warn("Geocoding lookup error:", e);
    }
  }

  // Combine location text with description if provided
  const fullText = locText ? `${desc} (Location: ${locText})` : desc;
  const citizenName = currentUser ? (currentUser.full_name || currentUser.username) : 'Citizen';
  const citizenPhone = currentUser ? (currentUser.username || '') : '';

  const payload = {
    original_text: fullText,
    category_hint: cat,
    lat: finalLat,
    lon: finalLon,
    ward: finalWard || undefined,
    location_name: finalWard || undefined,
    citizen_name: citizenName,
    citizen_phone: citizenPhone,
    image_data: selectedImageBase64 || ""
  };

  try {
    const res = await fetch(`${API_BASE}/api/grievance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (btn) btn.disabled = false;
    if (btnText) btnText.innerText = "Submit Grievance";

    if (result.success && result.data) {
      document.getElementById('description').value = '';
      document.getElementById('char-count').innerText = '0/500 chars';
      if (document.getElementById('incident-location-text')) document.getElementById('incident-location-text').value = '';
      selectedPlaceName = '';
      clearPhotoSelection();

      // Record ticket ID to current citizen's personal storage
      if (currentUser && currentUser.username) {
        const storedKey = 'my_tickets_' + currentUser.username;
        const stored = JSON.parse(localStorage.getItem(storedKey) || '[]');
        if (!stored.includes(result.data.id)) {
          stored.push(result.data.id);
          localStorage.setItem(storedKey, JSON.stringify(stored));
        }
      }

      // Live result summary in sidebar
      const preview = document.getElementById('live-ai-preview');
      if (preview) {
        preview.style.display = 'block';
        preview.innerHTML = `
          <div style="font-weight:700; color:#0f172a; margin-bottom:4px;">✓ Ticket #${result.data.id} Created</div>
          <div>Department: <strong>${result.data.department}</strong></div>
          <div>Priority: <strong style="color:${getPriorityColor(result.data.priority)}">${result.data.priority}</strong> (${result.data.severity_score}/100)</div>
          <div>Status: <strong>${result.data.status}</strong></div>
        `;
      }

      // Duplicate alert
      const dup = document.getElementById('duplicate-result-banner');
      if (result.data.is_duplicate === 1 && result.data.parent_id) {
        if (dup) {
          dup.style.display = 'flex';
          document.getElementById('dup-banner-text').innerText = `Your report matched existing ticket #${result.data.parent_id} within 400m and has been merged to speed up resolution.`;
        }
      } else {
        if (dup) dup.style.display = 'none';
      }

      await loadAllGrievances();
    } else {
      alert(result.error || 'Submission error.');
    }
  } catch (e) {
    if (btn) btn.disabled = false;
    if (btnText) btnText.innerText = "Submit Grievance";
    alert(`Server error: ${e.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════════════
// FETCH & RENDER GRIEVANCES (Strictly Personal for Citizens)
// ═══════════════════════════════════════════════════════════════════════
let myUpvotedTicketIds = new Set();

function getCitizenIdentifier() {
  if (!currentUser) return '';
  return currentUser.username || currentUser.phone || currentUser.id || '';
}

async function syncUserUpvotes() {
  const ident = getCitizenIdentifier();
  if (!ident || userRole !== 'citizen') {
    myUpvotedTicketIds = new Set();
    return;
  }
  const localList = JSON.parse(localStorage.getItem('upvoted_' + ident) || '[]');
  localList.forEach(id => myUpvotedTicketIds.add(id));

  try {
    const res = await fetch(`${API_BASE}/api/my_upvotes?user_id=${encodeURIComponent(ident)}`);
    const data = await res.json();
    if (data.upvoted_tickets && Array.isArray(data.upvoted_tickets)) {
      data.upvoted_tickets.forEach(id => myUpvotedTicketIds.add(id));
      localStorage.setItem('upvoted_' + ident, JSON.stringify(Array.from(myUpvotedTicketIds)));
    }
  } catch (e) {
    console.warn("Could not sync upvotes:", e);
  }
}

function renderUpvoteButtonHtml(item) {
  const upvoteCount = item.upvotes || 0;
  if (userRole === 'admin') {
    return `
      <div class="btn-upvote-chip" style="background:#f1f5f9; border-color:#cbd5e1; color:#475569; cursor:default;" title="${t('upvoteEndorsements', '👍 Endorsements')}">
        <span>${t('upvoteEndorsements', '👍 Endorsements')}</span>
        <strong>(${upvoteCount})</strong>
      </div>
    `;
  }

  const isUpvoted = myUpvotedTicketIds.has(item.id);
  if (isUpvoted) {
    return `
      <button type="button" class="btn-upvote-chip upvoted" disabled style="background:#ecfdf5; border-color:#6ee7b7; color:#065f46; cursor:default; opacity:0.95;" title="${t('upvoteSupported', '✓ Supported (+1)')}">
        <span>${t('upvoteSupported', '✓ Supported (+1)')}</span>
        <strong>(${upvoteCount})</strong>
      </button>
    `;
  }

  return `
    <button type="button" class="btn-upvote-chip" onclick="upvoteTicket('${item.id}', event)" title="${t('upvoteAffectsMe', '👍 Affects Me Too')}">
      <span>${t('upvoteAffectsMe', '👍 Affects Me Too')}</span>
      <strong>(${upvoteCount})</strong>
    </button>
  `;
}

async function loadAllGrievances() {
  try {
    const res = await fetch(`${API_BASE}/api/grievances`);
    const data = await res.json();
    grievancesData = data.records || [];
    await syncUserUpvotes();
    renderCitizenTickets();
    renderAuthorityDashboard();
  } catch (e) { console.error("Error loading grievances:", e); }
}

function renderCitizenTickets() {
  const container = document.getElementById('citizen-tickets-container');
  if (!container) return;

  let display = [];

  if (userRole === 'citizen') {
    const myPhone = currentUser ? (currentUser.username || '') : '';
    const storedKey = 'my_tickets_' + myPhone;
    const myStoredIds = JSON.parse(localStorage.getItem(storedKey) || '[]');

    // Strictly filter to ONLY complaints requested by THIS citizen
    display = grievancesData.filter(g => {
      if (myPhone && g.citizen_phone === myPhone) return true;
      if (myStoredIds.includes(g.id)) return true;
      return false;
    });

    if (display.length === 0) {
      container.innerHTML = `
        <div style="background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:48px 24px; text-align:center;">
          <div style="font-size:2.2rem; margin-bottom:12px;">📑</div>
          <h4 style="font-size:1.15rem; font-weight:800; color:#0f172a; margin-bottom:6px;">${t('noComplaintsFiled', 'No Complaints Filed Yet')}</h4>
          <p style="color:#64748b; font-size:0.88rem; max-width:440px; margin:0 auto 20px; line-height:1.5;">
            ${t('noComplaintsDesc', 'You can only track complaints that were filed from your registered account (+91 {phone}). Use the Citizen Portal to submit an issue and track its resolution progress here.').replace('{phone}', myPhone)}
          </p>
          <button type="button" class="btn-primary-submit" style="display:inline-flex; align-items:center; gap:6px; padding:10px 22px; font-size:0.88rem; margin:0 auto;" onclick="switchView('citizen')">
            <span>${t('btnReportIssue', 'Report a Civic Issue')}</span>
            <span>→</span>
          </button>
        </div>
      `;
      return;
    }
  } else {
    // Authority / Admin: filter by currentAdminDepartment
    if (currentAdminDepartment && currentAdminDepartment !== 'All') {
      display = grievancesData.filter(g => g.department === currentAdminDepartment);
      if (display.length === 0) {
        const localizedDept = getLocalizedDeptName(currentAdminDepartment);
        container.innerHTML = `
          <div style="background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:48px 24px; text-align:center;">
            <div style="font-size:2.2rem; margin-bottom:10px;">📂</div>
            <h4 style="font-size:1.15rem; font-weight:800; color:#0f172a; margin-bottom:6px;">${t('noComplaintsDept', 'No Complaints in {dept}').replace('{dept}', escapeHtml(localizedDept))}</h4>
            <p style="color:#64748b; font-size:0.85rem; max-width:420px; margin:0 auto 16px;">${t('noComplaintsDeptDesc', 'There are currently no open or pending complaints assigned to {dept}.').replace('{dept}', escapeHtml(localizedDept))}</p>
          </div>`;
        return;
      }
    } else {
      display = grievancesData;
      if (display.length === 0) {
        container.innerHTML = `<div style="background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:32px; text-align:center; color:#64748b;">${t('noComplaintsSystem', 'No complaints in the system.')}</div>`;
        return;
      }
    }
  }

  container.innerHTML = display.map(item => {
    const isWaiting = item.status === 'Waiting for Citizen Confirmation' || item.status === 'Awaiting Citizen Confirmation';
    const sClass = isWaiting ? 'waiting' : (item.status === 'Resolved' ? 'resolved' : (item.status === 'In Progress' ? 'progress' : (item.status === 'Reopened' ? 'breached' : 'pending')));
    const color = getPriorityColor(item.priority);
    const dup = item.is_duplicate === 1 ? ` <span style="color:#d97706;font-size:0.75rem;font-weight:700;">[Merged #${item.parent_id}]</span>` : '';
    const hasPhoto = (item.image_data || item.image_flag === 1) ? ` <span style="background:#eff6ff;color:#2563eb;font-size:0.7rem;font-weight:750;padding:2px 6px;border-radius:4px;border:1px solid #bfdbfe;">📷 ${currentSiteLang === 'hi' ? 'फोटो' : (currentSiteLang === 'mr' ? 'फोटो' : 'Photo')}</span>` : '';
    const hasProof = item.resolution_photo ? ` <span style="background:#ecfdf5;color:#059669;font-size:0.7rem;font-weight:750;padding:2px 6px;border-radius:4px;border:1px solid #a7f3d0;">✓ ${currentSiteLang === 'hi' ? 'फोटो प्रमाण' : (currentSiteLang === 'mr' ? 'फोटो पुरावा' : 'Photo Proof')}</span>` : '';
    const slaBadge = getSlaBadgeHtml(item.created_at, item.priority, item.status);
    const mapUrl = `https://www.google.com/maps/search/?api=1&query=${item.lat},${item.lon}`;
    return `
      <div class="ticket-row-card" onclick="openTicketModal('${item.id}')" style="cursor:pointer;">
        <div class="ticket-header-line">
          <div>
            <span class="ticket-id-tag font-mono">#${item.id}</span> · 
            <span class="ticket-dept-badge">${getLocalizedDeptName(item.department)}</span>${dup}${hasPhoto}${hasProof} · 
            <a href="${mapUrl}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" style="color:#2563eb; font-weight:700; font-size:0.76rem; text-decoration:none; display:inline-flex; align-items:center; gap:2px;" title="Open in Google Maps">
              📍 ${escapeHtml(item.ward || 'Municipal Zone')} ↗
            </a>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            ${slaBadge}
            <span class="status-badge ${sClass}">${getLocalizedStatus(item.status)}</span>
            <span style="color:${color};font-weight:800;font-size:0.75rem;border:1px solid ${color};padding:2px 8px;border-radius:9999px;">${item.priority} (${item.severity_score}/100)</span>
          </div>
        </div>
        <div class="ticket-body-text">"${escapeHtml(item.original_text)}"</div>
        <div class="ticket-footer-line">
          <span>${t('reportedAgo', 'Reported')}: ${item.created_at ? item.created_at.substring(0,16).replace('T',' ') : 'Recently'}</span>
          <div style="display:flex; gap:8px; align-items:center;">
            ${renderUpvoteButtonHtml(item)}
          </div>
        </div>
      </div>`;
  }).join('');
}

function renderAuthorityDashboard() {
  const deptFilter = currentAdminDepartment || 'All';
  let deptGrievances = grievancesData;
  if (deptFilter !== 'All') {
    deptGrievances = grievancesData.filter(g => g.department === deptFilter);
  }

  const total = deptGrievances.length;
  const pending = deptGrievances.filter(g => g.status === 'Pending' || g.status === 'Reopened').length;
  const high = deptGrievances.filter(g => (g.priority === 'Critical' || g.priority === 'High') && g.status !== 'Resolved').length;
  const resolved = deptGrievances.filter(g => g.status === 'Resolved').length;
  const dups = deptGrievances.filter(g => g.is_duplicate === 1).length;
  const upvotes = deptGrievances.reduce((a, g) => a + (g.upvotes || 0), 0);

  const el = id => document.getElementById(id);
  if (el('kpi-total-val')) el('kpi-total-val').innerText = total;
  if (el('kpi-pending-val')) el('kpi-pending-val').innerText = pending;
  if (el('kpi-high-val')) el('kpi-high-val').innerText = high;
  if (el('kpi-resolved-val')) el('kpi-resolved-val').innerText = resolved;
  if (el('kpi-res-rate')) {
    const rate = total > 0 ? Math.round((resolved / total) * 100) : 0;
    el('kpi-res-rate').innerText = `${rate}% closed`;
  }

  if (el('analytics-dup-reduction')) {
    const pct = total > 0 ? Math.round((dups / total) * 100) : 0;
    el('analytics-dup-reduction').innerText = `${pct}%`;
  }
  if (el('analytics-upvote-count')) el('analytics-upvote-count').innerText = upvotes;

  // Priority Queue
  const qc = document.getElementById('admin-queue-list');
  if (qc) {
    let filtered = deptGrievances.filter(g => g.status !== 'Resolved');
    const top = filtered.sort((a,b) => b.severity_score - a.severity_score).slice(0, 8);
    if (top.length === 0) {
      qc.innerHTML = `<div style="padding:24px;text-align:center;color:#64748b;">No open complaints ${deptFilter !== 'All' ? 'in ' + escapeHtml(getLocalizedDeptName(deptFilter)) : 'across departments'}.</div>`;
    } else {
      qc.innerHTML = top.map(item => {
        const pClass = item.priority.toLowerCase();
        const isWaiting = item.status === 'Waiting for Citizen Confirmation' || item.status === 'Awaiting Citizen Confirmation';
        const sClass = isWaiting ? 'waiting' : (item.status === 'In Progress' ? 'progress' : (item.status === 'Reopened' ? 'breached' : 'pending'));
        const hasPhoto = (item.image_data || item.image_flag === 1) ? ` <span style="background:#eff6ff;color:#2563eb;font-size:0.65rem;font-weight:750;padding:1px 4px;border-radius:3px;border:1px solid #bfdbfe;">📷 Photo</span>` : '';
        const slaBadge = getSlaBadgeHtml(item.created_at, item.priority, item.status);
        return `
          <div class="queue-item" onclick="openTicketModal('${item.id}')">
            <div class="queue-priority ${pClass}">${item.priority}</div>
            <div class="queue-copy">
              <strong>${getLocalizedDeptName(item.department)} (${item.ward || 'Area'})${hasPhoto}</strong>
              <span>#${item.id} · "${escapeHtml((item.text_en||item.original_text).substring(0,38))}..."</span>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:3px;">
              ${slaBadge}
              <span class="status-badge ${sClass}">${getLocalizedStatus(item.status)}</span>
            </div>
          </div>`;
      }).join('');
    }
  }

  initOrUpdateAdminMap();
}

function applyAdminFilters() {
  const dashSel = document.getElementById('filter-department');
  if (dashSel) switchAdminDepartment(dashSel.value);
}

// ═══════════════════════════════════════════════════════════════════════
// SLA ENGINE
// ═══════════════════════════════════════════════════════════════════════
function getSlaHoursLimit(priority) {
  if (priority === 'Critical') return 24;
  if (priority === 'High') return 48;
  if (priority === 'Medium') return 72;
  return 120; // Low
}

function getSlaBadgeHtml(createdAt, priority, status) {
  if (status === 'Resolved') {
    const txt = currentSiteLang === 'hi' ? '✓ समय सीमा में हल' : (currentSiteLang === 'mr' ? '✓ वेळेत निवारण' : '✓ Met SLA Target');
    return `<span class="sla-timer-badge sla-badge-resolved">${txt}</span>`;
  }
  if (status === 'Waiting for Citizen Confirmation' || status === 'Awaiting Citizen Confirmation') {
    const txt = currentSiteLang === 'hi' ? '✓ कार्य पूर्ण (पुष्टि प्रतीक्षारत)' : (currentSiteLang === 'mr' ? '✓ काम पूर्ण (पुष्टी प्रतीक्षेत)' : '✓ Work Complete (Pending Verification)');
    return `<span class="sla-timer-badge sla-badge-resolved">${txt}</span>`;
  }
  if (!createdAt) {
    return `<span class="sla-timer-badge sla-badge-safe">${t('slaActive', '⏱️ SLA Active')}</span>`;
  }

  const createdTime = new Date(createdAt).getTime();
  const now = Date.now();
  const limitHours = getSlaHoursLimit(priority);
  const deadlineMs = createdTime + (limitHours * 3600 * 1000);
  const remainingMs = deadlineMs - now;

  if (remainingMs <= 0) {
    const breachHrs = Math.max(1, Math.round(Math.abs(remainingMs) / 3600000));
    const txt = currentSiteLang === 'hi' ? `🚨 सीमा पार (${breachHrs} घंटे)` : (currentSiteLang === 'mr' ? `🚨 मुदत ओलांडली (${breachHrs} तास)` : `🚨 Breached by ${breachHrs}h (Escalated)`);
    return `<span class="sla-timer-badge sla-badge-breached">${txt}</span>`;
  } else if (remainingMs < 12 * 3600 * 1000) {
    const remHrs = Math.max(1, Math.round(remainingMs / 3600000));
    const txt = currentSiteLang === 'hi' ? `⚠️ ${remHrs} घंटे शेष (अति-आवश्यक)` : (currentSiteLang === 'mr' ? `⚠️ ${remHrs} तास शिल्लक (तातडीचे)` : `⚠️ ${remHrs}h left (Urgent)`);
    return `<span class="sla-timer-badge sla-badge-warning">${txt}</span>`;
  } else {
    const remHrs = Math.round(remainingMs / 3600000);
    const txt = currentSiteLang === 'hi' ? `⏱️ ${remHrs} घंटे शेष` : (currentSiteLang === 'mr' ? `⏱️ ${remHrs} तास शिल्लक` : `⏱️ ${remHrs}h remaining`);
    return `<span class="sla-timer-badge sla-badge-safe">${txt}</span>`;
  }
}

// ═══════════════════════════════════════════════════════════════════════
// PROGRESS STEPPER TIMELINE
// ═══════════════════════════════════════════════════════════════════════
function renderProgressStepperHtml(status, citizenFeedback) {
  const isAwaitingConfirmation = status === 'Waiting for Citizen Confirmation' || status === 'Awaiting Citizen Confirmation';
  const isResolved = status === 'Resolved';
  const isReopened = status === 'Reopened' || citizenFeedback === 'Reopened';
  const isInProgress = status === 'In Progress' || isAwaitingConfirmation || isResolved;

  const s1Class = "stepper-step completed";
  const s2Class = "stepper-step completed";
  const s3Class = "stepper-step completed";
  const s4Class = isInProgress ? (isAwaitingConfirmation || isResolved ? "stepper-step completed" : "stepper-step active") : "stepper-step";
  let s5Class = "stepper-step";
  if (isResolved) {
    s5Class = "stepper-step completed";
  } else if (isAwaitingConfirmation) {
    s5Class = "stepper-step active";
  } else if (isReopened) {
    s5Class = "stepper-step reopened";
  }

  const fillWidth = isResolved ? "100%" : (isAwaitingConfirmation ? "90%" : (status === 'In Progress' ? "75%" : "50%"));

  const timelineHeading = currentSiteLang === 'hi' ? 'प्रगति समयरेखा' : (currentSiteLang === 'mr' ? 'प्रगती टाइमलाइन' : 'Lifecycle Stepper Timeline');
  const lblReported = currentSiteLang === 'hi' ? 'दर्ज' : (currentSiteLang === 'mr' ? 'दाखल' : 'Reported');
  const lblRouted = currentSiteLang === 'hi' ? 'विभाग तय' : (currentSiteLang === 'mr' ? 'विभागणी' : 'AI Routed');
  const lblAssigned = currentSiteLang === 'hi' ? 'आवंटित' : (currentSiteLang === 'mr' ? 'नियुक्त' : 'Assigned');
  const lblCrew = currentSiteLang === 'hi' ? 'फील्ड टीम' : (currentSiteLang === 'mr' ? 'फील्ड पथक' : 'Field Crew');
  const lblResolved = isReopened 
    ? (currentSiteLang === 'hi' ? 'पुनः खोला' : (currentSiteLang === 'mr' ? 'पुन्हा उघडले' : 'Reopened'))
    : (isAwaitingConfirmation 
        ? (currentSiteLang === 'hi' ? 'नागरिक पुष्टि' : (currentSiteLang === 'mr' ? 'नागरिक पुष्टी' : 'Confirmation'))
        : (currentSiteLang === 'hi' ? 'समाधान' : (currentSiteLang === 'mr' ? 'निवारण' : 'Resolved')));

  return `
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 6px 14px; margin-bottom:12px;">
      <div style="font-size:0.72rem; font-weight:800; color:#475569; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px; padding-left:10px;">
        ${timelineHeading}
      </div>
      <div class="stepper-container">
        <div class="stepper-progress-fill" style="width:${fillWidth};"></div>
        <div class="${s1Class}">
          <div class="stepper-circle">✓</div>
          <span class="stepper-label">${lblReported}</span>
        </div>
        <div class="${s2Class}">
          <div class="stepper-circle">✓</div>
          <span class="stepper-label">${lblRouted}</span>
        </div>
        <div class="${s3Class}">
          <div class="stepper-circle">✓</div>
          <span class="stepper-label">${lblAssigned}</span>
        </div>
        <div class="${s4Class}">
          <div class="stepper-circle">${isInProgress ? (isAwaitingConfirmation || isResolved ? '✓' : '●') : '4'}</div>
          <span class="stepper-label">${lblCrew}</span>
        </div>
        <div class="${s5Class}">
          <div class="stepper-circle">${isResolved ? '✓' : (isAwaitingConfirmation ? '⏳' : (isReopened ? '!' : '5'))}</div>
          <span class="stepper-label">${lblResolved}</span>
        </div>
      </div>
    </div>
  `;
}


// ═══════════════════════════════════════════════════════════════════════
// "+1 AFFECTS ME TOO" UPVOTE ACTION (Strict Single-Vote for Citizens Only)
// ═══════════════════════════════════════════════════════════════════════
async function upvoteTicket(ticketId, event) {
  if (event) event.stopPropagation();

  if (userRole === 'admin') {
    alert("Authority Action Restricted: Municipal officers and administrators cannot upvote civic complaints.");
    return;
  }

  const ident = getCitizenIdentifier();
  if (!ident) {
    alert("Please log in as a citizen to support this grievance.");
    return;
  }

  if (myUpvotedTicketIds.has(ticketId)) {
    alert("You have already registered your support for this issue (+1).");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/upvote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: ticketId,
        role: 'citizen',
        user_id: ident
      })
    });
    const result = await res.json();
    if (result.success) {
      myUpvotedTicketIds.add(ticketId);
      localStorage.setItem('upvoted_' + ident, JSON.stringify(Array.from(myUpvotedTicketIds)));

      const item = grievancesData.find(g => g.id === ticketId);
      if (item) {
        item.upvotes = result.upvotes;
        item.severity_score = result.severity_score;
        item.priority = result.priority;
      }
      renderCitizenTickets();
      renderAuthorityDashboard();
      if (document.getElementById('ticket-modal').style.display !== 'none') {
        openTicketModal(ticketId);
      }
    } else {
      if (result.error && result.error.includes("already")) {
        myUpvotedTicketIds.add(ticketId);
        localStorage.setItem('upvoted_' + ident, JSON.stringify(Array.from(myUpvotedTicketIds)));
        renderCitizenTickets();
      }
      alert(result.error || "Unable to register upvote.");
    }
  } catch (err) {
    console.error("Upvote error:", err);
  }
}

// ═══════════════════════════════════════════════════════════════════════
// ADMIN RESOLUTION WITH MANDATORY PHOTO PROOF
// ═══════════════════════════════════════════════════════════════════════
let adminResolutionPhotoBase64 = "";

function onAdminResolutionPhotoSelected(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (evt) => {
    adminResolutionPhotoBase64 = evt.target.result;
    const preview = document.getElementById('admin-res-photo-preview');
    if (preview) {
      preview.src = adminResolutionPhotoBase64;
      preview.style.display = 'block';
    }
    const label = document.getElementById('admin-res-photo-label');
    if (label) label.innerText = `✓ ${file.name} attached (${(file.size/1024).toFixed(0)} KB)`;
  };
  reader.readAsDataURL(file);
}

async function resolveTicketWithProof(ticketId) {
  if (!adminResolutionPhotoBase64) {
    alert("⚠️ Mandatory Photographic Evidence:\nYou must capture or upload an 'After' completion photo showing the resolved site before submitting this complaint for citizen confirmation.");
    const photoInput = document.getElementById('admin-res-photo-input');
    if (photoInput) {
      photoInput.style.outline = "2px solid #ef4444";
      photoInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
      photoInput.focus();
    }
    return;
  }

  const noteInput = document.getElementById('admin-res-note-input');
  const note = noteInput ? noteInput.value.trim() : '';

  try {
    const res = await fetch(`${API_BASE}/api/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: ticketId,
        status: 'Waiting for Citizen Confirmation',
        resolution_photo: adminResolutionPhotoBase64,
        resolution_note: note || 'Field repair completed with photographic evidence by municipal operations crew. Awaiting citizen confirmation.'
      })
    });
    const result = await res.json();
    if (result.success) {
      adminResolutionPhotoBase64 = "";
      closeModal();
      await loadAllGrievances();
    } else {
      alert(result.error || "Failed to submit resolution for confirmation.");
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════════════
// CITIZEN FEEDBACK & REOPEN ACTION (Deletes ticket upon citizen confirmation)
// ═══════════════════════════════════════════════════════════════════════
async function submitCitizenFeedback(ticketId, feedbackType) {
  let remarks = "";
  if (feedbackType === 'Reopened') {
    const promptMsg = currentSiteLang === 'hi' 
      ? "कृपया बताएं कि ज़मीनी स्तर पर समस्या का समाधान ठीक से क्यों नहीं हुआ:"
      : (currentSiteLang === 'mr' 
          ? "कृपया सांगा की प्रत्यक्ष जमिनीवर समस्येचे निवारण योग्यरीत्या का झाले नाही:" 
          : "Please provide a reason why the issue was not resolved properly on the ground:");
    remarks = prompt(promptMsg, "Pothole still present / work was incomplete.");
    if (remarks === null) return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: ticketId,
        feedback: feedbackType,
        remarks: remarks || (feedbackType === 'Satisfied' ? 'Confirmed resolved by citizen.' : '')
      })
    });
    const result = await res.json();
    if (result.success) {
      if (result.deleted || feedbackType === 'Satisfied') {
        // Ticket confirmed resolved by citizen: delete from local active cache and view
        grievancesData = grievancesData.filter(g => g.id !== ticketId && g.parent_id !== ticketId);
        closeModal();
        renderCitizenTickets();
        renderAuthorityDashboard();
        const noticeTemplate = t('ticketDeletedNotice', '✓ Resolution confirmed! Ticket #{id} has been verified and permanently removed from active complaints.');
        alert(noticeTemplate.replace('{id}', ticketId));
      } else {
        closeModal();
      }
      await loadAllGrievances();
    } else {
      alert(result.error || "Failed to submit feedback.");
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════════════
// ROBUST VOICE DICTATION ENGINE (Multi-Language + Continuous Pause Recovery)
// ═══════════════════════════════════════════════════════════════════════
let speechRecognitionInstance = null;
let isRecordingVoice = false;
let shouldKeepListening = false;
let activeDictationLang = 'en-IN';
let accumulatedTranscript = '';
let restartTimer = null;
let baseTextBeforeSpeech = '';

function setDictationLanguage(lang) {
  activeDictationLang = lang;
  document.querySelectorAll('.btn-lang-chip').forEach(c => {
    c.classList.toggle('active', c.getAttribute('data-lang') === lang);
  });
  if (isRecordingVoice) {
    const statusText = document.getElementById('voice-status-text');
    if (statusText) statusText.innerText = `Switched language to ${lang === 'hi-IN' ? 'हिन्दी' : (lang === 'mr-IN' ? 'मराठी' : 'English')}...`;
    restartRecognition();
  }
}

async function toggleVoiceDictation() {
  if (isRecordingVoice) {
    stopVoiceDictation();
  } else {
    await startVoiceDictation();
  }
}

async function startVoiceDictation() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Voice recognition is not supported on this browser. Please use Google Chrome, Microsoft Edge, or a WebSpeech-enabled browser.");
    return;
  }

  // Explicitly prompt / check microphone permission first to avoid instant audio aborts
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(t => t.stop());
    }
  } catch (err) {
    console.warn("Microphone permission check:", err);
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      alert("🎙️ Microphone Access Blocked:\nPlease click the tune/lock icon on the left of your browser address bar (next to the URL) and set Microphone to 'Allow'.");
      return;
    }
  }

  shouldKeepListening = true;
  isRecordingVoice = true;

  const desc = document.getElementById('description');
  baseTextBeforeSpeech = desc ? desc.value.trim() : '';
  if (baseTextBeforeSpeech) baseTextBeforeSpeech += ' ';
  accumulatedTranscript = '';

  const btn = document.getElementById('btn-voice-dictation');
  const btnText = document.getElementById('voice-btn-text');
  const statusBar = document.getElementById('voice-status-indicator');
  const statusText = document.getElementById('voice-status-text');

  if (btn) btn.classList.add('recording');
  if (btnText) btnText.innerText = "Stop Listening";
  if (statusBar) statusBar.style.display = 'flex';
  if (statusText) statusText.innerText = `Listening (${activeDictationLang === 'hi-IN' ? 'हिंदी' : (activeDictationLang === 'mr-IN' ? 'मराठी' : 'English')})... Speak now`;

  initSpeechRecognition();
}

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  if (speechRecognitionInstance) {
    try { speechRecognitionInstance.abort(); } catch(e) {}
    speechRecognitionInstance = null;
  }

  try {
    speechRecognitionInstance = new SpeechRecognition();
    speechRecognitionInstance.continuous = true;
    speechRecognitionInstance.interimResults = true;
    speechRecognitionInstance.lang = activeDictationLang;
    speechRecognitionInstance.maxAlternatives = 1;

    const desc = document.getElementById('description');

    speechRecognitionInstance.onresult = (event) => {
      let interim = '';
      let newlyFinal = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          newlyFinal += text + ' ';
        } else {
          interim += text;
        }
      }

      if (newlyFinal) {
        accumulatedTranscript += newlyFinal;
      }

      if (desc) {
        desc.value = (baseTextBeforeSpeech + accumulatedTranscript + interim).trimStart();
        updateCharCount();
      }

      const statusText = document.getElementById('voice-status-text');
      if (statusText && (interim || newlyFinal)) {
        const snippet = (interim || newlyFinal).trim();
        statusText.innerText = `Heard: "${snippet.length > 40 ? snippet.substring(0, 40) + '...' : snippet}"`;
      }
    };

    speechRecognitionInstance.onerror = (event) => {
      console.warn("Speech recognition notice:", event.error);
      const statusText = document.getElementById('voice-status-text');

      if (event.error === 'no-speech') {
        // Normal momentary silence/pause: keep listening, do NOT shut down!
        if (statusText) statusText.innerText = "Listening... Speak clearly into microphone";
        return;
      }

      if (event.error === 'not-allowed') {
        shouldKeepListening = false;
        alert("🎙️ Microphone Permission Blocked:\nPlease click the lock or tune icon in the address bar and allow microphone permissions.");
        stopVoiceDictation();
        return;
      }

      if (event.error === 'network') {
        shouldKeepListening = false;
        alert("⚠️ Cloud Speech Service Error:\nChrome's speech engine requires internet access to connect to Google Speech servers. Please check your network connection.");
        stopVoiceDictation();
        return;
      }

      if (event.error === 'audio-capture') {
        shouldKeepListening = false;
        alert("🎙️ No Microphone Detected:\nPlease check your sound input devices in Windows settings.");
        stopVoiceDictation();
        return;
      }
    };

    speechRecognitionInstance.onend = () => {
      // Automatic Pause Recovery: Chrome WebSpeech naturally stops after pauses; restart automatically while active!
      if (shouldKeepListening && isRecordingVoice) {
        clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {
          if (shouldKeepListening && isRecordingVoice) {
            try {
              speechRecognitionInstance.start();
            } catch (e) {
              initSpeechRecognition();
            }
          }
        }, 150);
      }
    };

    speechRecognitionInstance.start();
  } catch (err) {
    console.error("Speech start failure:", err);
    if (shouldKeepListening) {
      clearTimeout(restartTimer);
      restartTimer = setTimeout(() => {
        if (shouldKeepListening && isRecordingVoice) initSpeechRecognition();
      }, 300);
    }
  }
}

function restartRecognition() {
  if (speechRecognitionInstance) {
    try { speechRecognitionInstance.abort(); } catch(e) {}
    speechRecognitionInstance = null;
  }
  if (shouldKeepListening && isRecordingVoice) {
    initSpeechRecognition();
  }
}

function stopVoiceDictation() {
  shouldKeepListening = false;
  isRecordingVoice = false;
  clearTimeout(restartTimer);

  if (speechRecognitionInstance) {
    try { speechRecognitionInstance.stop(); } catch(e) {}
    speechRecognitionInstance = null;
  }

  const btn = document.getElementById('btn-voice-dictation');
  const btnText = document.getElementById('voice-btn-text');
  const statusBar = document.getElementById('voice-status-indicator');
  const statusText = document.getElementById('voice-status-text');

  if (btn) btn.classList.remove('recording');
  if (btnText) btnText.innerText = "Voice Dictate";
  if (statusBar) statusBar.style.display = 'none';
  if (statusText) statusText.innerText = "Listening...";
}

// ═══════════════════════════════════════════════════════════════════════
// TICKET DETAILS MODAL
// ═══════════════════════════════════════════════════════════════════════
function openTicketModal(ticketId) {
  currentModalTicketId = ticketId;
  adminResolutionPhotoBase64 = "";
  const item = grievancesData.find(g => g.id === ticketId);
  if (!item) return;

  const modal = document.getElementById('ticket-modal');
  const title = document.getElementById('modal-ticket-id');
  const content = document.getElementById('modal-content');
  const color = getPriorityColor(item.priority);

  if (title) title.innerText = `Ticket #${item.id} — ${getLocalizedDeptName(item.department)}`;
  if (content) {
    const isAdmin = userRole === 'admin';
    const lat = typeof item.lat === 'number' ? item.lat : parseFloat(item.lat || 19.0760);
    const lon = typeof item.lon === 'number' ? item.lon : parseFloat(item.lon || 72.8777);
    const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
    const osmUrl = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`;
    const slaBadge = getSlaBadgeHtml(item.created_at, item.priority, item.status);
    const stepperHtml = renderProgressStepperHtml(item.status, item.citizen_feedback);

    // Build Before & After Photo comparison
    let photoComparisonHtml = '';
    const hasBefore = Boolean(item.image_data);
    const hasAfter = Boolean(item.resolution_photo);

    if (hasBefore || hasAfter) {
      const visualHeading = currentSiteLang === 'hi' ? 'समाधान दृश्य सत्यापन' : (currentSiteLang === 'mr' ? 'निवारण दृश्य पडताळणी' : 'Resolution Visual Verification');
      const noPhotoTxt = currentSiteLang === 'hi' ? 'कोई फोटो संलग्न नहीं' : (currentSiteLang === 'mr' ? 'कोणताही फोटो जोडलेला नाही' : 'No photo submitted');
      photoComparisonHtml = `
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; padding:12px;">
          <div style="font-size:0.75rem; font-weight:800; color:#0f172a; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.04em;">
            📷 ${visualHeading}
          </div>
          <div class="before-after-grid">
            <div class="photo-panel">
              <div class="photo-panel-tag tag-before">${t('evidenceBefore', 'Before: Citizen Evidence')}</div>
              ${hasBefore ? `
                <img src="${item.image_data}" alt="Reported Evidence" onclick="openFullPhoto('${item.id}', 'before')" />
                <div style="font-size:0.68rem; color:#64748b; margin-top:4px; text-align:center;">${t('clickFullSize', 'Click to inspect full size')}</div>
              ` : `
                <div style="height:140px; display:flex; align-items:center; justify-content:center; color:#94a3b8; font-size:0.75rem; background:#f1f5f9; border-radius:6px;">${noPhotoTxt}</div>
              `}
            </div>
            <div class="photo-panel">
              <div class="photo-panel-tag tag-after">${t('evidenceAfter', 'After: Field Resolution Proof')}</div>
              ${hasAfter ? `
                <img src="${item.resolution_photo}" alt="Resolution Proof" onclick="openFullPhoto('${item.id}', 'after')" />
                <div style="font-size:0.68rem; color:#059669; font-weight:700; margin-top:4px; text-align:center;">${t('verifiedRepair', '✓ Verified On-Site Repair')}</div>
              ` : `
                <div style="height:140px; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#94a3b8; font-size:0.75rem; background:#f1f5f9; border-radius:6px; text-align:center; padding:10px;">
                  <span>${t('pendingProof', 'Field crew resolution photo (Pending work completion)')}</span>
                </div>
              `}
            </div>
          </div>
          ${item.resolution_note ? `
            <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:6px; padding:8px 10px; margin-top:8px;">
              <strong style="color:#047857; font-size:0.74rem;">${t('officerNote', '✓ Field Officer Note:')}</strong>
              <div style="color:#065f46; font-size:0.8rem; margin-top:2px;">"${escapeHtml(item.resolution_note)}"</div>
              <div style="font-size:0.68rem; color:#059669; margin-top:2px;">${t('resolvedAt', 'Resolved at:')} ${item.resolved_at ? item.resolved_at.substring(0,16).replace('T',' ') : 'Recently'}</div>
            </div>
          ` : ''}
        </div>
      `;
    }

    const lblStatus = currentSiteLang === 'hi' ? 'स्थिति:' : (currentSiteLang === 'mr' ? 'स्थिती:' : 'Status:');
    const lblLocTitle = currentSiteLang === 'hi' ? 'घटना स्थल' : (currentSiteLang === 'mr' ? 'घटना स्थळ' : 'Incident Location');
    const lblCoords = currentSiteLang === 'hi' ? 'निर्देशांक' : (currentSiteLang === 'mr' ? 'निर्देशांक' : 'Coordinates');
    const lblCitizen = currentSiteLang === 'hi' ? 'नागरिक:' : (currentSiteLang === 'mr' ? 'नागरिक:' : 'Citizen:');
    const lblDesc = currentSiteLang === 'hi' ? 'विवरण:' : (currentSiteLang === 'mr' ? 'वर्णन:' : 'Description:');
    const lblTrans = currentSiteLang === 'hi' ? 'अनुवाद:' : (currentSiteLang === 'mr' ? 'भाषांतर:' : 'Translated:');
    const lblReason = currentSiteLang === 'hi' ? 'कारण:' : (currentSiteLang === 'mr' ? 'कारण:' : 'Reason:');
    const lblRationale = currentSiteLang === 'hi' ? 'आंतरिक सिस्टम तर्क:' : (currentSiteLang === 'mr' ? 'अंतर्गत सिस्टीम तर्क:' : 'Internal System Rationale:');

    content.innerHTML = `
      <div style="font-size:0.85rem; display:flex; flex-direction:column; gap:12px;">
        ${stepperHtml}

        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <strong>${lblStatus}</strong> 
            <span class="status-badge ${(item.status==='Waiting for Citizen Confirmation'||item.status==='Awaiting Citizen Confirmation')?'waiting':(item.status==='Resolved'?'resolved':(item.status==='In Progress'?'progress':(item.status==='Reopened'?'breached':'pending')))}">${getLocalizedStatus(item.status)}</span>
            ${slaBadge}
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="color:${color};font-weight:800;">${item.priority}</span> (${item.severity_score}/100)
            ${renderUpvoteButtonHtml(item)}
          </div>
        </div>

        <!-- Incident Location Card -->
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
          <div>
            <div style="font-size:0.72rem; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:0.04em;">${lblLocTitle}</div>
            <div style="font-size:0.95rem; font-weight:800; color:#0f172a; margin-top:2px;">
              📍 ${escapeHtml(item.ward || 'Municipal Area')}
            </div>
            <div style="font-size:0.74rem; font-family:monospace; color:#475569; margin-top:2px;">
              ${lblCoords}: ${lat.toFixed(5)}, ${lon.toFixed(5)}
            </div>
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <a href="${googleMapsUrl}" target="_blank" rel="noopener noreferrer" style="display:inline-flex; align-items:center; gap:6px; background:#0f172a; color:#ffffff; padding:7px 14px; border-radius:6px; font-size:0.78rem; font-weight:750; text-decoration:none; box-shadow:0 1px 3px rgba(0,0,0,0.15);" title="Open exact pin in Google Maps">
              <span>🗺️ Google Maps</span>
              <span style="font-size:0.7rem;">↗</span>
            </a>
            <a href="${osmUrl}" target="_blank" rel="noopener noreferrer" style="display:inline-flex; align-items:center; gap:4px; background:#ffffff; color:#2563eb; border:1px solid #cbd5e1; padding:6px 12px; border-radius:6px; font-size:0.75rem; font-weight:700; text-decoration:none;" title="Open in OpenStreetMap">
              <span>OSM</span>
              <span style="font-size:0.7rem;">↗</span>
            </a>
          </div>
        </div>

        <div><strong>${lblCitizen}</strong> ${item.citizen_name || t('anonymousUser', 'Anonymous Citizen')}</div>
        <div><strong>${lblDesc}</strong> <i>"${escapeHtml(item.original_text)}"</i></div>
        ${item.text_en && item.text_en !== item.original_text ? `<div style="background:#f8fafc;padding:10px;border-radius:8px;border:1px solid #e2e8f0;"><strong>${lblTrans}</strong> "${escapeHtml(item.text_en)}"</div>` : ''}

        ${photoComparisonHtml}

        <!-- Citizen Verification & Feedback Section -->
        ${!isAdmin && (item.status === 'Waiting for Citizen Confirmation' || item.status === 'Awaiting Citizen Confirmation' || item.status === 'Resolved') ? `
          <div class="citizen-feedback-box">
            ${item.citizen_feedback === 'Satisfied' ? `
              <div style="color:#065f46; font-weight:800; font-size:0.85rem;">${t('resolutionConfirmed', '✓ Resolution Confirmed')}</div>
              <p style="color:#047857; font-size:0.78rem; margin-top:2px;">${t('resolutionConfirmedDesc', 'You verified that this complaint was resolved satisfactorily.')}</p>
            ` : (item.citizen_feedback === 'Reopened' ? `
              <div style="color:#991b1b; font-weight:800; font-size:0.85rem;">${t('ticketReopened', '↺ Ticket Reopened')}</div>
              <p style="color:#b91c1c; font-size:0.78rem; margin-top:2px;">${lblReason} "${escapeHtml(item.citizen_remarks || 'Work was incomplete')}"</p>
            ` : `
              <div style="font-weight:800; color:#065f46; font-size:0.85rem; margin-bottom:4px;">${t('confirmQuestion', 'Did the municipal authority fix this issue?')}</div>
              <p style="font-size:0.76rem; color:#047857; margin-bottom:10px;">${t('confirmDesc', 'Please inspect the before & after evidence. If the issue is fixed on the ground, tap \'Confirm Resolved\' to close and permanently remove this ticket. If not resolved, tap \'Reopen Ticket\'.')}</p>
              <div style="display:flex; gap:8px;">
                <button type="button" class="btn-primary-submit" style="padding:7px 16px; font-size:0.78rem; background:#059669;" onclick="submitCitizenFeedback('${item.id}', 'Satisfied')">${t('btnConfirmResolved', '✓ Confirm Resolved (Close & Remove)')}</button>
                <button type="button" class="btn-browse-files" style="padding:7px 16px; font-size:0.78rem; color:#b91c1c; border-color:#fca5a5;" onclick="submitCitizenFeedback('${item.id}', 'Reopened')">${t('btnReopenTicket', '↺ Reopen Ticket')}</button>
              </div>
            `)}
          </div>
        ` : ''}

        <!-- Authority Admin Actions -->
        ${isAdmin ? `
          ${(item.status === 'Waiting for Citizen Confirmation' || item.status === 'Awaiting Citizen Confirmation') ? `
            <div class="waiting-verification-banner">
              <span>⏳</span>
              <div>${t('adminWaitingNotice', "Waiting for Citizen's Confirmation: Field work and completion photo have been submitted. Awaiting citizen verification to close and remove this ticket.")}</div>
            </div>
          ` : ''}

          <div style="background:#eff6ff;padding:12px;border-radius:8px;border:1px solid #bfdbfe;">
            <strong style="color:#1e40af;">${lblRationale}</strong>
            <pre style="white-space:pre-wrap;font-family:inherit;font-size:0.75rem;margin:6px 0 0;color:#1e293b;">${escapeHtml(item.xai_department||'')}\n\n${escapeHtml(item.xai_priority||'')}</pre>
          </div>

          <div class="admin-resolution-box">
            <strong style="color:#0f172a; font-size:0.82rem; display:block; margin-bottom:6px;">${t('workOrderTitle', '🛠️ Field Work Order & Resolution Action')}</strong>
            <div style="margin-bottom:8px;">
              <label style="font-size:0.72rem; font-weight:750; color:#475569; display:block; margin-bottom:4px;">
                ${t('resPhotoLabel', 'Upload "After" Resolution Photo Proof (Camera/File) *Required to Resolve:')}
              </label>
              <input type="file" id="admin-res-photo-input" accept="image/*" onchange="onAdminResolutionPhotoSelected(event)" style="font-size:0.75rem;">
              <div id="admin-res-photo-label" style="font-size:0.72rem; color:#059669; font-weight:700; margin-top:3px;"></div>
              <img id="admin-res-photo-preview" src="" style="display:none; max-height:140px; border-radius:6px; margin-top:6px; border:1px solid #cbd5e1;" />
            </div>
            <div style="margin-bottom:10px;">
              <label style="font-size:0.72rem; font-weight:750; color:#475569; display:block; margin-bottom:4px;">${t('workRemarks', 'Work Completion Remarks:')}</label>
              <input type="text" id="admin-res-note-input" class="form-control-styled" placeholder="${t('workRemarksPh', 'e.g. Patched 3 potholes with 20kg cold-mix asphalt')}" style="width:100%; padding:6px 10px; font-size:0.78rem;">
            </div>
            <div style="display:flex; gap:8px; justify-content:flex-end; flex-wrap:wrap;">
              <button type="button" class="btn-browse-files" style="color:#b91c1c;" onclick="updateTicketStatus('${item.id}','Pending')">${t('btnMarkPending', 'Mark Pending')}</button>
              <button type="button" class="btn-browse-files" style="color:#2563eb;" onclick="updateTicketStatus('${item.id}','In Progress')">${t('btnMarkProgress', 'Mark In Progress')}</button>
              <button type="button" class="btn-primary-submit" style="padding:8px 16px; font-size:0.8rem; background:#059669;" onclick="resolveTicketWithProof('${item.id}')">${t('btnResolvePhoto', '✓ Submit Work for Citizen Confirmation')}</button>
            </div>
          </div>
        ` : ''}
      </div>`;
  }
  if (modal) modal.style.display = 'flex';
}

function openFullPhoto(ticketId) {
  const item = grievancesData.find(g => g.id === ticketId);
  if (!item || !item.image_data) return;
  const w = window.open("");
  if (w) {
    w.document.write(`<!DOCTYPE html><html><head><title>Photo Evidence #${item.id}</title><style>body{margin:0;background:#090d16;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:#fff;font-family:system-ui,sans-serif;padding:20px;box-sizing:border-box;}img{max-width:94vw;max-height:86vh;object-fit:contain;border-radius:10px;box-shadow:0 20px 40px rgba(0,0,0,0.6);border:1px solid #334155;}</style></head><body><div style="margin-bottom:12px;font-size:0.9rem;font-weight:700;color:#cbd5e1;">Ticket #${item.id} — ${escapeHtml(item.department)}</div><img src="${item.image_data}" alt="Photo Evidence" /></body></html>`);
    w.document.close();
  }
}

function closeModal() {
  currentModalTicketId = null;
  document.getElementById('ticket-modal').style.display = 'none';
}

async function updateTicketStatus(ticketId, newStatus) {
  if (newStatus === 'Resolved') {
    alert("⚠️ Mandatory Photographic Evidence:\nTo mark a ticket as Resolved, you must upload photographic proof of the completed work using the '✓ Resolve with Photo Proof' button below.");
    const input = document.getElementById('admin-res-photo-input');
    if (input) {
      input.scrollIntoView({ behavior: 'smooth', block: 'center' });
      input.focus();
    }
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
      alert(result.error || 'Error updating status.');
    }
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

// ─── Utility Helpers ───
function getPriorityColor(p) {
  if (p === 'Critical') return '#dc2626';
  if (p === 'High') return '#ea580c';
  if (p === 'Medium') return '#d97706';
  return '#059669';
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, t => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[t]||t));
}

function updateCharCount() {
  const desc = document.getElementById('description');
  const countEl = document.getElementById('char-count');
  if (desc && countEl) {
    countEl.innerText = `${desc.value.length}/500 chars`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const desc = document.getElementById('description');
  if (desc) {
    desc.addEventListener('input', updateCharCount);
  }
});

