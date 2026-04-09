/**
 * auth.js — Authentication page JavaScript
 */

import '../src/css/auth.css'

function showTab(type) {
  // Remove active class from all tabs
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  // Hide all tab content
  document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');

  // Add active class to the tab with matching data-tab attribute
  const activeTab = document.querySelector(`.tab[data-tab="${type}"]`);
  if (activeTab) {
    activeTab.classList.add('active');
  }

  // Show the corresponding tab content
  const activeContent = document.getElementById(`${type}-tab`);
  if (activeContent) {
    activeContent.style.display = 'block';
  }
}

// Expose showTab to global scope for onclick handlers
window.showTab = showTab;

// Initialize tabs on page load
document.addEventListener('DOMContentLoaded', function() {
  // Only initialize tab switching if tabs exist
  const tabs = document.querySelectorAll('.tab');
  if (tabs.length > 0) {
    // Default to local login tab when tabs are present
    showTab('local');
  }
  // If no tabs exist (GitLab login disabled), the local tab content is already active via template
});