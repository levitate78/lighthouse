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

export function renderMetricsLoading() {
  const panel = document.getElementById('main-panel')
  if (panel) panel.innerHTML = loadingShimmer(8)
}

export function renderMetricsError(message) {
  const panel = document.getElementById('main-panel')
  if (!panel) return
  panel.innerHTML = `<div class="empty-state"><span class="error-text">Failed to load metrics: ${esc(message)}</span></div>`
}

export function renderMetricsPage(data, filters, onFilterChange) {
  const panel = document.getElementById('main-panel')
  if (!panel) return

  const groups = data.filters?.groups ?? []
  const projects = (data.filters?.projects ?? []).filter(project => (
    !filters.groupId || String(project.group_id) === String(filters.groupId)
  ))
  const summary = data.summary ?? {}
  const tests = summary.tests ?? {}
  const duration = summary.duration ?? {}
  const jobNames = (data.jobs_by_name ?? []).map(job => job.name).sort()

  panel.innerHTML = `
    <div class="metrics-header">
      <div>
        <div class="proj-title">Pipeline Job Metrics</div>
        <div class="proj-path">Aggregated job duration, status, tests, and coverage trends</div>
      </div>
      <div class="metrics-filters">
        <label>
          Group
          <select id="metrics-group-filter">
            <option value="">All groups</option>
            ${groups.map(group => `
              <option value="${group.group_id}" ${String(filters.groupId) === String(group.group_id) ? 'selected' : ''}>
                ${esc(group.group_name)}
              </option>`).join('')}
          </select>
        </label>
        <label>
          Project
          <select id="metrics-project-filter">
            <option value="">All projects</option>
            ${projects.map(project => `
              <option value="${project.id}" ${String(filters.projectId) === String(project.id) ? 'selected' : ''}>
                ${esc(project.namespace ? `${project.namespace} / ${project.name}` : project.name)}
              </option>`).join('')}
          </select>
        </label>
        <label>
          Window
          <select id="metrics-days-filter">
            ${[7, 14, 30, 60, 90, 180, 365].map(days => `
              <option value="${days}" ${Number(filters.days) === days ? 'selected' : ''}>${days} days</option>`).join('')}
          </select>
        </label>
        <label>
          Branch
          <input id="metrics-branch-filter" type="search" value="${esc(filters.branch || '')}" placeholder="Any branch">
        </label>
        <label>
          Job name
          <select id="metrics-job-filter">
            <option value="">All jobs</option>
            ${jobNames.map(name => `
              <option value="${esc(name)}" ${filters.jobName === name ? 'selected' : ''}>
                ${esc(name)}
              </option>`).join('')}
          </select>
        </label>
      </div>
    </div>

    <div class="metrics-kpis">
      ${metricKpi('Jobs', summary.job_count ?? 0, statusLine(summary.job_status_counts))}
      ${metricKpi('Pipelines', summary.pipeline_count ?? 0, statusLine(summary.pipeline_status_counts))}
      ${metricKpi('Avg job length', formatDuration(duration.avg), `min ${formatDuration(duration.min)} / max ${formatDuration(duration.max)}`)}
      ${metricKpi('Coverage', formatPercent(summary.coverage_avg), 'average reported coverage')}
      ${metricKpi('Tests', tests.total ?? 0, `${tests.success ?? 0} passed / ${tests.failed ?? 0} failed`)}
    </div>

    <div class="metrics-grid">
      <div class="card metrics-card">
        <div class="card-header">
          <span>Job duration trend</span>
          <span>avg with min/max range</span>
        </div>
        <div class="metrics-chart">${durationChart(data.trends ?? [])}</div>
      </div>
      <div class="card metrics-card">
        <div class="card-header">
          <span>Status by day</span>
          <span>passed vs failed jobs</span>
        </div>
        <div class="metrics-chart">${statusChart(data.trends ?? [])}</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span>Recent pipelines</span>
        <span>${data.recent_pipelines?.length ?? 0} shown</span>
      </div>
      ${recentPipelinesTable(data.recent_pipelines ?? [])}
    </div>

    <div class="card">
      <div class="card-header">
        <span>Slowest job names</span>
        <span>average duration</span>
      </div>
      ${jobsByNameTable(data.jobs_by_name ?? [])}
    </div>
  `

  const emit = () => onFilterChange({
    groupId: document.getElementById('metrics-group-filter')?.value || '',
    projectId: document.getElementById('metrics-project-filter')?.value || '',
    days: document.getElementById('metrics-days-filter')?.value || '30',
    branch: document.getElementById('metrics-branch-filter')?.value.trim() || '',
    jobName: document.getElementById('metrics-job-filter')?.value || '',
  })

  document.getElementById('metrics-group-filter')?.addEventListener('change', () => {
    document.getElementById('metrics-project-filter').value = ''
    emit()
  })
  document.getElementById('metrics-project-filter')?.addEventListener('change', emit)
  document.getElementById('metrics-days-filter')?.addEventListener('change', emit)
  document.getElementById('metrics-branch-filter')?.addEventListener('input', debounceEvent(emit, 350))
  document.getElementById('metrics-job-filter')?.addEventListener('change', emit)
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
  
  const defaultAvatar = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%236b7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/></svg>`;
  if (avatarEl) avatarEl.src = user.avatar || defaultAvatar
  
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

/**
 * Render sync progress status.
 * @param {Array} syncStatuses
 */
export function renderSyncProgress(syncStatuses) {
  const container = document.getElementById('sync-status-indicator')
  if (!container) return

  const activeSyncs = syncStatuses.filter(s => ['syncing', 'syncing_history'].includes(s.status))
  if (activeSyncs.length === 0) {
    container.style.display = 'none'
    container.innerHTML = ''
    return
  }

  // Show the first active sync progress message
  const sync = activeSyncs[0]
  container.style.display = 'inline-flex'
  
  let msg = sync.message || 'Syncing...'
  
  container.innerHTML = `
    <svg class="btn-icon" width="12" height="12" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2.2" aria-hidden="true" style="animation: spin 1s linear infinite; margin-right: 4px;">
      <polyline points="23 4 23 10 17 10"></polyline>
      <polyline points="1 20 1 14 7 14"></polyline>
      <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path>
    </svg>
    <span>${esc(msg)}</span>
  `
}

function metricKpi(label, value, detail) {
  return `
    <div class="metric-kpi">
      <div class="metric-kpi-label">${esc(label)}</div>
      <div class="metric-kpi-value">${esc(value)}</div>
      <div class="metric-kpi-detail">${esc(detail || '')}</div>
    </div>`
}

function statusLine(counts = {}) {
  return `${counts.success ?? 0} passed / ${counts.failed ?? 0} failed`
}

function formatPercent(value) {
  return value == null ? '-' : `${value.toFixed(1)}%`
}

/** Pick evenly-spaced indices (including first and last) for X-axis labels. */
function pickTickIndices(length, maxTicks = 6) {
  if (length <= maxTicks) return Array.from({ length }, (_, i) => i)
  const step = (length - 1) / (maxTicks - 1)
  const indices = new Set()
  for (let i = 0; i < maxTicks; i++) indices.add(Math.round(i * step))
  return Array.from(indices).sort((a, b) => a - b)
}

/** Format a "YYYY-MM-DD" trend bucket date as a short axis label, e.g. "Jun 15". */
function formatChartDate(dateStr) {
  if (!dateStr || dateStr === 'unknown') return dateStr || '—'
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function durationChart(trends) {
  if (!trends.length) return `<div class="jobs-placeholder">No metric data in this window</div>`
  const width = 720
  const height = 220
  const padLeft = 50
  const padRight = 20
  const padTop = 16
  const padBottom = 34
  const max = Math.max(...trends.map(row => row.duration?.max ?? 0), 1)
  const x = index => trends.length === 1
    ? (padLeft + (width - padRight)) / 2
    : padLeft + (index * (width - padLeft - padRight)) / (trends.length - 1)
  const y = value => height - padBottom - ((value ?? 0) / max) * (height - padTop - padBottom)

  const points = trends.map((row, index) => `${x(index)},${y(row.duration?.avg)}`).join(' ')
  const ranges = trends.map((row, index) => `
    <line x1="${x(index)}" y1="${y(row.duration?.min)}" x2="${x(index)}" y2="${y(row.duration?.max)}" class="chart-range"/>
    <circle cx="${x(index)}" cy="${y(row.duration?.avg)}" r="3" class="chart-point" data-toggle="tooltip"
      data-date="${esc(row.date)}" data-avg="${formatDuration(row.duration?.avg)}"
      data-min="${formatDuration(row.duration?.min)}" data-max="${formatDuration(row.duration?.max)}">
      <title>${esc(row.date)} avg ${esc(formatDuration(row.duration?.avg))} (min: ${esc(formatDuration(row.duration?.min))}, max: ${esc(formatDuration(row.duration?.max))})</title>
    </circle>`).join('')

  const yTickCount = 4
  const yTicks = Array.from({ length: yTickCount + 1 }, (_, i) => {
    const value = (max / yTickCount) * i
    const yPos = y(value)
    return `
      <line x1="${padLeft - 4}" y1="${yPos}" x2="${padLeft}" y2="${yPos}" class="chart-axis"/>
      <text x="${padLeft - 8}" y="${yPos}" class="chart-axis-label" text-anchor="end" dominant-baseline="middle">${esc(formatDuration(value))}</text>`
  }).join('')

  const xTicks = pickTickIndices(trends.length).map(index => `
    <text x="${x(index)}" y="${height - padBottom + 16}" class="chart-axis-label" text-anchor="middle">${esc(formatChartDate(trends[index].date))}</text>`).join('')

  return `
    <svg class="trend-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Job duration trend">
      <line x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${height - padBottom}" class="chart-axis"/>
      <line x1="${padLeft}" y1="${height - padBottom}" x2="${width - padRight}" y2="${height - padBottom}" class="chart-axis"/>
      ${yTicks}
      ${xTicks}
      <polyline points="${points}" class="chart-line"/>
      ${ranges}
    </svg>`
}

function statusChart(trends) {
  if (!trends.length) return `<div class="jobs-placeholder">No status data in this window</div>`
  const width = 720
  const height = 220
  const padLeft = 50
  const padRight = 20
  const padTop = 16
  const padBottom = 34
  const gap = 5
  const barWidth = Math.max(8, ((width - padLeft - padRight) / trends.length) - gap)
  const max = Math.max(...trends.map(row => (row.success ?? 0) + (row.failed ?? 0)), 1)

  const bars = trends.map((row, index) => {
    const barX = padLeft + index * (barWidth + gap)
    const successHeight = ((row.success ?? 0) / max) * (height - padTop - padBottom)
    const failedHeight = ((row.failed ?? 0) / max) * (height - padTop - padBottom)
    const failedY = height - padBottom - failedHeight
    const successY = failedY - successHeight
    const successCount = row.success ?? 0
    const failedCount = row.failed ?? 0
    const totalCount = successCount + failedCount
    return `
      <g class="chart-bar-group" data-toggle="tooltip" data-date="${esc(row.date)}" data-passed="${successCount}" data-failed="${failedCount}" data-total="${totalCount}">
        <title>${esc(row.date)} ${successCount} passed / ${failedCount} failed (${totalCount} total)</title>
        <rect x="${barX}" y="${successY}" width="${barWidth}" height="${successHeight}" class="chart-bar-success"/>
        <rect x="${barX}" y="${failedY}" width="${barWidth}" height="${failedHeight}" class="chart-bar-failed"/>
      </g>`
  }).join('')

  const yTickCount = 4
  const yTicks = Array.from({ length: yTickCount + 1 }, (_, i) => {
    const value = Math.round((max / yTickCount) * i)
    const yPos = height - padBottom - (value / max) * (height - padTop - padBottom)
    return `
      <line x1="${padLeft - 4}" y1="${yPos}" x2="${padLeft}" y2="${yPos}" class="chart-axis"/>
      <text x="${padLeft - 8}" y="${yPos}" class="chart-axis-label" text-anchor="end" dominant-baseline="middle">${value}</text>`
  }).join('')

  const xTicks = pickTickIndices(trends.length).map(index => {
    const barX = padLeft + index * (barWidth + gap) + barWidth / 2
    return `<text x="${barX}" y="${height - padBottom + 16}" class="chart-axis-label" text-anchor="middle">${esc(formatChartDate(trends[index].date))}</text>`
  }).join('')

  return `
    <svg class="trend-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Job status trend">
      <line x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${height - padBottom}" class="chart-axis"/>
      <line x1="${padLeft}" y1="${height - padBottom}" x2="${width - padRight}" y2="${height - padBottom}" class="chart-axis"/>
      ${yTicks}
      ${xTicks}
      ${bars}
    </svg>`
}

function recentPipelinesTable(pipelines) {
  if (!pipelines.length) return `<div class="jobs-placeholder">No pipelines with cached jobs in this window</div>`
  return `
    <div class="table-wrap">
      <table class="pipeline-table">
        <thead>
          <tr>
            <th>Pipeline</th>
            <th>Project</th>
            <th>Status</th>
            <th>Jobs</th>
            <th>Avg job</th>
            <th>Tests</th>
            <th>Coverage</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          ${pipelines.map(pipe => `
            <tr>
              <td><span class="pipeline-id">#${pipe.id}</span></td>
              <td>
                <div class="project-name">${esc(pipe.project_name)}</div>
                <div class="project-ns">${esc(pipe.namespace)} / ${esc(pipe.ref || '')}</div>
              </td>
              <td><span class="badge status-${esc(pipe.status)}">${statusIcon(pipe.status)} ${esc(pipe.status)}</span></td>
              <td>${pipe.job_count} (${pipe.job_status_counts?.success ?? 0}/${pipe.job_status_counts?.failed ?? 0})</td>
              <td><span class="duration-text">${formatDuration(pipe.job_duration?.avg)}</span></td>
              <td>${pipe.tests?.total ?? '-'} (${pipe.tests?.success ?? 0}/${pipe.tests?.failed ?? 0})</td>
              <td>${formatPercent(pipe.coverage)}</td>
              <td><span class="date-text">${formatDate(pipe.created_at)}</span></td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`
}

function jobsByNameTable(jobs) {
  if (!jobs.length) return `<div class="jobs-placeholder">No jobs found in this window</div>`
  return `
    <div class="jobs-rank">
      ${jobs.map(job => `
        <div class="job-rank-row">
          <div>
            <div class="job-name">${esc(job.name)}</div>
            <div class="project-ns">${job.count} runs - ${job.status_counts?.success ?? 0} passed / ${job.status_counts?.failed ?? 0} failed</div>
          </div>
          <div class="duration-text">${formatDuration(job.duration?.avg)}</div>
        </div>`).join('')}
    </div>`
}

function debounceEvent(callback, wait) {
  let timeout
  return () => {
    clearTimeout(timeout)
    timeout = setTimeout(callback, wait)
  }
}
