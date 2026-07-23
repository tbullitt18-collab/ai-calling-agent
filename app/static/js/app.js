const API_BASE = "";
let activeVoiceId = null;
let voicesCache = [];
let userProfile = null;

// XSS protection: escape HTML entities in user-supplied strings
function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ══════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════

async function init() {
    await checkProfile();
    await fetchVoices();
    await loadSetup();
    await fetchKnowledgeBase();
    await fetchCallHistory();
}

// ══════════════════════════════════════════
// DISPLAY NAME GATE
// ══════════════════════════════════════════

async function checkProfile() {
    try {
        const resp = await fetch(`${API_BASE}/profile/`);
        if (!resp.ok) return;

        userProfile = await resp.json();

        if (!userProfile.display_name) {
            // Show the name gate
            document.getElementById('nameGate').style.display = 'block';
            document.getElementById('mainDashboard').style.opacity = '0.15';
            document.getElementById('mainDashboard').style.pointerEvents = 'none';
        } else {
            document.getElementById('nameGate').style.display = 'none';
            document.getElementById('mainDashboard').style.opacity = '1';
            document.getElementById('mainDashboard').style.pointerEvents = 'auto';
            document.getElementById('displayNameBadge').textContent = userProfile.display_name;
        }
    } catch (e) {
        console.error("Failed to check profile", e);
    }
}

