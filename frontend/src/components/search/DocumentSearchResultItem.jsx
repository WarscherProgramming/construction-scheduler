import { formatAttachmentDateTime } from "../../utils/attachment";
import {
  extractionMethodLabel,
  snippetSegments,
} from "../../utils/documentSearch";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


function DocumentSearchResultItem({ result, onOpen }) {
  const drawingLabel = result.sheet_number
    ? `${result.sheet_number} - ${result.sheet_title}`
    : null;
  return (
    <li>
      <article className="project-document-search-result">
        <div className="project-document-search-result__heading">
          <div>
            <p className="project-document-search-result__type">
              {result.result_type === "drawing_revision"
                ? "Drawing revision"
                : result.document_type}
            </p>
            <h3>{drawingLabel || result.display_name}</h3>
            {drawingLabel && <p>{result.display_name}</p>}
          </div>
          <Button
            size="sm"
            onClick={() => onOpen(result)}
            aria-label={`Open ${drawingLabel || result.display_name}`}
          >
            Open
            <Icon name="arrow-right" size={16} />
          </Button>
        </div>
        <p className="project-document-search-result__snippet">
          {snippetSegments(result.snippet, result.match_ranges).map(
            (segment, index) =>
              segment.match ? (
                <mark key={`${index}-${segment.text}`}>{segment.text}</mark>
              ) : (
                <span key={`${index}-${segment.text}`}>{segment.text}</span>
              )
          )}
        </p>
        <dl className="project-document-search-result__metadata">
          {result.revision_code && (
            <div><dt>Revision</dt><dd>{result.revision_code} ({result.revision_status})</dd></div>
          )}
          {result.page_number && (
            <div><dt>Page</dt><dd>{result.page_number}</dd></div>
          )}
          <div>
            <dt>Text source</dt>
            <dd>{extractionMethodLabel(result.extraction_method)}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatAttachmentDateTime(result.updated_at)}</dd>
          </div>
        </dl>
      </article>
    </li>
  );
}

export default DocumentSearchResultItem;
