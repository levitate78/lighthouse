/**
 * render.js — All DOM construction and mutation.
 *
 * Functions here accept plain data objects and return/update DOM nodes.
 * They have no knowledge of API calls or application state.
 */

import { esc, formatDuration, formatDate, statusIcon, loadingShimmer } from './utils.js'

// ── Summary bar ────────────────────────────────────────────────────────────

/**
 * Update the header summary chips with fresh counts.
 * @param {{ total_projects: number, status_counts: Record<string,number> }} summary
 */
export function renderSummary(summary) {
  const set = (id, val) => {
    const el = document.getElementById(id)
    if (el) el.textContent = val ?? 0
  }
  set('stat-projects', summary.total_projects)
  set('stat-success',  summary.status_counts?.success  ?? 0)
  set('stat-failed',   summary.status_counts?.failed   ?? 0)
  set('stat-running',  summary.status_counts?.running  ?? 0)
  set('stat-pending',  summary.status_counts?.pending  ?? 0)
  set('stat-canceled', summary.status_counts?.canceled ?? 0)
}

// ── Sidebar project list ───────────────────────────────────────────────────

/**
 * Render the list of projects in the sidebar.
 * @param {Array}        projects
 * @param {number|null}  activeId        Currently selected project ID
 * @param {function}     onSelect        Called with a project object on click
 */
export function renderSidebar(projects, activeId, onSelect) {
  const list = document.getElementById('project-list')
  if (!list) return

  list.innerHTML = ''

  if (!projects.length) {
    list.innerHTML = `<li class="sidebar-empty">No projects found</li>`
    return
  }

  for (const project of projects) {
    const status = project.latest_pipeline?.status ?? 'unknown'
    const li = document.createElement('li')
    li.className = `project-item${project.id === activeId ? ' project-item--active' : ''}`
    li.dataset.id = project.id
    li.innerHTML = `
      <span class="dot status-${esc(status)}"></span>
      <div class="project-info">
        <div class="project-name">${esc(project.name)}</div>
        <div class="project-ns">${esc(project.namespace)}</div>
      </div>`
    li.addEventListener('click', () => onSelect(project))
    list.appendChild(li)
  }
}

// ── Main panel — project detail ────────────────────────────────────────────

/** Show a skeleton loader in the main panel. */
export function renderMainLoading() {
  const panel = document.getElementById('main-panel')
  if (panel) panel.innerHTML = loadingShimmer(8)
}

/** Show an empty/welcome state in the main panel. */
export function renderMainEmpty() {
  const panel = document.getElementById('main-panel')
  if (!panel) return
  panel.innerHTML = `
    <div class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M3 9h18M9 21V9"/>
      </svg>
      <span>Select a project to view its pipelines</span>
    </div>`
}

/** Show an error message in the main panel. */
export function renderMainError(message) {
  const panel = document.getElementById('main-panel')
  if (!panel) return
  panel.innerHTML = `
    <div class="empty-state">
      <span class="error-text">Failed to load: ${esc(message)}</span>
    </div>`
}

/**
 * Render the full project detail view — header + pipeline table + jobs placeholder.
 * Returns a cleanup function (no-op here, useful for future event listener cleanup).
 *
 * @param {object}   project
 * @param {Array}    pipelines
 * @param {number|null} activePipelineId
 * @param {function} onPipelineSelect  Called with (pipelineId, rowEl)
 * @returns {{ autoLoadPipelineId: number|null }}
 */
export function renderProjectDetail(project, pipelines, activePipelineId, onPipelineSelect) {
  const panel = document.getElementById('main-panel')
  if (!panel) return { autoLoadPipelineId: null }

  panel.innerHTML = ''

  // ── Project header
  const header = document.createElement('div')
  header.className = 'proj-header'
  header.innerHTML = `
    <div class="proj-header-info">
      <div class="proj-title">${esc(project.name)}</div>
      <div class="proj-path">${esc(project.namespace)} · <span class="proj-branch">${esc(project.default_branch)}</span></div>
      ${project.web_url
        ? `<a class="proj-link" href="${esc(project.web_url)}" target="_blank" rel="noopener">
             ${externalLinkIcon()} Open in GitLab
           </a>`
        : ''}
    </div>`
  panel.appendChild(header)

  // ── Pipeline table card
  const card = document.createElement('div')
  card.className = 'card'
  card.innerHTML = `
    <div class="card-header">
      <span>Recent Pipelines</span>
      <span>${pipelines.length} shown</span>
    </div>
    <div class="table-wrap">
      <table class="pipeline-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Status</th>
            <th>Branch / Tag</th>
            <th>Commit</th>
            <th>Source</th>
            <th>Duration</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="pipeline-tbody"></tbody>
      </table>
    </div>`
  panel.appendChild(card)

  const tbody = card.querySelector('#pipeline-tbody')
  if (!pipelines.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty">No pipelines found</td></tr>`
  } else {
    for (const pipe of pipelines) {
      const tr = document.createElement('tr')
      tr.className = `pipeline-row${pipe.id === activePipelineId ? ' pipeline-row--active' : ''}`
      tr.dataset.pipelineId = pipe.id
      tr.innerHTML = `
        <td><span class="pipeline-id">#${pipe.id}</span></td>
        <td><span class="badge status-${esc(pipe.status)}">${statusIcon(pipe.status)} ${esc(pipe.status)}</span></td>
        <td><span class="pipeline-ref">${branchIcon()} ${esc(pipe.ref)}</span></td>
        <td><span class="pipeline-sha">${esc(pipe.sha)}</span></td>
        <td><span class="source-label">${esc(pipe.source || '—')}</span></td>
        <td><span class="duration-text">${formatDuration(pipe.duration)}</span></td>
        <td><span class="date-text">${formatDate(pipe.created_at)}</span></td>
        <td>${pipe.web_url
          ? `<a class="row-link" href="${esc(pipe.web_url)}" target="_blank" rel="noopener"
               onclick="event.stopPropagation()">↗</a>`
          : ''}</td>`
      tr.addEventListener('click', () => onPipelineSelect(pipe.id, tr))
      tbody.appendChild(tr)
    }
  }

  // ── Jobs placeholder card
  const jobsCard = document.createElement('div')
  jobsCard.className = 'card'
  jobsCard.id = 'jobs-card'
  jobsCard.innerHTML = `
    <div class="card-header">
      <span>Jobs</span>
      <span id="jobs-subtitle" class="card-header-sub">click a pipeline row to view jobs</span>
    </div>
    <div id="jobs-body" class="jobs-placeholder">Select a pipeline above</div>`
  panel.appendChild(jobsCard)

  return { autoLoadPipelineId: pipelines[0]?.id ?? null }
}