async function setDisplayName() {
    const name = document.getElementById('displayNameInput').value.trim();
    const consent = document.getElementById('nameGateConsent').checked;
    const errEl = document.getElementById('nameGateError');
    errEl.textContent = '';

    if (!name || name.length < 2) {
        errEl.textContent = "Name must be at least 2 characters.";
        return;
    }
    if (!consent) {
        errEl.textContent = "You must acknowledge the privacy policy.";
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/profile/display-name`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ display_name: name })
        });

        const data = await resp.json();

        if (resp.ok) {
            document.getElementById('nameGate').style.display = 'none';
            document.getElementById('mainDashboard').style.opacity = '1';
            document.getElementById('mainDashboard').style.pointerEvents = 'auto';
            document.getElementById('displayNameBadge').textContent = name;
            userProfile = data.profile;
        } else {
            errEl.textContent = data.error || "Failed to set display name.";
        }
    } catch (e) {
        errEl.textContent = "Network error. Please try again.";
        console.error("Display name error", e);
    }
}

// ══════════════════════════════════════════
// TAB NAVIGATION
// ══════════════════════════════════════════

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });

    // Refresh data when switching to voices tab
    if (tabName === 'voices') {
        renderVoiceEditList();
    }
}

// ══════════════════════════════════════════
// VOICE FETCHING & RENDERING (Dashboard Tab)
// ══════════════════════════════════════════

async function fetchVoices() {
    try {
        const response = await fetch(`${API_BASE}/voices/`);

        const list = document.getElementById('voiceList');

        if (!response.ok) {
            const list = document.getElementById('voiceList');
            const err = await response.json();
            list.innerHTML = `<p style="color: #ff4d4d; font-size: 0.8rem;">Error: ${err.error || 'Failed to load voices'}</p>`;
            return;
        }

        const voices = await response.json();
        voicesCache = voices;
        renderVoices();
        renderVoiceEditList();
    } catch (e) {
        console.error("Failed to fetch voices", e);
    }
}

function renderVoices() {
    const list = document.getElementById('voiceList');
    list.innerHTML = '';

    if (voicesCache.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.8rem;">No voices found. Link one to get started!</p>';
        return;
    }

    // Default to first voice if none selected
    if (!activeVoiceId && voicesCache.length > 0) activeVoiceId = voicesCache[0].voice_id;

    voicesCache.forEach(v => {
        const isActive = v.voice_id === activeVoiceId;
        const div = document.createElement('div');
        div.className = `voice-item ${isActive ? 'active-voice' : ''}`;
        div.style.cursor = 'pointer';
        div.onclick = () => selectVoice(v.voice_id);

        const sourceTag = v.source === 'local' ? '<span class="status-pill" style="background:rgba(188, 140, 255, 0.15); color:var(--accent-purple);">Linked</span>' : '<span class="status-pill">System</span>';
        const activeIndicator = isActive ? '<span style="color: var(--accent-blue); font-size: 0.7rem; font-weight: 800;">● ACTIVE</span>' : '<span style="color: var(--text-secondary); font-size: 0.7rem;">Select</span>';

        div.innerHTML = `
            <div class="voice-info">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <h3>${v.name}</h3>
                    ${sourceTag}
                </div>
            </div>
            ${activeIndicator}
        `;
        list.appendChild(div);
    });
}

function selectVoice(voiceId) {
    activeVoiceId = voiceId;
    renderVoices();
}

// ══════════════════════════════════════════
// VOICE EDITING (Voices Tab)
// ══════════════════════════════════════════

function renderVoiceEditList() {
    const list = document.getElementById('voiceEditList');
    if (!list) return;

    list.innerHTML = '';

    if (voicesCache.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">No voice profiles yet. Create or link one from the Dashboard tab.</p>';
        return;
    }

    voicesCache.forEach(v => {
        const card = document.createElement('div');
        card.className = 'voice-edit-card';
        card.innerHTML = `
            <div class="voice-edit-info">
                <h3>🎙️ ${v.name}</h3>
                <div class="voice-meta">
                    <span>ID: ${v.voice_id.substring(0, 12)}...</span>
                    <span class="status-pill" style="background:rgba(63,185,80,0.1); color: #3fb950;">${v.status || 'active'}</span>
                    <span>${v.source === 'local' ? '🔗 Linked' : '📦 System'}</span>
                </div>
            </div>
            <div class="voice-edit-actions">
                <button class="btn btn-sm btn-edit" onclick="showEditModal('${v.voice_id}', '${v.name.replace(/'/g, "\\'")}')">✏️ Edit</button>
                <button class="btn btn-sm btn-delete" onclick="deleteVoice('${v.voice_id}')">🗑</button>
            </div>
        `;
        list.appendChild(card);
    });
}

function showEditModal(voiceId, currentName) {
    document.getElementById('editVoiceId').value = voiceId;
    document.getElementById('editVoiceName').value = currentName;
    document.getElementById('editVoiceError').textContent = '';
    document.getElementById('editVoiceModal').style.display = 'block';
    document.getElementById('modalOverlay').style.display = 'block';
}

function hideEditModal() {
    document.getElementById('editVoiceModal').style.display = 'none';
    document.getElementById('modalOverlay').style.display = 'none';
}

async function saveVoiceEdit() {
    const voiceId = document.getElementById('editVoiceId').value;
    const name = document.getElementById('editVoiceName').value.trim();
    const tone = document.getElementById('editVoiceTone').value;
    const delivery = document.getElementById('editVoiceDelivery').value;
    const errEl = document.getElementById('editVoiceError');
    errEl.textContent = '';

    if (!name) {
        errEl.textContent = "Name cannot be empty.";
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/voices/${voiceId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                characteristics: { tone, delivery }
            })
        });

        const data = await resp.json();

        if (resp.ok) {
            hideEditModal();
            await fetchVoices(); // Refresh
        } else {
            errEl.textContent = data.error || "Failed to update.";
        }
    } catch (e) {
        errEl.textContent = "Network error.";
        console.error("Edit voice error", e);
    }
}

async function deleteVoice(voiceId) {
    if (!confirm("Are you sure you want to delete this voice profile?")) return;

    try {
        const resp = await fetch(`${API_BASE}/voices/${voiceId}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.success !== false) {
            await fetchVoices();
        } else {
            alert("Failed to delete voice.");
        }
    } catch (e) {
        console.error("Delete voice error", e);
        alert("Network error.");
    }
}

// ══════════════════════════════════════════
// SETUP (Setup Tab)
// ══════════════════════════════════════════

let selectedWorkDays = [];

