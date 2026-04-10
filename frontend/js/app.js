/**
 * app.js — Application state, event wiring, and boot sequence.
 *
 * This is the only module that holds mutable state and orchestrates
 * calls between api.js and render.js.
 */

import {
  initCsrf,
  fetchSummary,
  fetchProjects,
  fetchPipelines,
  fetchJobs,
  triggerSync,
  fetchUserGroups,
  addUserGroup,
  removeUserGroup,
  fetchCurrentUser,
  updateGitlabToken,
  fetchAdminUsers,
  approveUser,
  rejectUser,
} from './api.js'

import { esc } from './utils.js'

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
  /** @type {object|null} */
  user: null,
  /** @type {Array} */
  groups: [],
  /** @type {Array} */
  projects: [],
  /** @type {object|null} */
  activeProject: null,
  /** @type {number|null} */
  activePipelineId: null,
}

// ── Group management ───────────────────────────────────────────────────────

async function handleRemoveGroup(groupId) {
  try {
    const removedGroup = state.groups.find(g => g.group_id === groupId)

    await removeUserGroup(groupId)
    state.groups = state.groups.filter(g => g.group_id !== groupId)

    if (removedGroup) {
      state.projects = state.projects.filter(p => p.group_id !== removedGroup.group_id)

      if (
        state.activeProject &&
        !state.projects.find(p => p.id === state.activeProject.id)
      ) {
        state.activeProject = null
        state.activePipelineId = null
        renderMainEmpty()
      }
    }

    renderGroups(state.groups, handleRemoveGroup)
    renderSidebar(state.projects, state.activeProject?.id, selectProject)

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
    if (err.message.includes('redirecting')) return
    alert('Failed to remove group: ' + err.message)
  }
}

// ── Boot ───────────────────────────────────────────────────────────────────

async function boot() {
  // Fetch and cache the CSRF token before any mutating requests are made.
  // This handles both development (meta tag) and production (endpoint) modes.
  await initCsrf()

  // Load user info — a 401 here means the session is invalid; api.js will
  // redirect to /login automatically.
  try {
    state.user = await fetchCurrentUser()
    renderUserInfo({
      name: state.user.name,
      avatar: state.user.avatar_url,
      has_gitlab_token: state.user.has_gitlab_token,
    })

    if (state.user.is_admin) {
      document.getElementById('admin-btn').style.display = 'inline-block'
    }
  } catch (err) {
    if (err.message.includes('redirecting')) return
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

  // ── Event listeners ──────────────────────────────────────────────────────

  document.getElementById('search-input')
    ?.addEventListener('input', e => filterProjects(e.target.value))

  document.getElementById('sync-btn')
    ?.addEventListener('click', handleSync)

  document.getElementById('logout-btn')
    ?.addEventListener('click', () => { window.location.href = '/logout' })

  document.getElementById('add-group-btn')
    ?.addEventListener('click', () => {
      document.getElementById('add-group-modal').style.display = 'flex'
    })

  document.getElementById('cancel-add-group')
    ?.addEventListener('click', () => {
      document.getElementById('add-group-modal').style.display = 'none'
      document.getElementById('add-group-form').reset()
    })

  document.getElementById('add-group-form')
    ?.addEventListener('submit', handleAddGroupForm)

  document.getElementById('update-token-btn')
    ?.addEventListener('click', () => {
      document.getElementById('update-token-modal').style.display = 'flex'
    })

  document.getElementById('cancel-update-token')
    ?.addEventListener('click', () => {
      document.getElementById('update-token-modal').style.display = 'none'
      document.getElementById('update-token-form').reset()
    })

  document.getElementById('update-token-form')
    ?.addEventListener('submit', handleUpdateTokenForm)

  document.getElementById('admin-btn')
    ?.addEventListener('click', () => {
      document.getElementById('admin-modal').style.display = 'flex'
      loadAdminUsers()
    })

  document.getElementById('cancel-admin')
    ?.addEventListener('click', () => {
      document.getElementById('admin-modal').style.display = 'none'
    })
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
      await selectPipeline(autoLoadPipelineId)
    }
  } catch (err) {
    if (!err.message.includes('redirecting')) renderMainError(err.message)
  }
}

