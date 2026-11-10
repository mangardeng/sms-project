import { useEffect, useRef, useState } from "react";

import { mediaUrl } from "../utils/media";

const MAX_BYTES = 5 * 1024 * 1024;

/**
 * Image picker with live preview.
 *   value:    File (newly chosen) | string (existing URL from the API) | ""
 *   existing: the URL that was saved before editing began (shown again if the
 *             user discards a newly chosen file)
 */
export default function PhotoInput({ id, name, value, existing, onChange, onError }) {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState("");
  const [localError, setLocalError] = useState("");

  const isNewFile = typeof File !== "undefined" && value instanceof File;

  useEffect(() => {
    if (isNewFile) {
      const url = URL.createObjectURL(value);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreview(value ? mediaUrl(value) : "");
    return undefined;
  }, [value, isNewFile]);

  function handlePick(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setLocalError("Please choose an image file (JPG, PNG, WEBP…).");
      e.target.value = "";
      return;
    }
    if (file.size > MAX_BYTES) {
      setLocalError("That image is larger than 5 MB. Please choose a smaller one.");
      e.target.value = "";
      return;
    }
    setLocalError("");
    onError?.();
    onChange(name, file);
  }

  function handleDiscard() {
    setLocalError("");
    if (inputRef.current) inputRef.current.value = "";
    onChange(name, existing || "");
  }

  return (
    <div className="photo-input">
      <div className="photo-preview">
        {preview ? <img src={preview} alt="Preview" /> : <span>No photo</span>}
      </div>
      <div className="photo-controls">
        <input ref={inputRef} id={id} name={name} type="file" accept="image/*" onChange={handlePick} />
        {isNewFile && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleDiscard}>
            Discard new photo
          </button>
        )}
        {localError && <span className="field-error">{localError}</span>}
      </div>
    </div>
  );
}
