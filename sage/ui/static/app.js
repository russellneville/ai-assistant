// Sage UI JavaScript
class SageUI {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.isOffline = false;
        this.wasOffline = false;
        this.sleepVideoPreloaded = false;
        this.preloadSleepVideo();
        this.connect();
        this.bindEvents();
        this.loadMarkdownLibrary();
    }
    
    loadMarkdownLibrary() {
        // Load marked.js for markdown rendering
        if (!window.marked) {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
            script.onload = () => {
                console.log('Markdown library loaded');
                // Configure marked for safe rendering
                if (window.marked) {
                    marked.setOptions({
                        breaks: true,
                        gfm: true,
                        sanitize: false, // We trust Sage's responses
                        smartLists: true,
                        smartypants: true
                    });
                }
            };
            document.head.appendChild(script);
        }
    }
    
    renderMarkdown(text) {
        if (window.marked) {
            return marked.parse(text);
        } else {
            // Fallback: basic markdown-like formatting
            return text
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                .replace(/^### (.*$)/gim, '<h3>$1</h3>')
                .replace(/^- (.*$)/gim, '<li>$1</li>')
                .replace(/\n/g, '<br>');
        }
    }
    
    preloadSleepVideo() {
        // Preload both sleep videos so they're cached and available even when offline
        this.sleepVideosPreloaded = { transition: false, state: false };
        
        // Preload transition video (sage-sleeps.mp4)
        const sleepTransitionVideo = document.createElement('video');
        sleepTransitionVideo.preload = 'auto';
        sleepTransitionVideo.muted = true;
        sleepTransitionVideo.style.display = 'none';
        
        const transitionSource = document.createElement('source');
        transitionSource.src = '/personality/video/sage-sleeps.mp4';
        transitionSource.type = 'video/mp4';
        
        sleepTransitionVideo.appendChild(transitionSource);
        document.body.appendChild(sleepTransitionVideo);
        
        sleepTransitionVideo.addEventListener('canplaythrough', () => {
            this.sleepVideosPreloaded.transition = true;
            console.log('Sleep transition video (sage-sleeps.mp4) preloaded and cached');
        });
        
        sleepTransitionVideo.addEventListener('error', (e) => {
            console.warn('Failed to preload sleep transition video:', e);
        });
        
        sleepTransitionVideo.load();
        
        // Preload sleep state video (sage-asleep.mp4)
        const sleepStateVideo = document.createElement('video');
        sleepStateVideo.preload = 'auto';
        sleepStateVideo.muted = true;
        sleepStateVideo.style.display = 'none';
        
        const stateSource = document.createElement('source');
        stateSource.src = '/personality/video/sage-asleep.mp4';
        stateSource.type = 'video/mp4';
        
        sleepStateVideo.appendChild(stateSource);
        document.body.appendChild(sleepStateVideo);
        
        sleepStateVideo.addEventListener('canplaythrough', () => {
            this.sleepVideosPreloaded.state = true;
            console.log('Sleep state video (sage-asleep.mp4) preloaded and cached');
        });
        
        sleepStateVideo.addEventListener('error', (e) => {
            console.warn('Failed to preload sleep state video:', e);
        });
        
        sleepStateVideo.load();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Connected to Sage');
            this.handleReconnection();
            this.updateStatus('online');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected from Sage');
            this.handleDisconnection();
            this.updateStatus('offline');
            setTimeout(() => this.connect(), this.reconnectInterval);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    handleDisconnection() {
        this.wasOffline = this.isOffline;
        
        // Only trigger offline sleep sequence if we weren't already offline
        if (!this.isOffline) {
            this.isOffline = true;
            
            // Show offline message
            this.showOfflineMessage();
            
            // Put Sage to sleep when going offline (only once)
            this.putSageToSleepOffline();
        }
    }
    
    handleReconnection() {
        if (this.isOffline) {
            this.isOffline = false;
            
            // Hide offline message
            this.hideOfflineMessage();
            
            // Show reconnection toast
            this.showReconnectionToast();
            
            // Wake Sage up when reconnecting
            this.wakeSageUpOnline();
        }
    }
    
    showOfflineMessage() {
        const offlineMessage = document.getElementById('offline-message');
        if (offlineMessage) {
            offlineMessage.classList.remove('hidden');
        }
    }
    
    hideOfflineMessage() {
        const offlineMessage = document.getElementById('offline-message');
        if (offlineMessage) {
            offlineMessage.classList.add('hidden');
        }
    }
    
    showReconnectionToast() {
        this.showToast('Sage is reconnected and ready to help!', 'success', '✅');
    }
    
    showToast(message, type = 'info', icon = 'ℹ️') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
            </div>
            <div class="toast-progress"></div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove toast after animation completes
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
    }
    
    putSageToSleepOffline() {
        // When offline, use two-video sleep sequence: transition -> looping sleep state
        const face = document.getElementById('sage-face');
        if (face) {
            const source = face.querySelector('source');
            if (source) {
                console.log('Starting offline sleep sequence: transition video first');
                
                // Step 1: Play transition video (sage-sleeps.mp4) without looping
                face.loop = false;
                face.removeAttribute('loop');
                
                // Remove any existing event listeners
                if (this.offlineSleepTransitionHandler) {
                    face.removeEventListener('ended', this.offlineSleepTransitionHandler);
                }
                
                // Create event listener to switch to sleep state video when transition ends
                this.offlineSleepTransitionHandler = () => {
                    console.log('Offline sleep transition video ended - switching to sleep state video');
                    
                    // Clear any existing timeout
                    if (this.offlineSleepTimeout) {
                        clearTimeout(this.offlineSleepTimeout);
                        this.offlineSleepTimeout = null;
                    }
                    
                    // Step 2: Switch to looping sleep state video (sage-asleep.mp4)
                    source.src = '/personality/video/sage-asleep.mp4';
                    face.loop = true;
                    face.setAttribute('loop', '');
                    
                    face.load();
                    face.play().catch(error => {
                        console.log('Sleep state video play failed (offline):', error);
                    });
                    
                    // Remove the transition event listener
                    face.removeEventListener('ended', this.offlineSleepTransitionHandler);
                    this.offlineSleepTransitionHandler = null;
                };
                
                face.addEventListener('ended', this.offlineSleepTransitionHandler);
                
                // Add debugging event listeners
                face.addEventListener('loadstart', () => {
                    console.log('Sleep transition video: loadstart event');
                });
                
                face.addEventListener('canplay', () => {
                    console.log('Sleep transition video: canplay event');
                });
                
                face.addEventListener('playing', () => {
                    console.log('Sleep transition video: playing event');
                });
                
                face.addEventListener('timeupdate', () => {
                    console.log(`Sleep transition video: timeupdate - currentTime: ${face.currentTime}, duration: ${face.duration}`);
                });
                
                // Start with transition video
                source.src = '/personality/video/sage-sleeps.mp4';
                face.load();
                
                // Add a timeout fallback in case the ended event doesn't fire
                this.offlineSleepTimeout = setTimeout(() => {
                    console.log('Sleep transition timeout reached - forcing switch to sleep state video');
                    if (this.offlineSleepTransitionHandler) {
                        this.offlineSleepTransitionHandler();
                    }
                }, 8000); // 8 second timeout (sage-sleeps.mp4 should be ~5 seconds)
                
                face.play().catch(error => {
                    console.log('Sleep transition video play failed (offline):', error);
                    // If transition video fails, go directly to sleep state
                    if (this.offlineSleepTransitionHandler) {
                        this.offlineSleepTransitionHandler();
                    }
                });
            }
        }
    }
    
    wakeSageUpOnline() {
        // When coming back online, wake Sage up using server API
        this.wakeSageUp();
    }
    
    updateStatus(status) {
        const indicator = document.getElementById('status-indicator');
        indicator.className = `status-${status}`;
        indicator.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }
    
    handleMessage(data) {
        if (data.type === 'message') {
            this.displayMessage(data.data, 'sage');
            this.updatePersonality(data.data);
        } else if (data.type === 'notification') {
            this.displayMessage(data.data, 'system');
            this.updatePersonality(data.data);
        } else if (data.type === 'file_change') {
            this.displayFileChange(data.data);
        } else if (data.type === 'conflict_resolution') {
            this.displayConflictResolution(data.data);
        } else if (data.type === 'video_change') {
            this.updatePersonality(data.data);
            console.log('Video changed:', data.data.emotion, data.data.type);
        } else if (data.type === 'thinking_start') {
            this.showThinkingIndicator();
        } else if (data.type === 'thinking_complete') {
            this.removeThinkingIndicator();
            console.log('Thinking completed:', data.data.response_time);
            // Ensure scroll after thinking indicator is removed
            setTimeout(() => this.scrollToBottom(), 100);
        } else if (data.type === 'thinking_error') {
            this.removeThinkingIndicator();
            console.log('Thinking error:', data.data.message);
            // Ensure scroll after error indicator is removed
            setTimeout(() => this.scrollToBottom(), 100);
        }
    }
    
    displayMessage(messageData, sender) {
        const messagesContainer = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const senderName = sender === 'sage' ? 'Sage' : sender === 'user' ? 'You' : 'System';
        const timestamp = new Date(parseInt(messageData.timestamp)).toLocaleTimeString();
        
        // Render markdown for Sage messages
        let messageContent = messageData.message;
        if (sender === 'sage') {
            messageContent = this.renderMarkdown(messageData.message);
        }
        
        messageDiv.innerHTML = `
            <div class="message-header">${senderName}</div>
            <div class="message-content">${messageContent}</div>
            <div class="message-time">${timestamp}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        
        // Ensure scrolling happens after message content is fully rendered
        // Use multiple timing checks for reliability
        this.scrollToBottom();
        setTimeout(() => this.scrollToBottom(), 50);
        setTimeout(() => this.scrollToBottom(), 150);
        setTimeout(() => this.scrollToBottom(), 300);
    }
    
    showThinkingIndicator() {
        const messagesContainer = document.getElementById('messages');
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message sage thinking-indicator';
        thinkingDiv.id = 'thinking-indicator';
        
        const timestamp = new Date().toLocaleTimeString();
        
        thinkingDiv.innerHTML = `
            <div class="message-header">Sage</div>
            <div class="message-content">
                <div class="thinking-animation">
                    <span class="thinking-dots">
                        <span>.</span><span>.</span><span>.</span>
                    </span>
                    <span class="thinking-text">Thinking...</span>
                </div>
            </div>
            <div class="message-time">${timestamp}</div>
        `;
        
        messagesContainer.appendChild(thinkingDiv);
        this.scrollToBottom();
        
        return thinkingDiv;
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('messages-container');
        if (!messagesContainer) {
            console.log('Messages container not found');
            return;
        }
        
        // Immediate scroll attempt
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Use requestAnimationFrame to ensure DOM has updated before scrolling
        requestAnimationFrame(() => {
            const currentScrollHeight = messagesContainer.scrollHeight;
            const currentScrollTop = messagesContainer.scrollTop;
            
            // Force scroll to bottom (immediate)
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Also try smooth scroll
            messagesContainer.scrollTo({
                top: currentScrollHeight,
                behavior: 'smooth'
            });
            
            console.log(`Scroll - Height: ${currentScrollHeight}, Was: ${currentScrollTop}, Now: ${messagesContainer.scrollTop}`);
        });
        
        // Additional fallback scrolls
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
        
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 500);
    }
    
    removeThinkingIndicator() {
        const thinkingIndicator = document.getElementById('thinking-indicator');
        if (thinkingIndicator) {
            thinkingIndicator.remove();
            // Ensure scroll position is maintained after removing indicator
            setTimeout(() => this.scrollToBottom(), 10);
        }
    }
    
    updatePersonality(messageData) {
        const face = document.getElementById('sage-face');
        const emotionSpan = document.getElementById('current-emotion');
        const descriptionSpan = document.getElementById('emotion-description');
        
        if (messageData.video) {
            // Update video source and play the new video
            const source = face.querySelector('source');
            if (source) {
                // Check if this is a sleep video (either transition or direct sleep)
                const isSleepVideo = messageData.video.includes('sage-sleeps') || 
                                   messageData.video.includes('sage-blink-slow') ||
                                   (messageData.emotion && messageData.emotion.toLowerCase() === 'sleep');
                
                if (isSleepVideo) {
                    console.log(`Starting server-controlled sleep sequence: transition video - ${messageData.video}`);
                    
                    // Step 1: Play transition video (sage-sleeps.mp4) without looping
                    face.loop = false;
                    face.removeAttribute('loop');
                    
                    // Remove any existing event listeners
                    face.removeEventListener('ended', this.handleServerSleepTransition);
                    
                    // Add event listener to switch to sleep state video when transition ends
                    this.handleServerSleepTransition = () => {
                        console.log('Server sleep transition video ended - switching to sleep state video');
                        
                        // Step 2: Switch to looping sleep state video (sage-asleep.mp4)
                        source.src = '/personality/video/sage-asleep.mp4';
                        face.loop = true;
                        face.setAttribute('loop', '');
                        
                        face.load();
                        face.play().catch(error => {
                            console.log('Sleep state video play failed (server):', error);
                        });
                        
                        // Remove the transition event listener
                        face.removeEventListener('ended', this.handleServerSleepTransition);
                    };
                    
                    face.addEventListener('ended', this.handleServerSleepTransition);
                    
                    // Start with transition video
                    source.src = messageData.video;
                    face.load();
                    face.play().catch(error => {
                        console.log('Server sleep transition video play failed:', error);
                        // If transition video fails, go directly to sleep state
                        this.handleServerSleepTransition();
                    });
                } else {
                    // Handle all other videos (idle, emotions, wake, etc.)
                    face.loop = true;
                    face.setAttribute('loop', '');
                    console.log(`Video: Enabled looping for ${messageData.emotion} video - ${messageData.video}`);
                    
                    // Remove any sleep transition event listeners for non-sleep videos
                    if (this.handleServerSleepTransition) {
                        face.removeEventListener('ended', this.handleServerSleepTransition);
                        this.handleServerSleepTransition = null;
                    }
                    
                    source.src = messageData.video;
                    face.load(); // Reload the video element
                    face.play().catch(error => {
                        console.log('Video play failed:', error);
                        // Auto-play might be blocked, try to play on user interaction
                    });
                }
            }
        }
        
        if (messageData.emotion && emotionSpan) {
            emotionSpan.textContent = messageData.emotion.charAt(0).toUpperCase() + 
                                    messageData.emotion.slice(1).replace('-', ' ');
        }
        
        if (messageData.description && descriptionSpan) {
            descriptionSpan.textContent = messageData.description;
        }
        
        // Log video timing information for debugging
        if (messageData.duration) {
            console.log(`Video duration: ${messageData.duration}s, Emotion: ${messageData.emotion}, Type: ${messageData.type || 'message'}`);
        }
    }
    
    displayFileChange(data) {
        this.displayMessage({
            message: data.message,
            timestamp: data.timestamp
        }, 'system');
        
        // Could add special styling for file changes
    }
    
    displayConflictResolution(data) {
        const messagesContainer = document.getElementById('messages');
        const conflictDiv = document.createElement('div');
        conflictDiv.className = 'message system conflict';
        
        let optionsHtml = '';
        data.options.forEach((option, index) => {
            optionsHtml += `<button class="conflict-option" data-option="${index}">${option}</button>`;
        });
        
        conflictDiv.innerHTML = `
            <div class="message-header">Sage - Conflict Resolution Needed</div>
            <div class="message-content">
                ${data.message}
                <div class="conflict-options">${optionsHtml}</div>
            </div>
            <div class="message-time">${new Date(parseInt(data.timestamp)).toLocaleTimeString()}</div>
        `;
        
        messagesContainer.appendChild(conflictDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Bind option buttons
        conflictDiv.querySelectorAll('.conflict-option').forEach(button => {
            button.addEventListener('click', (e) => {
                const option = e.target.dataset.option;
                this.sendConflictResolution(data.conflict_description, option);
            });
        });
        
        this.updatePersonality(data);
    }
    
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'user_message',
                message: message
            }));
            
            this.displayMessage({
                message: message,
                timestamp: Date.now().toString()
            }, 'user');
        }
    }
    
    sendConflictResolution(conflictDescription, selectedOption) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'conflict_resolution',
                conflict_description: conflictDescription,
                selected_option: selectedOption
            }));
        }
    }
    
    bindEvents() {
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        
        sendButton.addEventListener('click', () => {
            const message = messageInput.value.trim();
            if (message) {
                this.sendMessage(message);
                messageInput.value = '';
            }
        });
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendButton.click();
            }
        });
        
        // Bind Sage toggle functionality
        const sageToggle = document.getElementById('sage-toggle');
        const toggleLabel = document.getElementById('toggle-label');
        const sageFace = document.getElementById('sage-face');
        
        sageToggle.addEventListener('change', () => {
            if (sageToggle.checked) {
                // Show Sage
                sageFace.classList.remove('hidden');
                toggleLabel.textContent = 'Hide Sage';
            } else {
                // Hide Sage
                sageFace.classList.add('hidden');
                toggleLabel.textContent = 'Show Sage';
            }
        });
        
        // Load system stats and project data periodically
        this.loadStats();
        this.loadProjects();
        this.loadAgents();
        setInterval(() => {
            this.loadStats();
            this.loadProjects();
            this.loadAgents();
        }, 30000);
        
        // Enable video interaction on first user click to handle autoplay restrictions
        document.addEventListener('click', this.enableVideoAutoplay.bind(this), { once: true });
        
        // Handle page focus/blur for sleep/wake functionality
        this.bindFocusEvents();
    }
    
    enableVideoAutoplay() {
        const face = document.getElementById('sage-face');
        if (face) {
            face.muted = true; // Ensure muted for autoplay
            face.play().catch(error => {
                console.log('Initial video play failed:', error);
            });
        }
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            this.updateStats(data);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    updateStats(data) {
        const statsContent = document.getElementById('stats-content');
        statsContent.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">Status</span>
                <span class="stat-value">${data.status}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Connections</span>
                <span class="stat-value">${data.connections}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Messages</span>
                <span class="stat-value">${data.message_history_count}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Emotions</span>
                <span class="stat-value">${data.personality.available_emotions.length}</span>
            </div>
        `;
    }
    
    bindFocusEvents() {
        // Handle page focus/blur events for sleep/wake functionality
        window.addEventListener('blur', () => {
            console.log('Page lost focus - putting Sage to sleep');
            this.putSageToSleep();
        });
        
        window.addEventListener('focus', () => {
            console.log('Page gained focus - waking Sage up');
            this.wakeSageUp();
        });
        
        // Also handle visibility change API for better browser compatibility
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log('Page became hidden - putting Sage to sleep');
                this.putSageToSleep();
            } else {
                console.log('Page became visible - waking Sage up');
                this.wakeSageUp();
            }
        });
    }
    
    async putSageToSleep() {
        try {
            const response = await fetch('/api/sleep', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            console.log('Sleep response:', data);
        } catch (error) {
            console.error('Error putting Sage to sleep:', error);
        }
    }
    
    async wakeSageUp() {
        try {
            const response = await fetch('/api/wake', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            console.log('Wake response:', data);
        } catch (error) {
            console.error('Error waking Sage up:', error);
        }
    }
    
    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();
            this.updateProjects(data.projects);
        } catch (error) {
            console.error('Error loading projects:', error);
        }
    }
    
    updateProjects(projects) {
        const projectsList = document.getElementById('monitored-projects-list');
        
        if (projects.length === 0) {
            projectsList.innerHTML = '<div class="project-item"><div class="project-info"><div class="project-name">No projects configured</div></div></div>';
            return;
        }
        
        projectsList.innerHTML = projects.map(project => `
            <div class="project-item">
                <div class="project-info">
                    <div class="project-name">${project.name}</div>
                    <div class="project-status">${project.status} • ${project.crew_config} • ${project.priority} priority</div>
                </div>
                <div class="activity-indicator">
                    <div class="spinner ${project.is_active ? '' : 'hidden'}"></div>
                    <span class="status-badge status-${project.is_active ? 'processing' : 'idle'}">
                        ${project.is_active ? 'Active' : 'Idle'}
                    </span>
                </div>
            </div>
        `).join('');
    }
    
    async loadAgents() {
        try {
            const response = await fetch('/api/agents');
            const data = await response.json();
            this.updateAgents(data.agents);
        } catch (error) {
            console.error('Error loading agents:', error);
        }
    }
    
    updateAgents(agents) {
        const agentsList = document.getElementById('agents-list');
        
        if (agents.length === 0) {
            agentsList.innerHTML = '<div class="agent-item"><div class="agent-info"><div class="agent-name">No agents configured</div></div></div>';
            return;
        }
        
        agentsList.innerHTML = agents.map(agent => `
            <div class="agent-item">
                <div class="agent-info">
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status">${agent.status}</div>
                </div>
                <div class="activity-indicator">
                    <div class="spinner ${agent.is_processing ? '' : 'hidden'}"></div>
                    <span class="status-badge status-${agent.is_processing ? 'processing' : 'idle'}">
                        ${agent.is_processing ? 'Processing' : 'Idle'}
                    </span>
                </div>
            </div>
        `).join('');
    }
}

// Initialize the UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.sageUI = new SageUI();
});