function toggleDay(btn) {
    const day = btn.dataset.day;
    if (selectedWorkDays.includes(day)) {
        selectedWorkDays = selectedWorkDays.filter(d => d !== day);
        btn.classList.remove('selected');
    } else {
        selectedWorkDays.push(day);
        btn.classList.add('selected');
    }
}

async function loadSetup() {
    try {
        const resp = await fetch(`${API_BASE}/profile/setup`);
        if (!resp.ok) return;

        const data = await resp.json();
        const setup = data.setup || {};

        if (setup.employee_id) document.getElementById('setupEmployeeId').value = setup.employee_id;
        if (setup.company_name) document.getElementById('setupCompanyName').value = setup.company_name;
        if (setup.department) document.getElementById('setupDepartment').value = setup.department;
        if (setup.position) document.getElementById('setupPosition').value = setup.position;
        if (setup.location) document.getElementById('setupLocation').value = setup.location;
        if (setup.manager_name) document.getElementById('setupManagerName').value = setup.manager_name;
        if (setup.manager_number) {
            document.getElementById('setupManagerNumber').value = setup.manager_number;
            // Also pre-fill the dashboard call scheduler number
            document.getElementById('managerNumber').value = setup.manager_number;
        }
        if (setup.shift_start) document.getElementById('setupShiftStart').value = setup.shift_start;
        if (setup.shift_end) document.getElementById('setupShiftEnd').value = setup.shift_end;
        if (setup.notes) document.getElementById('setupNotes').value = setup.notes;

        // Work days
        if (setup.work_days && Array.isArray(setup.work_days)) {
            selectedWorkDays = setup.work_days;
            document.querySelectorAll('.day-btn').forEach(btn => {
                if (selectedWorkDays.includes(btn.dataset.day)) {
                    btn.classList.add('selected');
                }
            });
        }

    } catch (e) {
        console.error("Failed to load setup", e);
    }
}

