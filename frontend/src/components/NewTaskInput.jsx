import { useRef } from "react";


function NewTaskInput({ value, onChange, onSave, onCancel }) {
  const skipBlurSave = useRef(false);

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      skipBlurSave.current = true;
      onSave();
    }

    if (event.key === "Escape") {
      event.preventDefault();
      skipBlurSave.current = true;
      onCancel();
    }
  };

  return (
    <input
      autoFocus
      aria-label="New task name"
      className="schedule-cell-input"
      value={value}
      onChange={(event) => {
        skipBlurSave.current = false;
        onChange(event.target.value);
      }}
      onBlur={() => {
        if (!skipBlurSave.current) onSave();
      }}
      onKeyDown={handleKeyDown}
    />
  );
}

export default NewTaskInput;
