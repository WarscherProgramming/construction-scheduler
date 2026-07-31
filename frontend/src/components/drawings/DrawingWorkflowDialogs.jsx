import { useState } from "react";

import { formatLocalDateForApi } from "../../utils/date";
import {
  DRAWING_DISCIPLINES,
  DRAWING_PURPOSES,
  validateDrawingPdf,
} from "../../utils/drawing";
import FormField from "../FormField";
import Button from "../ui/Button";
import DrawingDialog from "./DrawingDialog";


function ErrorText({ message, id }) {
  return message ? (
    <p id={id} className="drawing-form-error" role="alert">
      {message}
    </p>
  ) : null;
}


export function DrawingSetDialog({
  drawingSet,
  busy,
  onSubmit,
  onClose,
}) {
  const [name, setName] = useState(drawingSet?.name || "");
  const [description, setDescription] = useState(
    drawingSet?.description || ""
  );
  const [status, setStatus] = useState(drawingSet?.status || "active");
  const [issueDate, setIssueDate] = useState(
    drawingSet?.issue_date || formatLocalDateForApi()
  );
  const [error, setError] = useState("");
  const formId = "drawing-set-form";

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    const result = await onSubmit({
      name,
      description: description || null,
      status,
      issue_date: issueDate || null,
    });
    if (result) onClose();
    else setError("The drawing set could not be saved. Review the feedback.");
  };

  return (
    <DrawingDialog
      title={drawingSet ? "Edit Drawing Set" : "Create Drawing Set"}
      eyebrow="Drawing register"
      busy={busy}
      onClose={onClose}
      actions={
        <>
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button
            form={formId}
            type="submit"
            variant="primary"
            disabled={busy}
          >
            {busy ? "Saving..." : "Save Drawing Set"}
          </Button>
        </>
      }
    >
      <form id={formId} className="drawing-form" onSubmit={submit}>
        <ErrorText id="drawing-set-error" message={error} />
        <FormField label="Set name" htmlFor="drawing-set-name" required>
          <input
            id="drawing-set-name"
            className="field-control"
            required
            maxLength={255}
            value={name}
            aria-describedby={error ? "drawing-set-error" : undefined}
            onChange={(event) => setName(event.target.value)}
          />
        </FormField>
        <FormField label="Status" htmlFor="drawing-set-status" required>
          <select
            id="drawing-set-status"
            className="field-control"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
          </select>
        </FormField>
        <FormField label="Issue date" htmlFor="drawing-set-date">
          <input
            id="drawing-set-date"
            className="field-control"
            type="date"
            value={issueDate}
            onChange={(event) => setIssueDate(event.target.value)}
          />
        </FormField>
        <FormField label="Description" htmlFor="drawing-set-description">
          <textarea
            id="drawing-set-description"
            className="field-control"
            maxLength={10000}
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </FormField>
      </form>
    </DrawingDialog>
  );
}