async function saveSetup() {
    const statusEl = document.getElementById('setupStatus');
    statusEl.textContent = 'Saving...';
    statusEl.style.color = 'var(--accent-blue)';

    const setupData = {
        employee_id: document.getElementById('setupEmployeeId').value.trim(),
        company_name: document.getElementById('setupCompanyName').value.trim(),
        department: document.getElementById('setupDepartment').value.trim(),
        position: document.getElementById('setupPosition').value.trim(),
        location: document.getElementById('setupLocation').value.trim(),
        manager_name: document.getElementById('setupManagerName').value.trim(),
        manager_number: document.getElementById('setupManagerNumber').value.trim(),
        shift_start: document.getElementById('setupShiftStart').value,
        shift_end: document.getElementById('setupShiftEnd').value,
        work_days: selectedWorkDays,
        notes: document.getElementById('setupNotes').value.trim()
    };

    try {
        const resp = await fetch(`${API_BASE}/profile/setup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(setupData)
        });

        const data = await resp.json();

        if (resp.ok) {
            statusEl.textContent = '✅ Setup saved successfully!';
            statusEl.style.color = 'var(--success-green)';
            // Also update the dashboard manager number
            if (setupData.manager_number) {
                document.getElementById('managerNumber').value = setupData.manager_number;
            }
        } else {
            statusEl.textContent = `❌ ${data.error || 'Failed to save'}`;
            statusEl.style.color = 'var(--error-red)';
        }
    } catch (e) {
        statusEl.textContent = '❌ Network error';
        statusEl.style.color = 'var(--error-red)';
        console.error("Save setup error", e);
    }

    setTimeout(() => { statusEl.textContent = ''; }, 4000);
}

// ══════════════════════════════════════════
// MODALS & AUTH
// ══════════════════════════════════════════

async function logout() {
    try {
        await fetch('/logout', { method: 'POST' });
    } catch (e) { }
    window.location.href = '/login';
}

function showCloneModal() {
    document.getElementById('cloneModal').style.display = 'block';
    document.getElementById('modalOverlay').style.display = 'block';
}

function hideCloneModal() {
    document.getElementById('cloneModal').style.display = 'none';
    document.getElementById('modalOverlay').style.display = 'none';
}



function showPrivacyModal() {
    document.getElementById('privacyModal').style.display = 'block';
    document.getElementById('modalOverlay').style.display = 'block';
}

function hidePrivacyModal() {
    document.getElementById('privacyModal').style.display = 'none';
    document.getElementById('modalOverlay').style.display = 'none';
}

function closeAllModals() {
    hideCloneModal();
    hideEditModal();
    hidePrivacyModal();
}

let mediaRecorder;
let audioChunks = [];
let recordedBlob = null;
let isRecording = false;

async function toggleRecording() {
    const btn = document.getElementById('recordBtn');
    const status = document.getElementById('recordStatus');
    
    if (isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        btn.innerHTML = '🔴 Start Recording';
        status.textContent = 'Recording stopped. Ready to clone!';
    } else {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };
            
            mediaRecorder.onstop = () => {
                // ElevenLabs accepts webm/wav etc, MediaRecorder usually produces webm
                recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
            isRecording = true;
            btn.innerHTML = '⏹ Stop Recording';
            status.textContent = 'Recording... Read a few sentences naturally.';
            recordedBlob = null;
        } catch (err) {
            console.error("Microphone access denied", err);
            status.textContent = 'Error: Microphone access denied.';
        }
    }
}

async function startCloning() {
    const name = document.getElementById('voiceName').value;
    const files = document.getElementById('voiceFiles').files;
    const consent = document.getElementById('consentCheck').checked;

    if (!name) return alert("Please provide a name for your custom voice.");
    if (!recordedBlob && !files.length) return alert("Please record an audio sample first.");
    if (!consent) return alert("You must provide explicit consent for ElevenLabs to process your audio recordings.");

    const formData = new FormData();
    formData.append('name', name);
    
    if (recordedBlob) {
        formData.append('files', recordedBlob, 'recording.webm');
    } else {
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
    }

    alert("Voice cloning initiated via ElevenLabs. This usually takes just a few seconds.");
    hideCloneModal();

    try {
        const response = await fetch(`${API_BASE}/voices/clone`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (response.ok) {
            alert("ElevenLabs Voice Clone created successfully!");
        } else {
            alert(`Error: ${result.error}`);
        }
        console.log("Custom Voice result:", result);
        fetchVoices();
    } catch (e) {
        console.error("Training submission failed", e);
        alert("Failed to submit voice training to ElevenLabs.");
    }
}

// ══════════════════════════════════════════
// CALL SCHEDULING
// ══════════════════════════════════════════

async function scheduleCall() {
    const number = document.getElementById('managerNumber').value;
    const time = document.getElementById('callTime').value;
    const reason = document.getElementById('callReason').value;
    const notes = document.getElementById('callNotes').value;

    if (!number || !time) return alert("Fill in number and time.");

    try {
        const response = await fetch(`${API_BASE}/session/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                to_number: number,
                time: time,
                reason: reason,
                notes: notes,
                voice_id: activeVoiceId
            })
        });
        const result = await response.json();

        if (!response.ok) {
            alert(`Scheduling failed: ${result.error || 'Unknown error'}`);
            return;
        }

        const list = document.getElementById('upcomingCalls');
        const item = document.createElement('div');
        item.className = 'call-item';
        item.innerHTML = `
            <span>${reason} (${number})</span>
            <span class="time">${time}</span>
        `;
        list.prepend(item);
        alert(`Call scheduled for ${time}!`);
    } catch (e) {
        console.error("Scheduling failed", e);
        alert("Network error. Check if server is running.");
    }
}

async function callNow() {
    const number = document.getElementById('managerNumber').value;
    const reason = document.getElementById('callReason').value;
    const notes = document.getElementById('callNotes').value;

    if (!number) return alert("Enter a phone number.");

    try {
        const response = await fetch(`${API_BASE}/session/call-now`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                to_number: number,
                reason: reason,
                notes: notes,
                voice_id: activeVoiceId
            })
        });
        const result = await response.json();

        if (!response.ok) {
            alert(`Call failed: ${result.error || 'Unknown error'}`);
            return;
        }

        alert("Call initiated!");
    } catch (e) {
        console.error("Call failed", e);
        alert("Network error. Check if server is running.");
    }
}

