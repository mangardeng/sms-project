import { makeResource } from "./resource";

export const subjectsApi = makeResource("/subjects");
export const classSubjectsApi = makeResource("/subjects/assignments");
