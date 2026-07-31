export const DRAWING_DISCIPLINES = [
  ["G", "General"],
  ["C", "Civil"],
  ["L", "Landscape"],
  ["A", "Architectural"],
  ["I", "Interiors"],
  ["S", "Structural"],
  ["M", "Mechanical"],
  ["P", "Plumbing"],
  ["FP", "Fire Protection"],
  ["E", "Electrical"],
  ["T", "Technology"],
  ["FA", "Fire Alarm"],
  ["K", "Kitchen"],
  ["Q", "Equipment"],
  ["V", "Vertical Transportation"],
  ["X", "Other"],
];

export const DRAWING_PURPOSES = [
  ["bid", "Bid"],
  ["permit", "Permit"],
  ["construction", "Construction"],
  ["addendum", "Addendum"],
  ["bulletin", "Bulletin"],
  ["record", "Record"],
  ["as_built", "As-Built"],
  ["other", "Other"],
];

export function drawingDisciplineLabel(code) {
  const discipline = DRAWING_DISCIPLINES.find(([value]) => value === code);
  return discipline ? `${discipline[0]} - ${discipline[1]}` : code;
}

export function validateDrawingPdf(file) {
  if (!file) return "Select a PDF drawing file.";
  if (!String(file.name || "").toLowerCase().endsWith(".pdf")) {
    return "Drawing revisions must use a .pdf file.";
  }
  if (file.type && file.type !== "application/pdf") {
    return "Drawing revisions must use the PDF file type.";
  }
  return "";
}
