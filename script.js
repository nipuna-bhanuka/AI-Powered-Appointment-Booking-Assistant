document.addEventListener('DOMContentLoaded', function () {
    const messagesContainer = document.getElementById('messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const resetButton = document.getElementById('reset-btn');

    // Backend URL
    const backendUrl = 'http://localhost:5000';

    function addMessage(text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        messageDiv.textContent = text;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function updateStatus(appInfo) {
        // Track if all fields are complete
        let allComplete = true;
        
        // Update each status field
        for (const [key, value] of Object.entries(appInfo)) {
            const statusElem = document.getElementById(`${key}-status`);
            if (statusElem) {
                if (value !== null && value !== undefined && value.trim() !== '') {
                    statusElem.textContent = value;
                    statusElem.className = 'complete';
                } else {
                    statusElem.textContent = 'Missing';
                    statusElem.className = 'missing';
                    allComplete = false;
                }
            }
        }

        // Check for ticket number in the bot's reply
        if (allComplete) {
            const ticketMatch = findTicketNumberInMessages();
            if (ticketMatch) {
                document.getElementById('ticket-value').textContent = ticketMatch;
                document.getElementById('ticket-number').style.display = 'block';
            }
        }
    }

    function findTicketNumberInMessages() {
        // Get all bot messages
        const messages = messagesContainer.querySelectorAll('.bot-message');
        
        // Look for ticket number in the last few messages (checking in reverse order)
        const messagesToCheck = Array.from(messages).slice(-3).reverse();
        
        for (const message of messagesToCheck) {
            const ticketMatch = message.textContent.match(/APPT-\d+/);
            if (ticketMatch) {
                return ticketMatch[0];
            }
        }
        
        return null;
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        addMessage(message, true);
        userInput.value = '';

        try {
            const response = await fetch(`${backendUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            addMessage(data.reply, false);

            if (data.appointmentInfo) {
                updateStatus(data.appointmentInfo);
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Sorry, there was an error processing your request.', false);
        }
    }

    async function resetChat() {
        try {
            const response = await fetch(`${backendUrl}/reset`, {
                method: 'POST'
            });

            const data = await response.json();

            // Clear messages except the first one
            while (messagesContainer.childNodes.length > 1) {
                messagesContainer.removeChild(messagesContainer.lastChild);
            }

            // Add reset confirmation
            addMessage(data.reply, false);

            // Reset status
            if (data.appointmentInfo) {
                updateStatus(data.appointmentInfo);
            }

            document.getElementById('ticket-number').style.display = 'none';

        } catch (error) {
            console.error('Error:', error);
            addMessage('Sorry, there was an error resetting the chat.', false);
        }
    }

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    resetButton.addEventListener('click', resetChat);

    userInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
