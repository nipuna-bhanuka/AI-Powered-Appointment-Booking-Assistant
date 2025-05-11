from flask import Flask, request, jsonify
from flask_cors import CORS
print("Starting script...")

try:
    from appointment_create_agent import agent, appointment_info
    print("Imported agent successfully.")
except Exception as e:
    print(f"Failed to import agent: {e}")
    agent = None
    appointment_info = {}



app = Flask(__name__)

# Enable CORS for the Flask app
CORS(app)

print("Starting script...")  # Should print no matter what


@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '')
    try:
        response = agent.invoke({"input": user_input})
        bot_response = response["output"]
        
        # Check if appointment is complete
        is_complete = all(appointment_info.values())
        
        return jsonify({
            "reply": bot_response,
            "isComplete": is_complete,
            "appointmentInfo": appointment_info
        })
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

@app.route('/reset', methods=['POST'])
def reset():
    # Reset appointment info
    for key in appointment_info:
        appointment_info[key] = None
    return jsonify({"reply": "Appointment reset successfully. 📝 Hi! I'm your appointment booking assistant. Please tell me your name, email, service, and preferred date. 🔐 If you want to log in as staff member, then enter the passcode.", "appointmentInfo": appointment_info})

if __name__ == '__main__':
    print("Starting appointment booking server on port 5000...")
    app.run(host='0.0.0.0', port=5000)



