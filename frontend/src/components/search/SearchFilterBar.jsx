import { DRAWING_DISCIPLINES } from "../../utils/drawing";


function SearchFilterBar({ filters, onChange }) {
  const update = (name, value) => onChange({ ...filters, [name]: value });
  return (
    <fieldset className="project-document-search-filters">
      <legend>Search filters</legend>
      <label>
        <span>Scope</span>
        <select
          className="field-control"
          value={filters.scope}
          onChange={(event) => update("scope", event.target.value)}
        >
          <option value="all">Documents and drawings</option>
          <option value="documents">Documents</option>
          <option value="drawings">Drawings</option>
        </select>
      </label>
      <label>
        <span>Document type</span>
        <select
          className="field-control"
          value={filters.documentType}
          onChange={(event) => update("documentType", event.target.value)}
        >
          <option value="">All types</option>
          <option value="General">General</option>
          <option value="Drawing">Drawing</option>
          <option value="Report">Report</option>
          <option value="Specification">Specification</option>
          <option value="Photo">Photo</option>
        </select>
      </label>
      <label>
        <span>Discipline</span>
        <select
          className="field-control"
          value={filters.discipline}
          onChange={(event) => update("discipline", event.target.value)}
        >
          <option value="">All disciplines</option>
          {DRAWING_DISCIPLINES.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>
      <label>
        <span>Drawing set ID</span>
        <input
          className="field-control"
          type="number"
          min="1"
          step="1"
          value={filters.drawingSetId}
          onChange={(event) => update("drawingSetId", event.target.value)}
        />
      </label>
      <label>
        <span>Text source</span>
        <select
          className="field-control"
          value={filters.extractionMethod}
          onChange={(event) => update("extractionMethod", event.target.value)}
        >
          <option value="">All sources</option>
          <option value="embedded_text">Embedded PDF text</option>
          <option value="ocr">OCR text</option>
          <option value="mixed">Embedded and OCR text</option>
          <option value="metadata_only">Metadata only</option>
          <option value="unavailable">Content unavailable</option>
        </select>
      </label>
      <label className="project-document-search-filters__checkbox">
        <input
          type="checkbox"
          checked={filters.currentRevisionsOnly}
          onChange={(event) =>
            update("currentRevisionsOnly", event.target.checked)
          }
        />
        <span>Current drawing revisions only</span>
      </label>
    </fieldset>
  );
}

export default SearchFilterBar;