// ── Pipeline / jobs selection ──────────────────────────────────────────────

async function selectPipeline(pipelineId) {
  state.activePipelineId = pipelineId
  setActivePipelineRow(pipelineId)
  renderJobsLoading(pipelineId)
  try {
    const jobs = await fetchJobs(pipelineId)
    renderJobs(jobs)
  } catch (err) {
    if (!err.message.includes('redirecting')) renderJobsError(err.message)
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
    if (!err.message.includes('redirecting')) console.error('[sync]', err)
  } finally {
    setSyncSpinning(false)
  }
}

// ── Add group form ─────────────────────────────────────────────────────────

async function handleAddGroupForm(e) {
  e.preventDefault()
  const groupInput = document.getElementById('group-input').value.trim()
  if (!groupInput) return

  const isId = /^\d+$/.test(groupInput)
  const groupData = isId
    ? { group_id: parseInt(groupInput, 10) }
    : { group_path: groupInput }

  try {
    const newGroup = await addUserGroup(groupData)
    state.groups.push(newGroup)
    renderGroups(state.groups, handleRemoveGroup)

    document.getElementById('add-group-modal').style.display = 'none'
    document.getElementById('add-group-form').reset()

    setSyncSpinning(true)
    try {
      await triggerSync()
      await refreshAll()
      setLastSync(new Date().toLocaleTimeString())
    } catch (syncErr) {
      console.error('[sync after add group]', syncErr)
    } finally {
      setSyncSpinning(false)
    }
  } catch (err) {
    if (!err.message.includes('redirecting')) alert('Failed to add group: ' + err.message)
  }
}

// ── Update token form ──────────────────────────────────────────────────────

async function handleUpdateTokenForm(e) {
  e.preventDefault()
  const tokenInput = document.getElementById('token-input').value.trim()
  if (!tokenInput) return

  try {
    await updateGitlabToken(tokenInput)
    alert('GitLab token updated successfully!')

    const user = await fetchCurrentUser()
    renderUserInfo({
      name: user.name,
      avatar: user.avatar_url,
      has_gitlab_token: user.has_gitlab_token,
    })

    document.getElementById('update-token-modal').style.display = 'none'
    document.getElementById('update-token-form').reset()
  } catch (err) {
    if (!err.message.includes('redirecting')) alert('Failed to update token: ' + err.message)
  }
}

// ── Admin panel ────────────────────────────────────────────────────────────

async function loadAdminUsers() {
  try {
    const users = await fetchAdminUsers()
    const usersList = document.getElementById('admin-users-list')
    usersList.innerHTML = ''

    for (const user of users) {
      const userDiv = document.createElement('div')
      userDiv.className = 'admin-user-item'
      userDiv.innerHTML = `
        <div class="user-info">
          <strong>${esc(user.name)}</strong> (${esc(user.username)})
          <br><small>${esc(user.email)} · ${esc(user.provider)} · ${user.approved ? 'Approved' : 'Pending'}</small>
        </div>
        <div class="user-actions">
          ${!user.approved
            ? `<button class="btn-small" data-action="approve" data-id="${user.id}">Approve</button>`
            : ''}
          ${user.username !== 'admin'
            ? `<button class="btn-small btn-danger" data-action="reject" data-id="${user.id}">Reject</button>`
            : ''}
        </div>`
      usersList.appendChild(userDiv)
    }

    // Use event delegation instead of inline onclick handlers to avoid XSS.
    usersList.addEventListener('click', async e => {
      const btn = e.target.closest('[data-action]')
      if (!btn) return
      const { action, id } = btn.dataset
      const userId = parseInt(id, 10)

      if (action === 'approve') {
        try {
          await approveUser(userId)
          loadAdminUsers()
        } catch (err) {
          alert('Failed to approve user: ' + err.message)
        }
      } else if (action === 'reject') {
        if (!confirm('Reject and permanently delete this user?')) return
        try {
          await rejectUser(userId)
          loadAdminUsers()
        } catch (err) {
          alert('Failed to reject user: ' + err.message)
        }
      }
    }, { once: true })
  } catch (err) {
    alert('Failed to load users: ' + err.message)
  }
}

// ── Start ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', boot)