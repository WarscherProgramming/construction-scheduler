import Button from "../ui/Button";
import Icon from "../ui/Icon";


function buildChildren(folders) {
  const children = new Map();
  for (const folder of folders) {
    const parentId = folder.parent_folder_id ?? null;
    const siblings = children.get(parentId) || [];
    siblings.push(folder);
    children.set(parentId, siblings);
  }
  for (const siblings of children.values()) {
    siblings.sort(
      (left, right) =>
        left.name.localeCompare(right.name, undefined, {
          sensitivity: "base",
        }) || left.id - right.id
    );
  }
  return children;
}


function FolderBranch({
  parentId,
  depth,
  children,
  activeFolderId,
  onSelect,
}) {
  const folders = children.get(parentId) || [];
  if (folders.length === 0) return null;

  return (
    <ul className="document-folder-tree__list">
      {folders.map((folder) => (
        <li key={folder.id}>
          <button
            type="button"
            className={`document-folder-tree__item${
              activeFolderId === folder.id
                ? " document-folder-tree__item--active"
                : ""
            }`}
            style={{ "--folder-depth": depth }}
            aria-current={
              activeFolderId === folder.id ? "location" : undefined
            }
            onClick={() => onSelect(folder.id)}
          >
            <Icon name="folder" size={17} />
            <span className="document-folder-tree__name">{folder.name}</span>
            <span
              className="document-folder-tree__count"
              aria-label={`${folder.document_count} documents`}
            >
              {folder.document_count}
            </span>
          </button>
          <FolderBranch
            parentId={folder.id}
            depth={depth + 1}
            children={children}
            activeFolderId={activeFolderId}
            onSelect={onSelect}
          />
        </li>
      ))}
    </ul>
  );
}


function DocumentFolderTree({
  folders,
  activeFolderId,
  isLoading,
  isOpen,
  onToggle,
  onSelect,
}) {
  const children = buildChildren(folders);

  return (
    <aside
      className={`document-folder-panel${
        isOpen ? " document-folder-panel--open" : ""
      }`}
      aria-label="Document folders"
    >
      <div className="document-folder-panel__header">
        <h2>Folders</h2>
        <Button
          size="sm"
          variant="ghost"
          className="document-folder-panel__toggle"
          aria-expanded={isOpen}
          aria-controls="document-folder-navigation"
          onClick={onToggle}
        >
          <Icon name={isOpen ? "chevron-down" : "chevron-right"} size={17} />
          {isOpen ? "Hide" : "Browse"}
        </Button>
      </div>
      <nav
        id="document-folder-navigation"
        className="document-folder-tree"
        aria-label="Folder tree"
      >
        <button
          type="button"
          className={`document-folder-tree__item${
            activeFolderId == null
              ? " document-folder-tree__item--active"
              : ""
          }`}
          aria-current={activeFolderId == null ? "location" : undefined}
          onClick={() => onSelect(null)}
        >
          <Icon name="home" size={17} />
          <span className="document-folder-tree__name">Project root</span>
        </button>
        {isLoading ? (
          <p className="document-folder-tree__status" role="status">
            Loading folders...
          </p>
        ) : folders.length === 0 ? (
          <p className="document-folder-tree__status">No folders yet.</p>
        ) : (
          <FolderBranch
            parentId={null}
            depth={1}
            children={children}
            activeFolderId={activeFolderId}
            onSelect={onSelect}
          />
        )}
      </nav>
    </aside>
  );
}

export default DocumentFolderTree;
