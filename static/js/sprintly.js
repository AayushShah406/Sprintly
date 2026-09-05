/**
 * SPRINTLY - ENTERPRISE AGILE PLATFORM CLIENT
 * Core SPA Logic, Drag & Drop Kanban, Chart.js Visualizations, and Theme Manager.
 */

const SprintlyApp = {
  state: {
    currentProject: null,
    currentSprint: null,
    issues: [],
    theme: localStorage.getItem("sprintly_theme") || "light",
  },

  init() {
    this.applyTheme(this.state.theme);
    this.bindKeyboardShortcuts();
    this.setupKanbanBoard();
    this.initChartsIfPresent();
    this.bindGlobalClickDismiss();

    if (window.lucide) {
      window.lucide.createIcons();
    }
  },

  getCsrfToken() {
    const inputToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
    if (inputToken) return inputToken;
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
    if (metaToken) return metaToken;
    const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
    if (cookieMatch) return cookieMatch[1];
    const cookieValue = document.cookie
      .split("; ")
      .find(row => row.startsWith("csrftoken="))
      ?.split("=")[1];
    return cookieValue || "";
  },

  showToast(message, type = "info") {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.style.cssText = "position:fixed;bottom:24px;left:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.style.cssText = "padding:10px 16px;border-radius:8px;font-size:0.85rem;font-weight:700;color:#fff;background:#1e293b;box-shadow:0 4px 12px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;gap:8px;pointer-events:auto;transition:opacity 0.3s ease;";
    if (type === "success") {
      toast.style.background = "#065f46";
      toast.style.borderColor = "#10b981";
    } else if (type === "error") {
      toast.style.background = "#991b1b";
      toast.style.borderColor = "#ef4444";
    } else if (type === "info") {
      toast.style.background = "#312e81";
      toast.style.borderColor = "#6366f1";
    }
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  },

  bindCardDragListeners() {
    document.querySelectorAll(".kanban-card").forEach(card => {
      card.setAttribute("draggable", "true");
      card.ondragstart = (e) => {
        card.classList.add("dragging");
        const issueId = card.getAttribute("data-id");
        if (issueId) {
          e.dataTransfer.setData("text/plain", issueId);
        }
      };
      card.ondragend = () => {
        card.classList.remove("dragging");
      };
    });
  },

  bindColumnDropListeners() {
    const columns = document.querySelectorAll(".kanban-column");
    columns.forEach(col => {
      col.ondragover = (e) => {
        e.preventDefault();
        col.classList.add("drag-over");
        col.style.background = "rgba(99, 102, 241, 0.08)";
      };

      col.ondragleave = () => {
        col.classList.remove("drag-over");
        col.style.background = "";
      };

      col.ondrop = async (e) => {
        e.preventDefault();
        col.classList.remove("drag-over");
        col.style.background = "";
        const issueId = e.dataTransfer.getData("text/plain");
        const newStatus = col.getAttribute("data-status");

        if (issueId && newStatus) {
          const cardEl = document.querySelector(`.kanban-card[data-id="${issueId}"]`);
          const targetCardsContainer = col.querySelector(".column-cards") || col;
          if (cardEl && targetCardsContainer) {
            const originalContainer = cardEl.parentElement;
            if (originalContainer === targetCardsContainer) {
              return;
            }
            // Optimistically move card in UI
            targetCardsContainer.appendChild(cardEl);
            SprintlyApp.updateKanbanCounters();

            // Send status update to API
            const success = await SprintlyApp.moveIssueStatus(issueId, newStatus);
            if (!success) {
              // Rollback card to original position if failed
              if (originalContainer) {
                originalContainer.appendChild(cardEl);
              }
              SprintlyApp.updateKanbanCounters();
            } else {
              cardEl.setAttribute("data-status", newStatus);
            }
          }
        }
      };
    });
  },

  updateKanbanCounters() {
    document.querySelectorAll(".kanban-column").forEach(col => {
      const status = col.getAttribute("data-status");
      const cards = col.querySelectorAll(".kanban-card");
      const countEl = col.querySelector(".col-count") || document.getElementById(`count-${status?.toLowerCase()}`);
      if (countEl) countEl.innerText = cards.length;
    });
  },

  // ==========================================
  // THEME MANAGEMENT (LIGHT / DARK)
  // ==========================================
  applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    this.state.theme = theme;
    localStorage.setItem("sprintly_theme", theme);

    const icon = document.getElementById("themeToggleIcon");
    if (icon) {
      icon.setAttribute("data-lucide", theme === "dark" ? "sun" : "moon");
      if (window.lucide) window.lucide.createIcons();
    }
  },

  toggleTheme() {
    const nextTheme = this.state.theme === "dark" ? "light" : "dark";
    this.applyTheme(nextTheme);
    this.showToast(`Switched to ${nextTheme.toUpperCase()} theme`, "info");
  },

  // ==========================================
  // KEYBOARD SHORTCUTS & SEARCH
  // ==========================================
  bindKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Ctrl+K or Cmd+K: Open Command Palette
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        this.openCommandPalette();
      }
      // Esc: Close Modals
      if (e.key === "Escape") {
        this.closeAllModals();
      }
    });
  },

  openCommandPalette() {
    const modal = document.getElementById("commandPaletteModal");
    if (modal) {
      modal.classList.add("active");
      const input = document.getElementById("paletteSearchInput") || document.getElementById("commandPaletteInput");
      if (input) {
        input.value = "";
        input.focus();
      }
    }
  },

  closeCommandPalette() {
    const modal = document.getElementById("commandPaletteModal");
    if (modal) modal.classList.remove("active");
  },

  openCreateProjectModal() {
    const modal = document.getElementById("createProjectModal");
    if (modal) modal.classList.add("active");
  },

  openCreateIssueModal() {
    const modal = document.getElementById("globalCreateIssueModal");
    if (modal) modal.classList.add("active");
  },

  bindGlobalClickDismiss() {
    document.addEventListener("click", (e) => {
      const popover = document.getElementById("systemStatusPopover");
      const widget = document.getElementById("systemStatusWidget");
      if (popover && popover.classList.contains("open")) {
        if (!popover.contains(e.target) && !widget?.contains(e.target)) {
          popover.classList.remove("open");
        }
      }
    });
  },

  toggleStatusPopover(event) {
    if (event) event.stopPropagation();
    const popover = document.getElementById("systemStatusPopover");
    if (popover) {
      popover.classList.toggle("open");
      if (popover.classList.contains("open") && window.lucide) {
        lucide.createIcons();
      }
    }
  },

  closeStatusPopover() {
    const popover = document.getElementById("systemStatusPopover");
    if (popover) popover.classList.remove("open");
  },

  closeAllModals() {
    document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active", "open"));
    this.closeStatusPopover();
  },

  async handlePaletteSearch(query) {
    const resultsContainer = document.getElementById("paletteResultsList") || document.getElementById("commandSearchResults");
    if (!resultsContainer) return;

    if (!query.trim()) {
      resultsContainer.innerHTML = `
        <div class="palette-section-title">QUICK ACTIONS</div>
        <div class="palette-item" onclick="SprintlyApp.openCreateIssueModal(); SprintlyApp.closeCommandPalette();">
          <i data-lucide="plus-circle" style="width:16px;height:16px;color:var(--accent-primary);"></i>
          <span>Create New Issue</span>
          <span class="palette-item-tag">Issue</span>
        </div>
        <div class="palette-item" onclick="window.location.href='/projects/';">
          <i data-lucide="folder-plus" style="width:16px;height:16px;color:#0284c7;"></i>
          <span>Create / Browse Projects</span>
          <span class="palette-item-tag">Project</span>
        </div>
        <div class="palette-item" onclick="SprintlyAI.toggleDrawer(); SprintlyApp.closeCommandPalette();">
          <i data-lucide="sparkles" style="width:16px;height:16px;color:#a855f7;"></i>
          <span>Ask Sprintly AI Assistant</span>
          <span class="palette-item-tag">AI</span>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    try {
      const res = await fetch(`/search/?q=${encodeURIComponent(query)}&format=json`, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });
      const data = await res.json();
      
      let html = "";
      if (data.issues && data.issues.length > 0) {
        html += `<div class="palette-section-title">ISSUES</div>`;
        data.issues.forEach(i => {
          html += `
            <a href="/issues/${i.id}/" class="palette-item">
              <span><strong>${i.key}</strong> - ${i.title}</span>
              <span class="badge-priority priority-${i.priority}">${i.priority}</span>
            </a>
          `;
        });
      }

      if (data.projects && data.projects.length > 0) {
        html += `<div class="palette-section-title">PROJECTS</div>`;
        data.projects.forEach(p => {
          html += `
            <a href="/projects/${p.id}/" class="palette-item">
              <span><i data-lucide="folder" style="width:14px;height:14px;margin-right:6px;"></i>${p.key} - ${p.name}</span>
              <span class="palette-item-tag">${p.category || 'Project'}</span>
            </a>
          `;
        });
      }

      if (!html) {
        html = `<div style="padding:16px;color:var(--text-muted);font-size:0.85rem;text-align:center;">No matching results found for "${query}".</div>`;
      }

      resultsContainer.innerHTML = html;
      if (window.lucide) window.lucide.createIcons();
    } catch (e) {
      console.error("Palette search error", e);
    }
  },

  async submitCreateIssue(event) {
    if (event) event.preventDefault();
    const projectId = document.getElementById("modalIssueProject")?.value || document.getElementById("createProject")?.value;
    const title = (document.getElementById("modalIssueTitle")?.value || document.getElementById("createTitle")?.value || "").trim();
    const issueType = document.getElementById("modalIssueType")?.value || document.getElementById("createType")?.value || "TASK";
    const priority = document.getElementById("modalIssuePriority")?.value || document.getElementById("createPriority")?.value || "MEDIUM";
    const storyPoints = parseInt(document.getElementById("modalIssuePoints")?.value || document.getElementById("createPoints")?.value || 3);
    const description = (document.getElementById("modalIssueDesc")?.value || document.getElementById("createDesc")?.value || "").trim();
    const dueDate = document.getElementById("createDueDate")?.value || null;
    const labels = document.getElementById("createLabels")?.value || "";

    if (!projectId || !title) {
      this.showToast("Please select a project and provide an issue title.", "error");
      return;
    }

    try {
      const res = await fetch("/api/issues/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken()
        },
        body: JSON.stringify({
          project_id: parseInt(projectId),
          project: parseInt(projectId),
          title: title,
          issue_type: issueType,
          priority: priority,
          story_points: storyPoints,
          description: description,
          due_date: dueDate,
          labels: labels,
        })
      });

      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        this.closeAllModals();
        const key = data.issue?.key || "Issue";
        this.showToast(`${key} created successfully!`, "success");
        setTimeout(() => window.location.reload(), 500);
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(err.error || err.detail || "Failed to create issue.", "error");
      }
    } catch (e) {
      console.error("Create issue error", e);
      this.showToast("Network error creating issue.", "error");
    }
  },

  // ==========================================
  // KANBAN BOARD & DRAG-AND-DROP
  // ==========================================
  setupKanbanBoard() {
    this.bindCardDragListeners();
    this.bindColumnDropListeners();
    this.updateKanbanCounters();
  },

  filterBoard() {
    const filterType = document.getElementById("filterType")?.value || "";
    const filterPriority = document.getElementById("filterPriority")?.value || "";
    const searchVal = document.getElementById("searchIssuesInput")?.value.toLowerCase().trim() || "";

    document.querySelectorAll(".kanban-card").forEach(card => {
      let show = true;
      if (filterType) {
        const typeEl = card.querySelector(".type-badge-pill");
        if (!typeEl || !typeEl.textContent.trim().toUpperCase().includes(filterType.toUpperCase())) {
          show = false;
        }
      }
      if (filterPriority) {
        const priorityEl = card.querySelector(".badge-priority");
        if (!priorityEl || !priorityEl.textContent.trim().toUpperCase().includes(filterPriority.toUpperCase())) {
          show = false;
        }
      }
      if (searchVal) {
        const text = card.textContent.toLowerCase();
        if (!text.includes(searchVal)) {
          show = false;
        }
      }
      card.style.display = show ? "block" : "none";
    });

    this.updateKanbanCounters();
  },

  async moveIssueStatus(issueId, newStatus) {
    try {
      const res = await fetch(`/api/issues/${issueId}/move/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken(),
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (res.ok) {
        this.updateKanbanCounters();
        this.showToast(`Updated ticket status to ${newStatus.replace(/_/g, " ")}`, "success");
        return true;
      } else {
        const errData = await res.json().catch(() => ({}));
        this.showToast(errData.detail || errData.error || "Failed to update status on server", "error");
        return false;
      }
    } catch (e) {
      console.error("Move status failed", e);
      this.showToast("Network error moving ticket", "error");
      return false;
    }
  },

  async toggleSubtask(subtaskId) {
    try {
      await fetch(`/api/issues/subtasks/${subtaskId}/toggle/`, {
        method: "POST",
        headers: { "X-CSRFToken": this.getCsrfToken() },
      });
      this.showToast("Subtask state updated.", "info");
    } catch (e) {
      console.error(e);
    }
  },

  async toggleWatchIssue(issueId) {
    try {
      const res = await fetch(`/api/issues/${issueId}/watch/`, {
        method: "POST",
        headers: { "X-CSRFToken": this.getCsrfToken() },
      });
      const data = await res.json();
      const text = document.getElementById("watchText");
      if (text) {
        text.innerText = data.watching ? `Watching (${data.total_watchers})` : `Watch (${data.total_watchers})`;
      }
      this.showToast(data.watching ? "You are now watching this ticket." : "Removed from watchers.", "info");
    } catch (e) {
      console.error(e);
    }
  },

  async improveIssueWithAI() {
    const titleInput = document.getElementById("createTitle");
    const descInput = document.getElementById("createDesc");
    const typeSelect = document.getElementById("createType");
    const prioritySelect = document.getElementById("createPriority");
    const pointsInput = document.getElementById("createPoints");
    const labelsInput = document.getElementById("createLabels");

    if (!titleInput || !titleInput.value.trim()) {
      this.showToast("Please enter an issue title first.", "error");
      return;
    }

    this.showToast("✨ Sprintly AI is analyzing your issue...", "info");

    try {
      const res = await fetch("/api/ai/improve-issue/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": this.getCsrfToken() },
        body: JSON.stringify({
          title: titleInput.value.trim(),
          description: descInput ? descInput.value.trim() : "",
        })
      });
      const data = await res.json();
      if (data.success && data.suggestion) {
        const s = data.suggestion;
        if (s.title) titleInput.value = s.title;
        if (descInput && s.description) descInput.value = s.description;
        if (typeSelect && s.issue_type) typeSelect.value = s.issue_type;
        if (prioritySelect && s.priority) prioritySelect.value = s.priority;
        if (pointsInput && s.story_points) pointsInput.value = s.story_points;
        if (labelsInput && s.labels) labelsInput.value = s.labels;

        this.showToast("✨ Issue improved with AI recommendations!", "success");
      }
    } catch (e) {
      this.showToast("Sprintly AI is temporarily unavailable.", "error");
    }
  },

  async findSimilarIssuesWithAI() {
    const titleInput = document.getElementById("createTitle");
    const projectSelect = document.getElementById("createProject");
    if (!titleInput || !titleInput.value.trim()) {
      this.showToast("Enter a title to search for duplicates.", "error");
      return;
    }

    try {
      const res = await fetch("/api/ai/find-similar/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": this.getCsrfToken() },
        body: JSON.stringify({
          title: titleInput.value.trim(),
          project_id: projectSelect ? projectSelect.value : null
        })
      });
      const data = await res.json();
      if (data.similar_issues && data.similar_issues.length > 0) {
        SprintlyAI.openDrawer();
        const items = data.similar_issues.map(i => `
          <div class="ai-action-item">
            <a href="/issues/${i.id}/" target="_blank" style="font-weight:700;color:var(--text-primary);text-decoration:none;">${i.key}: ${i.title}</a>
            <span class="badge-priority priority-HIGH">${i.similarity_pct}% Match</span>
          </div>
        `).join("");
        SprintlyAI.appendBotMessage(`<div><div style="font-weight:700;margin-bottom:6px;">✨ Similar / Duplicate Issues Found</div><div class="ai-action-list">${items}</div></div>`);
      } else {
        this.showToast("No duplicate issues detected. Looks good!", "info");
      }
    } catch (e) {
      this.showToast("Failed to check duplicate issues.", "error");
    }
  },

  // ==========================================
  // ISSUE DETAIL INTERACTIONS
  // ==========================================
  async toggleWatchIssue(issueId) {
    try {
      const res = await fetch(`/issues/${issueId}/watch/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken()
        }
      });
      const data = await res.json();
      const watchText = document.getElementById("watchText");
      const watchBtn = document.getElementById("watchBtn");
      if (watchText) {
        if (data.watching) {
          watchText.textContent = `Watching (${data.count})`;
          if (watchBtn) {
            watchBtn.style.background = "rgba(79, 70, 229, 0.12)";
            watchBtn.style.color = "var(--accent-primary)";
            watchBtn.style.borderColor = "var(--accent-primary)";
          }
          this.showToast("You are now watching this ticket.", "success");
        } else {
          watchText.textContent = `Watch (${data.count})`;
          if (watchBtn) {
            watchBtn.style.background = "";
            watchBtn.style.color = "";
            watchBtn.style.borderColor = "";
          }
          this.showToast("Unwatched ticket.", "info");
        }
      }
    } catch (err) {
      console.error("Failed to toggle watcher:", err);
      this.showToast("Could not update watch status.", "error");
    }
  },

  async toggleSubtask(subtaskId) {
    try {
      const res = await fetch(`/issues/subtasks/${subtaskId}/toggle/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken()
        }
      });
      const data = await res.json();
      const itemEl = document.getElementById(`subtask-item-${subtaskId}`);
      if (itemEl) {
        const textEl = itemEl.querySelector(".subtask-title-text");
        if (data.is_completed) {
          itemEl.classList.add("completed");
          if (textEl) textEl.classList.add("completed");
        } else {
          itemEl.classList.remove("completed");
          if (textEl) textEl.classList.remove("completed");
        }
      }
      this.recalcSubtasksProgress();
    } catch (err) {
      console.error("Failed to toggle subtask:", err);
      this.showToast("Failed to update subtask.", "error");
    }
  },

  async deleteSubtask(subtaskId) {
    if (!confirm("Remove this subtask?")) return;
    try {
      const res = await fetch(`/issues/subtasks/${subtaskId}/delete/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": this.getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        }
      });
      const data = await res.json();
      if (data.status === "success") {
        const itemEl = document.getElementById(`subtask-item-${subtaskId}`);
        if (itemEl) itemEl.remove();
        this.recalcSubtasksProgress();
        this.showToast("Subtask removed.", "success");
      }
    } catch (err) {
      console.error("Failed to delete subtask:", err);
      this.showToast("Could not remove subtask.", "error");
    }
  },

  recalcSubtasksProgress() {
    const all = document.querySelectorAll(".subtask-item");
    const completed = document.querySelectorAll(".subtask-item.completed");
    const total = all.length;
    const done = completed.length;
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    const counterEl = document.getElementById("subtasksCounter");
    const pctEl = document.getElementById("subtasksPct");
    const fillEl = document.getElementById("subtasksProgressFill");
    if (counterEl) counterEl.textContent = `(${done}/${total})`;
    if (pctEl) pctEl.textContent = `${pct}%`;
    if (fillEl) fillEl.style.width = `${pct}%`;
  },

  openDeleteIssueModal() {
    const modal = document.getElementById("deleteIssueModal");
    if (modal) {
      modal.classList.add("active");
      if (window.lucide) window.lucide.createIcons();
    }
  },

  closeDeleteIssueModal() {
    const modal = document.getElementById("deleteIssueModal");
    if (modal) modal.classList.remove("active");
  },

  async submitDeleteIssue(issueId) {
    const btn = document.getElementById("confirmDeleteBtn");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `Deleting...`;
    }
    try {
      const res = await fetch(`/issues/${issueId}/delete/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": this.getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json"
        }
      });
      const data = await res.json();
      if (data.status === "success") {
        this.showToast(data.message || "Ticket deleted successfully.", "success");
        setTimeout(() => {
          window.location.href = data.redirect_url || "/projects/";
        }, 350);
      } else {
        this.showToast(data.message || "Could not delete issue.", "error");
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i data-lucide="trash-2" style="width:14px;height:14px;"></i> Delete Permanently`;
          if (window.lucide) window.lucide.createIcons();
        }
      }
    } catch (err) {
      console.error("Delete issue failed, falling back to form submit:", err);
      const form = document.getElementById("deleteIssueForm");
      if (form) form.submit();
    }
  },

  setStoryPoints(points) {
    const input = document.getElementById("sidebarStoryPoints");
    if (input) {
      input.value = points;
      document.querySelectorAll(".story-point-pill").forEach(p => {
        p.classList.toggle("active", p.getAttribute("data-points") == points);
      });
      const form = document.getElementById("sidebarDetailsForm");
      if (form) form.submit();
    }
  },

  openCompleteSprintModal(sprintId, sprintName) {
    const modal = document.getElementById("completeSprintModal");
    if (!modal) return;
    const titleEl = document.getElementById("completeSprintModalTitle");
    const nameEl = document.getElementById("completeSprintNameText");
    const form = document.getElementById("completeSprintModalForm");
    if (titleEl) titleEl.textContent = `Complete ${sprintName}`;
    if (nameEl) nameEl.textContent = sprintName;
    if (form) {
      form.action = `/sprints/${sprintId}/complete/`;
      form.setAttribute("data-sprint-id", sprintId);
    }
    modal.classList.add("active");
    if (window.lucide) window.lucide.createIcons();
  },

  closeCompleteSprintModal() {
    const modal = document.getElementById("completeSprintModal");
    if (modal) modal.classList.remove("active");
  },

  async submitCompleteSprint(e) {
    if (e) e.preventDefault();
    const form = document.getElementById("completeSprintModalForm");
    if (!form) return;
    const btn = document.getElementById("confirmCompleteSprintBtn");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `Completing...`;
    }
    const sprintId = form.getAttribute("data-sprint-id");
    const targetSelect = form.querySelector("[name='target_sprint_id']");
    const targetSprintId = targetSelect ? targetSelect.value : "backlog";

    try {
      const res = await fetch(form.action || `/sprints/${sprintId}/complete/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": this.getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json"
        },
        body: new URLSearchParams({
          csrfmiddlewaretoken: this.getCsrfToken(),
          target_sprint_id: targetSprintId
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        this.showToast(data.message || "Sprint completed successfully!", "success");
        setTimeout(() => {
          window.location.href = data.redirect_url || window.location.href;
        }, 400);
      } else {
        this.showToast(data.message || "Failed to complete sprint.", "error");
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i data-lucide="check-circle" style="width:14px;height:14px;"></i> Confirm & Complete Sprint`;
          if (window.lucide) window.lucide.createIcons();
        }
      }
    } catch (err) {
      console.error("Complete sprint error, fallback to form submit:", err);
      form.submit();
    }
  },

  // ==========================================
  // CHART.JS VISUALIZATIONS (Dynamic Only)
  // ==========================================
  initChartsIfPresent() {
    // Dynamic initialization handled by template scripts with backend context
  }
};

// ==========================================================================
// SPRINTLY AI ASSISTANT CLIENT ENGINE
// ==========================================================================
const SprintlyAI = {
  state: {
    isOpen: false,
    context: {},
  },

  init() {
    this.detectContext();
    this.renderContextBanner();
    this.renderSuggestions();
    this.bindEvents();
  },

  detectContext() {
    const path = window.location.pathname;
    const ctx = {
      path: path,
      type: "WORKSPACE",
      label: "Workspace Overview",
      projectId: null,
      sprintId: null,
      issueId: null,
      tab: null,
    };

    const projMatch = path.match(/\/projects\/(\d+)(?:\/([a-z-]+))?/);
    if (projMatch) {
      ctx.projectId = projMatch[1];
      ctx.tab = projMatch[2] || "overview";
      ctx.type = ctx.tab.toUpperCase();
      ctx.label = `Project #${ctx.projectId} • ${ctx.tab.toUpperCase()}`;
    }

    const sprintMatch = path.match(/\/sprints\/(\d+)/);
    if (sprintMatch) {
      ctx.sprintId = sprintMatch[1];
      ctx.type = "SPRINT";
      ctx.label = `Sprint #${ctx.sprintId}`;
    }

    const issueMatch = path.match(/\/issues\/(\d+)/);
    if (issueMatch) {
      ctx.issueId = issueMatch[1];
      ctx.type = "ISSUE";
      ctx.label = `Issue #${ctx.issueId}`;
    }

    if (path.includes("my-work")) {
      ctx.type = "MY_WORK";
      ctx.label = "My Personal Work";
    }

    this.state.context = ctx;
  },

  renderContextBanner() {
    const chip = document.getElementById("aiContextChip");
    if (chip) {
      chip.innerHTML = `<i data-lucide="compass" style="width:14px;height:14px;"></i> <span>${this.state.context.label}</span>`;
      if (window.lucide) window.lucide.createIcons();
    }
  },

  renderSuggestions() {
    const container = document.getElementById("aiSuggestionPills");
    if (!container) return;

    const ctxType = this.state.context.type;
    let suggestions = [];

    if (ctxType === "PROJECT" || ctxType === "OVERVIEW") {
      suggestions = [
        { label: "Summarize Project", action: "project_summary" },
        { label: "Find Project Risks", action: "project_risks" },
        { label: "Review Team Workload", action: "team_workload" },
        { label: "Plan Sprint", action: "plan_sprint" },
      ];
    } else if (ctxType === "SPRINT") {
      suggestions = [
        { label: "Analyze Sprint Risk", action: "analyze_sprint" },
        { label: "Recommend Sprint Changes", action: "analyze_sprint" },
      ];
    } else if (ctxType === "BACKLOG") {
      suggestions = [
        { label: "Plan Next Sprint", action: "plan_sprint" },
        { label: "Find Project Risks", action: "project_risks" },
      ];
    } else if (ctxType === "ISSUE") {
      suggestions = [
        { label: "Generate Acceptance Criteria", action: "acceptance_criteria" },
        { label: "Break Down into Subtasks", action: "breakdown_issue" },
        { label: "Suggest Priority", action: "suggest_priority" },
      ];
    } else if (ctxType === "TEAM") {
      suggestions = [
        { label: "Analyze Team Workload", action: "team_workload" },
      ];
    } else if (ctxType === "MY_WORK") {
      suggestions = [
        { label: "What Should I Work On?", action: "daily_work" },
        { label: "Generate My Standup", action: "generate_standup" },
      ];
    } else {
      suggestions = [
        { label: "What Should I Work On?", action: "daily_work" },
        { label: "Generate My Standup", action: "generate_standup" },
        { label: "Summarize Project", action: "project_summary" },
      ];
    }

    container.innerHTML = suggestions.map(s => `
      <button type="button" class="ai-suggestion-chip" onclick="SprintlyAI.triggerAction('${s.action}')">
        <i data-lucide="sparkles" style="width:13px;height:13px;"></i>
        <span>${s.label}</span>
      </button>
    `).join("");
    if (window.lucide) lucide.createIcons();
  },

  getThread() {
    return document.getElementById("aiChatThread") || document.getElementById("aiDrawerMessages");
  },

  getInput() {
    return document.getElementById("aiChatInput") || document.getElementById("aiDrawerInput");
  },

  sendUserQuery() {
    return this.handleSendMessage();
  },

  bindEvents() {
    const input = this.getInput();
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        }
      });
    }
    const btn = document.getElementById("aiSendBtn") || document.querySelector(".ai-send-btn");
    if (btn) {
      btn.onclick = (e) => {
        e.preventDefault();
        this.handleSendMessage();
      };
    }
  },

  openDrawer() {
    const drawer = document.getElementById("sprintlyAiDrawer") || document.getElementById("aiDrawer");
    const overlay = document.getElementById("aiDrawerOverlay");
    if (drawer) drawer.classList.add("open");
    if (overlay) overlay.classList.add("active");
    this.state.isOpen = true;

    const input = this.getInput();
    if (input) setTimeout(() => input.focus(), 150);
  },

  closeDrawer() {
    const drawer = document.getElementById("sprintlyAiDrawer") || document.getElementById("aiDrawer");
    const overlay = document.getElementById("aiDrawerOverlay");
    if (drawer) drawer.classList.remove("open");
    if (overlay) overlay.classList.remove("active");
    this.state.isOpen = false;
  },

  toggleDrawer() {
    if (this.state.isOpen) this.closeDrawer();
    else this.openDrawer();
  },

  clearChat() {
    const thread = this.getThread();
    if (thread) {
      thread.innerHTML = `
        <div class="ai-msg-row">
          <div class="ai-avatar-badge" style="width:28px;height:28px;font-size:0.75rem;"><i data-lucide="sparkles" style="width:14px;height:14px;"></i></div>
          <div class="ai-msg-bubble bot">
            Hello! I am <strong>Sprintly AI</strong>. I analyze your project data, plan sprints, identify delivery risks, improve issues, and answer questions. How can I help you today?
          </div>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
    }
  },

  async handleSendMessage() {
    const input = this.getInput();
    if (!input || !input.value.trim()) return;

    const query = input.value.trim();
    input.value = "";
    this.appendUserMessage(query);
    this.showTypingIndicator();

    try {
      const res = await fetch("/api/ai/chat/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": SprintlyApp.getCsrfToken()
        },
        body: JSON.stringify({
          message: query,
          context: this.state.context
        })
      });
      const data = await res.json();
      this.removeTypingIndicator();
      if (data && data.answer) {
        this.appendBotMessage(data.answer);
      } else if (data && data.error) {
        this.appendBotMessage(`⚠️ ${data.error}`);
      } else {
        this.appendBotMessage("Sprintly AI is currently analyzing your request.");
      }
    } catch (e) {
      this.removeTypingIndicator();
      this.appendBotMessage("Sprintly AI is temporarily unavailable. Please try again later.");
    }
  },

  appendUserMessage(text) {
    const thread = this.getThread();
    if (!thread) return;
    const row = document.createElement("div");
    row.className = "ai-msg-row user";
    row.innerHTML = `<div class="ai-msg-bubble user">${this.escapeHtml(text)}</div>`;
    thread.appendChild(row);
    thread.scrollTop = thread.scrollHeight;
  },

  appendBotMessage(content) {
    const thread = this.getThread();
    if (!thread) return;
    
    // Check if content is already structured HTML or raw Markdown
    const formattedHtml = content.startsWith("<div") ? content : this.formatMarkdown(content);

    const row = document.createElement("div");
    row.className = "ai-msg-row";
    row.innerHTML = `
      <div class="ai-avatar-badge" style="width:28px;height:28px;font-size:0.75rem;"><i data-lucide="sparkles" style="width:14px;height:14px;"></i></div>
      <div class="ai-msg-bubble bot">${formattedHtml}</div>
    `;
    thread.appendChild(row);
    if (window.lucide) window.lucide.createIcons();
    thread.scrollTop = thread.scrollHeight;
  },

  formatMarkdown(text) {
    if (!text) return "";
    let html = text
      .replace(/^### (.*$)/gim, '<h4 style="font-size:0.92rem;font-weight:700;margin:10px 0 4px;color:var(--text-primary);">$1</h4>')
      .replace(/^## (.*$)/gim, '<h3 style="font-size:1.02rem;font-weight:800;margin:12px 0 6px;color:var(--text-primary);">$1</h3>')
      .replace(/^# (.*$)/gim, '<h2 style="font-size:1.1rem;font-weight:800;margin:14px 0 8px;color:var(--text-primary);">$1</h2>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/`([^`]+)`/gim, '<code style="background:rgba(79,70,229,0.1);color:var(--accent-primary);padding:2px 5px;border-radius:4px;font-family:var(--font-mono);font-size:0.8rem;">$1</code>')
      .replace(/^\s*-\s+(.*$)/gim, '<li style="margin:3px 0;">$1</li>')
      .replace(/^\s*\*\s+(.*$)/gim, '<li style="margin:3px 0;">$1</li>')
      .replace(/\n\n/gim, '<br><br>')
      .replace(/\n/gim, '<br>');
    return html;
  },

  showTypingIndicator() {
    const thread = this.getThread();
    if (!thread) return;
    const typing = document.createElement("div");
    typing.id = "aiTypingIndicator";
    typing.className = "ai-msg-row";
    typing.innerHTML = `
      <div class="ai-avatar-badge" style="width:28px;height:28px;font-size:0.75rem;"><i data-lucide="sparkles" style="width:14px;height:14px;"></i></div>
      <div class="ai-typing-indicator">
        <span class="ai-typing-dot"></span>
        <span class="ai-typing-dot"></span>
        <span class="ai-typing-dot"></span>
      </div>
    `;
    thread.appendChild(typing);
    thread.scrollTop = thread.scrollHeight;
  },

  removeTypingIndicator() {
    const ind = document.getElementById("aiTypingIndicator");
    if (ind) ind.remove();
  },

  async triggerAction(actionName) {
    this.openDrawer();
    this.showTypingIndicator();

    try {
      if (actionName === "plan_sprint") {
        const res = await fetch("/api/ai/plan-sprint/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
          body: JSON.stringify({ project_id: this.state.context.projectId })
        });
        const data = await res.json();
        this.removeTypingIndicator();

        if (data.recommended_issues && data.recommended_issues.length > 0) {
          const issueRows = data.recommended_issues.map(i => `
            <div class="ai-action-item">
              <span><strong>${i.key}</strong>: ${i.title}</span>
              <span class="badge-points">${i.points} pts</span>
            </div>
          `).join("");

          const html = `
            <div>
              <div style="font-weight:700;margin-bottom:6px;">✨ AI Sprint Recommendation</div>
              <p style="font-size:0.8rem;color:var(--text-secondary);">${data.reasoning}</p>
              <div style="margin:8px 0;font-size:0.8rem;">
                <strong>Planned Points:</strong> ${data.total_points} / ${data.capacity} pts
                <span class="badge-priority priority-${data.confidence === 'HIGH' ? 'LOW' : 'MEDIUM'}" style="margin-left:6px;">${data.confidence} Confidence</span>
              </div>
              <div class="ai-action-card">
                <div class="ai-action-header"><i data-lucide="layers" style="width:14px;height:14px;"></i> Recommended Scope</div>
                <div class="ai-action-list">${issueRows}</div>
                <div class="ai-action-btn-group">
                  <button class="btn-ai-apply" onclick="SprintlyAI.applySprintPlan(${JSON.stringify(data.recommended_issues.map(i=>i.id))})">
                    <i data-lucide="check" style="width:12px;height:12px;"></i> Apply Plan
                  </button>
                  <button class="btn-ai-cancel" onclick="this.closest('.ai-action-card').remove()">Cancel</button>
                </div>
              </div>
            </div>
          `;
          this.appendBotMessage(html);
        } else {
          this.appendBotMessage(data.reasoning || "No backlog issues currently available for planning.");
        }
      }
      else if (actionName === "analyze_sprint") {
        const res = await fetch("/api/ai/analyze-sprint/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
          body: JSON.stringify({
            sprint_id: this.state.context.sprintId,
            project_id: this.state.context.projectId
          })
        });
        const data = await res.json();
        this.removeTypingIndicator();

        const riskItems = (data.detected_risks || []).map(r => `<div style="color:#ef4444;font-size:0.8rem;margin:3px 0;">${r}</div>`).join("");
        const recItems = (data.recommendations || []).map(r => `<li style="font-size:0.8rem;margin:4px 0;">${r}</li>`).join("");

        const html = `
          <div>
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
              <strong>✨ Sprint Health: ${data.health_score}%</strong>
              <span class="badge-priority priority-${data.risk_level}">${data.risk_level} RISK</span>
            </div>
            <div style="margin-bottom:10px;">${riskItems}</div>
            <div style="font-weight:700;font-size:0.82rem;margin-top:8px;">Recommendations:</div>
            <ul style="padding-left:18px;margin-top:4px;">${recItems}</ul>
          </div>
        `;
        this.appendBotMessage(html);
      }
      else if (actionName === "project_summary" || actionName === "project_risks") {
        const res = await fetch("/api/ai/project-summary/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
          body: JSON.stringify({ project_id: this.state.context.projectId })
        });
        const data = await res.json();
        this.removeTypingIndicator();
        this.appendBotMessage(`<div><div style="font-weight:700;margin-bottom:6px;">✨ Project Summary (${data.project_name})</div><p style="font-size:0.83rem;line-height:1.5;">${data.summary}</p></div>`);
      }
      else if (actionName === "generate_standup") {
        const res = await fetch("/api/ai/standup/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() }
        });
        const data = await res.json();
        this.removeTypingIndicator();

        const yHtml = (data.yesterday || []).map(item => `<li>${item}</li>`).join("");
        const tHtml = (data.today || []).map(item => `<li>${item}</li>`).join("");
        const bHtml = (data.blockers || []).map(item => `<li>${item}</li>`).join("");

        const html = `
          <div>
            <div style="font-weight:700;margin-bottom:6px;">✨ Daily Standup Summary</div>
            <div style="font-size:0.8rem;">
              <strong>Yesterday:</strong><ul style="margin:2px 0 6px;padding-left:18px;">${yHtml}</ul>
              <strong>Today:</strong><ul style="margin:2px 0 6px;padding-left:18px;">${tHtml}</ul>
              <strong>Blockers:</strong><ul style="margin:2px 0 0;padding-left:18px;">${bHtml}</ul>
            </div>
          </div>
        `;
        this.appendBotMessage(html);
      }
      else if (actionName === "daily_work") {
        const res = await fetch("/api/ai/my-work-recommendations/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() }
        });
        const data = await res.json();
        this.removeTypingIndicator();

        if (data.recommendations && data.recommendations.length > 0) {
          const recHtml = data.recommendations.map(r => `
            <div class="ai-action-item" style="flex-direction:column;align-items:flex-start;gap:2px;">
              <div style="display:flex;align-items:center;justify-content:space-between;width:100%;">
                <a href="/issues/${r.id}/" style="font-weight:700;color:var(--text-primary);text-decoration:none;">${r.key}: ${r.title}</a>
                <span class="badge-priority priority-${r.priority}">${r.priority}</span>
              </div>
              <div style="font-size:0.75rem;color:var(--text-secondary);">${r.reason}</div>
            </div>
          `).join("");
          this.appendBotMessage(`<div><div style="font-weight:700;margin-bottom:8px;">✨ Recommended Daily Work Order</div><div class="ai-action-list">${recHtml}</div></div>`);
        } else {
          this.appendBotMessage("No pending assigned tickets found. Your queue is all clear!");
        }
      }
      else if (actionName === "acceptance_criteria") {
        if (!this.state.context.issueId) {
          this.removeTypingIndicator();
          this.appendBotMessage("Please navigate to an issue detail page to generate acceptance criteria.");
          return;
        }
        const res = await fetch("/api/ai/acceptance-criteria/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
          body: JSON.stringify({ issue_id: this.state.context.issueId })
        });
        const data = await res.json();
        this.removeTypingIndicator();

        const criteriaList = (data.acceptance_criteria || []).map(c => `<li>${c}</li>`).join("");
        this.appendBotMessage(`<div><div style="font-weight:700;margin-bottom:6px;">✨ Acceptance Criteria (${data.issue_key})</div><ul style="padding-left:18px;font-size:0.82rem;line-height:1.5;">${criteriaList}</ul></div>`);
      }
      else if (actionName === "breakdown_issue") {
        if (!this.state.context.issueId) {
          this.removeTypingIndicator();
          this.appendBotMessage("Please navigate to an issue detail page to break it into subtasks.");
          return;
        }
        const res = await fetch("/api/ai/breakdown-issue/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
          body: JSON.stringify({ issue_id: this.state.context.issueId })
        });
        const data = await res.json();
        this.removeTypingIndicator();

        const subtaskList = (data.suggested_subtasks || []).map(st => `<div class="ai-action-item"><span>${st}</span></div>`).join("");
        const html = `
          <div>
            <div style="font-weight:700;margin-bottom:6px;">✨ Suggested Subtasks (${data.issue_key})</div>
            <div class="ai-action-card">
              <div class="ai-action-list">${subtaskList}</div>
              <div class="ai-action-btn-group">
                <button class="btn-ai-apply" onclick="SprintlyAI.applySubtasks(${this.state.context.issueId}, ${JSON.stringify(data.suggested_subtasks)})">
                  <i data-lucide="plus" style="width:12px;height:12px;"></i> Create Subtasks
                </button>
                <button class="btn-ai-cancel" onclick="this.closest('.ai-action-card').remove()">Cancel</button>
              </div>
            </div>
          </div>
        `;
        this.appendBotMessage(html);
      }
      else if (actionName === "suggest_priority") {
        if (!this.state.context.issueId) {
          this.removeTypingIndicator();
          this.appendBotMessage("Please open an issue page to suggest priority.");
          return;
        }
        const res = await fetch("/api/ai/suggest-priority/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
          body: JSON.stringify({ issue_id: this.state.context.issueId })
        });
        const data = await res.json();
        this.removeTypingIndicator();
        this.appendBotMessage(`
          <div>
            <div style="font-weight:700;margin-bottom:6px;">✨ AI Priority Recommendation (${data.issue_key || 'Ticket'})</div>
            <div style="margin-bottom:8px;font-size:0.85rem;">
              Recommended Priority: <span class="badge-priority priority-${data.suggested_priority}">${data.suggested_priority}</span>
              <span style="color:var(--text-muted);font-size:0.8rem;margin-left:8px;">(Confidence: <strong>${data.confidence}</strong>)</span>
            </div>
            <p style="font-size:0.83rem;color:var(--text-secondary);line-height:1.5;">${data.reasoning || data.explanation || ''}</p>
          </div>
        `);
      }
      else if (actionName === "team_workload" || actionName === "allocate_work") {
        const res = await fetch("/api/ai/allocate-work/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
          body: JSON.stringify({ project_id: this.state.context.projectId })
        });
        const data = await res.json();
        this.removeTypingIndicator();
        if (data.allocations && data.allocations.length > 0) {
          const rows = data.allocations.map(a => `
            <div class="ai-action-item" style="flex-direction:column;align-items:flex-start;gap:2px;">
              <div style="display:flex;align-items:center;justify-content:space-between;width:100%;">
                <span><strong>${a.issue_key}</strong>: ${a.issue_title}</span>
                <span class="badge-points">${a.story_points} pts</span>
              </div>
              <div style="font-size:0.75rem;color:var(--text-secondary);">→ <strong>${a.assigned_to.name}</strong> (${a.assigned_to.role}): ${a.reasoning}</div>
            </div>
          `).join("");
          this.appendBotMessage(`
            <div>
              <div style="font-weight:700;margin-bottom:8px;">✨ Smart Team Workload Allocation</div>
              <div class="ai-action-list">${rows}</div>
            </div>
          `);
        } else {
          this.appendBotMessage("Team workload is currently well distributed across all active members.");
        }
      }
      else {
        this.removeTypingIndicator();
        this.appendBotMessage(`Sprintly AI is ready to assist with ${actionName.replace('_', ' ')}. Ask any question in the prompt below.`);
      }
    } catch (e) {
      this.removeTypingIndicator();
      this.appendBotMessage("Sprintly AI is temporarily unavailable. Please try again later.");
    }
  },

  async applySprintPlan(issueIds) {
    try {
      if (!Array.isArray(issueIds)) {
        issueIds = [issueIds];
      }
      const res = await fetch("/api/ai/apply-action/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
        body: JSON.stringify({
          action_type: "APPLY_SPRINT_PLAN",
          payload: {
            issue_ids: issueIds,
            project_id: this.state.context.projectId,
            sprint_id: this.state.context.sprintId
          }
        })
      });
      const data = await res.json();
      if (data.success) {
        SprintlyApp.showToast(data.message, "success");
        setTimeout(() => window.location.reload(), 1000);
      } else {
        SprintlyApp.showToast(data.error || "Failed to apply sprint plan.", "error");
      }
    } catch (e) {
      SprintlyApp.showToast("Failed to apply sprint plan.", "error");
    }
  },

  async applySubtasks(issueId, subtasks) {
    try {
      const res = await fetch("/api/ai/apply-action/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": SprintlyApp.getCsrfToken() },
        body: JSON.stringify({
          action_type: "CREATE_SUBTASKS",
          payload: { issue_id: issueId, subtasks: subtasks }
        })
      });
      const data = await res.json();
      if (data.success) {
        SprintlyApp.showToast(data.message, "success");
        setTimeout(() => window.location.reload(), 1000);
      } else {
        SprintlyApp.showToast(data.error || "Failed to create subtasks.", "error");
      }
    } catch (e) {
      SprintlyApp.showToast("Failed to create subtasks.", "error");
    }
  },

  escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
};

