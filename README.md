# AI-Powered Appointment Booking Assistant

This project is an AI-powered appointment booking assistant designed to streamline the process of scheduling appointments. It features a chatbot interface integrated with a Flask backend and a database for storing appointment details.

## Features

- **AI Chatbot**: Handles user input to extract appointment details such as name, email, service, and date.
- **Flask Backend**: Manages API endpoints for chat interactions and appointment resets.
- **Database Integration**: Stores and retrieves appointment details using SQLite.
- **Staff Mode**: Allows authenticated staff to query, cancel, and manage appointments.
- **Frontend Integration**: Provides a user-friendly interface for customers to interact with the assistant.

## Project Structure

```
appointment_create_agent.py  # Core logic for extracting and managing appointment data
server.py                    # Flask server handling API requests
script.js                    # Frontend logic for interacting with the server
styles.css                   # Styling for the chatbot UI
chatbot_ui.html              # Frontend HTML for the chatbot interface
appointmentdb.db             # SQLite database for storing appointments
```

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd AI-Powered-Appointment-Booking-Assistant
   ```

2. **Install Dependencies**:
   - Install Python dependencies:
     ```bash
     pip install flask flask-cors python-dotenv langchain-openai langchain-google-genai
     ```

3. **Set Up Environment Variables**:
   - Create a `.env` file in the project root and add the following:
     ```env
     GOOGLE_API_KEY=<your-google-api-key>
     ```

4. **Initialize the Database**:
   - Run the Flask server to automatically initialize the database:
     ```bash
     python server.py
     ```

5. **Run the Application**:
   - Start the Flask server:
     ```bash
     python server.py
     ```
   - Open `chatbot_ui.html` in a browser to interact with the chatbot.

## API Endpoints

### `/chat` (POST)
- **Description**: Handles user input and returns chatbot responses.
- **Request Body**:
  ```json
  {
    "message": "<user-input>"
  }
  ```
- **Response**:
  ```json
  {
    "reply": "<bot-response>",
    "isComplete": <true/false>,
    "appointmentInfo": {
      "name": "<name>",
      "email": "<email>",
      "service": "<service>",
      "date": "<date>"
    }
  }
  ```

### `/reset` (POST)
- **Description**: Resets the appointment information.
- **Response**:
  ```json
  {
    "reply": "Appointment reset successfully.",
    "appointmentInfo": {
      "name": null,
      "email": null,
      "service": null,
      "date": null
    }
  }
  ```

## Debugging Tips

- Ensure the `Content-Type` header is set to `application/json` for API requests.
- Check the Flask server logs for detailed error messages.
- Use the debug print statements in `appointment_create_agent.py` to trace data extraction issues.

## Future Enhancements

- Add support for multiple languages.
- Implement a calendar integration for real-time scheduling.
- Enhance the chatbot UI with more interactive elements.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
