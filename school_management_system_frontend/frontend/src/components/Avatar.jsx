import { useEffect, useState } from "react";

import { mediaUrl } from "../utils/media";
import { initialsFor } from "../utils/roles";

/** Round profile picture; falls back to the person's initials when there is no photo. */
export default function Avatar({ src, name, size = 36 }) {
  const url = mediaUrl(src);
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [url]);

  const style = { width: size, height: size, fontSize: Math.max(11, Math.round(size * 0.36)) };

  if (url && !failed) {
    return <img className="avatar-photo" src={url} alt={name || "Photo"} style={style} onError={() => setFailed(true)} />;
  }
  return (
    <span className="avatar-photo avatar-initials" style={style} aria-label={name || "No photo"}>
      {initialsFor(name)}
    </span>
  );
}
