document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const messagesContainer = document.getElementById('messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const connectCalendarButton = document.getElementById('connect-calendar');
    
    // Templates
    const userMessageTemplate = document.getElementById('user-message-template');
    const assistantMessageTemplate = document.getElementById('assistant-message-template');
    const typingIndicatorTemplate = document.getElementById('typing-indicator-template');
    const reminderTemplate = document.getElementById('reminder-template');
    
    // Socket.io connection
    const socket = io();
    
    // User ID (in production, use a real user authentication system)
    const userId = 'default_user';
    
    // Auto-resize input field
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        
        // Cap maximum height
        if (this.scrollHeight > 120) {
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }
        
        // Show/hide send button based on content
        if (this.value.trim() !== '') {
            sendButton.classList.add('active');
        } else {
            sendButton.classList.remove('active');
        }
    });
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key (but allow Shift+Enter for new line)
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Connect Google Calendar
    connectCalendarButton.addEventListener('click', connectCalendar);
    
    // Socket events
    socket.on('connect', function() {
        console.log('Connected to server');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
    });
    
    socket.on('response', function(data) {
        if (data.user_id === userId) {
            addMessage('assistant', data.response);
            // Remove typing indicator if present
            const typingIndicator = document.querySelector('.typing');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
    });
    
    socket.on('reminder', function(data) {
        if (data.user_id === userId) {
            addReminder(data.message, data.event);
        }
    });
    
    // Functions
    function sendMessage() {
        const message = userInput.value.trim();
        
        if (message) {
            // Add user message to chat
            addMessage('user', message);
            
            // Show typing indicator
            addTypingIndicator();
            
            // Send message to server
            socket.emit('message', {
                message: message,
                user_id: userId
            });
            
            // Clear input
            userInput.value = '';
            userInput.style.height = 'auto';
            
            // Scroll to bottom
            scrollToBottom();
        }
    }
    
    function addMessage(sender, content) {
        // Use appropriate template
        const template = sender === 'user' ? userMessageTemplate : assistantMessageTemplate;
        
        // Clone template
        const messageElement = document.importNode(template.content, true);
        
        // Set message content
        messageElement.querySelector('p').textContent = content;
        
        // Add to chat
        messagesContainer.appendChild(messageElement);
        
        // Scroll to bottom
        scrollToBottom();
    }
    
    function addTypingIndicator() {
        // Use typing indicator template
        const typingElement = document.importNode(typingIndicatorTemplate.content, true);
        
        // Add to chat
        messagesContainer.appendChild(typingElement);
        
        // Scroll to bottom
        scrollToBottom();
    }
    
    function addReminder(message, event) {
        // Use reminder template
        const reminderElement = document.importNode(reminderTemplate.content, true);
        
        // Set reminder content
        reminderElement.querySelector('.reminder-content').textContent = message;
        
        // Add event listeners to buttons
        const acceptBtn = reminderElement.querySelector('.reminder-btn.accept');
        const declineBtn = reminderElement.querySelector('.reminder-btn.decline');
        const reminderDiv = reminderElement.querySelector('.reminder');
        
        acceptBtn.addEventListener('click', function() {
            // Remove reminder
            reminderDiv.remove();
            
            // Add user message about ordering food
            const eventTime = new Date(event.start.dateTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            const orderMessage = `I want to order food before my ${event.summary} at ${eventTime}`;
            addMessage('user', orderMessage);
            
            // Show typing indicator
            addTypingIndicator();
            
            // Send message to server
            socket.emit('message', {
                message: orderMessage,
                user_id: userId
            });
        });
        
        declineBtn.addEventListener('click', function() {
            // Remove reminder
            reminderDiv.remove();
        });
        
        // Add to chat
        messagesContainer.appendChild(reminderElement);
        
        // Scroll to bottom
        scrollToBottom();
    }
    
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Add visual feedback when sending messages
    sendButton.addEventListener('mousedown', function() {
        this.style.transform = 'translateY(0)';
    });
    
    sendButton.addEventListener('mouseup', function() {
        this.style.transform = 'translateY(-2px)';
    });
    
    // Add animation when receiving messages
    socket.on('response', function(data) {
        if (data.user_id === userId) {
            // Add a slight delay to make it feel more natural
            setTimeout(() => {
                addMessage('assistant', data.response);
                // Remove typing indicator if present
                const typingIndicator = document.querySelector('.typing');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            }, 500);
        }
    });
    
    function connectCalendar() {
        // Add a subtle loading animation to the button
        const originalButtonContent = connectCalendarButton.innerHTML;
        connectCalendarButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting...';
        connectCalendarButton.disabled = true;
        connectCalendarButton.style.opacity = '0.7';
        
        // Request Google Calendar authorization URL
        fetch('/api/authorize/google')
            .then(response => response.json())
            .then(data => {
                // Open authorization URL in a new tab
                window.open(data.auth_url, '_blank');
                
                // Add system message
                addMessage('assistant', 'I\'ve opened Google Calendar authorization in a new tab. Please complete the authorization process to allow me to access your calendar.');
                
                // Check auth status periodically
                const checkInterval = setInterval(() => {
                    fetch('/api/auth/status')
                        .then(response => response.json())
                        .then(status => {
                            if (status.authenticated) {
                                clearInterval(checkInterval);
                                // Update button to show connected status
                                connectCalendarButton.innerHTML = '<i class="fas fa-check"></i> Connected';
                                connectCalendarButton.style.backgroundColor = '#4CAF50';
                                connectCalendarButton.style.color = 'white';
                                connectCalendarButton.disabled = true;
                                connectCalendarButton.style.opacity = '1';
                                
                                // Add success message
                                addMessage('assistant', 'Successfully connected to your Google Calendar! I\'ll now monitor your schedule and suggest food orders at appropriate times.');
                            }
                        })
                        .catch(error => {
                            console.error('Error checking auth status:', error);
                        });
                }, 5000); // Check every 5 seconds
                
                // Stop checking after 2 minutes (in case user never completes auth)
                setTimeout(() => {
                    clearInterval(checkInterval);
                    if (connectCalendarButton.innerHTML.includes('Connecting')) {
                        connectCalendarButton.innerHTML = originalButtonContent;
                        connectCalendarButton.disabled = false;
                        connectCalendarButton.style.opacity = '1';
                    }
                }, 120000);
            })
            .catch(error => {
                console.error('Error connecting to Google Calendar:', error);
                connectCalendarButton.innerHTML = originalButtonContent;
                connectCalendarButton.disabled = false;
                connectCalendarButton.style.opacity = '1';
                addMessage('assistant', 'Sorry, I encountered an error connecting to Google Calendar. Please try again later.');
            });
    }
});
