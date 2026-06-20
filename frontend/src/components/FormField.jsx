function FormField({ label, htmlFor, required = false, hint, children }) {
  return (
    <div className="field-group">
      <label className="field-label" htmlFor={htmlFor}>
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  );
}

export default FormField;
