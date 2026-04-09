/**
 * app.js — Application state, event wiring, and boot sequence.
 *
 * This is the only module that holds mutable state and orchestrates
 * calls between api.js and render.js.
 */

import {
  fetchSummary,
  fetchProjects,
  fetchPipelines,
  fetchJobs,
  triggerSync,
  fetchUserGroups,
  addUserGroup,
  removeUserGroup,
  fetchCurrentUser,
} from './api.js'

import { esc } from './utils.js'

function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || ''
}

function csrfHeaders(headers = {}) {
  const token = getCsrfToken()
  return token ? { ...headers, 'X-CSRFToken': token } : headers
}

import {
  renderSummary,
  renderSidebar,
  renderMainEmpty,
  renderMainLoading,
  renderMainError,
  renderProjectDetail,
  renderJobsLoading,
  renderJobs,
  renderJobsError,
  setActivePipelineRow,
  setSyncSpinning,
  setLastSync,
  renderUserInfo,
  renderGroups,
} from './render.js'

// ── Application state ──────────────────────────────────────────────────────

const state = {
  /** @type {object|null} Current user */
  user: null,
  /** @type {Array} User's selected groups */
  groups: [],
  /** @type {Array} All projects returned from the API */
  projects: [],
  /** @type {object|null} Currently selected project */
  activeProject: null,
  /** @type {number|null} Currently displayed pipeline's ID */
  activePipelineId: null,
}

// ── Group management ──────────────────────────────────────────────────────

async function handleRemoveGroup(groupId) {
  try {
    // Find the group being removed to get its full path
    const removedGroup = state.groups.find(g => g.group_id === groupId)
    
    await removeUserGroup(groupId)
    state.groups = state.groups.filter(g => g.group_id !== groupId)
    
    // Remove projects that belong to the removed group
    if (removedGroup) {
      state.projects = state.projects.filter(p => p.group_id !== removedGroup.group_id)
      
      // If the currently active project was removed, clear the selection
      if (state.activeProject && state.projects.find(p => p.id === state.activeProject.id) === undefined) {
        state.activeProject = null
        state.activePipelineId = null
        renderMainEmpty()
      }
    }
    
    renderGroups(state.groups, handleRemoveGroup)
    renderSidebar(state.projects, state.activeProject?.id, selectProject)
    
    // Trigger sync after removing group
    setSyncSpinning(true)
    try {
      await triggerSync()
      await refreshAll()
      setLastSync(new Date().toLocaleTimeString())
    } catch (syncErr) {
      console.error('[sync after remove group]', syncErr)
    } finally {
      setSyncSpinning(false)
    }
  } catch (err) {
    alert('Failed to remove group: ' + err.message)
  }
}

// ── Boot ───────────────────────────────────────────────────────────────────

async function boot() {
  // Load user info
  try {
    const user = await fetchCurrentUser()
    renderUserInfo({
      name: user.name,
      avatar: user.avatar_url,
      has_gitlab_token: user.has_gitlab_token,
    })
    
    // Show admin button for admin user
    if (user.username === 'admin') {
      document.getElementById('admin-btn').style.display = 'inline-block'
    }
  } catch (err) {
    console.error('Failed to load user:', err)
  }

  // Load groups
  try {
    state.groups = await fetchUserGroups()
    renderGroups(state.groups, handleRemoveGroup)
  } catch (err) {
    console.error('Failed to load groups:', err)
  }

  renderMainEmpty()
  await refreshAll()

  // Auto-refresh every 30 s
  setInterval(refreshAll, 30_000)

  // Search input
  document.getElementById('search-input')
    ?.addEventListener('input', e => filterProjects(e.target.value))

  // Manual sync button
  document.getElementById('sync-btn')
    ?.addEventListener('click', handleSync)

  // Logout button
  document.getElementById('logout-btn')
    ?.addEventListener('click', () => window.location.href = '/logout')

  // Add group button
  document.getElementById('add-group-btn')
    ?.addEventListener('click', () => {
      document.getElementById('add-group-modal').style.display = 'flex';
    });

  // Cancel add group
  document.getElementById('cancel-add-group')
    ?.addEventListener('click', () => {
      document.getElementById('add-group-modal').style.display = 'none';
      document.getElementById('add-group-form').reset();
    });

  // Add group form
  document.getElementById('add-group-form')
    ?.addEventListener('submit', handleAddGroupForm);

  // Update token button
  document.getElementById('update-token-btn')
    ?.addEventListener('click', () => {
      document.getElementById('update-token-modal').style.display = 'flex';
    });

  // Cancel update token
  document.getElementById('cancel-update-token')
    ?.addEventListener('click', () => {
      document.getElementById('update-token-modal').style.display = 'none';
      document.getElementById('update-token-form').reset();
    });

  // Update token form
  document.getElementById('update-token-form')
    ?.addEventListener('submit', handleUpdateTokenForm);

  // Admin button
  document.getElementById('admin-btn')
    ?.addEventListener('click', () => {
      document.getElementById('admin-modal').style.display = 'flex';
      loadAdminUsers();
    });

  // Cancel admin
  document.getElementById('cancel-admin')
    ?.addEventListener('click', () => {
      document.getElementById('admin-modal').style.display = 'none';
    });
}

