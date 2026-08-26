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

    if (window.lucide) {
      window.lucide.createIcons();
    }
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
      const input = document.getElementById("commandPaletteInput");
      if (input) {
        input.value = "";
        input.focus();
      }
    }
  },

  async handleGlobalSearch(query) {
    const resultsContainer = document.getElementById("commandSearchResults");
    if (!resultsContainer) return;

    if (!query.trim()) {
      resultsContainer.innerHTML = `
        <div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;margin:4px 0;">Quick Navigation</div>
        <a href="/dashboard/" class="nav-item"><i data-lucide="layout-dashboard" style="width:16px;height:16px;"></i> Go to Dashboard</a>
        <a href="/my-work/" class="nav-item"><i data-lucide="check-square" style="width:16px;height:16px;"></i> View My Work</a>
        <a href="/projects/" class="nav-item"><i data-lucide="folder" style="width:16px;height:16px;"></i> Browse Projects</a>
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
        html += `<div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;margin:6px 0 2px;">Issues</div>`;
        data.issues.forEach(i => {
          html += `
            <a href="/issues/${i.id}/" class="nav-item" style="display:flex;align-items:center;justify-content:space-between;">
              <span><strong>${i.key}</strong> - ${i.title}</span>
              <span class="badge-priority priority-${i.priority}">${i.priority}</span>
            </a>
          `;
        });
      }

      if (data.projects && data.projects.length > 0) {
        html += `<div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;margin:6px 0 2px;">Projects</div>`;
        data.projects.forEach(p => {
          html += `
            <a href="/projects/${p.id}/" class="nav-item">
              <i data-lucide="folder" style="width:14px;height:14px;"></i> ${p.key} - ${p.name}
            </a>
          `;
        });
      }

      if (!html) {
        html = `<div style="padding:16px;color:var(--text-muted);font-size:0.85rem;text-align:center;">No matching results found.</div>`;
      }

      resultsContainer.innerHTML = html;
      if (window.lucide) window.lucide.createIcons();
    } catch (e) {
      console.error("Search error", e);
    }
  },

  // ==========================================
  // KANBAN BOARD & DRAG-AND-DROP
  // ==========================================
  async setupKanbanBoard() {
    const board = document.querySelector(".kanban-board");
    if (!board) return;

    // Fetch live board issues from Django API
    const projectSelector = document.getElementById("projectSelector");
    const projectId = projectSelector ? projectSelector.value : 1;

    try {
      const res = await fetch(`/api/issues/?project_id=${projectId}`);
      if (res.ok) {
        this.state.issues = await res.json();
        this.renderKanbanColumns();
      }
    } catch (e) {
      console.error("Failed to load kanban issues", e);
    }

    // Bind drop listeners to columns
    const columns = document.querySelectorAll(".kanban-column");
    columns.forEach(col => {
      col.addEventListener("dragover", (e) => {
        e.preventDefault();
        col.classList.add("drag-over");
      });

      col.addEventListener("dragleave", () => {
        col.classList.remove("drag-over");
      });

      col.addEventListener("drop", async (e) => {
        e.preventDefault();
        col.classList.remove("drag-over");
        const issueId = e.dataTransfer.getData("text/plain");
        const newStatus = col.getAttribute("data-status");

        if (issueId && newStatus) {
          await this.moveIssueStatus(issueId, newStatus);
        }
      });
    });
  },

  renderKanbanColumns() {
    const statuses = ["BACKLOG", "TODO", "IN_PROGRESS", "IN_REVIEW", "BLOCKED", "DONE"];
    
    // Reset columns
    statuses.forEach(status => {
      const colEl = document.getElementById(`column-cards-${status.toLowerCase()}`);
      const countEl = document.getElementById(`count-${status.toLowerCase()}`);
      if (colEl) colEl.innerHTML = "";
      if (countEl) countEl.innerText = "0";
    });

    // Populate filtered issues
    const filterType = document.getElementById("filterType")?.value || "";
    const filterPriority = document.getElementById("filterPriority")?.value || "";
    const searchVal = document.getElementById("searchIssuesInput")?.value.toLowerCase() || "";

    const counts = { BACKLOG: 0, TODO: 0, IN_PROGRESS: 0, IN_REVIEW: 0, BLOCKED: 0, DONE: 0 };

    this.state.issues.forEach(issue => {
      if (filterType && issue.issue_type !== filterType) return;
      if (filterPriority && issue.priority !== filterPriority) return;
      if (searchVal && !issue.title.toLowerCase().includes(searchVal) && !issue.key.toLowerCase().includes(searchVal)) return;

      const colEl = document.getElementById(`column-cards-${issue.status.toLowerCase()}`);
      if (colEl) {
        counts[issue.status] = (counts[issue.status] || 0) + 1;
        colEl.appendChild(this.createKanbanCardElement(issue));
      }
    });

    statuses.forEach(status => {
      const countEl = document.getElementById(`count-${status.toLowerCase()}`);
      if (countEl) countEl.innerText = counts[status] || 0;
    });

    if (window.lucide) window.lucide.createIcons();
  },

  createKanbanCardElement(issue) {
    const card = document.createElement("div");
    card.className = "kanban-card";
    card.setAttribute("draggable", "true");
    card.setAttribute("data-id", issue.id);

    card.addEventListener("dragstart", (e) => {
      card.classList.add("dragging");
      e.dataTransfer.setData("text/plain", issue.id);
    });

    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
    });

    card.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
        <span class="type-badge-pill type-${issue.issue_type}">${issue.issue_type}</span>
        <span class="badge-priority priority-${issue.priority}">${issue.priority}</span>
      </div>
      <a href="/issues/${issue.id}/" style="font-weight:700;font-size:0.9rem;color:var(--text-primary);text-decoration:none;display:block;margin-bottom:8px;line-height:1.4;">
        <span style="color:var(--text-muted);font-size:0.8rem;margin-right:4px;">${issue.key}</span>
        ${issue.title}
      </a>
      <div style="display:flex;align-items:center;justify-content:space-between;border-top:1px solid var(--border-subtle);padding-top:8px;font-size:0.75rem;">
        <span class="badge-points">${issue.story_points} pts</span>
        ${issue.assignee ? `
          <div class="avatar-circle" style="background:${issue.assignee.avatar_color};width:24px;height:24px;font-size:0.65rem;" title="${issue.assignee.name}">
            ${issue.assignee.initials}
          </div>
        ` : `<span style="color:var(--text-muted);">Unassigned</span>`}
      </div>
    `;
    return card;
  },

  filterBoard() {
    this.renderKanbanColumns();
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
        const item = this.state.issues.find(i => i.id == issueId);
        if (item) item.status = newStatus;
        this.renderKanbanColumns();
        this.showToast(`Updated ticket status to ${newStatus.replace("_", " ")}`, "success");
      }
    } catch (e) {
      console.error("Move status failed", e);
    }
  },

  // ==========================================
  // MODALS & ACTIONS
  // ==========================================
  openCreateIssueModal() {
    const modal = document.getElementById("createIssueModal");
    if (modal) modal.classList.add("active");
  },

  openCreateProjectModal() {
    const modal = document.getElementById("createProjectModal");
    if (modal) modal.classList.add("active");
  },

  closeAllModals() {
    document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
  },

  async submitCreateIssue(e) {
    e.preventDefault();
    const title = document.getElementById("createTitle")?.value;
    const desc = document.getElementById("createDesc")?.value;
    const project = document.getElementById("createProject")?.value;
    const issueType = document.getElementById("createType")?.value;
    const priority = document.getElementById("createPriority")?.value;
    const points = document.getElementById("createPoints")?.value;
    const dueDate = document.getElementById("createDueDate")?.value;
    const labels = document.getElementById("createLabels")?.value;

    try {
      const res = await fetch("/api/issues/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken(),
        },
        body: JSON.stringify({
          title,
          description: desc,
          project_id: project,
          issue_type: issueType,
          priority,
          story_points: points,
          due_date: dueDate,
          labels,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        this.closeAllModals();
        this.showToast(`Issue ${data.issue.key} created successfully!`, "success");
        setTimeout(() => {
          window.location.reload();
        }, 400);
      } else {
        const errData = await res.json().catch(() => ({}));
        this.showToast(errData.error || "Failed to create issue. Please check required fields.", "error");
      }
    } catch (e) {
      console.error("Create issue failed", e);
      this.showToast("Network error creating issue. Please try again.", "error");
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
  // CHART.JS VISUALIZATIONS (Dynamic Only)
  // ==========================================
  initChartsIfPresent() {
    // Dynamic initialization handled by template scripts with backend context
  },

  // ==========================================
  // TOAST NOTIFICATIONS & HELPERS
  // ==========================================
  showToast(message, type = "info") {
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerText = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3000);
  },

  getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
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

  bindEvents() {
    const input = document.getElementById("aiChatInput");
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        }
      });
    }
  },

  openDrawer() {
    const drawer = document.getElementById("sprintlyAiDrawer");
    const overlay = document.getElementById("aiDrawerOverlay");
    if (drawer) drawer.classList.add("open");
    if (overlay) overlay.classList.add("active");
    this.state.isOpen = true;

    const input = document.getElementById("aiChatInput");
    if (input) setTimeout(() => input.focus(), 150);
  },

  closeDrawer() {
    const drawer = document.getElementById("sprintlyAiDrawer");
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
    const thread = document.getElementById("aiChatThread");
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
    const input = document.getElementById("aiChatInput");
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
      this.appendBotMessage(data.answer || "Sprintly AI is currently analyzing your request.");
    } catch (e) {
      this.removeTypingIndicator();
      this.appendBotMessage("Sprintly AI is temporarily unavailable. Please try again later.");
    }
  },

  appendUserMessage(text) {
    const thread = document.getElementById("aiChatThread");
    if (!thread) return;
    const row = document.createElement("div");
    row.className = "ai-msg-row user";
    row.innerHTML = `<div class="ai-msg-bubble user">${this.escapeHtml(text)}</div>`;
    thread.appendChild(row);
    thread.scrollTop = thread.scrollHeight;
  },

  appendBotMessage(content) {
    const thread = document.getElementById("aiChatThread");
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
    const thread = document.getElementById("aiChatThread");
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
          body: JSON.stringify({ sprint_id: this.state.context.sprintId })
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

document.addEventListener("DOMContentLoaded", () => {
  SprintlyApp.init();
  SprintlyAI.init();
});

