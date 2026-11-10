import client from "./client";
import { makeResource } from "./resource";

export const examinationTypesApi = makeResource("/examinations/types");
export const examinationsApi = {
  ...makeResource("/examinations"),
  publish: (id) => client.post(`/examinations/${id}/publish/`).then((r) => r.data),
};
export const examinationResultsApi = {
  ...makeResource("/examinations/results"),
  bulkEntry: (payload) => client.post("/examinations/results/bulk-entry/", payload).then((r) => r.data),
};

// Grading scale (e.g. 80+ = A). Editing it re-grades everything on the server.
export const gradeScaleApi = makeResource("/examinations/grade-scale");

// Computed automatically from Midterm + End-of-term marks (read-only).
export const termResultsApi = makeResource("/examinations/term-results");
export const termSummariesApi = {
  ...makeResource("/examinations/term-summaries"),
  reportCard: (id) => client.get(`/examinations/term-summaries/${id}/report-card/`).then((r) => r.data),
  recompute: (payload) => client.post("/examinations/term-summaries/recompute/", payload).then((r) => r.data),
};

// One sheet per class + subject + term: the subject teacher types midterm and end-of-term marks,
// everything else (total, %, grade, remark, positions) is calculated by the server.
export const subjectSheetApi = {
  options: () => client.get("/examinations/subject-sheet/options/").then((r) => r.data),
  get: (params) => client.get("/examinations/subject-sheet/", { params }).then((r) => r.data),
  save: (payload) => client.post("/examinations/subject-sheet/", payload).then((r) => r.data),
};
