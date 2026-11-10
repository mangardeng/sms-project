import client from "./client";
import { makeResource } from "./resource";

const base = makeResource("/teachers");

export const teachersApi = {
  ...base,
  me: () => client.get("/teachers/me/").then((r) => r.data),
};
