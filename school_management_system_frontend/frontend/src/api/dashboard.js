import client from "./client";

export function fetchDashboard() {
  return client.get("/dashboard/").then((r) => r.data);
}
