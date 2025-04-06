document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const messagesContainer = document.getElementById('messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const connectCalendarButton = document.getElementById('connect-calendar');
    const logoutButton = document.getElementById('logout-btn');
    
    // Calendar UI elements
    const calendarToggle = document.getElementById('calendar-toggle');
    const calendarContainer = document.getElementById('calendar-container');
    const calendarClose = document.getElementById('calendar-close');
    const calendarEvents = document.getElementById('calendar-events');
    
    // Add calendar range selector
    const calendarHeader = document.querySelector('.calendar-header');
    let calendarRangeSelector = document.createElement('div');
    calendarRangeSelector.className = 'calendar-range-selector';
    calendarRangeSelector.innerHTML = `
        <select id="calendar-range">
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="upcoming">Next 7 Days</option>
        </select>
    `;
    calendarHeader.appendChild(calendarRangeSelector);

    // Get the calendar range dropdown
    const calendarRange = document.getElementById('calendar-range');
    
    // Templates
    const userMessageTemplate = document.getElementById('user-message-template');
    const assistantMessageTemplate = document.getElementById('assistant-message-template');
    const typingIndicatorTemplate = document.getElementById('typing-indicator-template');
    const reminderTemplate = document.getElementById('reminder-template');
    const calendarEventTemplate = document.getElementById('calendar-event-template');
    
    // Socket.io connection
    const socket = io();
    
    // User ID (in production, use a real user authentication system)
    const userId = 'default_user';
    
    // Calendar state
    let calendarConnected = false;
    let calendarData = null;
    let calendarFetchInterval = null;
    
    // Check if we should show the login overlay 
    // Note: requireLogin is a variable set in the HTML by Flask
    let requireLogin = false; 
    // The template injects the require_login variable when rendering
    
    // Function to generate a unique ID
    function generateUniqueId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Initially hide calendar toggle until authenticated
    if (calendarToggle) {
        calendarToggle.style.display = 'none';
    }
    
    // Update UI based on authentication status
    function updateLoginState(isAuthenticated) {
        if (isAuthenticated) {
            // User is authenticated
            if (connectCalendarButton) {
                connectCalendarButton.innerHTML = '<i class="fas fa-check"></i> Connected';
                connectCalendarButton.style.backgroundColor = '#4CAF50';
                connectCalendarButton.style.color = 'white';
                connectCalendarButton.disabled = true;
            }
            if (calendarToggle) {
                calendarToggle.style.display = 'flex';
            }
        } else {
            // User is not authenticated
            if (connectCalendarButton) {
                connectCalendarButton.innerHTML = '<i class="fas fa-calendar"></i> Connect Calendar';
                connectCalendarButton.style.backgroundColor = '';
                connectCalendarButton.style.color = '';
                connectCalendarButton.disabled = false;
            }
            if (calendarToggle) {
                calendarToggle.style.display = 'none';
            }
        }
    }
    
    // Check authentication status on page load
    function checkAuthStatus() {
        fetch(`/api/auth/status?user_id=${userId}`)
            .then(response => response.json())
            .then(status => {
                calendarConnected = status.authenticated;
                updateLoginState(status.authenticated);
                
                if (status.authenticated) {
                    // Start fetching calendar events periodically
                    fetchCalendarEvents();
                    
                    if (calendarFetchInterval) {
                        clearInterval(calendarFetchInterval);
                    }
                    
                    calendarFetchInterval = setInterval(fetchCalendarEvents, 5 * 60 * 1000); // Refresh every 5 minutes
                } else {
                    // Clear any existing fetch interval
                    if (calendarFetchInterval) {
                        clearInterval(calendarFetchInterval);
                        calendarFetchInterval = null;
                    }
                }
            })
            .catch(error => {
                console.error('Error checking auth status:', error);
            });
    }
    
    // Check auth status on page load
    checkAuthStatus();
    
    // Handle logout button click
    if (logoutButton) {
        logoutButton.addEventListener('click', function() {
            // Clear Google Calendar credentials
            fetch('/api/auth/logout', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI
                    updateLoginState(false);
                    calendarConnected = false;
                    
                    // Clear calendar data and stop fetching
                    if (calendarFetchInterval) {
                        clearInterval(calendarFetchInterval);
                        calendarFetchInterval = null;
                    }
                    
                    // Reset calendar UI
                    if (calendarEvents) {
                        calendarEvents.innerHTML = `
                            <div class="no-events">
                                <i class="fas fa-calendar-day fa-3x" style="color: #e0e0e0; margin-bottom: 15px;"></i>
                                <p>Connect your calendar to see your events</p>
                            </div>
                        `;
                    }
                    
                    // Add logout message
                    addMessage('assistant', 'You have been logged out. Please connect your Google Calendar again to use all features.');
                }
            })
            .catch(error => {
                console.error('Error logging out:', error);
            });
        });
    }
    
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

    // Function to add food options
    function addFoodOptions() {
        const foodOptionsTemplate = document.getElementById('food-options-template');
        const foodOptions = foodOptionsTemplate.content.cloneNode(true);
        
        // Set food item 1 details
        const card1 = foodOptions.querySelector('.food-card:first-child');
        card1.querySelector('img').src = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c';
        card1.querySelector('h3').textContent = 'Grilled Chicken Caesar Salad';
        card1.querySelector('p em').textContent = 'Fresh & Co';
        card1.querySelector('.price').textContent = '$12.99';
        
        // Set food item 2 details
        const card2 = foodOptions.querySelector('.food-card:last-child');
        card2.querySelector('img').src = 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c';
        card2.querySelector('h3').textContent = 'Spicy Tuna Roll Combo';
        card2.querySelector('p em').textContent = 'Sushi Palace';
        card2.querySelector('.price').textContent = '$15.99';
        
        // Add click handlers for the buttons
        card1.querySelector('button').addEventListener('click', () => {
            sendMessage('I would like to order the Grilled Chicken Caesar Salad from Fresh & Co');
        });
        
        card2.querySelector('button').addEventListener('click', () => {
            sendMessage('I would like to order the Spicy Tuna Roll Combo from Sushi Palace');
        });
        
        // Add the food options to the messages container
        messagesContainer.appendChild(foodOptions);
        scrollToBottom();
    }
    
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
    
    // Calendar View Toggle
    calendarToggle.addEventListener('click', toggleCalendarView);
    calendarClose.addEventListener('click', toggleCalendarView);
    
    // Function to toggle calendar view
    function toggleCalendarView() {
        calendarContainer.classList.toggle('active');
        
        // If calendar is now visible and we're connected, fetch events
        if (calendarContainer.classList.contains('active') && calendarConnected) {
            fetchCalendarEvents();
        }
    }
    
    // Listen for calendar range changes
    calendarRange.addEventListener('change', function() {
        fetchCalendarEvents();
    });
    
    // Track previous messages to avoid duplicates
    const messageHistory = new Set();
    
    // Socket events
    socket.on('connect', function() {
        console.log('Connected to server');
        
        // Check auth status when connected
        checkAuthStatus();
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
    });
    
    // Set to track processed message IDs to prevent duplicates
    const processedMessageIds = new Set();
    
    socket.on('response', function(data) {
        console.log('Received response:', data);
        
        if (data.user_id === userId) {
            // Check if this is a message with an ID we can track
            if (data.message_id) {
                // If we've already processed this exact message ID, ignore it
                if (processedMessageIds.has(data.message_id)) {
                    console.log('Ignoring duplicate message with ID:', data.message_id);
                    return;
                }
                
                // Mark this message as processed
                processedMessageIds.add(data.message_id);
                
                // Prevent set from growing too large
                if (processedMessageIds.size > 100) {
                    // Convert to array, keep only the most recent 50 IDs
                    const recentIds = Array.from(processedMessageIds).slice(-50);
                    processedMessageIds.clear();
                    recentIds.forEach(id => processedMessageIds.add(id));
                }
            } else {
                // For messages without IDs, use content-based deduplication (fallback)
                const contentId = `content_${data.response.substring(0, 50)}`;
                if (messageHistory.has(contentId)) {
                    console.log('Duplicate content prevented:', contentId);
                    return;
                }
                messageHistory.add(contentId);
            }
            
            // Add the message to the UI
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
            
            // Send message to server with a unique message ID
            const messageId = generateUniqueId();
            socket.emit('message', {
                message: message,
                user_id: userId,
                message_id: messageId
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
    
    // Fetch calendar events
    function fetchCalendarEvents() {
        if (!calendarConnected) return;
        
        const range = calendarRange.value;
        
        fetch(`/api/calendar/events?user_id=${userId}&range=${range}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to fetch calendar events');
                    });
                }
                return response.json();
            })
            .then(data => {
                calendarData = data;
                renderCalendarEvents();
            })
            .catch(error => {
                console.error('Error fetching calendar events:', error);
                calendarEvents.innerHTML = `
                    <div class="no-events">
                        <i class="fas fa-exclamation-circle fa-3x" style="color: #e74c3c; margin-bottom: 15px;"></i>
                        <p>Failed to load calendar events</p>
                        <p style="font-size: 0.9rem; margin-top: 10px;">${error.message}</p>
                    </div>
                `;
            });
    }
    
    // Render calendar events
    function renderCalendarEvents() {
        if (!calendarData || !calendarData.events || calendarData.events.length === 0) {
            calendarEvents.innerHTML = `
                <div class="no-events">
                    <i class="fas fa-calendar-day fa-3x" style="color: #e0e0e0; margin-bottom: 15px;"></i>
                    <p>No events for ${calendarData ? calendarData.date : 'today'}</p>
                </div>
            `;
            return;
        }
        
        // Clear current events
        calendarEvents.innerHTML = '';
        
        // For multi-day views, render events grouped by date
        if (calendarRange.value !== 'today' && calendarData.eventsByDate) {
            calendarData.eventsByDate.forEach(dateGroup => {
                // Add date header
                const dateHeader = document.createElement('div');
                dateHeader.className = 'calendar-date';
                dateHeader.textContent = dateGroup.dateFormatted;
                calendarEvents.appendChild(dateHeader);
                
                // Add events for this date
                dateGroup.events.forEach(event => {
                    appendEventElement(event);
                });
            });
        } else {
            // Single day view - just add the date header once
            const dateHeader = document.createElement('div');
            dateHeader.className = 'calendar-date';
            dateHeader.textContent = calendarData.date;
            calendarEvents.appendChild(dateHeader);
            
            // Add all events
            calendarData.events.forEach(event => {
                appendEventElement(event);
            });
        }
    }
    
    // Helper function to append an event element
    function appendEventElement(event) {
        const eventElement = document.importNode(calendarEventTemplate.content, true);
        
        // Set event details
        const timeElement = eventElement.querySelector('.calendar-event-time');
        timeElement.textContent = event.timeRange || event.start.formatted;
        
        const titleElement = eventElement.querySelector('.calendar-event-title');
        titleElement.textContent = event.summary;
        
        const locationElement = eventElement.querySelector('.calendar-event-location');
        locationElement.textContent = event.location || '';
        
        // Add to calendar events container
        calendarEvents.appendChild(eventElement);
    }
    
    function connectCalendar() {
        // Add a subtle loading animation to the button
        const originalButtonContent = connectCalendarButton.innerHTML;
        connectCalendarButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting...';
        connectCalendarButton.disabled = true;
        connectCalendarButton.style.opacity = '0.7';
        
        // Request Google Calendar authorization URL with user ID
        fetch(`/api/authorize/google?user_id=${userId}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to connect to Google Calendar');
                    });
                }
                return response.json();
            })
            .then(data => {
                // If there's an error message in the response, throw it
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Open authorization URL in a new window
                window.open(data.auth_url, '_blank', 'width=600,height=700');
                
                // Add system message
                addMessage('assistant', 'I\'ve opened Google Calendar authorization in a new window. Please complete the authorization process to connect your calendar. This will allow me to suggest food orders before your meetings.');
                
                // Check auth status periodically
                const checkInterval = setInterval(() => {
                    fetch(`/api/auth/status?user_id=${userId}`)
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
                                
                                // Set calendar as connected
                                calendarConnected = true;
                                
                                // Show calendar toggle button
                                calendarToggle.style.display = 'flex';
                                
                                // Fetch calendar events right away
                                fetchCalendarEvents();
                                
                                // Start periodic fetch
                                if (calendarFetchInterval) {
                                    clearInterval(calendarFetchInterval);
                                }
                                
                                calendarFetchInterval = setInterval(fetchCalendarEvents, 5 * 60 * 1000); // Refresh every 5 minutes
                                
                                // Add success message
                                addMessage('assistant', 'Successfully connected to your Google Calendar! I\'ll now monitor your schedule and suggest food orders at appropriate times, like before lunch meetings.');
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
                addMessage('assistant', `Sorry, I encountered an error connecting to Google Calendar: ${error.message}`);
            });
    }
});
