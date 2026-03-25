document.addEventListener('DOMContentLoaded', () => {

    // ── Elements ──────────────────────────────────────────
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadFeedback = document.getElementById('upload-status');
    const fileInfo = document.getElementById('file-info');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileList = document.getElementById('file-list'); // Added fileList

    const btnGenerate = document.getElementById('btn-generate');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');

    const statTotal = document.getElementById('stat-total');
    const statPending = document.getElementById('stat-pending');
    const statSent = document.getElementById('stat-sent');
    const statFailed = document.getElementById('stat-failed');

    const statusBadge = document.getElementById('bot-status-badge');
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-indicator');
    const statusSidebar = document.getElementById('status-text-sidebar');
    const pulseDot = document.getElementById('pulse-dot');
    const currentUser = document.getElementById('current-user');

    const terminal = document.getElementById('terminal-output');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    const templateArea = document.getElementById('message-template');
    const charCount = document.getElementById('char-count');
    const cardTemplate = templateArea.closest('.card');

    // AI Settings
    const aiToggle = document.getElementById('ai-toggle');
    const aiToggleLabel = document.getElementById('ai-toggle-label');
    const aiFields = document.getElementById('ai-fields');
    const aiApiKey = document.getElementById('ai-api-key');
    const aiModel = document.getElementById('ai-model');
    const aiSystemPrompt = document.getElementById('ai-system-prompt');
    const btnEye = document.getElementById('btn-eye');
    const eyeIcon = document.getElementById('eye-icon');
    const btnTestModel = document.getElementById('btn-test-model');
    const testResultWrap = document.getElementById('test-result-wrap');
    const testResultContent = document.getElementById('test-result-content');
    const btnCloseTest = document.getElementById('btn-close-test');

    const navDash = document.getElementById('nav-dashboard');
    const navApprovals = document.getElementById('nav-approvals');
    const navLogs = document.getElementById('nav-logs');
    const viewDash = document.getElementById('view-dashboard');
    const viewApprovals = document.getElementById('view-approvals');
    const viewLogs = document.getElementById('view-logs');

    // Approvals specific elements
    const approvalsContainer = document.getElementById('approvals-container');

    let currentLogLength = 0;
    let isUploadReady = false;
    let isStopping = false;
    let useAI = false;

    // ── Char counter ───────────────────────────────────────
    function updateCharCount() {
        charCount.textContent = templateArea.value.length;
    }
    templateArea.addEventListener('input', () => {
        updateCharCount();
        localStorage.setItem('messageTemplate', templateArea.value);
    });
    if (localStorage.getItem('messageTemplate')) {
        templateArea.value = localStorage.getItem('messageTemplate');
    }
    updateCharCount();

    // ── AI Toggle ──────────────────────────────────────────
    function applyAIToggleState() {
        useAI = aiToggle.checked;
        aiToggleLabel.textContent = useAI ? 'AI ON' : 'AI OFF';
        aiToggleLabel.style.color = useAI ? 'var(--accent-purple, #a78bfa)' : '';
        // When AI is ON, collapse the manual template card visually
        if (cardTemplate) {
            cardTemplate.style.opacity = useAI ? '0.45' : '1';
            cardTemplate.style.pointerEvents = useAI ? 'none' : '';
        }
    }

    // Load from local storage
    if (localStorage.getItem('aiApiKey')) aiApiKey.value = localStorage.getItem('aiApiKey');
    aiModel.value = localStorage.getItem('aiModel') || 'openai/gpt-4o-mini';
    if (localStorage.getItem('useAI') === 'true') {
        aiToggle.checked = true;
    }
    applyAIToggleState();

    aiToggle.addEventListener('change', () => {
        applyAIToggleState();
        localStorage.setItem('useAI', useAI);
    });

    if (localStorage.getItem('aiSystemPrompt')) aiSystemPrompt.value = localStorage.getItem('aiSystemPrompt');

    const btnSavePrompt = document.getElementById('btn-save-prompt');
    const promptSavedMsg = document.getElementById('prompt-saved-msg');

    aiApiKey.addEventListener('input', () => localStorage.setItem('aiApiKey', aiApiKey.value.trim()));
    aiModel.addEventListener('input', () => localStorage.setItem('aiModel', aiModel.value.trim()));
    
    // Explicit Save button for System Prompt
    btnSavePrompt.addEventListener('click', () => {
        localStorage.setItem('aiSystemPrompt', aiSystemPrompt.value);
        promptSavedMsg.classList.remove('hidden');
        btnSavePrompt.innerHTML = '<i class="fa-solid fa-check"></i> Saved';
        btnSavePrompt.style.borderColor = 'var(--accent-green, #10b981)';
        btnSavePrompt.style.color = 'var(--accent-green, #10b981)';
        
        setTimeout(() => {
            promptSavedMsg.classList.add('hidden');
            btnSavePrompt.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Prompt';
            btnSavePrompt.style.borderColor = '';
            btnSavePrompt.style.color = '';
        }, 2000);
    });

    // Test Model Logic
    btnTestModel.addEventListener('click', () => {
        const key = aiApiKey ? aiApiKey.value.trim() : '';
        const model = aiModel ? aiModel.value.trim() : 'openai/gpt-4o-mini';
        const systemPrompt = aiSystemPrompt ? aiSystemPrompt.value.trim() : '';
        
        if (!key) {
            alert('Please enter an OpenRouter API Key to test.');
            return;
        }

        btnTestModel.disabled = true;
        btnTestModel.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Testing...';
        testResultWrap.classList.add('hidden');

        fetch('/api/test_model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: key,
                model: model,
                system_prompt: systemPrompt
            })
        })
        .then(r => r.json())
        .then(data => {
            btnTestModel.disabled = false;
            btnTestModel.innerHTML = '<i class="fa-solid fa-vial"></i> Test Model';
            testResultWrap.classList.remove('hidden');
            
            if (data.success) {
                testResultWrap.style.background = 'rgba(16, 185, 129, 0.1)';
                testResultWrap.style.border = '1px solid var(--accent-green, #10b981)';
                testResultContent.innerHTML = `<span style="color:var(--accent-green, #10b981); font-weight:600;">SUCCESS! Model is working.</span>\n\nGenerated Test Output:\n"${data.message}"`;
            } else {
                testResultWrap.style.background = 'rgba(239, 68, 68, 0.1)';
                testResultWrap.style.border = '1px solid #ef4444';
                
                let errorHtml = `<span style="color:#ef4444; font-weight:600;">ERROR: ${data.error}</span>`;
                if (data.error.includes('Insufficient credits')) {
                    errorHtml += `\n\n<a href="https://openrouter.ai/settings/credits" target="_blank" style="color:#60a5fa; text-decoration:underline;">Click here to top up your credits</a>`;
                } else if (data.error.includes('privacy')) {
                    errorHtml += `\n\n<a href="https://openrouter.ai/settings/privacy" target="_blank" style="color:#60a5fa; text-decoration:underline;">Click here to fix your privacy settings</a>`;
                }
                testResultContent.innerHTML = errorHtml;
            }
        })
        .catch(err => {
            btnTestModel.disabled = false;
            btnTestModel.innerHTML = '<i class="fa-solid fa-vial"></i> Test Model';
            alert('Communication error with server: ' + err.message);
        });
    });

    btnCloseTest.addEventListener('click', () => {
        testResultWrap.classList.add('hidden');
    });

    // Add Reset to Default button logic
    const btnResetPrompt = document.createElement('button');
    btnResetPrompt.className = 'btn-save-tiny';
    btnResetPrompt.style.marginLeft = '10px';
    btnResetPrompt.innerHTML = '<i class="fa-solid fa-undo"></i> Reset to Default';
    btnSavePrompt.parentNode.appendChild(btnResetPrompt);

    const DEFAULT_PROMPT = `## WHO YOU ARE
Your name is Sneh Desai. You work in sales and business development at a software development company in India. You recently built ProposalBiz with your team because none of the existing platforms had AI. ProposalBiz has everything PandaDoc has plus AI that builds the entire proposal from a single prompt.

## GREETING RULES
- DO NOT start with "Hey", "Hi", "Hello", or any other informal greeting.
- DO NOT start with "Hey @username" or "Hi @username".
- Dive straight into the personalized reaction, context, or validation.

## HOW SNEH TYPES
- Use standard English capitalization (sentences, names, brands like PandaDoc, ProposalBiz, etc.)
- AI -> Always capital
- "Honestly", "Ngl", "Tbh" come naturally but don't overdo them
- Never sounds salesy or excited
- Use double line breaks (paragraphs) to separate ideas for better readability
- One emoji max, only if it genuinely fits
- 4-6 lines total, structured into 2-3 short paragraphs

## WHAT TO NEVER DO
- Never list multiple features at once
- Never use "game changer", "revolutionary", "powerful"
- Never be pushy or end with a hard CTA
- Never mention ProposalBiz more than once
- Never write more than 6 lines
- Never ignore what they actually said

## OUTPUT RULES
- Return the reply text only
- Use proper spacing and paragraph breaks
- No labels, no explanations, no quotation marks
- No hashtags
- 4-6 lines maximum`;

    btnResetPrompt.addEventListener('click', () => {
        if (confirm('Reset system prompt to default? This will overwrite your current instructions.')) {
            aiSystemPrompt.value = DEFAULT_PROMPT;
            localStorage.setItem('aiSystemPrompt', DEFAULT_PROMPT);
            btnResetPrompt.innerHTML = '<i class="fa-solid fa-check"></i> Reset Done';
            setTimeout(() => {
                btnResetPrompt.innerHTML = '<i class="fa-solid fa-undo"></i> Reset to Default';
            }, 2000);
        }
    });

    aiSystemPrompt.addEventListener('input', () => {
        // Just show that it's changed but not saved if you want, 
        // but the user wants an explicit SAVE.
    });

    // ── Eye button (show/hide API key) ────────────────────
    btnEye.addEventListener('click', () => {
        const show = aiApiKey.type === 'password';
        aiApiKey.type = show ? 'text' : 'password';
        eyeIcon.className = show ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
    });

    // ── Sidebar Navigation ──────────────────────────────────
    navDash.addEventListener('click', (e) => {
        e.preventDefault();
        navDash.classList.add('active');
        navApprovals.classList.remove('active');
        navLogs.classList.remove('active');
        viewDash.classList.add('active');
        viewApprovals.classList.remove('active');
        viewLogs.classList.remove('active');
    });

    navApprovals.addEventListener('click', (e) => {
        e.preventDefault();
        navApprovals.classList.add('active');
        navDash.classList.remove('active');
        navLogs.classList.remove('active');
        viewApprovals.classList.add('active');
        viewDash.classList.remove('active');
        viewLogs.classList.remove('active');
        pollApprovals(); // Fetch immediately when opening tab
    });

    navLogs.addEventListener('click', (e) => {
        e.preventDefault();
        navLogs.classList.add('active');
        navDash.classList.remove('active');
        navApprovals.classList.remove('active');
        viewLogs.classList.add('active');
        viewDash.classList.remove('active');
        viewApprovals.classList.remove('active');
    });

    // ── File Upload ────────────────────────────────────────
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFileUpload(e.target.files);
    });

    function handleFileUpload(files) {
        const formData = new FormData();
        let validFiles = 0;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (file.name.match(/\.(csv|xlsx|xls)$/i)) {
                formData.append('file', file);
                validFiles++;
            }
        }

        if (validFiles === 0) {
            showUploadFeedback('Please upload valid .csv or .xlsx files', 'error');
            return;
        }

        showUploadFeedback('Uploading ' + validFiles + ' file(s)...', '');

        fetch('/upload', { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showUploadFeedback(data.message, 'success');
                    updateFileListUI(data.files || []);
                    isUploadReady = true;
                    btnStart.disabled = false;
                    btnGenerate.disabled = false;
                    if (data.stats) updateStatsUI(data.stats);
                } else {
                    showUploadFeedback(data.error || 'Upload failed', 'error');
                }
            })
            .catch(() => showUploadFeedback('Network error during upload', 'error'));
    }

    function updateFileListUI(files) {
        fileList.innerHTML = '';
        if (!files || files.length === 0) {
            isUploadReady = false;
            btnStart.disabled = true;
            btnGenerate.disabled = true;
            return;
        }

        files.forEach(filename => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <div class="file-item-info">
                    <i class="fa-solid fa-file-csv"></i>
                    <span class="file-item-name" title="${filename}">${filename}</span>
                </div>
                <button class="btn-remove-file" title="Remove this file">
                    <i class="fa-solid fa-trash"></i>
                </button>
            `;
            const btnRemove = item.querySelector('.btn-remove-file');
            btnRemove.addEventListener('click', () => removeFile(filename));
            fileList.appendChild(item);
        });
    }

    function removeFile(filename) {
        if (!confirm(`Are you sure you want to remove ${filename}?`)) return;

        fetch('/api/remove_file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateFileListUI(data.files || []);
                if (data.stats) updateStatsUI(data.stats);
                showUploadFeedback('File removed.', 'success');
            } else {
                alert(data.error || 'Failed to remove file');
            }
        })
        .catch(err => console.error('Error removing file:', err));
    }

    function showUploadFeedback(msg, type) {
        uploadFeedback.textContent = msg;
        uploadFeedback.className = `upload-feedback ${type}`;
        uploadFeedback.classList.remove('hidden');
    }

    // ── Start / Stop ───────────────────────────────────────
    btnGenerate.addEventListener('click', () => {
        const tmpl = templateArea.value.trim();
        const key = aiApiKey ? aiApiKey.value.trim() : '';
        const model = aiModel ? aiModel.value.trim() : 'openai/gpt-4o-mini';
        const systemPrompt = aiSystemPrompt ? aiSystemPrompt.value.trim() : '';

        if (!useAI) { alert('You must enable AI to generate drafts.'); return; }
        if (!key) {
            if (!confirm('AI is ON but no API key entered. It will fail unless using the fallback. Continue?')) return;
        }

        btnGenerate.disabled = true;
        btnStart.disabled = true;

        fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message_template: tmpl,
                use_ai: useAI,
                openrouter_api_key: key,
                openrouter_model: model,
                ai_system_prompt: systemPrompt
            })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    pollStatus();
                } else {
                    btnGenerate.disabled = false;
                    btnStart.disabled = false;
                    alert(data.error);
                }
            })
            .catch(() => {
                btnGenerate.disabled = false;
                btnStart.disabled = false;
                alert('Network error while requesting generation.');
            });
    });

    btnStart.addEventListener('click', () => {
        const tmpl = templateArea.value.trim();
        const key = aiApiKey ? aiApiKey.value.trim() : '';
        const model = aiModel ? aiModel.value.trim() : 'openai/gpt-4o-mini';
        const systemPrompt = aiSystemPrompt ? aiSystemPrompt.value.trim() : '';

        if (!useAI && !tmpl) { alert('Message template cannot be empty.'); return; }
        if (useAI && !key) {
            if (!confirm('AI is ON but no API key entered. The bot will fall back to the manual template. Continue?')) return;
        }

        btnGenerate.disabled = true;
        btnStart.disabled = true;

        fetch('/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message_template: tmpl,
                use_ai: useAI,
                openrouter_api_key: key,
                openrouter_model: model,
                ai_system_prompt: systemPrompt
            })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    pollStatus();
                } else {
                    btnGenerate.disabled = false;
                    btnStart.disabled = false;
                    alert(data.error);
                }
            })
            .catch(() => {
                btnGenerate.disabled = false;
                btnStart.disabled = false;
                alert('Network error while starting automation.');
            });
    });

    btnStop.addEventListener('click', () => {
        if (isStopping) return; // prevent double-clicks
        fetch('/stop', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    isStopping = true;
                    btnStop.disabled = true;
                    btnStart.disabled = true;
                    btnGenerate.disabled = true;
                    btnStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Stopping...</span>';
                } else {
                    alert(data.error || 'Could not stop automation.');
                }
            })
            .catch(() => alert('Network error while stopping.'));
    });

    // ── Clear logs ─────────────────────────────────────────
    btnClearLogs.addEventListener('click', () => {
        terminal.innerHTML = '<span class="terminal-placeholder">Logs cleared.</span>';
        currentLogLength = 0;
    });

    // ── Polling ────────────────────────────────────────────
    function pollStatus() {
        fetch('/status')
            .then(r => r.json())
            .then(data => {
                updateStatusUI(data.is_running);
                if (data.stats) updateStatsUI(data.stats);
                updateLogsUI(data.logs);

                // Handle session restoration
                if (data.session_files && data.session_files.length > 0) {
                    isUploadReady = true;
                    updateFileListUI(data.session_files);
                    // Check if we need to enable buttons (only if not running)
                    if (!data.is_running) {
                        btnStart.disabled = false;
                        btnGenerate.disabled = false;
                    }
                } else if (data.session_files) {
                    // Files might have been cleared
                    updateFileListUI([]);
                }
            })
            .catch(err => console.error('Polling error:', err));

        // If Approvals view is active, poll for approvals too
        if (viewApprovals.classList.contains('active')) {
            pollApprovals();
        }
    }

    // ── Approvals Logic ────────────────────────────────────
    function pollApprovals() {
        if (!isUploadReady) return;

        // Don't poll if user is actively typing in a feedback textarea
        if (document.activeElement && document.activeElement.classList.contains('feedback-input')) return;
        // Don't poll if user is actively editing a message
        if (document.activeElement && document.activeElement.classList.contains('approval-message')) return;

        fetch('/api/approvals')
            .then(r => r.json())
            .then(data => {
                if (data.approvals) renderApprovals(data.approvals);
            })
            .catch(err => console.error('Approvals polling error:', err));
    }

    function renderApprovals(approvals) {
        if (!approvals || approvals.length === 0) {
            approvalsContainer.innerHTML = `
                <div class="empty-approvals">
                    <i class="fa-solid fa-inbox"></i>
                    <p>No messages pending approval.</p>
                </div>
            `;
            return;
        }

        // DOM diffing: also compare statuses so we re-render when a card's status changes
        const currentCards = approvalsContainer.querySelectorAll('.approval-card');
        const currentSignature = Array.from(currentCards).map(c => `${c.dataset.index}:${c.dataset.status}`).join(',');
        const newSignature = approvals.map(a => `${a.index}:${a.data.status}`).join(',');

        if (currentSignature === newSignature && currentCards.length > 0) return; // Unchanged

        approvalsContainer.innerHTML = '';
        approvals.forEach(approval => {
            const idx = approval.index;
            const user = approval.data.username || 'Unknown';
            const post = approval.data.post_content || 'No post content provided';
            const msg = approval.data.generated_message || '';

            const card = document.createElement('div');
            card.className = 'approval-card';
            card.dataset.index = idx;
            card.dataset.status = approval.data.status || 'pending_approval';

            const isApproved = approval.data.status === 'approved';
            const isSent = approval.data.status === 'sent';
            const isFailed = approval.data.status === 'failed';

            // Try to parse msg as a JSON array of variations
            let variations = [];
            try {
                variations = JSON.parse(msg);
                if (!Array.isArray(variations)) variations = [msg];
            } catch (e) {
                variations = [msg]; // Fallback if it's just a raw string
            }

            let actionHtml = '';
            let variationsHtml = '';

            if (isApproved || isSent || isFailed) {
                let statusColor = isSent ? 'var(--accent-green)' : (isFailed ? 'var(--accent-red)' : 'var(--accent-blue)');
                let statusIcon = isSent ? 'fa-paper-plane' : (isFailed ? 'fa-circle-xmark' : 'fa-check-circle');
                let statusText = isSent ? 'Sent' : (isFailed ? 'Failed' : 'Approved');

                actionHtml = `
                <div class="approval-actions" style="justify-content: center; padding-top: 10px;">
                    <div style="color: ${statusColor}; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid ${statusIcon}"></i> ${statusText}
                    </div>
                </div>`;
                
                // If it's already approved/sent, we only show the FIRST variation (which is the final chosen one)
                variationsHtml = `<textarea class="approval-message" rows="5" disabled>${variations[0] || ''}</textarea>`;

            } else {
                // Pending approval: show ALL variations
                actionHtml = `
                <div class="approval-actions" id="actions-${idx}" style="justify-content: space-between; border-top: 1px solid var(--border-color); padding-top: 15px; margin-top: 15px;">
                    <button class="btn-disapprove" onclick="toggleFeedback(${idx})">
                        <i class="fa-solid fa-thumbs-down"></i> None of these (Regenerate)
                    </button>
                </div>`;

                // Get the models selected by the user to label the variations
                let modelInput = document.getElementById('ai-model');
                let selectedModels = [];
                if (modelInput && modelInput.value) {
                    selectedModels = modelInput.value.split(',').map(m => m.trim()).filter(m => m);
                }

                variations.forEach((variation, vIdx) => {
                    let optionName = vIdx === 0 ? "DM Message" : "Comment Message";
                    if (selectedModels[vIdx] && variations.length > 2) {
                        optionName += ` (${selectedModels[vIdx]})`;
                    }
                    variationsHtml += `
                    <div class="variation-block" style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                            <span style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">${optionName}</span>
                        </div>
                        <textarea class="approval-message" rows="4" id="msg-${idx}-${vIdx}">${variation}</textarea>
                    </div>
                    `;
                });
                
                // Add the master approve button
                if (variations.length > 1) {
                    variationsHtml += `
                        <button class="btn-approve" onclick="handleApproveBoth(${idx}, event)" style="width: 100%; margin-top: 5px; font-size: 1rem; padding: 10px;">
                            <i class="fa-solid fa-check-double"></i> Approve Both Messages
                        </button>
                    `;
                } else {
                    variationsHtml += `
                        <button class="btn-approve" onclick="handleApprove(${idx}, 0)" style="width: 100%; margin-top: 5px; font-size: 1rem; padding: 10px;">
                            <i class="fa-solid fa-check"></i> Approve Message
                        </button>
                    `;
                }
            }

            card.innerHTML = `
                <div class="approval-header">
                    <div class="approval-user">@${user}</div>
                </div>
                <div class="approval-post">"${post}"</div>
                
                <div class="variations-container" style="margin-top: 15px;">
                    ${variationsHtml}
                </div>
                
                <div class="feedback-area" id="feedback-area-${idx}">
                    <textarea class="feedback-input" id="feedback-input-${idx}" rows="2" placeholder="How should the AI change these? e.g. 'Make them shorter and funnier'"></textarea>
                    <button class="btn-regenerate" onclick="handleRegenerate(${idx})">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> Regenerate Options
                    </button>
                </div>

                ${actionHtml}
            `;
            approvalsContainer.appendChild(card);
        });
    }

    window.toggleFeedback = function (idx) {
        const area = document.getElementById(`feedback-area-${idx}`);
        const input = document.getElementById(`feedback-input-${idx}`);

        if (area.classList.contains('active')) {
            area.classList.remove('active');
        } else {
            // Close all others first
            document.querySelectorAll('.feedback-area.active').forEach(el => el.classList.remove('active'));
            area.classList.add('active');
            input.focus();
        }
    };

    window.handleApproveBoth = function (idx, event) {
        const dmMsg = document.getElementById(`msg-${idx}-0`).value;
        const commentMsg = document.getElementById(`msg-${idx}-1`).value;
        const combined = JSON.stringify([dmMsg, commentMsg]);
        const btn = event ? event.currentTarget : document.querySelector(`.approval-card[data-index="${idx}"] .btn-approve`);

        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Approving...';
            btn.disabled = true;
        }

        fetch('/api/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: idx, message: combined })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const card = document.querySelector(`.approval-card[data-index="${idx}"]`);
                    if (card) {
                        card.dataset.status = 'approved';
                        const actionsEl = card.querySelector('.approval-actions') || card.querySelector(`#actions-${idx}`);
                        if (actionsEl) {
                            actionsEl.outerHTML = `<div class="approval-actions" style="justify-content: center; padding-top: 10px;">
                                <div style="color: var(--accent-blue); font-weight: 600; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-check-circle"></i> Approved Both
                                </div>
                            </div>`;
                        }
                    }
                } else {
                    alert(data.error);
                }
            });
    };

    window.handleApprove = function (idx, vIdx = 0) {
        // If vIdx is provided (new UI), grab that specific textarea. Otherwise fallback to old ID.
        const msgArea = document.getElementById(`msg-${idx}-${vIdx}`) || document.getElementById(`msg-${idx}`);
        const currentMsg = msgArea.value;
        const btn = event.currentTarget || document.querySelector(`.approval-card[data-index="${idx}"] .btn-approve`);

        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Approving...';
        btn.disabled = true;

        fetch('/api/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: idx, message: currentMsg })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    // Immediately update the card UI to show Approved badge
                    const card = document.querySelector(`.approval-card[data-index="${idx}"]`);
                    if (card) {
                        card.dataset.status = 'approved';
                        const actionsEl = card.querySelector('.approval-actions') || card.querySelector(`#actions-${idx}`);
                        if (actionsEl) {
                            actionsEl.outerHTML = `<div class="approval-actions" style="justify-content: center; padding-top: 10px;">
                                <div style="color: var(--accent-blue); font-weight: 600; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-check-circle"></i> Approved
                                </div>
                            </div>`;
                        }
                        
                        // Replace the variations container with just the single approved message
                        const varContainer = card.querySelector('.variations-container');
                        if (varContainer) {
                            varContainer.innerHTML = `<textarea class="approval-message" rows="5" disabled>${currentMsg}</textarea>`;
                        }
                    }
                } else {
                    alert(data.error);
                    btn.innerHTML = originalHtml;
                    btn.disabled = false;
                }
            });
    };

    window.handleRegenerate = function (idx) {
        const feedbackInput = document.getElementById(`feedback-input-${idx}`);
        const feedback = feedbackInput.value.trim();
        const btn = document.querySelector(`#feedback-area-${idx} .btn-regenerate`);

        if (!feedback) {
            alert('Please provide some feedback for regeneration.');
            feedbackInput.focus();
            return;
        }

        const key = aiApiKey ? aiApiKey.value.trim() : '';
        const model = aiModel ? aiModel.value.trim() : 'openai/gpt-4o-mini';
        const fallbackTemplate = templateArea.value.trim();
        const systemPrompt = aiSystemPrompt ? aiSystemPrompt.value.trim() : '';

        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Regenerating...';
        btn.disabled = true;
        feedbackInput.disabled = true;

        fetch('/api/disapprove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                index: idx,
                feedback: feedback,
                api_key: key,
                model: model,
                fallback_template: fallbackTemplate,
                ai_system_prompt: systemPrompt
            })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    toggleFeedback(idx); // Close feedback area
                    feedbackInput.value = ''; // Clear feedback
                    // Force a re-render so the new variations show immediately
                    approvalsContainer.innerHTML = '';
                    pollApprovals();
                } else {
                    alert(data.error);
                }
            })
            .finally(() => {
                btn.innerHTML = originalHtml;
                btn.disabled = false;
                feedbackInput.disabled = false;
            });
    };

    function updateStatusUI(isRunning) {
        if (isRunning) {
            statusBadge.classList.add('running');
            pulseDot.classList.add('running');
            statusDot.classList.add('running');
            statusText.textContent = isStopping ? 'Stopping...' : 'Running';
            statusSidebar.textContent = isStopping ? 'Stopping...' : 'Running';
            btnStart.disabled = true;
            btnGenerate.disabled = true;
            
            // Lock file upload and remove buttons
            fileInput.disabled = true;
            dropZone.style.pointerEvents = 'none';
            dropZone.style.opacity = '0.5';
            document.querySelectorAll('.btn-remove-file').forEach(btn => btn.disabled = true);
            
            // Don't override the button state while a stop is in progress
            if (!isStopping) {
                btnStop.disabled = false;
                btnStop.innerHTML = '<i class="fa-solid fa-stop"></i><span>Stop</span>';
            }
        } else {
            // Bot has fully stopped — clear the stopping flag
            isStopping = false;
            statusBadge.classList.remove('running');
            pulseDot.classList.remove('running');
            statusDot.classList.remove('running');
            statusText.textContent = 'Idle';
            statusSidebar.textContent = 'Idle';
            
            // Unlock file upload and remove buttons
            fileInput.disabled = false;
            dropZone.style.pointerEvents = 'auto';
            dropZone.style.opacity = '1';
            document.querySelectorAll('.btn-remove-file').forEach(btn => btn.disabled = false);

            // Re-enable action buttons whenever a file is uploaded — don't gate on pending count
            btnStart.disabled = !isUploadReady;
            btnGenerate.disabled = !isUploadReady;
            btnStop.disabled = true;
            btnStop.innerHTML = '<i class="fa-solid fa-stop"></i><span>Stop</span>';
        }
    }

    function updateStatsUI(stats) {
        statTotal.textContent = stats.total ?? 0;
        statPending.textContent = stats.pending ?? 0;
        statSent.textContent = stats.sent ?? 0;
        statFailed.textContent = stats.failed ?? 0;
        currentUser.textContent = stats.current_user || '— Idle —';
        // Note: button enable/disable is handled by updateStatusUI — don't override here
    }

    function updateLogsUI(logs) {
        if (!logs || logs.length === currentLogLength) return;

        terminal.innerHTML = '';
        logs.forEach(msg => {
            const line = document.createElement('div');
            line.className = 'log-line';
            if (msg.match(/ERROR|CRITICAL/i)) line.classList.add('error');
            else if (msg.match(/WARNING/i)) line.classList.add('warning');
            else if (msg.match(/SUCCESS/i)) line.classList.add('success');
            else if (msg.match(/DEBUG/i)) line.classList.add('debug');
            line.textContent = msg;
            terminal.appendChild(line);
        });
        terminal.scrollTop = terminal.scrollHeight;
        currentLogLength = logs.length;
    }

    // Poll every 1.5s
    setInterval(pollStatus, 1500);
    pollStatus();
});
