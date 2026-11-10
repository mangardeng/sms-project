import client from "./client";
import { makeResource } from "./resource";

export const feeStructuresApi = makeResource("/fees/structures");

export const paymentsApi = {
  ...makeResource("/fees/payments"),
  correct: (id, payload) => client.patch(`/fees/payments/${id}/`, payload).then((r) => r.data),
  void: (id, reason) => client.post(`/fees/payments/${id}/void/`, { reason }).then((r) => r.data),
  history: (id) => client.get(`/fees/payments/${id}/history/`).then((r) => r.data),
};

export const sponsorsApi = makeResource("/fees/sponsors");
export const sponsorshipsApi = {
  ...makeResource("/fees/sponsorships"),
  report: (term) => client.get("/fees/sponsorships/report/", { params: { term } }).then((r) => r.data),
};
export const carryForwardApi = {
  ...makeResource("/fees/carry-forward"),
  generate: (payload) => client.post("/fees/carry-forward/generate/", payload).then((r) => r.data),
};
export const expensesApi = makeResource("/fees/expenses");
export const otherIncomeApi = makeResource("/fees/other-income");
export const salariesApi = {
  ...makeResource("/fees/salaries"),
  staff: () => client.get("/fees/salaries/staff/").then((r) => r.data),
  generate: (payload) => client.post("/fees/salaries/generate/", payload).then((r) => r.data),
  markPaid: (id, payload = {}) => client.post(`/fees/salaries/${id}/mark-paid/`, payload).then((r) => r.data),
};

export const financeApi = {
  summary: (params) => client.get("/fees/finance/summary/", { params }).then((r) => r.data),
  arrears: (params) => client.get("/fees/finance/arrears/", { params }).then((r) => r.data),
};

export function getFeeBalance(studentId) {
  return client.get("/fees/balance/", { params: { student: studentId } }).then((r) => r.data);
}
