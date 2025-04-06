import asyncio

from api.browser import find_2_lunch_options, order_food
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import json
import datetime
from dateutil import parser
from google_calendar import GoogleCalendarAPI
from dotenv import load_dotenv
import threading
import time
import requests

# Load environment variables
load_dotenv(override=True) # Force load/override from .env

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Highrise AI client using OpenAI compatible API
highrise_api_key = os.getenv('HIGHRISE_API_KEY')
highrise_base_url = os.getenv('HIGHRISE_BASE_URL', 'https://cloud.highrise.ai/highrise-api/maas/ai')
highrise_model = os.getenv('HIGHRISE_MODEL', 'DeepSeek-R1')

# No OpenAI client needed - using direct requests to Highrise API

# Import Blueprints
from api.doordash_routes import doordash_bp

# Register Blueprints
app.register_blueprint(doordash_bp)

# Initialize Google Calendar API
calendar_api = GoogleCalendarAPI()

# Global variables
user_state = {}
active_reminders = {}

# Track message ids to prevent duplicates
message_ids = set()

@app.route('/')
def index():
    # No longer requiring login overlay
    return render_template('index.html')

# Removing duplicate API endpoint - using only WebSockets now
# @app.route('/api/message', methods=['POST'])
# def receive_message():
#     data = request.json
#     user_message = data.get('message', '')
#     user_id = data.get('user_id', 'default_user')
#     
#     # Get response from LLM
#     response = generate_response(user_message, user_id)
#     
#     return jsonify({'response': response})

@socketio.on('order')
def handle_order(data):
    user_id = data.get('user_id', 'default_user')
    message_id = data.get('message_id', '')

    # print(f"Order received: {data['name']} from {data['restaurant']}")
    # print(f"Order URL: {data['url']}")
    asyncio.run(order_food(data['restaurant_url'], data['item_name']))

    emit('response',
         {'response': "Your food was ordered", 'user_id': user_id, 'message_id': message_id},
         room=request.sid)


@socketio.on('connect')
def handle_connect():
    # Create a room with the session ID to ensure message isolation
    print('Client connected')
    join_room(request.sid)
    print(f"Client {request.sid} joined their own room")
    
    # Send initial welcome message
    # initial_message = """Hello! It's lunch time"""
    
    # emit('response', 
    #      {'response': initial_message, 'user_id': 'default_user', 'message_id': 'initial'},
    #      room=request.sid)
    
    # emit('response', 
    # {'response': "here are your lunch options", 'user_id': 'default_user', 'message_id': 'show_food_options'},
    # room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    leave_room(request.sid)
    print(f"Client {request.sid} disconnected")

@socketio.on('message')
def handle_message(data):
    user_message = data.get('message', '')
    user_id = data.get('user_id', 'default_user')
    message_id = data.get('message_id', '')
    
    # Check if we've already processed this message to prevent duplicates
    if message_id and message_id in message_ids:
        print(f"Ignoring duplicate message with ID: {message_id}")
        return
    
    print(f"Processing message from {user_id} in room {request.sid}: {user_message[:50]}...")
        
    # Add message_id to our tracking set
    if message_id:
        message_ids.add(message_id)
        # Limit size of the set to avoid memory issues
        if len(message_ids) > 1000:
            message_ids.clear()
    
    # Get response from LLM
    response = generate_response(user_message, user_id)
    
    # Send response back only to the requesting client using their room
    emit('response', 
         {'response': response, 'user_id': user_id, 'message_id': message_id},
         room=request.sid)

