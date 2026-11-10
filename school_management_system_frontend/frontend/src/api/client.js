import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

const ACCESS_KEY = "sms_access_token";
const REFRESH_KEY = "sms_refresh_token";

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  setTokens: (access, refresh) => {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  setAccess: (access) => localStorage.setItem(ACCESS_KEY, access),
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

const client = axios.create({
  baseURL: BASE_URL,
});

client.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Prevents a stampede of parallel refresh calls when several requests
// 401 at the same moment (e.g. a dashboard firing multiple fetches).
let refreshPromise = null;

function performRefresh() {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return Promise.reject(new Error("No refresh token available."));

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${BASE_URL}/auth/token/refresh/`, { refresh })
      .then((res) => {
        tokenStore.setAccess(res.data.access);
        return res.data.access;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error;

    if (!response) {
      return Promise.reject(error);
    }

    const isAuthEndpoint =
      config.url?.includes("/auth/login/") || config.url?.includes("/auth/token/refresh/");

    if (response.status === 401 && !config._retried && !isAuthEndpoint) {
      config._retried = true;
      try {
        const newAccess = await performRefresh();
        config.headers.Authorization = `Bearer ${newAccess}`;
        return client(config);
      } catch (refreshError) {
        tokenStore.clear();
        window.dispatchEvent(new CustomEvent("sms:session-expired"));
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/** Pulls a friendly message out of DRF's various error response shapes. */
export function extractErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  const data = error?.response?.data;
  if (!data) return error?.message || fallback;
  if (typeof data === "string") return data;

  // The backend wraps validation failures as { detail: "Validation error.", errors: {...} }.
  // Show the real reason instead of the generic label.
  if (data.errors) {
    const messages = flattenErrors(data.errors);
    if (messages.length) return messages.join(" ");
  }
  if (data.detail && typeof data.detail === "string" && data.detail !== GENERIC_VALIDATION) return data.detail;

  const messages = flattenErrors(Object.fromEntries(Object.entries(data).filter(([k]) => k !== "code")));
  if (messages.length) return messages.join(" ");
  return fallback;
}

export default client;
