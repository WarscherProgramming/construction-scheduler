import { useEffect, useId, useMemo, useRef, useState } from "react";

import { listRelationshipCandidates } from "../../services/api";
import {
  buildRelationshipPayload,
  getRelationshipChoices,
  isExistingRelationship,
  RELATIONSHIP_ENTITY_LABELS,
} from "../../utils/relationships";
import FormField from "../FormField";
import Button from "../ui/Button";
import DrawingDialog from "../drawings/DrawingDialog";


function isAbortError(error) {
  return error?.name === "AbortError";
}


function CreateRelationshipDialog({
  projectId,
  entityType,
  entityId,
  relationships,
  isCreating,
  mutationError,
  onCreate,
  onClose,
  onError,
}) {
  const listboxId = useId();
  const choices = useMemo(
    () => getRelationshipChoices(entityType),
    [entityType]
  );
  const [choiceKey, setChoiceKey] = useState("");
  const [relatedType, setRelatedType] = useState("");
  const [search, setSearch] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [searchVersion, setSearchVersion] = useState(0);
  const [candidateState, setCandidateState] = useState({
    identity: null,
    candidates: [],
    error: null,
    pending: false,
  });
  const requestRef = useRef(null);
  const choice = choices.find((item) => item.key === choiceKey);
  const relatedOptions = choice?.options || [];
  const selectedOption = relatedOptions.find(
    (option) => option.relatedType === relatedType
  );
  const candidateIdentity = selectedOption
    ? `${projectId}:${selectedOption.relatedType}:${search}:${searchVersion}`
    : null;
  const candidates =
    candidateState.identity === candidateIdentity
      ? candidateState.candidates
      : [];
  const searchError =
    candidateState.identity === candidateIdentity
      ? candidateState.error
      : null;
  const isSearching = Boolean(
    candidateIdentity &&
      (candidateState.identity !== candidateIdentity ||
        candidateState.pending)
  );

  useEffect(() => {
    requestRef.current?.abort();
    if (!selectedOption || !candidateIdentity) return undefined;

    const controller = new AbortController();
    requestRef.current = controller;
    const timer = window.setTimeout(() => {
      setCandidateState({
        identity: candidateIdentity,
        candidates: [],
        error: null,
        pending: true,
      });
      listRelationshipCandidates(projectId, selectedOption.relatedType, {
        search,
        limit: 20,
        excludeType:
          selectedOption.relatedType === entityType ? entityType : undefined,
        excludeId:
          selectedOption.relatedType === entityType ? entityId : undefined,
        signal: controller.signal,
      })
        .then((response) => {
          if (controller.signal.aborted) return;
          setCandidateState({
            identity: candidateIdentity,
            candidates: (response?.candidates || []).filter(
              (candidate) =>
                !isExistingRelationship(
                  relationships,
                  selectedOption.relationshipType,
                  candidate
                )
            ),
            error: null,
            pending: false,
          });
        })
        .catch((error) => {
          if (isAbortError(error)) return;
          setCandidateState({
            identity: candidateIdentity,
            candidates: [],
            error: error?.message || "Candidates could not be loaded.",
            pending: false,
          });
          onError?.("Unable to search relationship candidates", error);
        });
    }, 250);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    candidateIdentity,
    entityId,
    entityType,
    onError,
    projectId,
    relationships,
    search,
    searchVersion,
    selectedOption,
  ]);

  const selectChoice = (nextKey) => {
    const nextChoice = choices.find((item) => item.key === nextKey);
    setChoiceKey(nextKey);
    setRelatedType(
      nextChoice?.options.length === 1
        ? nextChoice.options[0].relatedType
        : ""
    );
    setSearch("");
    setSelectedCandidate(null);
    setActiveIndex(-1);
  };

  const selectCandidate = (candidate) => {
    setSelectedCandidate(candidate);
  };

  const handleSearchKeyDown = (event) => {
    if (!candidates.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) =>
        current >= candidates.length - 1 ? 0 : current + 1
      );
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) =>
        current <= 0 ? candidates.length - 1 : current - 1
      );
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      selectCandidate(candidates[activeIndex]);
    }
  };

  const confirm = async () => {
    if (!selectedOption || !selectedCandidate) return;
    const payload = buildRelationshipPayload(
      entityType,
      entityId,
      selectedOption,
      selectedCandidate
    );
    if (await onCreate(payload)) onClose();
  };

  return (
    <DrawingDialog
      title="Add relationship"
      eyebrow={RELATIONSHIP_ENTITY_LABELS[entityType]}
      onClose={onClose}
      busy={isCreating}
      actions={
        <>
          <Button onClick={onClose} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!selectedCandidate || isCreating}
            onClick={confirm}
          >
            {isCreating ? "Adding..." : "Add Relationship"}
          </Button>
        </>
      }
    >
      <div className="relationship-dialog__fields">
        <FormField label="Relationship" htmlFor="relationship-type" required>
          <select
            id="relationship-type"
            className="field-control"
            required
            value={choiceKey}
            onChange={(event) => selectChoice(event.target.value)}
          >
            <option value="">Select relationship</option>
            {choices.map((item) => (
              <option key={item.key} value={item.key}>
                {item.relationshipLabel}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Record type" htmlFor="relationship-entity" required>
          <select
            id="relationship-entity"
            className="field-control"
            required
            disabled={!choice}
            value={relatedType}
            onChange={(event) => {
              setRelatedType(event.target.value);
              setSearch("");
              setSelectedCandidate(null);
              setActiveIndex(-1);
            }}
          >
            <option value="">Select record type</option>
            {relatedOptions.map((option) => (
              <option key={option.key} value={option.relatedType}>
                {RELATIONSHIP_ENTITY_LABELS[option.relatedType]}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Find record" htmlFor="relationship-search">
          <input
            id="relationship-search"
            className="field-control"
            type="search"
            role="combobox"
            autoComplete="off"
            disabled={!selectedOption}
            value={search}
            aria-expanded={Boolean(selectedOption)}
            aria-controls={listboxId}
            aria-autocomplete="list"
            aria-activedescendant={
              activeIndex >= 0
                ? `${listboxId}-option-${candidates[activeIndex]?.id}`
                : undefined
            }
            onChange={(event) => {
              setSearch(event.target.value);
              setSelectedCandidate(null);
              setActiveIndex(-1);
            }}
            onKeyDown={handleSearchKeyDown}
          />
        </FormField>
      </div>

      <div className="relationship-candidate-status" role="status" aria-live="polite">
        {isSearching
          ? "Searching project records..."
          : selectedOption && !searchError
            ? `${candidates.length} available ${
                candidates.length === 1 ? "record" : "records"
              }`
            : ""}
      </div>
      {searchError && (
        <div className="relationship-dialog__error" role="alert">
          <span>{searchError}</span>
          <Button size="sm" onClick={() => setSearchVersion((value) => value + 1)}>
            Retry
          </Button>
        </div>
      )}
      {mutationError && (
        <div className="relationship-dialog__error" role="alert">
          {mutationError.status === 409
            ? "That relationship already exists."
            : mutationError.message}
        </div>
      )}

      <div
        id={listboxId}
        className="relationship-candidates"
        role="listbox"
        aria-label="Related project records"
      >
        {!isSearching && selectedOption && candidates.length === 0 && !searchError ? (
          <p>No available records found.</p>
        ) : (
          candidates.map((candidate, index) => (
            <button
              key={candidate.id}
              id={`${listboxId}-option-${candidate.id}`}
              type="button"
              role="option"
              aria-selected={selectedCandidate?.id === candidate.id}
              className={
                selectedCandidate?.id === candidate.id || activeIndex === index
                  ? "relationship-candidate relationship-candidate--active"
                  : "relationship-candidate"
              }
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selectCandidate(candidate)}
            >
              <strong>{candidate.identifier}</strong>
              <span>{candidate.title}</span>
              {candidate.status && <span>Status: {candidate.status}</span>}
            </button>
          ))
        )}
      </div>

      {selectedCandidate && selectedOption && (
        <div className="relationship-dialog__review">
          <strong>Relationship summary</strong>
          <span>
            {selectedOption.relationshipLabel} {selectedCandidate.identifier}
          </span>
        </div>
      )}
    </DrawingDialog>
  );
}

export default CreateRelationshipDialog;