def generate_response(message, user_id):
    try:
        # Create a system prompt that defines the assistant's role
        system_prompt = """You are ExecuMate, an AI Executive Assistant that helps users manage their tasks, including ordering food.
        Your primary responsibilities are:
        1. Understand the user's preferences, schedule, and priorities
        2. Suggest restaurants and meal options based on the user's schedule
        3. Place orders on behalf of the user when requested
        4. Be conversational, professional, and helpful
        
        Respond in a friendly, professional manner appropriate for an executive assistant.
        """
        
        # Get conversation history or initialize if it doesn't exist
        if user_id not in user_state:
            user_state[user_id] = {
                "conversation_history": []
            }
        
        # Add user message to history
        user_state[user_id]["conversation_history"].append({"role": "user", "content": message})
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(user_state[user_id]["conversation_history"][-10:])  # Keep last 10 messages
        
        # Get response from Highrise AI using direct requests
        try:
            # Create headers and payload
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {highrise_api_key}'
            }
            
            payload = {
                'model': "Meta-Llama-31-70B-Instruct",
                'messages': messages,
                'max_tokens': 1028,
                'temperature': 0.5,
                'top_p': 0.5,
                'stream': False  # Explicitly disable streaming to get a complete response
            }
            
            # Send request to Highrise API
            chat_endpoint = f"{highrise_base_url}/chat/completions"
            
            response = requests.post(chat_endpoint, json=payload, headers=headers)
            
            # Parse the response
            # print(f"Response headers: {response.headers}")
            
            # Safely check response content
            response_text = response.text
            # print(f"response text: {response_text}")
            
            if response.status_code == 200:
                # Parse the Highrise API response format
                try:
                    response_data = response.json()
                    # print(f"Response data structure: {json.dumps(response_data, indent=2)[:200]}...")
                    
                    # Extract message from the correct response structure
                    if 'data' in response_data:
                        data = response_data['data']
                        if 'choices' in data and len(data['choices']) > 0:
                            choice = data['choices'][0]
                            if 'message' in choice and 'content' in choice['message']:
                                assistant_message = choice['message']['content']
                            else:
                                assistant_message = "Response missing message content"
                        else:
                            assistant_message = "Response missing choices"
                    else:
                        # Fallback for other response formats
                        if 'choices' in response_data and len(response_data['choices']) > 0:
                            choice = response_data['choices'][0]
                            if 'message' in choice and 'content' in choice['message']:
                                assistant_message = choice['message']['content']
                            else:
                                assistant_message = "Response missing message content"
                        else:
                            assistant_message = "Response missing expected data structure"
                except json.JSONDecodeError as json_err:
                    assistant_message = f"Error parsing JSON response: {str(json_err)}"
            else:
                assistant_message = f"Server error: {response.status_code} - {response_text[:100]}"
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error generating response: {str(e)}\n{error_trace}")
            assistant_message = f"Sorry, I encountered an error: {str(e)}"
        
        # Add assistant message to history
        user_state[user_id]["conversation_history"].append({"role": "assistant", "content": assistant_message})

        # assistant_message = assistant_message.split("</think>")[-1]
        
        return assistant_message
    
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm having trouble processing your request right now. Please try again later."