export function DrawingSheetDialog({
  drawingSet,
  busy,
  onSubmit,
  onClose,
}) {
  const [values, setValues] = useState({
    sheet_number: "",
    title: "",
    discipline: "A",
    description: "",
    revision_code: "0",
    revision_date: formatLocalDateForApi(),
    revision_description: "",
  });
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const formId = "drawing-sheet-form";
  const update = (field, value) =>
    setValues((current) => ({ ...current, [field]: value }));

  const submit = async (event) => {
    event.preventDefault();
    const fileError = validateDrawingPdf(file);
    if (fileError) {
      setError(fileError);
      return;
    }
    setError("");
    const result = await onSubmit(
      drawingSet.id,
      {
        ...values,
        description: values.description || null,
        revision_description: values.revision_description || null,
      },
      file
    );
    if (result) onClose();
    else setError("The sheet could not be created. Your entries were kept.");
  };

  return (
    <DrawingDialog
      title="Add Drawing Sheet"
      eyebrow={drawingSet.name}
      busy={busy}
      onClose={onClose}
      actions={
        <>
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button
            form={formId}
            type="submit"
            variant="primary"
            disabled={busy}
          >
            {busy ? "Uploading..." : "Create Sheet"}
          </Button>
        </>
      }
    >
      <form id={formId} className="drawing-form" onSubmit={submit}>
        <ErrorText id="drawing-sheet-error" message={error} />
        <div className="drawing-form__grid">
          <FormField label="Sheet number" htmlFor="drawing-sheet-number" required>
            <input
              id="drawing-sheet-number"
              className="field-control"
              required
              maxLength={100}
              value={values.sheet_number}
              aria-describedby={error ? "drawing-sheet-error" : undefined}
              onChange={(event) => update("sheet_number", event.target.value)}
            />
          </FormField>
          <FormField label="Discipline" htmlFor="drawing-sheet-discipline" required>
            <select
              id="drawing-sheet-discipline"
              className="field-control"
              value={values.discipline}
              onChange={(event) => update("discipline", event.target.value)}
            >
              {DRAWING_DISCIPLINES.map(([code, label]) => (
                <option key={code} value={code}>{code} - {label}</option>
              ))}
            </select>
          </FormField>
        </div>
        <FormField label="Title" htmlFor="drawing-sheet-title" required>
          <input
            id="drawing-sheet-title"
            className="field-control"
            required
            maxLength={500}
            value={values.title}
            onChange={(event) => update("title", event.target.value)}
          />
        </FormField>
        <FormField label="Sheet description" htmlFor="drawing-sheet-description">
          <textarea
            id="drawing-sheet-description"
            className="field-control"
            rows={2}
            maxLength={10000}
            value={values.description}
            onChange={(event) => update("description", event.target.value)}
          />
        </FormField>
        <div className="drawing-form__grid">
          <FormField label="First revision" htmlFor="drawing-revision-code" required>
            <input
              id="drawing-revision-code"
              className="field-control"
              required
              maxLength={50}
              value={values.revision_code}
              onChange={(event) => update("revision_code", event.target.value)}
            />
          </FormField>
          <FormField label="Revision date" htmlFor="drawing-revision-date" required>
            <input
              id="drawing-revision-date"
              className="field-control"
              type="date"
              required
              value={values.revision_date}
              onChange={(event) => update("revision_date", event.target.value)}
            />
          </FormField>
        </div>
        <FormField label="Revision description" htmlFor="drawing-revision-description">
          <textarea
            id="drawing-revision-description"
            className="field-control"
            rows={2}
            maxLength={10000}
            value={values.revision_description}
            onChange={(event) =>
              update("revision_description", event.target.value)
            }
          />
        </FormField>
        <FormField
          label="PDF drawing"
          htmlFor="drawing-sheet-file"
          required
          hint="PDF only. The existing project upload-size limit applies."
        >
          <input
            id="drawing-sheet-file"
            className="field-control"
            type="file"
            accept=".pdf,application/pdf"
            required
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </FormField>
      </form>
    </DrawingDialog>
  );
}


