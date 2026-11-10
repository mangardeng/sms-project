const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

/**
 * Turns an uploaded-file path from the API (e.g. "/media/student_photos/a.png")
 * into a URL the browser can load. Absolute URLs, blob: and data: URLs
 * (used for local previews) are returned untouched.
 */
export function mediaUrl(path) {
  if (!path) return "";
  if (/^(https?:|blob:|data:)/i.test(path)) return path;
  const origin = API_BASE.replace(/\/api\/?$/, "");
  return `${origin}${path.startsWith("/") ? "" : "/"}${path}`;
}