def check_calendar_and_notify():
    """Background task to check calendar and send food ordering reminders"""
    
    # TESTING: Set this to True to enable test mode
    test_mode = False  # Changed to False by default, will be enabled conditionally
    # TESTING: When test_mode is True, these times will be used instead of real time
    test_current_time = datetime.time(12, 30)  # 12:30 PM for testing lunch time
    # test_current_time = datetime.time(18, 0)  # 6:00 PM for testing dinner time
    
    # DEBUG message to indicate test mode is active
    if test_mode:
        print("\n\n==== TEST MODE IS ACTIVE ====")
        print(f"Using test time: {test_current_time}")
        print("Will forcibly send test reminders")
        print("==== TEST MODE IS ACTIVE ====\n\n")
    
    # Force a test reminder on startup
    if test_mode:
        try:
            test_reminder_message = "[TEST MODE] This is a test reminder to verify notifications are working."
            # Send to all connected users
            socketio.emit('reminder', {
                'message': test_reminder_message,
                'user_id': 'default_user',
                'event': {'summary': 'Test Reminder', 'start': {'dateTime': datetime.datetime.now().isoformat()}}
            })
            print(f"SENT INITIAL TEST REMINDER: {test_reminder_message}")
        except Exception as e:
            print(f"ERROR sending test reminder: {e}")
    
    while True:
        try:
            # Get current time
            now = datetime.datetime.now()
            print(f"Calendar check at {now.strftime('%H:%M:%S')}")
            
            # Check if there are any users with calendar credentials
            users_with_credentials = False
            
            # For each user
            for user_id in user_state:
                print(f"Checking calendar for user {user_id}")
                
                # Check if we have calendar access for this user
                if calendar_api.has_credentials(user_id):
                    users_with_credentials = True
                    print(f"User {user_id} has calendar credentials")
                    # Get events for today
                    events = calendar_api.get_todays_events(user_id)
                    print(f"Found {len(events)} events for today")
                    
                    # Define meal time ranges
                    lunch_start = datetime.time(11, 0)  # 11:00 AM
                    lunch_end = datetime.time(14, 0)    # 2:00 PM
                    dinner_start = datetime.time(17, 0) # 5:00 PM
                    dinner_end = datetime.time(20, 0)   # 8:00 PM
                    
                    # Check for upcoming meal time meetings
                    for event in events:
                        event_id = event.get('id')
                        print(f"Processing event: {event.get('summary', 'Unnamed event')}")
                        
                        # Skip all-day events or events without start times
                        if 'dateTime' not in event.get('start', {}):
                            print("Skipping all-day event")
                            continue
                            
                        start_time = parser.parse(event.get('start', {}).get('dateTime'))
                        print(f"Event starts at: {start_time}")
                        
                        # Skip events that have already ended
                        if start_time < now:
                            print("Skipping past event")
                            continue
                        
                        # Get the event's local time values
                        event_time = start_time.time()
                        
                        # Determine if this is during a meal time
                        is_lunch_time = lunch_start <= event_time <= lunch_end
                        is_dinner_time = dinner_start <= event_time <= dinner_end
                        is_meal_time = is_lunch_time or is_dinner_time
                        
                        print(f"Meal time check: lunch={is_lunch_time}, dinner={is_dinner_time}, any={is_meal_time}")
                        
                        # Check if this is a meal time event and we haven't reminded yet
                        reminder_key = f"{user_id}_{event_id}"
                        
                        if is_meal_time and reminder_key not in active_reminders:
                            print(f"Need to send reminder for event: {event.get('summary')}")
                            # Calculate reminder time (1 hour before event)
                            reminder_time = start_time - datetime.timedelta(hours=1)
                            
                            # If it's time to remind
                            if now >= reminder_time and now <= start_time:
                                # Create reminder message
                                event_name = event.get('summary', 'your meeting')
                                event_time_str = start_time.strftime("%I:%M %p")
                                meal_type = "lunch" if is_lunch_time else "dinner"
                                reminder_message = f"I noticed you have {event_name} at {event_time_str}. Would you like to order {meal_type} before your meeting starts?"
                                
                                print(f"Sending reminder: {reminder_message}")
                                # Send reminder through socket
                                socketio.emit('reminder', {
                                    'message': reminder_message,
                                    'user_id': user_id,
                                    'event': event
                                })
                                
                                # Mark as reminded
                                active_reminders[reminder_key] = now
                                
                                # Log that we sent a reminder
                                print(f"Sent {meal_type} reminder for event {event_name} at {event_time_str}")
                    
                    # Also check for general meal times when no meetings but user might want to eat
                    current_time = now.time()
                    
                    # For general mealtime reminders, we use a different key format
                    general_lunch_key = f"{user_id}_general_lunch_{now.strftime('%Y-%m-%d')}"
                    general_dinner_key = f"{user_id}_general_dinner_{now.strftime('%Y-%m-%d')}"
                    
                    # Check if it's around lunchtime (11:30 AM) and we haven't reminded yet
                    lunch_time_check = datetime.time(11, 30) <= current_time <= datetime.time(11, 45)
                    
                    if lunch_time_check and general_lunch_key not in active_reminders:
                        # Check if user has any meetings during lunch hours
                        has_lunch_meetings = any(
                            lunch_start <= parser.parse(event.get('start', {}).get('dateTime', '2099-01-01T00:00:00')).time() <= lunch_end
                            for event in events if 'dateTime' in event.get('start', {})
                        )
                        
                        # If no lunch meetings, send a general lunch reminder
                        if not has_lunch_meetings:
                            reminder_message = "It's almost lunchtime. Would you like me to suggest some food options for delivery?"
                            
                            print(f"Sending general lunch reminder: {reminder_message}")
                            socketio.emit('reminder', {
                                'message': reminder_message,
                                'user_id': user_id,
                                'event': {'summary': 'Lunch Break', 'start': {'dateTime': (now + datetime.timedelta(minutes=30)).isoformat()}}
                            })
                            
                            # Mark as reminded
                            active_reminders[general_lunch_key] = now
                            print("Sent general lunch reminder")
                    
                    # Similar check for dinner time
                    dinner_time_check = datetime.time(17, 45) <= current_time <= datetime.time(18, 0)
                        
                    if dinner_time_check and general_dinner_key not in active_reminders:
                        # Check if user has any meetings during dinner hours
                        has_dinner_meetings = any(
                            dinner_start <= parser.parse(event.get('start', {}).get('dateTime', '2099-01-01T00:00:00')).time() <= dinner_end
                            for event in events if 'dateTime' in event.get('start', {})
                        )
                        
                        # If no dinner meetings, send a general dinner reminder
                        if not has_dinner_meetings:
                            reminder_message = "It's approaching dinner time. Would you like me to suggest some food options for delivery?"
                            
                            print(f"Sending general dinner reminder: {reminder_message}")
                            socketio.emit('reminder', {
                                'message': reminder_message,
                                'user_id': user_id,
                                'event': {'summary': 'Dinner Time', 'start': {'dateTime': (now + datetime.timedelta(minutes=15)).isoformat()}}
                            })
                            
                            # Mark as reminded
                            active_reminders[general_dinner_key] = now
                            print("Sent general dinner reminder")
                else:
                    print(f"User {user_id} does not have calendar credentials")
            
            # If no users have credentials, enable test mode temporarily
            if not users_with_credentials and len(user_state) > 0:
                print("No users have calendar credentials, activating test mode temporarily")
                # Use test mode until real calendar credentials are available
                test_mode = True
                
                for user_id in user_state:
                    # Create a fake event for testing
                    fake_event = {
                        'id': 'fake_test_event_' + str(int(time.time())),
                        'summary': 'Test Meeting',
                        'start': {
                            'dateTime': (datetime.datetime.combine(now.date(), test_current_time) + 
                                        datetime.timedelta(hours=1)).isoformat()
                        }
                    }

                    items = []
                    # Send test reminder
                    ##### DON't USE
                    test_meal_type = "lunch" if test_current_time.hour < 15 else "dinner"
                    test_reminder_message = f"[TEST MODE] It's time to order {test_meal_type}! I found two options for you: {items}. Would you like to see the menus?"
                    
                    socketio.emit('reminder', {
                        'message': test_reminder_message,
                        'user_id': user_id,
                        'event': fake_event
                    })
                    
                    # Only send once per 5 minutes per user
                    test_reminder_key = f"{user_id}_test_reminder_{now.strftime('%Y-%m-%d_%H')}"
                    if test_reminder_key not in active_reminders:
                        active_reminders[test_reminder_key] = now
                        print(f"Sent test reminder to {user_id}")
            else:
                test_mode = False
                
            # Clean up old reminders (more than 3 hours old)
            for key in list(active_reminders.keys()):
                if (now - active_reminders[key]) > datetime.timedelta(hours=3):
                    del active_reminders[key]
                        
        except Exception as e:
            print(f"Error in calendar checking: {e}")
            import traceback
            traceback.print_exc()
        
        # Sleep interval
        if test_mode:
            print("TESTING MODE: Checking calendar every 60 seconds...")
            time.sleep(60)  # Check every minute in test mode
        else:
            # Sleep for 5 minutes before checking again in normal mode
            time.sleep(300)