export function DrawingRevisionDialog({
  sheet,
  busy,
  onSubmit,
  onClose,
}) {
  const [code, setCode] = useState("");
  const [date, setDate] = useState(formatLocalDateForApi());
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const formId = "drawing-revision-upload-form";

  const submit = async (event) => {
    event.preventDefault();
    const fileError = validateDrawingPdf(file);
    if (fileError) {
      setError(fileError);
      return;
    }
    setError("");
    const result = await onSubmit(
      sheet.id,
      {
        revision_code: code,
        revision_date: date,
        description: description || null,
      },
      file
    );
    if (result) onClose();
    else setError("The revision could not be uploaded. Your entries were kept.");
  };

  return (
    <DrawingDialog
      title={`Upload Revision - ${sheet.sheet_number}`}
      eyebrow="Controlled superseding"
      busy={busy}
      onClose={onClose}
      actions={
        <>
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button
            form={formId}
            type="submit"
            variant="primary"
            disabled={busy}
          >
            {busy ? "Uploading..." : "Upload New Revision"}
          </Button>
        </>
      }
    >
      <p className="drawing-supersede-note">
        Current revision {sheet.current_revision?.revision_code || "-"} will
        remain in revision history and become superseded.
      </p>
      <form id={formId} className="drawing-form" onSubmit={submit}>
        <ErrorText id="drawing-revision-error" message={error} />
        <div className="drawing-form__grid">
          <FormField label="Revision code" htmlFor="new-revision-code" required>
            <input
              id="new-revision-code"
              className="field-control"
              required
              maxLength={50}
              value={code}
              aria-describedby={error ? "drawing-revision-error" : undefined}
              onChange={(event) => setCode(event.target.value)}
            />
          </FormField>
          <FormField label="Revision date" htmlFor="new-revision-date" required>
            <input
              id="new-revision-date"
              className="field-control"
              type="date"
              required
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </FormField>
        </div>
        <FormField label="Description" htmlFor="new-revision-description">
          <textarea
            id="new-revision-description"
            className="field-control"
            rows={3}
            maxLength={10000}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </FormField>
        <FormField label="PDF drawing" htmlFor="new-revision-file" required>
          <input
            id="new-revision-file"
            className="field-control"
            type="file"
            accept=".pdf,application/pdf"
            required
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </FormField>
      </form>
    </DrawingDialog>
  );
}


export function DrawingIssueDialog({
  drawingSet,
  issue,
  busy,
  onSubmit,
  onClose,
}) {
  const [values, setValues] = useState({
    name: issue?.name || "",
    issue_number: issue?.issue_number || "",
    issue_date: issue?.issue_date || formatLocalDateForApi(),
    purpose: issue?.purpose || "construction",
    notes: issue?.notes || "",
  });
  const [error, setError] = useState("");
  const formId = "drawing-issue-form";
  const update = (field, value) =>
    setValues((current) => ({ ...current, [field]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    const result = await onSubmit({
      ...values,
      notes: values.notes || null,
    });
    if (result) onClose();
    else setError("The drawing issue could not be saved.");
  };

  return (
    <DrawingDialog
      title={issue ? "Edit Draft Issue" : "Create Draft Issue"}
      eyebrow={drawingSet.name}
      busy={busy}
      onClose={onClose}
      actions={
        <>
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button
            form={formId}
            type="submit"
            variant="primary"
            disabled={busy}
          >
            {busy ? "Saving..." : "Save Draft Issue"}
          </Button>
        </>
      }
    >
      <form id={formId} className="drawing-form" onSubmit={submit}>
        <ErrorText id="drawing-issue-error" message={error} />
        <FormField label="Issue name" htmlFor="drawing-issue-name" required>
          <input
            id="drawing-issue-name"
            className="field-control"
            required
            maxLength={255}
            value={values.name}
            aria-describedby={error ? "drawing-issue-error" : undefined}
            onChange={(event) => update("name", event.target.value)}
          />
        </FormField>
        <div className="drawing-form__grid">
          <FormField label="Issue number" htmlFor="drawing-issue-number" required>
            <input
              id="drawing-issue-number"
              className="field-control"
              required
              maxLength={100}
              value={values.issue_number}
              onChange={(event) => update("issue_number", event.target.value)}
            />
          </FormField>
          <FormField label="Issue date" htmlFor="drawing-issue-date" required>
            <input
              id="drawing-issue-date"
              className="field-control"
              type="date"
              required
              value={values.issue_date}
              onChange={(event) => update("issue_date", event.target.value)}
            />
          </FormField>
        </div>
        <FormField label="Purpose" htmlFor="drawing-issue-purpose" required>
          <select
            id="drawing-issue-purpose"
            className="field-control"
            value={values.purpose}
            onChange={(event) => update("purpose", event.target.value)}
          >
            {DRAWING_PURPOSES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Notes" htmlFor="drawing-issue-notes">
          <textarea
            id="drawing-issue-notes"
            className="field-control"
            rows={3}
            maxLength={10000}
            value={values.notes}
            onChange={(event) => update("notes", event.target.value)}
          />
        </FormField>
      </form>
    </DrawingDialog>
  );
}
