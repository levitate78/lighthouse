/**
 * api.js — All communication with the Flask REST backend.
 *
 * CSRF strategy
 * ─────────────
 * In development Flask injects the token via a <meta name="csrf-token"> tag
 * in the Jinja2-rendered index.html.  In production nginx serves a pre-built
 * static bundle that has no Jinja2 processing, so the meta tag is absent.
 * To handle both environments uniformly the module always fetches the token
 * from GET /api/csrf-token on first use, falling back to the meta tag value
 * as a fast-path when it is already present (development only).
 *
 * Every state-mutating request (POST / PUT / PATCH / DELETE) includes the
 * X-CSRFToken header which Flask-WTF validates server-side.
 */

const API_BASE = import.meta.env.VITE_API_BASE || ''

// Cached CSRF token — populated by ensureCsrfToken() on first use.
let _csrfToken = ''

/**
 * Return the CSRF token, fetching it from the server if needed.
 * The meta tag is read first as a zero-cost fast-path (dev mode).
 * @returns {Promise<string>}
 */
async function ensureCsrfToken() {
  if (_csrfToken) return _csrfToken

  // Fast path: Flask injected the token into the page (development).
  const meta = document.querySelector('meta[name="csrf-token"]')
  if (meta?.content) {
    _csrfToken = meta.content
    return _csrfToken
  }

  // Slow path: fetch from the dedicated endpoint (production / SPA mode).
  try {
    const res = await fetch(API_BASE + '/api/csrf-token', { credentials: 'same-origin' })
    if (res.ok) {
      const data = await res.json()
      _csrfToken = data.csrf_token || ''
    }
  } catch (err) {
    console.error('[csrf] Failed to fetch CSRF token:', err)
  }
  return _csrfToken
}

/**
 * Build headers that include the CSRF token for mutating requests.
 * @param {Record<string,string>} [extra]
 * @returns {Promise<Record<string,string>>}
 */
async function csrfHeaders(extra = {}) {
  const token = await ensureCsrfToken()
  return token ? { ...extra, 'X-CSRFToken': token } : extra
}

/**
 * Handle non-OK fetch responses.
 * A 401 Unauthorized response means the session has expired; redirect to
 * /login so the user can re-authenticate.
 * @param {Response} response
 */
function handleResponseError(response) {
  if (response.status === 401) {
    // Session expired — redirect to the login page.
    window.location.href = '/login'
    // Throw so callers see a rejection rather than attempting to parse an
    // error body as data.
    throw new Error('Unauthorised — redirecting to login')
  }
  throw new Error(`${response.status} ${response.statusText}`)
}

/**
 * Generic GET request.
 * @param {string} path
 * @returns {Promise<any>}
 */
async function get(path) {
  const response = await fetch(API_BASE + path, { credentials: 'same-origin' })
  if (!response.ok) handleResponseError(response)
  return response.json()
}

/**
 * Generic mutating request (POST / DELETE / etc.).
 * @param {string} method
 * @param {string} path
 * @param {object|null} [body]
 * @returns {Promise<Response>}
 */