@app.route('/api/authorize/google', methods=['GET'])
def authorize_google():
    user_id = request.args.get('user_id', 'default_user')
    
    try:
        auth_url = calendar_api.get_authorization_url(user_id)
        return jsonify({'auth_url': auth_url})
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Unexpected error: {str(e)}"}), 500

@app.route('/api/callback/google', methods=['GET'])
def google_callback():
    code = request.args.get('code')
    user_id = request.args.get('state', 'default_user')
    calendar_api.exchange_code_for_token(code, user_id)
    
    # Schedule a welcome reminder 10 seconds after authentication
    def send_welcome_reminder():
        # Wait 10 seconds
        time.sleep(7)
        res = []

        try:
            # Get the user's calendar events
            events = calendar_api.get_todays_events(user_id)
            print(events)
            
            # Current time
            now = datetime.datetime.now()
            current_time_str = now.strftime("%I:%M %p")
            
            # Define lunch time range
            lunch_start = datetime.time(11, 0)
            lunch_end = datetime.time(14, 0)
            
            # Look for meetings during lunch hours
            lunch_meetings = []
            for event in events:
                if 'dateTime' in event.get('start', {}):
                    start_time = parser.parse(event.get('start', {}).get('dateTime'))
                    
                    # Check if event is today
                    if start_time.date() == now.date():
                        # Check if event is during lunch hours
                        event_time = start_time.time()
                        if lunch_start <= event_time <= lunch_end:
                            lunch_meetings.append(event)
            
            # Create welcome message based on actual calendar
            if lunch_meetings:

                res = asyncio.run(find_2_lunch_options())["menu_items"]
                items = ",".join([item.get("item_name") for item in res])

                # Sort meetings by start time
                lunch_meetings.sort(key=lambda x: parser.parse(x.get('start', {}).get('dateTime')))
                
                # Get time range of meetings
                first_meeting = lunch_meetings[0]
                last_meeting = lunch_meetings[-1]
                first_time = parser.parse(first_meeting.get('start', {}).get('dateTime'))
                last_time = parser.parse(last_meeting.get('start', {}).get('dateTime'))
                
                # Format meeting time range
                first_time_str = first_time.strftime("%I:%M %p")
                last_time_str = last_time.strftime("%I:%M %p")
                meeting_time_str = f"{first_time_str} to {last_time_str}"
                
                # Meeting description
                if len(lunch_meetings) > 1:
                    meeting_desc = f"back-to-back meetings between {meeting_time_str}"
                else:
                    meeting_desc = f"a meeting at {first_time_str}"
                
                welcome_message = f"It's 11:00 AM, I noticed you have {meeting_desc}. Time to order food! I found two options for you: {items}. Would you like to see the menus?"
                event = lunch_meetings[0]  # Use the first meeting as the reference event
            else:
                # No lunch meetings found, create a generic message
                current_time_str = "11:00 AM"
                meeting_time_str = "11:30 AM to 12:30 PM"
                welcome_message = f"It's {current_time_str}, I can help you order food for lunch today. I recommend Chipotle and Sweetgreen. Would you like to see the menus?"
                
                # Create a simulated calendar event
                now = datetime.datetime.now()
                meeting_start = now.replace(hour=11, minute=30, second=0)
                meeting_end = now.replace(hour=12, minute=30, second=0)
                event = {
                    'id': 'welcome_event',
                    'summary': 'Lunch Break',
                    'start': {
                        'dateTime': meeting_start.isoformat()
                    },
                    'end': {
                        'dateTime': meeting_end.isoformat()
                    }
                }
            
            # Send the welcome reminder
            payload = {
                'message': welcome_message,
                'user_id': user_id,
                'event': event,
            }

            if len(res) > 0:
                payload['food_options'] = res

            socketio.emit('reminder', payload)

            print(f"Sent welcome food reminder to {user_id}")
            
        except Exception as e:
            print(f"Error sending welcome reminder: {e}")
            import traceback
            traceback.print_exc()
    
    # Start the welcome reminder thread
    welcome_thread = threading.Thread(target=send_welcome_reminder)
    welcome_thread.daemon = True
    welcome_thread.start()
    
    return render_template('callback_success.html')

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    user_id = request.args.get('user_id', 'default_user')
    is_authenticated = calendar_api.has_credentials(user_id)
    return jsonify({'authenticated': is_authenticated})

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    user_id = request.args.get('user_id', 'default_user')
    range_type = request.args.get('range', 'today')  # Options: today, week, upcoming
    days = int(request.args.get('days', '7'))  # Number of days for 'upcoming' range
    
    # Check if user has calendar access
    if not calendar_api.has_credentials(user_id):
        return jsonify({'error': 'Calendar not connected'}), 401
    
    try:
        events = []
        now = datetime.datetime.now()
        
        # Get events based on range_type
        if range_type == 'today':
            events = calendar_api.get_todays_events(user_id)
            date_info = now.strftime('%A, %B %d, %Y')
        elif range_type == 'week':
            # Calculate start and end of week
            start_of_week = now - datetime.timedelta(days=now.weekday())
            start_of_week = datetime.datetime.combine(start_of_week.date(), datetime.time(0, 0, 0))
            end_of_week = start_of_week + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            events = calendar_api.get_events_for_range(user_id, start_of_week, end_of_week)
            date_info = f"Week of {start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"
        elif range_type == 'upcoming':
            events = calendar_api.get_upcoming_events(user_id, days)
            date_info = f"Next {days} days"
        else:
            return jsonify({'error': 'Invalid range type'}), 400
        
        # Debug log to help troubleshoot
        print(f"Range: {range_type}, Events found: {len(events)}")
        for event in events:
            if 'dateTime' in event.get('start', {}):
                start_time = parser.parse(event.get('start', {}).get('dateTime'))
                print(f"Event: {event.get('summary')}, Date: {start_time.date()}, Time: {start_time.strftime('%H:%M')}")
        
        # Format events for display
        formatted_events = []
        events_by_date = {}
        
        for event in events:
            # Skip events without dateTime (all-day events)
            if 'dateTime' not in event.get('start', {}):
                continue
                
            # Parse event times
            start_time = parser.parse(event.get('start', {}).get('dateTime'))
            end_time = parser.parse(event.get('end', {}).get('dateTime')) if 'dateTime' in event.get('end', {}) else None
            
            # Get event date for grouping
            event_date = start_time.date()
            today = now.date()
            
            # For the 'today' range, double-check we're including only today's events
            if range_type == 'today' and event_date != today:
                print(f"Skipping event {event.get('summary')} because {event_date} is not today ({today})")
                continue
                
            # Format event data
            formatted_event = {
                'id': event.get('id'),
                'summary': event.get('summary', 'Untitled Event'),
                'location': event.get('location', ''),
                'date': event_date.strftime('%Y-%m-%d'),
                'dateFormatted': event_date.strftime('%A, %B %d'),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'formatted': start_time.strftime('%I:%M %p')
                }
            }
            
            if end_time:
                formatted_event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'formatted': end_time.strftime('%I:%M %p')
                }
                
                # Add formatted time range
                formatted_event['timeRange'] = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
            
            formatted_events.append(formatted_event)
            
            # Group events by date for multi-day views
            date_key = event_date.strftime('%Y-%m-%d')
            if date_key not in events_by_date:
                events_by_date[date_key] = {
                    'date': date_key,
                    'dateFormatted': event_date.strftime('%A, %B %d'),
                    'events': []
                }
            
            events_by_date[date_key]['events'].append(formatted_event)
        
        # Sort events by start time
        formatted_events.sort(key=lambda x: x['start']['dateTime'])
        
        # For multi-day views, sort the grouped events
        for date_key in events_by_date:
            events_by_date[date_key]['events'].sort(key=lambda x: x['start']['dateTime'])
        
        # Sort the dates
        sorted_dates = sorted(events_by_date.values(), key=lambda x: x['date'])
        
        print(f"Formatted events count: {len(formatted_events)}")
        print(f"Events by date groups: {len(sorted_dates)}")
        
        return jsonify({
            'range': range_type,
            'date': date_info,
            'events': formatted_events,
            'eventsByDate': sorted_dates
        })
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Failed to fetch calendar events: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    user_id = request.args.get('user_id', 'default_user')
    
    # Clear Google Calendar credentials for this user
    if calendar_api.has_credentials(user_id):
        success = calendar_api.clear_credentials(user_id)
    else:
        success = True
    
    return jsonify({'success': success})

if __name__ == '__main__':
    # Start the calendar checking thread
    calendar_thread = threading.Thread(target=check_calendar_and_notify, daemon=True)
    calendar_thread.start()
    
    # Start the Flask app
    socketio.run(app, debug=True, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True)
