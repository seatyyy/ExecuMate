# ExecuMate - AI Executive Assistant

ExecuMate is an intelligent executive assistant that helps users order food based on their schedule. It integrates with Google Calendar to provide proactive food ordering reminders before meetings and events. ExecuMate uses Highrise AI for its natural language processing capabilities.

## Features

- 🤖 AI-powered chat interface using Highrise AI models
- 📅 Google Calendar integration for schedule awareness
- 🍔 Proactive food ordering reminders
- ⏰ Smart timing for meal suggestions
- 💬 Real-time messaging with SocketIO

## Project Structure

```
ai_food_delivery/
├── app.py                 # Main Flask application
├── google_calendar.py     # Google Calendar API integration
├── requirements.txt       # Python dependencies
├── static/                # Static files
│   ├── css/
│   │   └── style.css      # Main stylesheet
│   └── js/
│       └── app.js         # Frontend JavaScript
└── templates/             # HTML templates
    ├── index.html         # Main chat interface
    └── callback_success.html  # Google auth callback page
```

## Setup Instructions

1. **Clone the repository**

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root with the following variables:
   ```
   # Highrise AI configuration
   HIGHRISE_API_KEY=your_highrise_api_key
   HIGHRISE_BASE_URL=https://api.highrise.ai/api/v1/ai
   HIGHRISE_MODEL=meta-llama-3-8b-instruct  # Or your preferred Highrise model
   
   SECRET_KEY=your_secret_key
   GOOGLE_CLIENT_SECRET_FILE=path_to_client_secret.json
   GOOGLE_REDIRECT_URI=http://localhost:5000/api/callback/google
   ```

4. **Set up Google Calendar API**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Web application type)
   - Download the client secret JSON file and place it in your project directory
   - Update the path in your `.env` file

5. **Run the application**
   ```
   python app.py
   ```

6. **Access the application**
   Open your browser and navigate to: `http://localhost:5000`

## Usage

1. Connect your Google Calendar using the "Connect Calendar" button
2. MealMinder will automatically scan your calendar for upcoming events
3. Based on your schedule, it will suggest ordering food before meetings
4. You can interact with the assistant to order food, set preferences, or ask questions

## Technologies Used

- **Backend**: Python, Flask, SocketIO
- **Frontend**: HTML, CSS, JavaScript
- **APIs**: Highrise AI API, Google Calendar API
- **Data Storage**: Local file storage for credentials
