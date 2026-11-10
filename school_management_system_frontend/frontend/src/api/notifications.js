import client from "./client";
import { makeResource } from "./resource";

const base = makeResource("/notifications");

export const notificationsApi = {
  ...base,
  markRead: (id) => client.post(`/notifications/${id}/mark_read/`).then((r) => r.data),
  markAllRead: () => client.post("/notifications/mark-all-read/").then((r) => r.data),
  unreadCount: () => client.get("/notifications/unread-count/").then((r) => r.data),
  broadcast: (payload) => client.post("/notifications/broadcast/", payload).then((r) => r.data),
};
