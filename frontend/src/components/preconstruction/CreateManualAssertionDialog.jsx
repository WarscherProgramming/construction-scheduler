import { useEffect, useId, useMemo, useState } from "react";

import DrawingDialog from "../drawings/DrawingDialog";
import Button from "../ui/Button";


/**
 * Human-authored assertion capture.
 *
 * Evidence is selected from segments already loaded in the Content Inspector
 * for the chosen source, so this dialog issues no content request of its own
 * and cannot reference an arbitrary page or segment identifier.
 */
function CreateManualAssertionDialog({
  sources,
  taxonomy,
  isTaxonomyLoading,
  inspector,
  busy,
  onLoadTaxonomy,
  onClose,
  onSubmit,
}) {
  const preparedSources = useMemo(
    () =>
      sources.filter((source) =>
        ["ready", "ready_with_warnings"].includes(source.preparation_status)
      ),
    [sources]
  );
  const [sourceId, setSourceId] = useState(
    inspector?.sourceId || preparedSources[0]?.id || ""
  );
  const [conceptSearch, setConceptSearch] = useState("");
  const [conceptCategory, setConceptCategory] = useState("");
  const [conceptCode, setConceptCode] = useState("");
  const [assertionType, setAssertionType] = useState("requirement");
  const [inclusionState, setInclusionState] = useState("included");
  const [subject, setSubject] = useState("");
  const [requirementText, setRequirementText] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [trade, setTrade] = useState("");
  const [responsibility, setResponsibility] = useState("");
  const [specificationSection, setSpecificationSection] = useState("");
  const [locationText, setLocationText] = useState("");
  const [selectedSegments, setSelectedSegments] = useState([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  useEffect(() => {
    if (!taxonomy && !isTaxonomyLoading) onLoadTaxonomy?.();
  }, [isTaxonomyLoading, onLoadTaxonomy, taxonomy]);

  const concepts = useMemo(() => {
    const all = taxonomy?.concepts || [];
    const search = conceptSearch.trim().toLowerCase();
    return all
      .filter((item) => !conceptCategory || item.category === conceptCategory)
      .filter(
        (item) =>
          !search ||
          item.name.toLowerCase().includes(search) ||
          item.code.toLowerCase().includes(search) ||
          (item.aliases || []).some((alias) =>
            alias.toLowerCase().includes(search)
          )
      )
      .slice(0, 50);
  }, [conceptCategory, conceptSearch, taxonomy]);

  const selectedConcept = useMemo(
    () => (taxonomy?.concepts || []).find((item) => item.code === conceptCode),
    [conceptCode, taxonomy]
  );

  // Evidence may only come from the inspector's currently loaded segments for
  // the selected source.
  const availableSegments = useMemo(() => {
    if (!inspector?.content || String(inspector.sourceId) !== String(sourceId)) {
      return [];
    }
    return inspector.content.segments || [];
  }, [inspector, sourceId]);

  const pending = busy || submitting;

  const toggleSegment = (id) => {
    setSelectedSegments((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id]
    );
  };

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    if (!sourceId) return setError("Select a prepared source.");
    if (!conceptCode) return setError("Select a scope concept.");
    if (!subject.trim()) return setError("A subject is required.");
    if (selectedSegments.length === 0) {
      return setError("Select at least one evidence segment.");
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        source_id: Number(sourceId),
        concept_code: conceptCode,
        assertion_type: assertionType,
        subject: subject.trim(),
        requirement_text: requirementText.trim() || null,
        responsibility_party: responsibility.trim() || null,
        discipline: discipline.trim() || null,
        trade: trade.trim() || null,
        specification_section: specificationSection.trim() || null,
        location_text: locationText.trim() || null,
        inclusion_state: inclusionState,
        evidence_segment_ids: selectedSegments,
        reviewer_note: note.trim() || null,
      });
      onClose();
    } catch (requestError) {
      setError(requestError.message || "Unable to create this assertion.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DrawingDialog
      title="Add a human-authored assertion"
      eyebrow="Manual scope capture"
      onClose={onClose}
      busy={pending}
      actions={
        <>
          <Button disabled={pending} onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={pending}
            type="submit"
            form="manual-assertion-form"
          >
            {pending ? "Saving…" : "Create assertion"}
          </Button>
        </>
      }
    >
      <form
        id="manual-assertion-form"
        className="preconstruction-dialog-form"
        onSubmit={submit}
      >
        <p className="preconstruction-hint">
          This assertion is authored by you, not generated by a model. It is
          recorded as accepted with your name on the review history.
        </p>

        <label className="field-group">
          <span>Source</span>
          <select
            value={sourceId}
            onChange={(event) => {
              setSourceId(event.target.value);
              setSelectedSegments([]);
            }}
          >
            <option value="">Select a prepared source</option>
            {preparedSources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.display_name} ({source.role_label})
              </option>
            ))}
          </select>
        </label>

        <fieldset className="field-group">
          <legend>Scope concept</legend>
          <div className="assertion-taxonomy-filters">
            <label>
              <span>Search</span>
              <input
                value={conceptSearch}
                maxLength="120"
                onChange={(event) => setConceptSearch(event.target.value)}
              />
            </label>
            <label>
              <span>Category</span>
              <select
                value={conceptCategory}
                onChange={(event) => setConceptCategory(event.target.value)}
              >
                <option value="">All categories</option>
                {(taxonomy?.categories || []).map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
          </div>
          <label>
            <span>Concept</span>
            <select
              value={conceptCode}
              onChange={(event) => setConceptCode(event.target.value)}
            >
              <option value="">
                {isTaxonomyLoading ? "Loading taxonomy…" : "Select a concept"}
              </option>
              {concepts.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.category_label} — {item.name}
                </option>
              ))}
            </select>
          </label>
          {selectedConcept && (
            <p className="preconstruction-hint">
              {selectedConcept.code} · {selectedConcept.scope_kind_label} ·{" "}
              {selectedConcept.description}
            </p>
          )}
        </fieldset>

        <div className="assertion-form-grid">
          <label className="field-group">
            <span>Assertion type</span>
            <select
              value={assertionType}
              onChange={(event) => setAssertionType(event.target.value)}
            >
              {(taxonomy?.assertion_types || []).map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <label className="field-group">
            <span>Inclusion</span>
            <select
              value={inclusionState}
              onChange={(event) => setInclusionState(event.target.value)}
            >
              {(taxonomy?.inclusion_states || []).map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="field-group">
          <span>Subject</span>
          <input
            value={subject}
            maxLength="300"
            onChange={(event) => setSubject(event.target.value)}
          />
        </label>
        <label className="field-group">
          <span>Requirement</span>
          <textarea
            value={requirementText}
            rows="3"
            maxLength="2000"
            onChange={(event) => setRequirementText(event.target.value)}
          />
        </label>

        <div className="assertion-form-grid">
          <label className="field-group">
            <span>Discipline</span>
            <input
              value={discipline}
              maxLength="120"
              onChange={(event) => setDiscipline(event.target.value)}
            />
          </label>
          <label className="field-group">
            <span>Trade</span>
            <input
              value={trade}
              maxLength="120"
              onChange={(event) => setTrade(event.target.value)}
            />
          </label>
          <label className="field-group">
            <span>Responsibility</span>
            <input
              value={responsibility}
              maxLength="200"
              onChange={(event) => setResponsibility(event.target.value)}
            />
          </label>
          <label className="field-group">
            <span>Specification section</span>
            <input
              value={specificationSection}
              maxLength="60"
              onChange={(event) => setSpecificationSection(event.target.value)}
            />
          </label>
        </div>

        <label className="field-group">
          <span>Location</span>
          <input
            value={locationText}
            maxLength="300"
            onChange={(event) => setLocationText(event.target.value)}
          />
        </label>

        <fieldset className="field-group">
          <legend>Evidence</legend>
          {availableSegments.length === 0 ? (
            <p className="preconstruction-hint">
              Open this source in the Content Inspector to choose evidence
              segments. Evidence must come from prepared content.
            </p>
          ) : (
            <ul className="assertion-evidence-picker">
              {availableSegments.map((segment) => (
                <li key={segment.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedSegments.includes(segment.id)}
                      onChange={() => toggleSegment(segment.id)}
                    />
                    <span>
                      Page {segment.page_number}, segment {segment.segment_index}
                    </span>
                  </label>
                  <p className="assertion-evidence-preview">
                    {segment.text.slice(0, 240)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        <label className="field-group">
          <span>Note</span>
          <textarea
            value={note}
            rows="2"
            maxLength="2000"
            aria-describedby={error ? errorId : undefined}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        {error && (
          <p id={errorId} className="preconstruction-form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </DrawingDialog>
  );
}

export default CreateManualAssertionDialog;
