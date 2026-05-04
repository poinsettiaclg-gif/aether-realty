// ─── DOM Elements ────────────────────────────────────────────────────────────
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');
const resetBtn = document.getElementById('reset-btn');

// Lead Card Elements
const leadIntent = document.getElementById('lead-intent');
const leadTimeline = document.getElementById('lead-timeline');
const leadBudget = document.getElementById('lead-budget');
const leadContact = document.getElementById('lead-contact');
const leadBadge = document.getElementById('lead-badge');
const leadProgressFill = document.getElementById('lead-progress-fill');

// ─── Session ─────────────────────────────────────────────────────────────────
const sessionId = 'session_' + Math.random().toString(36).substring(2, 15);

// Auto-detect API URL: use localhost for local dev, production URL otherwise
const API_URL = (() => {
    // Check for explicit override via data attribute on script tag
    const scriptTag = document.querySelector('script[data-api-url]');
    if (scriptTag) return scriptTag.getAttribute('data-api-url');
    // If opened as a local file, use localhost
    if (window.location.protocol === 'file:' || window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') return 'http://127.0.0.1:8000';
    // In production, the API is on the same origin or a configured backend
    return window.AETHER_API_URL || 'https://47086247c49e59.lhr.life';
})();

// ─── Chat Functions ──────────────────────────────────────────────────────────
function addMessage(text, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message');
    msgDiv.classList.add(isUser ? 'user-message' : 'agent-message');
    
    const p = document.createElement('p');
    p.textContent = text;
    msgDiv.appendChild(p);
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setTyping(isTyping) {
    if (isTyping) {
        typingIndicator.classList.remove('hidden');
    } else {
        typingIndicator.classList.add('hidden');
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ─── Lead Card Functions ─────────────────────────────────────────────────────
function updateLeadCard(extractedData) {
    if (!extractedData) return;
    
    let fieldsCollected = 0;
    const totalFields = 4;
    
    // Intent
    if (extractedData.intent && extractedData.intent !== 'unknown') {
        leadIntent.textContent = extractedData.intent.charAt(0).toUpperCase() + extractedData.intent.slice(1);
        leadIntent.classList.add('filled');
        fieldsCollected++;
    }
    
    // Timeline
    if (extractedData.timeline && extractedData.timeline !== 'unknown') {
        leadTimeline.textContent = extractedData.timeline;
        leadTimeline.classList.add('filled');
        fieldsCollected++;
    }
    
    // Budget
    if (extractedData.budget && extractedData.budget !== 'unknown') {
        leadBudget.textContent = extractedData.budget;
        leadBudget.classList.add('filled');
        fieldsCollected++;
    }
    
    // Contact
    if (extractedData.contact && extractedData.contact !== 'unknown') {
        leadContact.textContent = extractedData.contact;
        leadContact.classList.add('filled');
        fieldsCollected++;
    }
    
    // Update progress bar
    const progress = (fieldsCollected / totalFields) * 100;
    leadProgressFill.style.width = progress + '%';
    
    // Update badge
    if (extractedData.is_qualified || fieldsCollected === totalFields) {
        leadBadge.textContent = '✓ Qualified';
        leadBadge.className = 'lead-badge qualified';
        leadProgressFill.classList.add('complete');
    } else if (fieldsCollected > 0) {
        leadBadge.textContent = `${fieldsCollected}/${totalFields} Collected`;
        leadBadge.className = 'lead-badge partial';
    }
}

function resetLeadCard() {
    leadIntent.textContent = '—';
    leadTimeline.textContent = '—';
    leadBudget.textContent = '—';
    leadContact.textContent = '—';
    
    [leadIntent, leadTimeline, leadBudget, leadContact].forEach(el => {
        el.classList.remove('filled');
    });
    
    leadBadge.textContent = 'Gathering...';
    leadBadge.className = 'lead-badge';
    leadProgressFill.style.width = '0%';
    leadProgressFill.classList.remove('complete');
}

// ─── API Communication ───────────────────────────────────────────────────────
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    
    // Clear input and show user message
    userInput.value = '';
    addMessage(text, true);
    
    // Show typing indicator
    setTyping(true);
    
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ session_id: sessionId, message: text })
        });
        
        if (response.status === 429) {
            setTyping(false);
            addMessage("Please slow down — I need a moment to think. Try again in a few seconds.");
            return;
        }
        
        const data = await response.json();
        
        setTyping(false);
        
        if (data.reply) {
            addMessage(data.reply);
            
            // Update the Lead Card with extracted data
            if (data.extracted_data) {
                updateLeadCard(data.extracted_data);
            }
        } else {
            addMessage("I'm sorry, I had trouble processing that. Could you rephrase?");
        }
    } catch (error) {
        setTyping(false);
        console.error("Error connecting to backend:", error);
        addMessage("Our systems are warming up. Please make sure the server is running and try again in a moment.");
    }
}

async function resetConversation() {
    // Reset the UI
    chatMessages.innerHTML = '';
    addMessage("Hi there! Welcome to Lake Region Realty. I'm here to help you get started — are you looking to buy or sell a property?");
    resetLeadCard();
    
    // Reset the server session
    try {
        await fetch(`${API_URL}/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
    } catch (error) {
        console.error("Error resetting session:", error);
    }
}

// ─── Event Listeners ─────────────────────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

resetBtn.addEventListener('click', resetConversation);
