import { useState } from "react";

import { PDF_SEARCH_QUERY_MAX } from "../../../utils/pdfViewer";
import Button from "../../ui/Button";
import Icon from "../../ui/Icon";


function DrawingSearchPanel({ search, onSearch, onPrevious, onNext, onClear }) {
  const [query, setQuery] = useState(search.query);

  const status = search.isIndexing
    ? "Indexing searchable text..."
    : search.hasText === false
      ? "Searchable text is not available for this revision."
      : search.error
        ? search.error
        : search.query && search.matches.length === 0
          ? "No matches"
          : search.matches.length
            ? `${search.matchIndex + 1} of ${search.matches.length} matches`
            : "Search uses the PDF's existing text only.";

  return (
    <section className="drawing-search-panel" aria-labelledby="drawing-search-title">
      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault();
          void onSearch(query);
        }}
      >
        <label id="drawing-search-title" htmlFor="drawing-pdf-search">Search Drawing</label>
        <div>
          <input
            id="drawing-pdf-search"
            type="search"
            maxLength={PDF_SEARCH_QUERY_MAX}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search existing PDF text"
          />
          <Button size="sm" type="submit" disabled={!query.trim() || search.isIndexing}>
            <Icon name="search" size={15} />
            Search
          </Button>
          <Button
            size="sm"
            type="button"
            disabled={!search.matches.length}
            onClick={onPrevious}
          >
            Previous Match
          </Button>
          <Button
            size="sm"
            type="button"
            disabled={!search.matches.length}
            onClick={onNext}
          >
            Next Match
          </Button>
          <Button
            size="sm"
            type="button"
            disabled={!query && !search.query}
            onClick={() => {
              setQuery("");
              onClear();
            }}
          >
            Clear
          </Button>
        </div>
      </form>
      <p className="drawing-search-status" role="status" aria-live="polite">{status}</p>
    </section>
  );
}

export default DrawingSearchPanel;
