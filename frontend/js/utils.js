/**
 * utils.js — Pure helper functions. No side-effects, no imports.
 */

/**
 * Escape a value for safe insertion into HTML.
 * @param {*} s
 * @returns {string}
 */
export function esc(s) {
  if (s == null) return ''
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/**
 * Format a duration in seconds as a human-readable string.
 * @param {number|null} secs
 * @returns {string}
 */
export function formatDuration(secs) {
  if (secs == null || secs === '') return '—'
  const s = Math.round(secs)
  if (s < 60)   return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
}

/**
 * Format an ISO datetime string as a compact local date+time.
 * @param {string|null} iso
 * @returns {string}
 */
export function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return (
    d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) +
    ' ' +
    d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  )
}

/**
 * Map a pipeline/job status string to a short icon character.
 * @param {string} status
 * @returns {string}
 */
export function statusIcon(status) {
  const icons = {
    success:  '✓',
    failed:   '✕',
    running:  '▶',
    pending:  '◷',
    canceled: '⊘',
    skipped:  '⤼',
  }
  return icons[status] ?? '•'
}

/**
 * Set the text content of a DOM element by ID.
 * @param {string} id
 * @param {*} val
 */
export function setText(id, val) {
  const el = document.getElementById(id)
  if (el) el.textContent = val
}

/**
 * Generate a loading shimmer skeleton as an HTML string.
 * @param {number} rows
 * @returns {string}
 */
export function loadingShimmer(rows = 6) {
  return Array.from({ length: rows }, () => `
    <div class="shimmer-row">
      <div class="shimmer" style="width:${40 + Math.random() * 50}%"></div>
      <div class="shimmer shimmer--sm" style="width:${20 + Math.random() * 30}%"></div>
    </div>`
  ).join('')
}

/**
 * Debounce function calls to prevent rapid firing.
 * @param {Function} func
 * @param {number} wait
 * @returns {Function}
 */
export function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}