// ==========================================================================
// SPRINTLY USER PROFILE CONTROLLER
// ==========================================================================
const SprintlyProfile = {
  init() {
    const form = document.getElementById("profileForm");
    if (!form) return;
    this.updateBioCount();
    this.loadProfile();
  },

  async loadProfile() {
    try {
      const res = await fetch("/api/profile/", {
        headers: {
          "Accept": "application/json",
          "X-CSRFToken": SprintlyApp.getCsrfToken()
        }
      });
      if (res.ok) {
        const data = await res.json();
        this.populateFields(data);
      }
    } catch (e) {
      console.warn("Could not fetch live profile API; using server-rendered data.", e);
    }
  },

  populateFields(data) {
    if (!data) return;
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.value = val;
    };

    setVal("profileFirstName", data.first_name);
    setVal("profileLastName", data.last_name);
    setVal("profileUsername", data.username);
    setVal("profileEmail", data.email);
    setVal("profileJobTitle", data.job_title);
    setVal("profileLocation", data.location);
    setVal("profileBio", data.bio);
    setVal("profileRole", data.role);
    setVal("profileDepartment", data.department);
    setVal("profileJoinedDate", data.joined_date);

    this.updateBioCount();

    // Profile Picture
    const imgEl = document.getElementById("avatarPreviewImg");
    const initialsEl = document.getElementById("avatarInitialsFallback");
    if (data.initials && initialsEl) {
      initialsEl.textContent = data.initials;
    }
    if (data.profile_picture) {
      if (imgEl) {
        imgEl.src = data.profile_picture;
      }
    } else {
      if (imgEl) {
        imgEl.src = "";
        imgEl.style.display = "none";
      }
      if (initialsEl) initialsEl.style.display = "flex";
    }

    // Synchronize Top Navbar Avatar
    const navImg = document.getElementById("navbarAvatarImg");
    const navInitials = document.getElementById("navbarAvatarInitials");
    if (data.profile_picture) {
      if (navImg) {
        navImg.src = data.profile_picture;
        navImg.style.display = "block";
      }
      if (navInitials) navInitials.style.display = "none";
    } else {
      if (navImg) {
        navImg.src = "";
        navImg.style.display = "none";
      }
      if (navInitials) {
        if (data.initials) navInitials.textContent = data.initials;
        navInitials.style.display = "flex";
      }
    }
  },

  handleImageLoad(imgEl) {
    if (!imgEl) return;
    imgEl.style.display = "block";
    const initialsEl = document.getElementById("avatarInitialsFallback");
    if (initialsEl) initialsEl.style.display = "none";
  },

  handleImageError(imgEl) {
    if (!imgEl) return;
    imgEl.style.display = "none";
    const initialsEl = document.getElementById("avatarInitialsFallback");
    if (initialsEl) initialsEl.style.display = "flex";
  },

  handleImageSelect(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate size (<= 5MB)
    if (file.size > 5 * 1024 * 1024) {
      SprintlyApp.showToast("Image file size exceeds the 5MB limit.", "error");
      event.target.value = "";
      return;
    }

    // Validate extension & mime type
    const validExtensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"];
    const name = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => name.endsWith(ext));
    if (!isValid) {
      SprintlyApp.showToast("Unsupported file format. Please upload JPG, PNG, WEBP, or GIF.", "error");
      event.target.value = "";
      return;
    }

    const previewImg = document.getElementById("avatarPreviewImg");
    const initialsEl = document.getElementById("avatarInitialsFallback");
    const removeFlag = document.getElementById("removePictureFlag");

    if (removeFlag) removeFlag.value = "false";

    // Use FileReader for robust data: URL preview that never fails CSP or object URL lifecycle
    const reader = new FileReader();
    reader.onload = (e) => {
      if (previewImg) {
        previewImg.src = e.target.result;
        previewImg.style.display = "block";
      }
      if (initialsEl) initialsEl.style.display = "none";
    };
    reader.onerror = () => {
      try {
        if (previewImg) {
          previewImg.src = URL.createObjectURL(file);
          previewImg.style.display = "block";
        }
        if (initialsEl) initialsEl.style.display = "none";
      } catch (err) {
        console.error("Preview creation error:", err);
      }
    };
    reader.readAsDataURL(file);
  },

  removeProfilePicture() {
    const input = document.getElementById("profilePictureInput");
    if (input) input.value = "";

    const previewImg = document.getElementById("avatarPreviewImg");
    const initialsEl = document.getElementById("avatarInitialsFallback");
    const removeFlag = document.getElementById("removePictureFlag");

    if (previewImg) {
      previewImg.src = "";
      previewImg.style.display = "none";
    }
    if (initialsEl) initialsEl.style.display = "flex";
    if (removeFlag) removeFlag.value = "true";

    SprintlyApp.showToast("Profile picture marked for removal. Click 'Save Changes' to apply.", "info");
  },

  updateBioCount() {
    const bio = document.getElementById("profileBio");
    const counter = document.getElementById("bioCharCounter");
    if (bio && counter) {
      counter.textContent = `${bio.value.length} / 1000`;
      if (bio.value.length >= 950) {
        counter.style.color = "#ef4444";
      } else {
        counter.style.color = "var(--text-muted)";
      }
    }
  },

  async saveProfile(event) {
    if (event) event.preventDefault();

    const saveBtn = document.getElementById("saveProfileBtn");
    const saveBtnText = document.getElementById("saveBtnText");
    const successBanner = document.getElementById("profileSuccessBanner");
    const errorBanner = document.getElementById("profileErrorBanner");
    const errorText = document.getElementById("profileErrorText");

    if (successBanner) successBanner.style.display = "none";
    if (errorBanner) errorBanner.style.display = "none";

    // Disable button to prevent duplicate submissions
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.style.opacity = "0.7";
      saveBtn.style.cursor = "not-allowed";
    }
    if (saveBtnText) saveBtnText.textContent = "Saving...";

    const form = document.getElementById("profileForm");
    const formData = new FormData(form);

    try {
      const res = await fetch("/api/profile/", {
        method: "PUT",
        headers: {
          "X-CSRFToken": SprintlyApp.getCsrfToken()
        },
        body: formData
      });

      const data = await res.json();

      if (res.ok) {
        if (successBanner) successBanner.style.display = "flex";
        SprintlyApp.showToast(data.message || "Profile updated successfully.", "success");
        this.populateFields(data);
      } else {
        const errorMsg = data.error || (data.errors ? Object.values(data.errors)[0] : "Failed to update profile.");
        if (errorBanner) {
          if (errorText) errorText.textContent = errorMsg;
          errorBanner.style.display = "flex";
        }
        SprintlyApp.showToast(errorMsg, "error");
      }
    } catch (e) {
      console.error("Save profile error:", e);
      if (errorBanner) {
        if (errorText) errorText.textContent = "Network error. Please try again.";
        errorBanner.style.display = "flex";
      }
      SprintlyApp.showToast("Network error saving profile.", "error");
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.style.opacity = "1";
        saveBtn.style.cursor = "pointer";
      }
      if (saveBtnText) saveBtnText.textContent = "Save Changes";
      if (window.lucide) lucide.createIcons();
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  SprintlyApp.init();
  SprintlyAI.init();
  SprintlyProfile.init();
});

