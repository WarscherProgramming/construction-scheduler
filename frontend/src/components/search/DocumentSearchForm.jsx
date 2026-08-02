import Button from "../ui/Button";
import Icon from "../ui/Icon";


function DocumentSearchForm({ query, onQueryChange, onSubmit, onClear, error }) {
  return (
    <form className="project-document-search-form" role="search" onSubmit={onSubmit}>
      <label htmlFor="project-document-search-query">Document content</label>
      <div className="project-document-search-form__controls">
        <input
          id="project-document-search-query"
          className="field-control"
          type="search"
          maxLength={200}
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          aria-describedby={error ? "project-document-search-error" : undefined}
          aria-invalid={Boolean(error)}
        />
        <Button variant="primary" type="submit">
          <Icon name="search" size={17} />
          Search
        </Button>
        <Button disabled={!query} onClick={onClear}>
          Clear
        </Button>
      </div>
      {error && (
        <p id="project-document-search-error" className="field-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}

export default DocumentSearchForm;
