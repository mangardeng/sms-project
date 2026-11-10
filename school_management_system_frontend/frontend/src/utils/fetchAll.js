/**
 * Loads every page of a paginated list endpoint (the backend caps page_size at 200)
 * and returns one flat array. Also copes with endpoints that return a bare array.
 */
export async function fetchAll(api, params = {}, maxPages = 50) {
  const out = [];
  let page = 1;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const data = await api.list({ ...params, page, page_size: 200 });
    if (Array.isArray(data)) return data;
    out.push(...(data.results || []));
    if (!data.next || page >= (data.total_pages || maxPages) || page >= maxPages) break;
    page += 1;
  }
  return out;
}

/** Same as fetchAll but resolves to [] instead of throwing (e.g. a role without access to that list). */
export async function fetchAllSafe(api, params = {}) {
  try {
    return await fetchAll(api, params);
  } catch {
    return [];
  }
}
