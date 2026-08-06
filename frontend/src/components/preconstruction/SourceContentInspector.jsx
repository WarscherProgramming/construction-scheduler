import { useState } from "react";

import EmptyState from "../EmptyState";
import LoadingState from "../LoadingState";
import StatusBadge from "../StatusBadge";
import DrawingDialog from "../drawings/DrawingDialog";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


function SourceContentInspector({
  source,
  content,
  query,
  loading,
  error,
  onLoad,
  onClose,
  onNavigate,
}) {
  const [search, setSearch] = useState(query.search || "");
  const pagination = content?.pagination;
  const page = query.page ?? "";

  const submitSearch = (event) => {
    event.preventDefault();
    onLoad({ ...query, search: search.trim(), segmentOffset: 0 });
  };

  const openSource = () => {
    const target = content?.source.route_target || source.route_target;
    onNavigate(target.page, target.projectId, target);
  };

  return (
    <DrawingDialog
      title="Prepared Content"
      eyebrow={source.display_name}
      onClose={onClose}
      busy={loading}
      actions={
        <>
          <Button onClick={openSource}>
            <Icon name="arrow-right" size={16} /> Open Source
          </Button>
          <Button variant="primary" onClick={onClose}>Done</Button>
        </>
      }
    >
      <div className="preconstruction-content-inspector">
        {loading ? (
          <LoadingState message="Loading prepared content..." />
        ) : error ? (
          <div className="preconstruction-local-error" role="alert">
            <p>Prepared content could not be loaded.</p>
            <Button onClick={() => onLoad(query)}>Retry</Button>
          </div>
        ) : content ? (
          <>
            <section aria-labelledby="content-lineage-title">
              <div className="preconstruction-section-heading">
                <div>
                  <h3 id="content-lineage-title">Content Snapshot</h3>
                  <p>Immutable extraction and preparation lineage</p>
                </div>
                <StatusBadge value={content.snapshot.lineage_current ? "Current" : "Stale"} />
              </div>
              <dl className="preconstruction-content-lineage">
                <div><dt>Extraction</dt><dd>{content.snapshot.extraction_method}</dd></div>
                <div><dt>Pages</dt><dd>{content.snapshot.page_count}</dd></div>
                <div><dt>Segments</dt><dd>{content.snapshot.segment_count}</dd></div>
                <div><dt>Warnings</dt><dd>{content.snapshot.warning_count}</dd></div>
                <div><dt>Preparation</dt><dd>{content.snapshot.preparation_version}</dd></div>
                <div><dt>Fingerprint</dt><dd><code>{content.snapshot.lineage_fingerprint.slice(0, 16)}</code></dd></div>
              </dl>
              {!content.snapshot.lineage_current && (
                <p className="preconstruction-content-warning" role="status">
                  This historical snapshot no longer matches the current extraction lineage.
                </p>
              )}
            </section>

            <section aria-labelledby="content-segments-title">
              <div className="preconstruction-section-heading">
                <div>
                  <h3 id="content-segments-title">Content Segments</h3>
                  <p>Plain text, bounded by page</p>
                </div>
              </div>
              <form className="preconstruction-content-controls" onSubmit={submitSearch}>
                <label>
                  <span>Page</span>
                  <select
                    value={page}
                    onChange={(event) => onLoad({
                      ...query,
                      page: event.target.value ? Number(event.target.value) : null,
                      segmentOffset: 0,
                    })}
                  >
                    <option value="">All pages</option>
                    {content.pages.map((item) => (
                      <option key={item.id} value={item.page_number}>
                        {item.sheet_number ? `${item.sheet_number} - ` : ""}Page {item.page_label || item.page_number}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Search prepared text</span>
                  <input
                    value={search}
                    maxLength="200"
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </label>
                <Button type="submit"><Icon name="search" size={16} />Search</Button>
              </form>

              {content.segments.length ? (
                <ol className="preconstruction-content-segments" aria-label="Prepared content segments">
                  {content.segments.map((segment) => (
                    <li key={segment.id}>
                      <article>
                        <header>
                          <strong>Page {segment.page_number}, segment {segment.segment_index + 1}</strong>
                          <span>{segment.extraction_method}</span>
                        </header>
                        <pre>{segment.text}</pre>
                      </article>
                    </li>
                  ))}
                </ol>
              ) : (
                <EmptyState title="No matching content segments" announce={false} />
              )}

              <nav className="preconstruction-content-pagination" aria-label="Content segment pages">
                <Button
                  size="sm"
                  disabled={!pagination.offset}
                  onClick={() => onLoad({
                    ...query,
                    segmentOffset: Math.max(0, pagination.offset - pagination.limit),
                  })}
                >Previous</Button>
                <span>
                  {pagination.total
                    ? `${pagination.offset + 1}-${Math.min(pagination.offset + content.segments.length, pagination.total)} of ${pagination.total}`
                    : "0 segments"}
                </span>
                <Button
                  size="sm"
                  disabled={pagination.offset + pagination.limit >= pagination.total}
                  onClick={() => onLoad({
                    ...query,
                    segmentOffset: pagination.offset + pagination.limit,
                  })}
                >Next</Button>
              </nav>
              {pagination.response_truncated && (
                <p className="preconstruction-content-warning" role="status">
                  This response reached the configured character limit. Narrow the page or search.
                </p>
              )}
            </section>
          </>
        ) : null}
      </div>
    </DrawingDialog>
  );
}

export default SourceContentInspector;