// ── Data loading ───────────────────────────────────────────────────────────

async function refreshAll() {
  await Promise.allSettled([refreshSummary(), refreshProjects()])
  if (state.activeProject) {
    await loadProjectDetail(state.activeProject.id)
  }
}

async function refreshSummary() {
  try {
    const summary = await fetchSummary()
    renderSummary(summary)
  } catch (err) {
    console.warn('[summary]', err)
  }
}

async function refreshProjects() {
  try {
    state.projects = await fetchProjects()
    renderSidebar(state.projects, state.activeProject?.id, selectProject)
    setLastSync(new Date().toLocaleTimeString())
  } catch (err) {
    console.warn('[projects]', err)
  }
}

// ── Project selection ──────────────────────────────────────────────────────

function selectProject(project) {
  state.activeProject = project
  state.activePipelineId = null
  // Re-render sidebar to move the active highlight
  renderSidebar(state.projects, project.id, selectProject)
  loadProjectDetail(project.id)
}

async function loadProjectDetail(projectId) {
  const project = state.projects.find(p => p.id === projectId)
  if (!project) return

  renderMainLoading()
  try {
    const pipelines = await fetchPipelines(projectId)
    const { autoLoadPipelineId } = renderProjectDetail(
      project,
      pipelines,
      state.activePipelineId,
      selectPipeline,
    )

    if (autoLoadPipelineId) {
      const firstRow = document.querySelector(`[data-pipeline-id="${autoLoadPipelineId}"]`)
      await selectPipeline(autoLoadPipelineId, firstRow)
    }
  } catch (err) {
    renderMainError(err.message)
  }
}

// ── Pipeline / jobs selection ──────────────────────────────────────────────

async function selectPipeline(pipelineId, rowEl) {
  state.activePipelineId = pipelineId
  setActivePipelineRow(pipelineId)
  renderJobsLoading(pipelineId)
  try {
    const jobs = await fetchJobs(pipelineId)
    renderJobs(jobs)
  } catch (err) {
    renderJobsError(err.message)
  }
}

// ── Search / filter ────────────────────────────────────────────────────────

function filterProjects(query) {
  const q = query.toLowerCase().trim()
  const filtered = q
    ? state.projects.filter(
        p =>
          p.name.toLowerCase().includes(q) ||
          p.namespace.toLowerCase().includes(q),
      )
    : state.projects
  renderSidebar(filtered, state.activeProject?.id, selectProject)
}

// ── Manual sync ────────────────────────────────────────────────────────────

async function handleSync() {
  setSyncSpinning(true)
  try {
    await triggerSync()
    await refreshAll()
    setLastSync(new Date().toLocaleTimeString())
  } catch (err) {
    console.error('[sync]', err)
  } finally {
    setSyncSpinning(false)
  }
}

