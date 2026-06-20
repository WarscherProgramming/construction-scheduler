export function toLocalDateInputValue(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

export function sortByDateDescending(records) {
  return [...records].sort((left, right) => {
    const dateComparison = String(right.date || "").localeCompare(
      String(left.date || "")
    );

    if (dateComparison !== 0) return dateComparison;
    return Number(right.id || 0) - Number(left.id || 0);
  });
}
