import client from "./client";
import { makeResource } from "./resource";

const base = makeResource("/students");

export const studentsApi = {
  ...base,
  me: () => client.get("/students/me/").then((r) => r.data),
  transfer: (id, payload) => base.action(id, "transfer", payload),
  transferHistory: (id) => client.get(`/students/${id}/transfer-history/`).then((r) => r.data),
};