// ── Jobs panel ─────────────────────────────────────────────────────────────

/** Show a loading skeleton inside the jobs card. */
export function renderJobsLoading(pipelineId) {
  const subtitle = document.getElementById('jobs-subtitle')
  if (subtitle) subtitle.textContent = `pipeline #${pipelineId}`
  const body = document.getElementById('jobs-body')
  if (body) body.innerHTML = loadingShimmer(3)
}

/**
 * Render jobs grouped by stage inside the jobs card.
 * @param {Array} jobs
 */
export function renderJobs(jobs) {
  const body = document.getElementById('jobs-body')
  if (!body) return

  if (!jobs.length) {
    body.innerHTML = `<div class="jobs-placeholder">No jobs found for this pipeline</div>`
    return
  }

  // Group by stage, preserving insertion order
  const stages = {}
  for (const job of jobs) {
    ;(stages[job.stage] ??= []).push(job)
  }

  let html = ''
  for (const [stage, stageJobs] of Object.entries(stages)) {
    html += `<div class="stage-label">${esc(stage)}</div><div class="jobs-grid">`
    for (const j of stageJobs) {
      html += `
        <div class="job-card">
          <div class="job-card-top">
            <span class="job-name" title="${esc(j.name)}">${esc(j.name)}</span>
            <span class="badge badge--sm status-${esc(j.status)}">${statusIcon(j.status)}</span>
          </div>
          <div class="job-stage">${esc(j.stage)}</div>
          <div class="job-dur">${formatDuration(j.duration)}</div>
          ${j.web_url
            ? `<a class="job-link" href="${esc(j.web_url)}" target="_blank" rel="noopener">View logs ↗</a>`
            : ''
          }
        </div>`
    }
    html += `</div>`
  }
  body.innerHTML = html
}

/** Show an error inside the jobs card. */
export function renderJobsError(message) {
  const body = document.getElementById('jobs-body')
  if (body) body.innerHTML = `<div class="jobs-placeholder error-text">Error: ${esc(message)}</div>`
}

/**
 * Highlight the active pipeline row and un-highlight all others.
 * @param {number} pipelineId
 */
export function setActivePipelineRow(pipelineId) {
  document.querySelectorAll('.pipeline-row').forEach(row => {
    row.classList.toggle(
      'pipeline-row--active',
      Number(row.dataset.pipelineId) === pipelineId,
    )
  })
}

// ── Sync button ────────────────────────────────────────────────────────────

export function setSyncSpinning(spinning) {
  const btn = document.getElementById('sync-btn')
  if (!btn) return
  btn.classList.toggle('btn--spinning', spinning)
  btn.disabled = spinning
}

export function setLastSync(timeString) {
  const el = document.getElementById('last-sync')
  if (el) el.textContent = timeString
}

// ── User info ──────────────────────────────────────────────────────────────

export function renderUserInfo(user) {
  const nameEl = document.getElementById('user-name')
  const avatarEl = document.getElementById('user-avatar')
  const gitlabStatusEl = document.getElementById('gitlab-status')
  
  if (nameEl) nameEl.textContent = user.name
  if (avatarEl) avatarEl.src = user.avatar || '/static/default-avatar.png'
  
  if (gitlabStatusEl) {
    if (user.has_gitlab_token) {
      gitlabStatusEl.textContent = '🔑'
      gitlabStatusEl.title = 'GitLab token configured'
      gitlabStatusEl.style.color = 'var(--success)'
    } else {
      gitlabStatusEl.textContent = '⚠️'
      gitlabStatusEl.title = 'No GitLab token - limited functionality'
      gitlabStatusEl.style.color = 'var(--fail)'
    }
  }
}

// ── Groups list ────────────────────────────────────────────────────────────

export function renderGroups(groups, onRemoveGroup) {
  const list = document.getElementById('group-list')
  if (!list) return

  list.innerHTML = ''

  if (!groups.length) {
    list.innerHTML = `<li class="sidebar-empty">No groups selected</li>`
    return
  }

  for (const group of groups) {
    const li = document.createElement('li')
    li.className = 'group-item'
    li.innerHTML = `
      <span class="group-name">${esc(group.group_name)}</span>
      <button class="group-remove" data-group-id="${group.group_id}">×</button>
    `
    li.querySelector('.group-remove').addEventListener('click', () => {
      if (onRemoveGroup) onRemoveGroup(group.group_id)
    })
    list.appendChild(li)
  }
}

// ── Private icon helpers ───────────────────────────────────────────────────

function externalLinkIcon() {
  return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
    <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
  </svg>`
}

function branchIcon() {
  return `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <line x1="6" y1="3" x2="6" y2="15"/>
    <circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/>
    <path d="M18 9a9 9 0 0 1-9 9"/>
  </svg>`
}