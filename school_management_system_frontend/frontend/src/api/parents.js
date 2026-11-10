import client from "./client";
import { makeResource } from "./resource";

export const parentsApi = makeResource("/parents");

export const parentLinksApi = {
  list: (params) => client.get("/parents/links/", { params }).then((r) => r.data),
  create: (payload) => client.post("/parents/links/", payload).then((r) => r.data),
  remove: (id) => client.delete(`/parents/links/${id}/`),
};
