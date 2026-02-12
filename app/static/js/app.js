const API_BASE = "";
let activeVoiceId = null;
let voicesCache = [];

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
                <p style="font-family: monospace; font-size: 0.65rem; margin-top: 2px;">${v.voice_id}</p>
            </div>
            ${activeIndicator}
        `;
        list.appendChild(div);
    });
}

function selectVoice(voiceId) {
    activeVoiceId = voiceId;
    renderVoices(); // Instant update!
}


function showCloneModal() {
    document.getElementById('cloneModal').style.display = 'block';
}

function hideCloneModal() {
    document.getElementById('cloneModal').style.display = 'none';
}

function showLinkModal() {
    document.getElementById('linkModal').style.display = 'block';
}

function hideLinkModal() {
    document.getElementById('linkModal').style.display = 'none';
}

async function linkVoice() {
    const name = document.getElementById('linkName').value;
    const voice_id = document.getElementById('linkVoiceId').value;

    if (!name || !voice_id) return alert("Please provide both a name and a Voice ID.");

    try {
        const response = await fetch(`${API_BASE}/voices/link`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, voice_id })
        });
        const result = await response.json();
        if (response.ok) {
            alert("Voice linked successfully!");
            hideLinkModal();
            fetchVoices();
        } else {
            alert(`Error: ${result.error || 'Failed to link voice'}`);
        }
    } catch (e) {
        console.error("Linking failed", e);
        alert("Network error. Check if server is running.");
    }
}

async function startCloning() {
    const name = document.getElementById('voiceName').value;
    const files = document.getElementById('voiceFiles').files;

    if (!files.length) return alert("Please select audio samples.");

    const formData = new FormData();
    formData.append('name', name);
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    alert("Cloning initiated! This will take a few minutes. Check console for status.");
    hideCloneModal();

    try {
        const response = await fetch(`${API_BASE}/voices/clone`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        console.log("Clone result:", result);
        fetchVoices();
    } catch (e) {
        console.error("Cloning failed", e);
    }
}

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
        alert("Call initiated!");
    } catch (e) {
        console.error("Call failed", e);
        alert("Failed to initiate call. Check server logs.");
    }
}

// Initial load
fetchVoices();