// ══════════════════════════════════════════
// KNOWLEDGE BASE (MCP INTEGRATION)
// ══════════════════════════════════════════

async function fetchKnowledgeBase() {
    try {
        // Fetch FAQs
        const faqResp = await fetch(`${API_BASE}/api/mcp/faqs`);
        if (faqResp.ok) {
            const faqData = await faqResp.json();
            const faqs = faqData.faqs || [];
            const faqList = document.getElementById('faqList');
            faqList.innerHTML = faqs.length ? '' : '<p style="color: var(--text-secondary); font-size: 0.8rem;">No FAQs yet.</p>';
            faqs.forEach(f => {
                faqList.innerHTML += `<div style="background: rgba(255,255,255,0.05); padding: 0.6rem; border-radius: 6px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <strong style="display:block; font-size: 0.85rem; color: var(--accent-blue);">Q: ${escapeHtml(f.question)}</strong>
                        <span style="font-size: 0.8rem;">A: ${escapeHtml(f.answer)}</span>
                    </div>
                    <button class="btn btn-sm" style="background: transparent; border: none; padding: 0.2rem; cursor: pointer; font-size: 1rem;" onclick="deleteFaq('${f._id}')" title="Delete">🗑️</button>
                </div>`;
            });
        }

        // Fetch Calendar
        const calResp = await fetch(`${API_BASE}/api/mcp/calendar`);
        if (calResp.ok) {
            const calData = await calResp.json();
            const events = calData.events || [];
            const calList = document.getElementById('calendarList');
            calList.innerHTML = events.length ? '' : '<p style="color: var(--text-secondary); font-size: 0.8rem;">No events yet.</p>';
            events.forEach(e => {
                calList.innerHTML += `<div style="background: rgba(255,255,255,0.05); padding: 0.6rem; border-radius: 6px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <strong style="display:block; font-size: 0.85rem; color: var(--accent-purple);">${escapeHtml(e.title)}</strong>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(e.date)}</span>
                    </div>
                    <button class="btn btn-sm" style="background: transparent; border: none; padding: 0.2rem; cursor: pointer; font-size: 1rem;" onclick="deleteCalendarEvent('${e._id}')" title="Delete">🗑️</button>
                </div>`;
            });
        }

        // Fetch Contacts
        const conResp = await fetch(`${API_BASE}/api/mcp/contacts`);
        if (conResp.ok) {
            const conData = await conResp.json();
            const contacts = conData.contacts || [];
            const conList = document.getElementById('contactList');
            conList.innerHTML = contacts.length ? '' : '<p style="color: var(--text-secondary); font-size: 0.8rem;">No contacts yet.</p>';
            contacts.forEach(c => {
                conList.innerHTML += `<div style="background: rgba(255,255,255,0.05); padding: 0.6rem; border-radius: 6px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <strong style="display:block; font-size: 0.85rem; color: #3fb950;">${escapeHtml(c.name)}</strong>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(c.role)}</span>
                    </div>
                    <button class="btn btn-sm" style="background: transparent; border: none; padding: 0.2rem; cursor: pointer; font-size: 1rem;" onclick="deleteContact('${c._id}')" title="Delete">🗑️</button>
                </div>`;
            });
        }
    } catch (e) {
        console.error("Failed to load knowledge base", e);
    }
}

async function addFaq() {
    const q = document.getElementById('newFaqQ').value;
    const a = document.getElementById('newFaqA').value;
    if (!q || !a) return alert('Enter question and answer');
    try {
        await fetch(`${API_BASE}/api/mcp/faqs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: q, answer: a })
        });
        document.getElementById('newFaqQ').value = '';
        document.getElementById('newFaqA').value = '';
        fetchKnowledgeBase();
    } catch (e) { alert('Error adding FAQ'); }
}

async function addCalendarEvent() {
    const t = document.getElementById('newCalTitle').value;
    const d = document.getElementById('newCalDate').value;
    if (!t || !d) return alert('Enter title and date');
    try {
        await fetch(`${API_BASE}/api/mcp/calendar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: t, date: d })
        });
        document.getElementById('newCalTitle').value = '';
        document.getElementById('newCalDate').value = '';
        fetchKnowledgeBase();
    } catch (e) { alert('Error adding event'); }
}