async function mutate(method, path, body = null) {
  const headers = await csrfHeaders(
    body !== null ? { 'Content-Type': 'application/json' } : {}
  )
  const response = await fetch(API_BASE + path, {
    method,
    headers,
    credentials: 'same-origin',
    body: body !== null ? JSON.stringify(body) : undefined,
  })
  return response
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Pre-fetch and cache the CSRF token.
 * Call this once during application boot so the token is ready before the
 * first mutating request is issued.
 * @returns {Promise<void>}
 */
export async function initCsrf() {
  await ensureCsrfToken()
}

/**
 * Fetch high-level status counts for the summary bar.
 * @returns {Promise<{total_projects: number, status_counts: Record<string,number>}>}
 */
export async function fetchSummary() {
  return get('/api/summary')
}

/**
 * Fetch all cached projects (each includes their latest pipeline inline).
 * Iterates through all pages to return the complete list.
 * @param {string} [branch='']
 * @returns {Promise<Array>}
 */
export async function fetchProjects(branch = '') {
  const perPage = 200
  let page = 1
  const allProjects = []
  const branchParam = branch ? `&branch=${encodeURIComponent(branch)}` : ''

  while (true) {
    const response = await get(`/api/projects?page=${page}&per_page=${perPage}${branchParam}`)
    allProjects.push(...response.projects)

    if (page >= response.pages || response.projects.length === 0) break
    page++
  }

  return allProjects
}

/**
 * Fetch recent pipelines for a single project.
 * @param {number} projectId
 * @param {number} [limit=15]
 * @param {string} [branch='']
 * @returns {Promise<Array>}
 */
export async function fetchPipelines(projectId, limit = 15, branch = '') {
  const branchParam = branch ? `&branch=${encodeURIComponent(branch)}` : ''
  return get(`/api/projects/${projectId}/pipelines?limit=${limit}${branchParam}`)
}

/**
 * Fetch all jobs for a specific pipeline.
 * @param {number} pipelineId
 * @returns {Promise<Array>}
 */
export async function fetchJobs(pipelineId) {
  return get(`/api/pipelines/${pipelineId}/jobs`)
}

/**
 * Fetch user's selected groups.
 * @returns {Promise<Array>}
 */
export async function fetchUserGroups() {
  return get('/api/user/groups')
}

/**
 * Add a group to user's selection.
 * @param {object} groupData
 * @returns {Promise<object>}
 */
export async function addUserGroup(groupData) {
  const response = await mutate('POST', '/api/user/groups', groupData)
  if (!response.ok) {
    let errorData = null
    try { errorData = await response.json() } catch { /* ignore */ }
    throw new Error(errorData?.error || `${response.status} ${response.statusText}`)
  }
  return response.json()
}

/**
 * Fetch current user info.
 * @returns {Promise<object>}
 */
export async function fetchCurrentUser() {
  return get('/api/user/current')
}

/**
 * Remove a group from user's selection.
 * @param {number} groupId
 * @returns {Promise<object>}
 */
export async function removeUserGroup(groupId) {
  const response = await mutate('DELETE', `/api/user/groups/${groupId}`)
  if (!response.ok) handleResponseError(response)
  return response.json()
}

/**
 * Trigger an immediate backend sync with GitLab.
 * @returns {Promise<{status: string, synced_at: string}>}
 */
export async function triggerSync() {
  const response = await mutate('POST', '/api/sync')
  if (!response.ok) handleResponseError(response)
  return response.json()
}

/**
 * Update the user's GitLab personal access token.
 * @param {string} token
 * @returns {Promise<object>}
 */
export async function updateGitlabToken(token) {
  const response = await mutate('POST', '/api/user/gitlab-token', { token })
  const data = await response.json()
  if (!response.ok) throw new Error(data?.error || `${response.status} ${response.statusText}`)
  return data
}

/**
 * Approve a user (admin only).
 * @param {number} userId
 * @returns {Promise<object>}
 */
export async function approveUser(userId) {
  const response = await mutate('POST', `/api/admin/users/${userId}/approve`)
  if (!response.ok) handleResponseError(response)
  return response.json()
}

/**
 * Reject and delete a user (admin only).
 * @param {number} userId
 * @returns {Promise<object>}
 */
export async function rejectUser(userId) {
  const response = await mutate('POST', `/api/admin/users/${userId}/reject`)
  if (!response.ok) handleResponseError(response)
  return response.json()
}

/**
 * Fetch all users (admin only).
 * @returns {Promise<Array>}
 */
export async function fetchAdminUsers() {
  return get('/api/admin/users')
}

/**
 * Fetch active sync status.
 * @returns {Promise<Array>}
 */
export async function fetchSyncStatus() {
  return get('/api/sync/status')
}