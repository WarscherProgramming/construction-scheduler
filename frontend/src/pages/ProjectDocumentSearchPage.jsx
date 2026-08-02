import { useEffect, useRef, useState } from "react";

import DocumentSearchForm from "../components/search/DocumentSearchForm";
import DocumentSearchResults from "../components/search/DocumentSearchResults";
import SearchFilterBar from "../components/search/SearchFilterBar";
import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import useDocumentSearch from "../hooks/useDocumentSearch";
import {
  INITIAL_DOCUMENT_SEARCH_FILTERS,
  searchResultNavigation,
} from "../utils/documentSearch";


function ProjectDocumentSearchPage({
  projectId,
  projectName = "Project",
  onNavigate,
  onLogout,
  onRequestError,
}) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    ...INITIAL_DOCUMENT_SEARCH_FILTERS,
  });
  const [validationError, setValidationError] = useState("");
  const summaryRef = useRef(null);
  const search = useDocumentSearch({ projectId, onError: onRequestError });

  useEffect(() => {
    if (search.data) summaryRef.current?.focus();
  }, [search.data]);

  const submit = (event) => {
    event.preventDefault();
    const normalized = query.trim();
    if (!normalized) {
      setValidationError("Search query is required.");
      return;
    }
    setValidationError("");
    void search.submit(normalized, filters);
  };

  const clear = () => {
    setQuery("");
    setValidationError("");
    search.clear();
  };

  const openResult = (result) => {
    const target = searchResultNavigation(result, projectId);
    onNavigate(target.page, target.projectId, target.options);
  };

  const pagination = search.data?.pagination;
  return (
    <ProjectLayout
      projectName={projectName}
      activeId="projectDocumentSearch"
      onNavigate={onNavigate}
      onLogout={onLogout}
      mainClassName="project-document-search-page"
    >
      <PageHeader title="Document Search" eyebrow={projectName} />
      <section className="project-document-search-controls" aria-label="Document search controls">
        <DocumentSearchForm
          query={query}
          onQueryChange={(value) => {
            setQuery(value);
            if (validationError) setValidationError("");
          }}
          onSubmit={submit}
          onClear={clear}
          error={validationError}
        />
        <SearchFilterBar filters={filters} onChange={setFilters} />
      </section>

      <section className="project-document-search-content" aria-labelledby="project-document-search-results-title">
        {search.isLoading ? (
          <LoadingState message="Searching project documents..." />
        ) : search.error ? (
          <div className="project-document-search-state" role="alert">
            <Icon name="alert-triangle" size={22} />
            <h2 id="project-document-search-results-title">Search unavailable</h2>
            <p>{search.error.message}</p>
            <Button onClick={search.retry}>
              <Icon name="refresh" size={16} />
              Retry
            </Button>
          </div>
        ) : search.data ? (
          <>
            <div
              ref={summaryRef}
              className="project-document-search-summary"
              tabIndex="-1"
              aria-live="polite"
            >
              <h2 id="project-document-search-results-title">Search Results</h2>
              <p>
                {pagination.total} {pagination.total === 1 ? "result" : "results"} for &quot;{search.data.query}&quot;
              </p>
            </div>
            {search.data.results.length ? (
              <DocumentSearchResults
                results={search.data.results}
                onOpen={openResult}
              />
            ) : (
              <EmptyState title="No matching documents" announce={false} />
            )}
            {pagination.total > 0 && (
              <nav className="project-document-search-pagination" aria-label="Search result pages">
                <Button
                  size="sm"
                  disabled={pagination.offset === 0}
                  onClick={() =>
                    search.goToOffset(
                      Math.max(0, pagination.offset - pagination.limit)
                    )
                  }
                >
                  <Icon name="chevron-left" size={16} />
                  Previous
                </Button>
                <span>
                  {pagination.offset + 1}-{Math.min(
                    pagination.offset + search.data.results.length,
                    pagination.total
                  )} of {pagination.total}
                </span>
                <Button
                  size="sm"
                  disabled={!pagination.has_more}
                  onClick={() =>
                    search.goToOffset(pagination.offset + pagination.limit)
                  }
                >
                  Next
                  <Icon name="chevron-right" size={16} />
                </Button>
              </nav>
            )}
          </>
        ) : (
          <div className="project-document-search-state">
            <h2 id="project-document-search-results-title">No search submitted</h2>
          </div>
        )}
      </section>
    </ProjectLayout>
  );
}

export default ProjectDocumentSearchPage;
