import client from "./client";

const isFile = (v) => typeof File !== "undefined" && v instanceof File;

/**
 * Sends JSON normally, but switches to multipart/form-data automatically when
 * the payload contains a File (e.g. a student/teacher photo).
 * Note: with multipart, DRF treats a missing checkbox as "false", so forms that
 * can contain a file must always include their checkbox fields (ResourceForm does).
 */
export function toRequestBody(payload) {
  if (!payload || !Object.values(payload).some(isFile)) return payload;
  const form = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined) return;
    if (value === null) form.append(key, "");
    else if (Array.isArray(value)) value.forEach((item) => form.append(key, item));
    else if (typeof value === "boolean") form.append(key, value ? "true" : "false");
    else form.append(key, value);
  });
  return form;
}

/**
 * Generic REST resource factory matching our DRF ViewSet conventions
 * (list/create/retrieve/update/partial_update/destroy) and the
 * StandardResultsPagination response shape
 * ({count, total_pages, current_page, next, previous, results}).
 */
export function makeResource(basePath) {
  const url = (suffix = "") => `${basePath}${suffix}`;

  return {
    list: (params = {}) => client.get(url("/"), { params }).then((r) => r.data),
    get: (id) => client.get(url(`/${id}/`)).then((r) => r.data),
    create: (payload) => client.post(url("/"), toRequestBody(payload)).then((r) => r.data),
    update: (id, payload) => client.patch(url(`/${id}/`), toRequestBody(payload)).then((r) => r.data),
    replace: (id, payload) => client.put(url(`/${id}/`), toRequestBody(payload)).then((r) => r.data),
    remove: (id) => client.delete(url(`/${id}/`)),
    action: (id, actionName, payload = {}, method = "post") =>
      client[method](url(`/${id}/${actionName}/`), payload).then((r) => r.data),
    listAction: (actionName, params = {}) =>
      client.get(url(`/${actionName}/`), { params }).then((r) => r.data),
    postAction: (actionName, payload = {}) =>
      client.post(url(`/${actionName}/`), payload).then((r) => r.data),
  };
}