async function handleAddGroupForm(e) {
  e.preventDefault();
  const groupInput = document.getElementById('group-input').value.trim();
  if (!groupInput) return;

  // Determine if it's an ID or path
  const isId = /^\d+$/.test(groupInput);
  const groupData = isId ? { group_id: parseInt(groupInput) } : { group_path: groupInput };

  try {
    const newGroup = await addUserGroup(groupData);
    state.groups.push(newGroup);
    renderGroups(state.groups, handleRemoveGroup);
    
    // Close modal immediately after adding group
    document.getElementById('add-group-modal').style.display = 'none';
    document.getElementById('add-group-form').reset();
    
    // Trigger sync with visual feedback
    setSyncSpinning(true);
    try {
      await triggerSync();
      await refreshAll();
      setLastSync(new Date().toLocaleTimeString());
    } catch (syncErr) {
      console.error('[sync after add group]', syncErr);
    } finally {
      setSyncSpinning(false);
    }
  } catch (err) {
    alert('Failed to add group: ' + err.message);
  }
}

async function handleUpdateTokenForm(e) {
  e.preventDefault();
  const tokenInput = document.getElementById('token-input').value.trim();
  if (!tokenInput) return;

  try {
    const response = await fetch('/api/user/gitlab-token', {
      method: 'POST',
      headers: csrfHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({ token: tokenInput }),
    });

    const data = await response.json();

    if (response.ok) {
      alert('GitLab token updated successfully!');
      // Refresh user info to update the status indicator
      const user = await fetchCurrentUser();
      renderUserInfo({
        name: user.name,
        avatar: user.avatar_url,
        has_gitlab_token: user.has_gitlab_token,
      });
      
      // Close modal
      document.getElementById('update-token-modal').style.display = 'none';
      document.getElementById('update-token-form').reset();
    } else {
      alert('Failed to update token: ' + (data.error || 'Unknown error'));
    }
  } catch (err) {
    alert('Failed to update token: ' + err.message);
  }
}

// ── Admin functions ────────────────────────────────────────────────────────

async function loadAdminUsers() {
  try {
    const response = await fetch('/api/admin/users')
    if (!response.ok) throw new Error('Failed to load users')
    const users = await response.json()
    
    const usersList = document.getElementById('admin-users-list')
    usersList.innerHTML = ''
    
    for (const user of users) {
      const userDiv = document.createElement('div')
      userDiv.className = 'admin-user-item'
      userDiv.innerHTML = `
        <div class="user-info">
          <strong>${esc(user.name)}</strong> (${esc(user.username)})
          <br><small>${esc(user.email)} • ${user.provider} • ${user.approved ? 'Approved' : 'Pending'}</small>
        </div>
        <div class="user-actions">
          ${!user.approved ? `<button class="btn-small" onclick="approveUser(${user.id})">Approve</button>` : ''}
          ${user.username !== 'admin' ? `<button class="btn-small btn-danger" onclick="rejectUser(${user.id})">Reject</button>` : ''}
        </div>
      `
      usersList.appendChild(userDiv)
    }
  } catch (err) {
    alert('Failed to load users: ' + err.message)
  }
}

async function approveUser(userId) {
  try {
    const response = await fetch(`/api/admin/users/${userId}/approve`, {
      method: 'POST',
      headers: csrfHeaders(),
    })
    if (!response.ok) throw new Error('Failed to approve user')
    loadAdminUsers() // Refresh the list
  } catch (err) {
    alert('Failed to approve user: ' + err.message)
  }
}

async function rejectUser(userId) {
  if (!confirm('Are you sure you want to reject and delete this user?')) return
  
  try {
    const response = await fetch(`/api/admin/users/${userId}/reject`, {
      method: 'POST',
      headers: csrfHeaders(),
    })
    if (!response.ok) throw new Error('Failed to reject user')
    loadAdminUsers() // Refresh the list
  } catch (err) {
    alert('Failed to reject user: ' + err.message)
  }
}

// Make functions global for onclick handlers
window.approveUser = approveUser
window.rejectUser = rejectUser

// ── Start ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', boot)