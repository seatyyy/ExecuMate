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
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Highrise AI client using OpenAI compatible API
highrise_api_key = os.getenv('HIGHRISE_API_KEY')
highrise_base_url = os.getenv('HIGHRISE_BASE_URL', 'https://cloud.highrise.ai/highrise-api/maas/ai')
highrise_model = os.getenv('HIGHRISE_MODEL', 'DeepSeek-R1')

# No OpenAI client needed - using direct requests to Highrise API

# Initialize Google Calendar API
calendar_api = GoogleCalendarAPI()

# Global variables
user_state = {}
active_reminders = {}

# Track message ids to prevent duplicates
message_ids = set()

@app.route('/')
def index():
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

@socketio.on('connect')
def handle_connect():
    # Create a room with the session ID to ensure message isolation
    print('Client connected')
    join_room(request.sid)
    print(f"Client {request.sid} joined their own room")

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
    while True:
        try:
            # Get all users' calendars
            now = datetime.datetime.now()
            
            # For each user
            for user_id in user_state:
                # Check if we have calendar access for this user
                if calendar_api.has_credentials(user_id):
                    # Get events for today
                    events = calendar_api.get_todays_events(user_id)
                    
                    for event in events:
                        event_id = event.get('id')
                        start_time = parser.parse(event.get('start', {}).get('dateTime', event.get('start', {}).get('date')))
                        
                        # If event starts between 12-2pm (lunch) or 6-8pm (dinner)
                        is_meal_time = (12 <= start_time.hour <= 14) or (18 <= start_time.hour <= 20)
                        
                        # Check if this is a meal time event and we haven't reminded yet
                        reminder_key = f"{user_id}_{event_id}"
                        
                        if is_meal_time and reminder_key not in active_reminders:
                            # Calculate reminder time (1 hour before event)
                            reminder_time = start_time - datetime.timedelta(hours=1)
                            
                            # If it's time to remind
                            if now >= reminder_time and now <= start_time:
                                # Create reminder message
                                event_name = event.get('summary', 'your meeting')
                                event_time = start_time.strftime("%I:%M %p")
                                
                                reminder_message = f"I noticed you have {event_name} at {event_time}. Would you like to order food before your meeting starts?"
                                
                                # Send reminder through socket
                                socketio.emit('reminder', {
                                    'message': reminder_message,
                                    'user_id': user_id,
                                    'event': event
                                })
                                
                                # Mark as reminded
                                active_reminders[reminder_key] = now
        
        except Exception as e:
            print(f"Error in calendar checking: {e}")
        
        # Sleep for 5 minutes before checking again
        time.sleep(300)

@app.route('/api/authorize/google', methods=['GET'])
def authorize_google():
    auth_url = calendar_api.get_authorization_url()
    return jsonify({'auth_url': auth_url})

@app.route('/api/callback/google', methods=['GET'])
def google_callback():
    code = request.args.get('code')
    user_id = request.args.get('state', 'default_user')
    calendar_api.exchange_code_for_token(code, user_id)
    return render_template('callback_success.html')

if __name__ == '__main__':
    # Start the calendar checking thread
    calendar_thread = threading.Thread(target=check_calendar_and_notify, daemon=True)
    calendar_thread.start()
    
    # Start the Flask app
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
