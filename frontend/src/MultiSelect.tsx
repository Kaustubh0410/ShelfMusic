import { useEffect, useRef, useState } from "react";

// A compact multi-select dropdown with a search box, for genre/artist/mood.
export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  searchable = false,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  searchable?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const shown = searchable && query
    ? options.filter((o) => o.toLowerCase().includes(query.toLowerCase()))
    : options;

  function toggle(opt: string) {
    onChange(selected.includes(opt) ? selected.filter((s) => s !== opt) : [...selected, opt]);
  }

  return (
    <div className="ms" ref={ref}>
      <button className="ms-trigger" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="ms-label">{label}</span>
        <span className="ms-count">
          {selected.length > 0 ? `${selected.length} selected` : "Any"}
        </span>
        <span className="ms-caret">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="ms-panel">
          {searchable && (
            <input
              className="ms-search"
              placeholder={`Search ${label.toLowerCase()}…`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
          )}
          <div className="ms-options">
            {shown.slice(0, 200).map((opt) => (
              <label key={opt} className="ms-option">
                <input
                  type="checkbox"
                  checked={selected.includes(opt)}
                  onChange={() => toggle(opt)}
                />
                <span>{opt}</span>
              </label>
            ))}
            {shown.length === 0 && <div className="ms-empty">No matches</div>}
          </div>
          {selected.length > 0 && (
            <button className="ms-clear" onClick={() => onChange([])}>Clear</button>
          )}
        </div>
      )}
    </div>
  );
}
