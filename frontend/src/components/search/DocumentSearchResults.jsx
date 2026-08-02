import DocumentSearchResultItem from "./DocumentSearchResultItem";


function DocumentSearchResults({ results, onOpen }) {
  return (
    <ol className="project-document-search-results">
      {results.map((result, index) => (
        <DocumentSearchResultItem
          key={`${result.document_id}:${result.page_number || 0}:${index}`}
          result={result}
          onOpen={onOpen}
        />
      ))}
    </ol>
  );
}

export default DocumentSearchResults;
