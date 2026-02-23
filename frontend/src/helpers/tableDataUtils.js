function isTableLikeData(data) {
  return (
    Array.isArray(data) &&
    data.length > 0 &&
    data.every(
      (item) =>
        item !== null &&
        item !== undefined &&
        typeof item === "object" &&
        !Array.isArray(item)
    )
  );
}

/**
 * Splits a flat array of row-objects into groups where each group shares the
 * same set of column keys. Rows are grouped in order of first appearance.
 * @param {Array<Record<string, unknown>>} rows - Flat array of row objects
 * @return {Array<{name: string, data: Array<Record<string, unknown>>}>}
 */
function splitByColumns(rows) {
  const groups = [];
  const fingerMap = new Map();
  for (const row of rows) {
    const fp = Object.keys(row).sort().join("\0");
    if (fingerMap.has(fp)) {
      fingerMap.get(fp).push(row);
    } else {
      const arr = [row];
      fingerMap.set(fp, arr);
      groups.push(arr);
    }
  }
  if (groups.length <= 1) {
    return [{ name: "Table 1", data: rows }];
  }
  return groups.map((g, i) => ({ name: `Table ${i + 1}`, data: g }));
}

/**
 * Returns an array of {name, data} objects for multi-table display and export,
 * or null when no table-like data is found.
 * Handles: raw array (auto-split by column sets), object with one or more keys
 * whose values are table-like arrays, or a JSON string that parses to either.
 * @param {unknown} parsedOutput - Parsed prompt output
 * @return {Array<{name: string, data: Array<Record<string, unknown>>}> | null}
 */
function getMultiTableData(parsedOutput) {
  let data = parsedOutput;
  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch {
      return null;
    }
  }
  if (isTableLikeData(data)) return splitByColumns(data);
  if (typeof data === "object" && data !== null && !Array.isArray(data)) {
    const tables = [];
    for (const [key, val] of Object.entries(data)) {
      if (isTableLikeData(val)) {
        tables.push({ name: key, data: val });
      }
    }
    if (tables.length > 0) return tables;
  }
  return null;
}

function sanitizeSheetName(name, index) {
  let sheet = String(name)
    .replace(/[[\]:*?/\\]/g, "_")
    .slice(0, 31);
  if (!sheet) sheet = `Sheet${index + 1}`;
  return sheet;
}

export {
  isTableLikeData,
  splitByColumns,
  getMultiTableData,
  sanitizeSheetName,
};
