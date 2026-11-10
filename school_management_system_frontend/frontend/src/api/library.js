import client from "./client";
import { makeResource } from "./resource";

export const booksApi = makeResource("/library");

const borrowingBase = makeResource("/library/borrowing");
export const borrowingApi = {
  ...borrowingBase,
  markReturned: (id) => client.post(`/library/borrowing/${id}/mark_returned/`).then((r) => r.data),
  overdue: () => client.get("/library/borrowing/overdue/").then((r) => r.data),
};
