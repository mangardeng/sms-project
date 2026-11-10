import client, { tokenStore } from "./client";

export async function login(identifier, password) {
  const { data } = await client.post("/auth/login/", { username: identifier, password });
  tokenStore.setTokens(data.access, data.refresh);
  return data; // { access, refresh, user, dashboard }
}

export async function logout() {
  const refresh = tokenStore.getRefresh();
  try {
    if (refresh) await client.post("/auth/logout/", { refresh });
  } finally {
    tokenStore.clear();
  }
}

export function fetchMe() {
  return client.get("/auth/me/").then((r) => r.data);
}

export function updateMe(payload) {
  return client.patch("/auth/me/", payload).then((r) => r.data);
}

export function changePassword(oldPassword, newPassword) {
  return client
    .post("/auth/change-password/", { old_password: oldPassword, new_password: newPassword })
    .then((r) => r.data);
}

// ---- Admin user management -------------------------------------------------
export const usersApi = {
  list: (params) => client.get("/auth/users/", { params }).then((r) => r.data),
  create: (payload) => client.post("/auth/users/", payload).then((r) => r.data),
  update: (id, payload) => client.patch(`/auth/users/${id}/`, payload).then((r) => r.data),
  remove: (id) => client.delete(`/auth/users/${id}/`),
  activate: (id) => client.post(`/auth/users/${id}/activate/`).then((r) => r.data),
  deactivate: (id) => client.post(`/auth/users/${id}/deactivate/`).then((r) => r.data),
  resetPassword: (id, newPassword) =>
    client.post(`/auth/users/${id}/reset-password/`, { new_password: newPassword }).then((r) => r.data),
  unlock: (id) => client.post(`/auth/users/${id}/unlock/`).then((r) => r.data),
};
