// ============================================================
// EIFM WCC & PPM
// Application data / dropdown lists
// ============================================================

// ------------------------------------------------------------
// BUILDINGS
// ------------------------------------------------------------
// IMPORTANT:
// Yahan building names manually maintain kiye ja sakte hain.
// Jo exact building names aap use karte hain, unko isi list me
// ek-ek line par add karein.

export const buildings = [
  // Example:
  // "Building Name 1",
  // "Building Name 2",
  // "Building Name 3",
];

// ------------------------------------------------------------
// EQUIPMENT SHEETS
// ------------------------------------------------------------
// IMPORTANT:
// In names ko supplied Excel workbook ke ORIGINAL worksheet
// names ke exactly same rakhna hai.
//
// Abhi placeholder structure rakha gaya hai taaki app error
// na de. Exact worksheet names milne par yahan replace karenge.

export const equipmentSheets = [
  // Example:
  // "AHU",
  // "FCU",
  // "Chiller",
  // "Pump",
  // "Exhaust Fan",
  // "Lighting",
];

// ------------------------------------------------------------
// DEFAULT CLIENT
// ------------------------------------------------------------

export const clientDefault =
  "East & West International";

// ------------------------------------------------------------
// CHECKLIST TABLE HEADERS
// ------------------------------------------------------------

export const checklistHeaders = [
  "#",
  "Service Specification / Task",
  "OK",
  "Not OK",
  "Remarks",
  "Follow-up WO",
];

// ------------------------------------------------------------
// WCC ENCLOSED DOCUMENTS
// ------------------------------------------------------------

export const documents = [
  "LPO",
  "Invoice",
  "Delivery Note",
  "Petty Cash",
  "Material Requisition",
  "Job Completion",
];

// ------------------------------------------------------------
// PPM OPTIONS
// ------------------------------------------------------------

export const ppmOptions = [
  "1st PPM",
  "2nd PPM",
  "3rd PPM",
  "4th PPM",
];

// ------------------------------------------------------------
// FREQUENCY OPTIONS
// ------------------------------------------------------------

export const frequencies = [
  "Monthly",
  "Quarterly",
  "Semi-Annual",
  "Annual",
  "Corrective / Complaint",
];

// ------------------------------------------------------------
// SATISFACTION OPTIONS
// ------------------------------------------------------------

export const satisfactionOptions = [
  "1. Poor",
  "2. Satisfied",
  "3. Good",
  "4. Very Good",
  "5. Excellent",
];