async function addContact() {
    const n = document.getElementById('newContactName').value;
    const r = document.getElementById('newContactRole').value;
    if (!n || !r) return alert('Enter name and role');
    try {
        await fetch(`${API_BASE}/api/mcp/contacts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: n, role: r })
        });
        document.getElementById('newContactName').value = '';
        document.getElementById('newContactRole').value = '';
        fetchKnowledgeBase();
    } catch (e) { alert('Error adding contact'); }
}

async function deleteFaq(id) {
    if (!confirm('Delete this FAQ?')) return;
    try {
        await fetch(`${API_BASE}/api/mcp/faqs/${id}`, { method: 'DELETE' });
        fetchKnowledgeBase();
    } catch (e) { alert('Error deleting FAQ'); }
}

async function deleteCalendarEvent(id) {
    if (!confirm('Delete this calendar event?')) return;
    try {
        await fetch(`${API_BASE}/api/mcp/calendar/${id}`, { method: 'DELETE' });
        fetchKnowledgeBase();
    } catch (e) { alert('Error deleting calendar event'); }
}

async function deleteContact(id) {
    if (!confirm('Delete this contact?')) return;
    try {
        await fetch(`${API_BASE}/api/mcp/contacts/${id}`, { method: 'DELETE' });
        fetchKnowledgeBase();
    } catch (e) { alert('Error deleting contact'); }
}

async function seedDemoData() {
    try {
        const btn = event.target;
        btn.textContent = 'Seeding...';
        btn.disabled = true;
        
        await fetch(`${API_BASE}/api/mcp/seed`, { method: 'POST' });
        
        btn.textContent = '✅ Seeded';
        fetchKnowledgeBase();
        
        setTimeout(() => {
            btn.textContent = 'Seed Demo Data';
            btn.disabled = false;
        }, 2000);
    } catch (e) {
        alert('Error seeding demo data');
        event.target.textContent = 'Seed Demo Data';
        event.target.disabled = false;
    }
}

async function clearKnowledgeBase() {
    if (!confirm('Are you sure you want to delete all FAQs, Calendar events, and Contacts? This cannot be undone.')) {
        return;
    }
    
    try {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = 'Clearing...';
        btn.disabled = true;
        
        await fetch(`${API_BASE}/api/mcp/clear`, { method: 'DELETE' });
        
        btn.textContent = '✅ Cleared';
        fetchKnowledgeBase();
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    } catch (e) {
        alert('Error clearing knowledge base data');
        const btn = event.target;
        btn.textContent = 'Clear Data';
        btn.disabled = false;
    }
}

async function fetchCallHistory() {
    try {
        const resp = await fetch(`${API_BASE}/api/calls/recent?limit=5`);
        if (!resp.ok) return;

        const data = await resp.json();
        const calls = data.calls || [];
        const list = document.getElementById('callHistoryList');
        
        if (calls.length === 0) {
            list.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.8rem;">No call history available.</p>';
            return;
        }

        list.innerHTML = '';
        calls.forEach(call => {
            const dateStr = new Date(call.timestamp).toLocaleString();
            const durationStr = call.duration_seconds > 0 ? `${call.duration_seconds}s` : 'Unknown';
            const intentStr = call.intent !== 'unknown' ? `<span class="status-pill">${call.intent}</span>` : '';
            const statusColor = call.status === 'completed' ? 'var(--success-green)' : 'var(--text-secondary)';
            
            // Encode transcript as a JSON string to pass it to the modal
            const transcriptJson = encodeURIComponent(JSON.stringify(call.transcript || []));
            const summaryText = (call.summary || 'No summary available').replace(/'/g, "\\'");

            list.innerHTML += `<div class="call-item" style="display: block; cursor: pointer; padding: 1rem; border-left: 3px solid ${statusColor};" onclick="showTranscriptModal('${summaryText}', '${transcriptJson}')">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <strong style="color: white; font-size: 0.9rem;">To: ${call.caller}</strong>
                    <span style="font-size: 0.75rem; color: var(--text-secondary);">${dateStr}</span>
                </div>
                <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-size: 0.75rem; color: var(--text-secondary);">Duration: ${durationStr}</span>
                    <span style="font-size: 0.75rem; color: var(--text-secondary);">Status: ${call.status}</span>
                    ${intentStr}
                </div>
                <p style="font-size: 0.85rem; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                    <strong>Summary:</strong> ${call.summary}
                </p>
            </div>`;
        });
    } catch (e) {
        console.error("Failed to fetch call history", e);
    }
}

function showTranscriptModal(summary, transcriptEncoded) {
    let transcriptHtml = '';
    try {
        const transcript = JSON.parse(decodeURIComponent(transcriptEncoded));
        if (transcript && transcript.length > 0) {
            transcriptHtml = transcript.map(t => {
                const isAI = t.role === 'assistant';
                const color = isAI ? 'var(--accent-blue)' : 'white';
                const name = isAI ? 'AI Twin' : 'Manager';
                return `<div style="margin-bottom: 0.8rem; background: rgba(255,255,255,0.05); padding: 0.8rem; border-radius: 8px;">
                            <strong style="color: ${color}; font-size: 0.8rem;">${name}</strong>
                            <p style="margin-top: 0.3rem; font-size: 0.9rem; line-height: 1.4; color: var(--text-secondary);">${t.content}</p>
                        </div>`;
            }).join('');
        } else {
            transcriptHtml = '<p style="color: var(--text-secondary); font-size: 0.9rem;">No transcript recorded for this call.</p>';
        }
    } catch (e) {
        transcriptHtml = '<p style="color: var(--error-red); font-size: 0.9rem;">Failed to load transcript.</p>';
    }

    const modal = document.createElement('div');
    modal.id = 'transcriptModal';
    modal.style = 'position:fixed; top:50%; left:50%; transform:translate(-50%, -50%); background: var(--bg-color); padding: 2.5rem; border-radius: 20px; border: 1px solid var(--glass-border); z-index: 205; width: 600px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 0 50px rgba(0,0,0,0.8);';
    
    modal.innerHTML = `
        <h2 style="margin-bottom: 1rem; flex-shrink: 0;">Call Details</h2>
        <div style="flex-grow: 1; overflow-y: auto; padding-right: 1rem;">
            <div style="margin-bottom: 1.5rem; background: rgba(88,166,255,0.1); border: 1px solid var(--accent-blue); padding: 1rem; border-radius: 12px;">
                <h3 style="color: white; font-size: 0.9rem; margin-bottom: 0.5rem;">AI Summary</h3>
                <p style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.5;">${summary}</p>
            </div>
            <h3 style="color: white; font-size: 1rem; margin-bottom: 1rem;">Transcript</h3>
            ${transcriptHtml}
        </div>
        <button class="btn" style="width: 100%; margin-top: 1.5rem; flex-shrink: 0;" onclick="document.body.removeChild(document.getElementById('transcriptModal')); document.getElementById('modalOverlay').style.display = 'none';">Close</button>
    `;

    document.body.appendChild(modal);
    document.getElementById('modalOverlay').style.display = 'block';
    
    // Add custom close handler for overlay
    const overlay = document.getElementById('modalOverlay');
    const oldOnclick = overlay.onclick;
    overlay.onclick = function() {
        if (document.getElementById('transcriptModal')) {
            document.body.removeChild(document.getElementById('transcriptModal'));
        }
        if (oldOnclick) oldOnclick();
        else overlay.style.display = 'none';
        overlay.onclick = oldOnclick; // restore
    };
}

init();
