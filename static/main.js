document.addEventListener('DOMContentLoaded', () => {
    // --- Backend API Base URL ---
    // When served from the same server (HF Space / local), use '' (same origin).
    // When deployed to Vercel or another static host, point to your HF Space.
    const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? ''  // local dev: same origin
        : 'https://psg-hf72-cognition-env.hf.space';  // production: HF Space backend

    // --- Elements ---
    const btnReset = document.getElementById('btn-reset');
    const btnSubmitEpisode = document.getElementById('btn-submit-episode');
    const btnApplyLabels = document.getElementById('btn-apply-labels');
    
    const valReward = document.getElementById('reward-val');
    const valStatus = document.getElementById('status-val');
    const queueCount = document.getElementById('queue-count');
    const globalTaskText = document.getElementById('global-task-text');
    
    const ticketListEl = document.getElementById('ticket-list');
    const unselectedStateEl = document.getElementById('unselected-state');
    const triageFormEl = document.getElementById('triage-form');
    
    // Form elements
    const formTicketId = document.getElementById('form-ticket-id');
    const formTicketBody = document.getElementById('form-ticket-body');
    const selCategory = document.getElementById('sel-category');
    const selPriority = document.getElementById('sel-priority');
    const selTeam = document.getElementById('sel-team');
    const inpTags = document.getElementById('inp-tags');
    const actionFeedback = document.getElementById('action-feedback');
    
    // Modal elements
    const modal = document.getElementById('results-modal');
    const modalGraderScore = document.getElementById('modal-grader-score');
    const modalTotalReward = document.getElementById('modal-total-reward');
    const modalFeedbackList = document.getElementById('modal-feedback-list');
    const btnCloseModal = document.getElementById('btn-close-modal');

    // --- State ---
    let currentTickets = [];
    let currentTask = null;
    let activeTicketId = null;
    let accumulatedReward = 0.0;
    
    let isDone = false;
    let enumsLoaded = false;
    
    // --- API Calls ---
    
    async function resetEnvironment() {
        setLoading(true);
        try {
            const res = await fetch(API_BASE + '/reset', { method: 'POST' });
            const data = await res.json();
            
            accumulatedReward = data.reward;
            processObservation(data);
            showFeedback("Session Reset. Selected new task.", 'success');
        } catch (err) {
            console.error(err);
            showFeedback("Failed to connect to backend", 'error');
        } finally {
            setLoading(false);
        }
    }
    
    async function takeStep(actionPayload) {
        setLoading(true);
        try {
            const res = await fetch(API_BASE + '/step', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(actionPayload)
            });
            const data = await res.json();
            
            accumulatedReward += data.reward;
            processObservation(data);
            
            if (actionPayload.command === 'set_labels') {
                showFeedback(data.observation.feedback || "Labels applied.", 'success');
            }
            if (actionPayload.command === 'submit') {
                showModal(data);
            }
        } catch (err) {
            console.error(err);
            showFeedback("Action failed", 'error');
        } finally {
            setLoading(false);
        }
    }

    
    // --- UI Logic ---
    
    function processObservation(payload) {
        const obs = payload.observation;
        isDone = payload.done;
        
        // Update stats
        valReward.textContent = accumulatedReward.toFixed(3);
        if (isDone) {
            valStatus.textContent = 'Done';
            valStatus.className = 'status-done';
            btnSubmitEpisode.disabled = true;
            btnApplyLabels.disabled = true;
            document.getElementById('active-ticket-area').style.opacity = '0.5';
        } else {
            valStatus.textContent = 'Running';
            valStatus.className = 'status-running';
            btnSubmitEpisode.disabled = false;
            btnApplyLabels.disabled = false;
            document.getElementById('active-ticket-area').style.opacity = '1';
        }
        
        // Update global task instructions
        if (obs.instruction) {
            let taskText = `<strong>[${obs.task_name || obs.task_key}]</strong> ${obs.instruction}`;
            if (obs.constraints_summary) {
                taskText += `<br><em>⚠️ Constraints: ${obs.constraints_summary}</em>`;
            }
            globalTaskText.innerHTML = taskText;
        }
        
        // Load enums only once or if they change
        if (!enumsLoaded && obs.allowed_categories && obs.allowed_categories.length > 0) {
            populateSelect(selCategory, obs.allowed_categories, '-- Select Category --');
            populateSelect(selPriority, obs.allowed_priorities, '-- Select Priority --');
            populateSelect(selTeam, obs.allowed_teams, '-- Select Team --');
            enumsLoaded = true;
        }
        
        // Render Ticket list
        currentTickets = obs.tickets || [];
        queueCount.textContent = `${currentTickets.length} Tickets`;
        renderTicketList();
        
        // Update active selection visibility
        if (activeTicketId && currentTickets.find(t => t.id === activeTicketId)) {
            // Keep it active
            selectTicket(activeTicketId);
        } else {
            unselectAll();
        }
    }
    
    function renderTicketList() {
        ticketListEl.innerHTML = '';
        if (currentTickets.length === 0) {
            ticketListEl.innerHTML = '<div class="empty-state">No tickets in queue.</div>';
            return;
        }
        
        currentTickets.forEach(ticket => {
            const el = document.createElement('div');
            el.className = `ticket-item ${ticket.id === activeTicketId ? 'active' : ''}`;
            el.onclick = () => selectTicket(ticket.id);
            
            el.innerHTML = `
                <div class="ticket-item-header">
                    <span class="ticket-id">${ticket.id}</span>
                </div>
                <div class="ticket-snippet">${ticket.title}</div>
            `;
            ticketListEl.appendChild(el);
        });
    }
    
    function unselectAll() {
        activeTicketId = null;
        unselectedStateEl.style.display = 'flex';
        triageFormEl.style.display = 'none';
        triageFormEl.parentElement.classList.add('unselected');
        
        document.querySelectorAll('.ticket-item').forEach(el => el.classList.remove('active'));
    }
    
    function selectTicket(id) {
        const ticket = currentTickets.find(t => t.id === id);
        if (!ticket) return;
        
        activeTicketId = id;
        
        // Render form context
        formTicketId.textContent = ticket.id;
        formTicketBody.innerHTML = `<strong>${ticket.title}</strong><br><br>${ticket.body}`;
        
        // Clear/reset form fields
        selCategory.value = "";
        selPriority.value = "";
        selTeam.value = "";
        inpTags.value = "";
        actionFeedback.textContent = "";
        
        // Toggle view
        unselectedStateEl.style.display = 'none';
        triageFormEl.style.display = 'flex';
        triageFormEl.parentElement.classList.remove('unselected');
        
        // Highlight active left panel item
        document.querySelectorAll('.ticket-item').forEach(el => {
            el.classList.toggle('active', el.querySelector('.ticket-id').textContent === id);
        });
    }
    
    function showModal(payload) {
        // Find grader score in metadata
        const metadata = payload.info || {};
        const graderScore = metadata.grader_score !== undefined ? metadata.grader_score : "0.00";
        
        modalGraderScore.textContent = Number(graderScore).toFixed(4);
        modalTotalReward.textContent = accumulatedReward.toFixed(3);
        
        const feedbackStr = payload.observation.feedback || "Done.";
        modalFeedbackList.textContent = feedbackStr;
        
        modal.classList.remove('hidden');
    }
    
    // --- Helpers ---
    
    function populateSelect(selectEl, optionsArray, defaultOption) {
        selectEl.innerHTML = `<option value="">${defaultOption}</option>`;
        optionsArray.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt;
            el.textContent = opt;
            selectEl.appendChild(el);
        });
    }
    
    function showFeedback(msg, type) {
        actionFeedback.textContent = msg;
        actionFeedback.className = `feedback-msg ${type}`;
        setTimeout(() => { if (actionFeedback.textContent === msg) actionFeedback.textContent = ''; }, 4000);
    }
    
    function setLoading(isLoading) {
        if (isLoading) {
            document.body.style.cursor = 'wait';
        } else {
            document.body.style.cursor = 'default';
        }
    }
    
    // --- Event Listeners ---
    
    btnReset.addEventListener('click', resetEnvironment);
    
    btnApplyLabels.addEventListener('click', () => {
        if (!activeTicketId) return;
        
        const tagsRaw = inpTags.value.split(',').map(s => s.trim()).filter(s => s.length > 0);
        
        takeStep({
            command: "set_labels",
            ticket_id: activeTicketId,
            category: selCategory.value || null,
            priority: selPriority.value || null,
            assign_team: selTeam.value || null,
            tags: tagsRaw.length > 0 ? tagsRaw : null
        });
    });
    
    btnSubmitEpisode.addEventListener('click', () => {
        if (!confirm("Are you sure you want to finish the episode and submit for grading?")) return;
        takeStep({ command: "submit" });
    });
    
    btnCloseModal.addEventListener('click', () => {
        modal.classList.add('hidden');
        resetEnvironment(); // auto-reset after close
    });
});
