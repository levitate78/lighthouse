/**
 * api.js — All communication with the Flask REST backend.
 *
 * Every function returns a Promise that resolves to parsed JSON,
 * or rejects with an Error containing the HTTP status message.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '';

/**
 * Generic GET wrapper.
 * @param {string} path
 * @returns {Promise<any>}
 */
async function get(path) {
  const response = await fetch(API_BASE + path)
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json()
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
 * @returns {Promise<Array>}
 */
export async function fetchProjects() {
  const response = await get('/api/projects')
  return response.projects
}

/**
 * Fetch recent pipelines for a single project.
 * @param {number} projectId
 * @param {number} [limit=15]
 * @returns {Promise<Array>}
 */
export async function fetchPipelines(projectId, limit = 15) {
  return get(`/api/projects/${projectId}/pipelines?limit=${limit}`)
}

/**
 * Fetch all jobs for a specific pipeline.
 * @param {number} pipelineId
 * @returns {Promise<Array>}
 */
export async function fetchJobs(pipelineId) {
  return get(`/api/pipelines/${pipelineId}/jobs`)
}

/** * Fetch user's selected groups.
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
  const response = await fetch('/api/user/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(groupData)
  })
  if (!response.ok) {
    // Try to parse JSON error response
    try {
      const errorData = await response.json()
      throw new Error(errorData.error || `${response.status} ${response.statusText}`)
    } catch (jsonError) {
      // If JSON parsing fails, use the status text
      throw new Error(`${response.status} ${response.statusText}`)
    }
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
  const response = await fetch(`/api/user/groups/${groupId}`, {
    method: 'DELETE'
  })
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json()
}

/** * Trigger an immediate backend sync with GitLab.
 * @returns {Promise<{status: string, synced_at: string}>}
 */
export async function triggerSync() {
  const response = await fetch('/api/sync', { method: 'POST' })
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json()
}