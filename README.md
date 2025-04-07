# ExecuMate - AI-Powered Meal & Meeting Assistant

ExecuMate is an intelligent assistant that helps busy professionals manage their meals and meetings by integrating with Google Calendar. It analyzes your schedule, provides timely meal reminders, and ensures you never miss important events.

## Features

- **Google Calendar Integration**: Seamlessly connects with your Google Calendar to analyze your schedule
- **Smart Meal Reminders**: Sends notifications for meal times based on your meeting schedule
- **Personalized Experience**: Tailors recommendations to your preferences and availability
- **Real-time Updates**: Maintains synchronization with calendar changes

## Getting Started

### Prerequisites

- Python 3.7+
- Google account with Calendar API access

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/seatyyy/ExecuMate.git
   cd ExecuMate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up Google Calendar API:
   - Create a project in [Google Developer Console](https://console.developers.google.com/)
   - Enable the Google Calendar API
   - Create OAuth credentials
   - Download the client secret JSON file and save it as `credentials/client_secret.json`

4. Configure environment variables:
   - Copy `.env.template` to `.env`
   - Update the required environment variables

### Usage

1. Start the application:
   ```
   python app.py
   ```

2. Open your browser and navigate to `http://localhost:8080`

3. Connect your Google Calendar when prompted

4. ExecuMate will now analyze your schedule and provide meal reminders based on your availability

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
