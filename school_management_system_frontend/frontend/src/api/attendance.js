import client from "./client";
import { makeResource } from "./resource";

const base = makeResource("/attendance");

export const attendanceApi = {
  ...base,
  bulkRecord: (payload) => client.post("/attendance/bulk-record/", payload).then((r) => r.data),
  classSummary: (params) => client.get("/attendance/class-summary/", { params }).then((r) => r.data),
};
