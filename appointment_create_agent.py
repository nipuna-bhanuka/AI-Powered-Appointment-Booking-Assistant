from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
import os
import re
import random
import dateparser
from datetime import datetime, timedelta
import sqlite3

load_dotenv()

from langchain_google_genai import GoogleGenerativeAI
# Initialize LLM
llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.environ["GOOGLE_API_KEY"])

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Global variable to store appointment info
appointment_info = {
    "name": None,
    "email": None,
    "service": None,
    "date": None
}

# Staff authentication variables
STAFF_PASSCODE = "staff1234"  
is_staff_mode = False

def is_date_valid(date_str):
    """Check if the date is valid (not today or in the past)"""
    try:
        appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        return appointment_date > today
    except Exception as e:
        print(f"Date validation error: {str(e)}")
        return False

def extract_appointment_info(text: str) -> str: 
    global appointment_info  # Ensure we're accessing the global variable
    
    print(f"Debug - Before extraction, stored info: {appointment_info}")
    
    # Use existing values as defaults
    current_info = appointment_info.copy()
    
    # Try to extract name - expanded pattern to catch single names
    name_match = re.search(r"(?:my name is|i am|name is|name -|name:|^)\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)", text, re.IGNORECASE)
    if name_match and len(name_match.group(1)) >= 2:  
        current_info["name"] = name_match.group(1).title()
    
    # Try to extract email
    email_match = re.search(r"\b[\w.-]+@[\w.-]+\.\w+\b", text)  
    if email_match:
        current_info["email"] = email_match.group(0)
    
    # Try to extract service - more flexible pattern
    service_match = re.search(r"(?:service is|i need|service -|service:|need a)\s+(.+?)(?:,|\.|$|and)", text, re.IGNORECASE)
    if not service_match:
        
        common_services = ["haircut", "manicure", "pedicure", "massage", "facial", "consultation", "appointment", "checkup", "cleaning"]
        for service in common_services:
            if service in text.lower():
                current_info["service"] = service
                break
    else:
        current_info["service"] = service_match.group(1).strip()
    
    # Try to extract date - handle various formats
    date_extracted = None
    
    # Standard format date (DD/MM/YYYY)
    std_date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
    if std_date_match:
        date_text = std_date_match.group(1)
        parsed_date = dateparser.parse(date_text)
        if parsed_date:
            date_extracted = parsed_date.strftime("%Y-%m-%d")
    
    # ISO format date (YYYY-MM-DD)
    if not date_extracted:
        iso_date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if iso_date_match:
            date_extracted = iso_date_match.group(1)
    
    # Date words and phrases
    if not date_extracted:
        date_match = re.search(r"(?:date is|on|date -|date:|for)\s+(\S+(?:\s+\S+)*?)(?:,|\.|$)", text, re.IGNORECASE)
        if date_match:
            date_text = date_match.group(1)
            parsed_date = dateparser.parse(date_text)
            if parsed_date:
                date_extracted = parsed_date.strftime("%Y-%m-%d")
    
    # Common date words
    if not date_extracted:
        date_words = ["tomorrow", "today", "next week", "next month"]
        for date_word in date_words:
            if date_word in text.lower():
                parsed_date = dateparser.parse(date_word)
                if parsed_date:
                    date_extracted = parsed_date.strftime("%Y-%m-%d")
                    break
    
    # Now validate the date if a date was extracted
    if date_extracted:
        if is_date_valid(date_extracted):
            current_info["date"] = date_extracted
        else:
            return "⚠️ I noticed you selected today or a past date. Please choose a future date for your appointment."
    

    print(f"Debug - Extracted from text: {text}")
    print(f"Debug - Extracted info: {current_info}")
    
    # Update the global variable with any new information
    changes = []
    for key, value in current_info.items():
        if value and value != appointment_info[key]:
            appointment_info[key] = value
            changes.append(f"✅ {key.title()} saved: {value}")
    
    print(f"Debug - Updated info after extraction: {appointment_info}")
    
    # If no changes were made but we already have some info, don't say "couldn't extract"
    if not changes:
        has_some_info = any(appointment_info.values())
        if has_some_info:

            response = get_appointment_status()
            return response
        else:
            return "❓ I couldn't extract any new info. Please provide your name, email, service, or date."
    
    response = " ".join(changes)
    
    # Add current appointment status
    response += "\n" + get_appointment_status()
    
    # If all information is complete, book the appointment
    if all(appointment_info.values()):
        response += "\n✅ All information complete! Booking your appointment now..."
        
        # Create ticket and book appointment
        ticket_number = f"APPT-{random.randint(10000, 99999)}"
        db_result = save_appointment_to_db(
            appointment_info["name"],
            appointment_info["email"],
            appointment_info["service"],
            appointment_info["date"],
            ticket_number)
        
        if db_result:
            print("Hello")
            response += f"\n🎉 Your appointment has been booked successfully! Your ticket number is: {ticket_number}"
        else:
            response += f"\n⚠️ Your information is complete, but there was an issue with the booking system. Please try again later. Ticket number: {ticket_number}"
    
    return response

def get_appointment_status():
    """Get the current status of appointment information"""
    status_parts = []
    
    # Add confirmed information
    confirmed = []
    for key, value in appointment_info.items():
        if value:
            confirmed.append(f"{key.title()}: {value}")
    
    if confirmed:
        status_parts.append("📝 Current information:\n" + "\n".join(confirmed))
    
    # Add missing information
    missing = [k.title() for k, v in appointment_info.items() if not v]
    if missing:
        status_parts.append(f"⏳ Still need: {', '.join(missing)}.")
    
    return "\n".join(status_parts)

def reset_appointment_info():
    """Reset appointment info after booking is complete"""
    global appointment_info
    appointment_info = {
        "name": None,
        "email": None,
        "service": None,
        "date": None
    }

    is_staff_mode = False

def check_appointment_goal(_: str) -> str:
    """Check if all required information has been provided and book appointment if complete."""
    if all(appointment_info.values()):
        # Additional check for date validity
        if not is_date_valid(appointment_info["date"]):
            return "⚠️ The selected date is today or in the past. Please choose a future date for your appointment."
            
        ticket_number = f"APPT-{random.randint(10000, 99999)}"
        
        db_result = save_appointment_to_db(
            appointment_info["name"],
            appointment_info["email"],
            appointment_info["service"],
            appointment_info["date"],
            ticket_number)
        
        if db_result:
            success_message = (f"✅ Booking complete! Name: {appointment_info['name']}, Email: {appointment_info['email']}, "
                    f"Service: {appointment_info['service']}, Date: {appointment_info['date']}. "
                    f"Your appointment is confirmed! 🎉 Your ticket number is: {ticket_number}")
    
            return success_message

        else:
            return f"✅ Your information is complete, but there was an issue saving to the database. Name: {appointment_info['name']}, Email: {appointment_info['email']}, Service: {appointment_info['service']}, Date: {appointment_info['date']}. Ticket: {ticket_number}"
    else:
        missing = [k.title() for k, v in appointment_info.items() if not v]
        return f"⏳ Still need: {', '.join(missing)}. Please provide this information."

def get_current_info(_: str) -> str:
    """Return the current state of appointment information."""
    info_status = []
    for key, value in appointment_info.items():
        status = f"{key.title()}: {value}" if value else f"{key.title()}: Not provided yet"
        info_status.append(status)
    
    return "Current information:\n" + "\n".join(info_status)

def verify_staff_passcode(text: str) -> str:
    """Check if the provided text contains the staff passcode."""
    global is_staff_mode
    
    # Look for a passcode pattern (4+ consecutive digits or characters)
    passcode_match = re.search(r"[a-zA-Z0-9]{4,}", text)
    
    if passcode_match and passcode_match.group(0) == STAFF_PASSCODE:
        is_staff_mode = True
        return "✅ Staff authentication successful. You can now query appointments."
    elif passcode_match:
        return "❌ Invalid passcode. Please try again or continue as a customer."
    else:
        return "No passcode detected. Please enter the staff passcode to access staff features."

def query_appointments(text: str) -> str:
    """Query the database for appointment information based on various criteria."""
    global is_staff_mode

    if not is_staff_mode:
        return "⛔ You need staff authentication to access this feature. Please enter the staff passcode first."

    conn = sqlite3.connect("appointmentdb.db")
    cursor = conn.cursor()

    query = "SELECT name, email, service, date, ticket_number FROM appointments WHERE 1=1"
    params = []

    # Check for name
    name_match = re.search(r"name\s*(is)?\s*([A-Za-z\s]+)", text, re.IGNORECASE)
    if name_match:
        query += " AND name LIKE ?"
        params.append(f"%{name_match.group(2).strip()}%")

    # Check for email
    email_match = re.search(r"\b[\w.-]+@[\w.-]+\.\w+\b", text)
    if email_match:
        query += " AND email LIKE ?"
        params.append(f"%{email_match.group(0)}%")

    # Check for service
    service_match = re.search(r"(haircut|manicure|pedicure|massage|facial|consultation|appointment|checkup|cleaning)", text, re.IGNORECASE)
    if service_match:
        query += " AND service LIKE ?"
        params.append(f"%{service_match.group(1).strip()}%")

    # Check for date (standard formats)
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
    if date_match:
        date_text = date_match.group(1)
        parsed_date = dateparser.parse(date_text)
        if parsed_date:
            formatted_date = parsed_date.strftime("%Y-%m-%d")
            query += " AND date = ?"
            params.append(formatted_date)

    # Check for status keywords
    status_filter = None
    if re.search(r"\b(done|completed|finish|ended)\b", text, re.IGNORECASE):
        status_filter = "done"
    elif re.search(r"\b(pending|upcoming|scheduled|future)\b", text, re.IGNORECASE):
        status_filter = "pending"
    elif re.search(r"\b(cancel|cancelled|canceled)\b", text, re.IGNORECASE):
        status_filter = "cancel"
        
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

        
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if results:
        response_lines = ["📋 Appointments found:"]
        for row in results:
            response_lines.append(f"- Name: {row[0]}, Email: {row[1]}, Service: {row[2]}, Date: {row[3]}, Ticket: {row[4]}")
        return "\n".join(response_lines)
    else:
        return "🔎 No appointments found matching your criteria."


def exit_staff_mode(_: str) -> str:
    """Exit staff mode and return to customer booking mode."""
    global is_staff_mode
    
    if is_staff_mode:
        is_staff_mode = False

        reset_appointment_info()

        return "✅ Exited staff mode. Now in customer booking mode."
    else:
        return "You're already in customer mode."

def update_database_schema():
    """Add ticket_number column to appointments table if it doesn't exist"""
    try:
        conn = sqlite3.connect('appointmentdb.db')
        cursor = conn.cursor()
        
        # First verify the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
        if not cursor.fetchone():
            print("⚠️ appointments table doesn't exist! Creating it...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    service TEXT NOT NULL,
                    date TEXT NOT NULL,
                    ticket_number TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ appointments table created!")
        else:
            # Check if the ticket_number column exists
            cursor.execute("PRAGMA table_info(appointments)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if "ticket_number" not in columns:
                print("Adding ticket_number column to appointments table...")
                cursor.execute('''
                    ALTER TABLE appointments
                    ADD COLUMN ticket_number TEXT
                ''')
                print("✅ ticket_number column added successfully!")
            else:
                print("✅ ticket_number column already exists!")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Schema update error: {str(e)}")
        return False

def initialize_database():
    """Create the appointments table if it doesn't exist"""
    try:
        # Make sure the database directory exists
        db_path = 'appointmentdb.db'
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                service TEXT NOT NULL,
                date TEXT NOT NULL,
                ticket_number TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Verify the table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
        if not cursor.fetchone():
            raise Exception("Failed to create appointments table")
            
        conn.commit()
        conn.close()
        print("✅ Database initialized!")
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        return False

# In the save_appointment_to_db function, add the reset_appointment_info() call:

def save_appointment_to_db(name, email, service, date, ticket_number):
    """Save the appointment data to the database including ticket number"""
    # Additional validation before saving to database
    if not is_date_valid(date):
        print("⚠️ Invalid date detected - booking canceled.")
        return False
        
    try:
        conn = sqlite3.connect('appointmentdb.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO appointments (name, email, service, date, ticket_number, status, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, service, date, ticket_number, "pending", 0.0))

        conn.commit()
        conn.close()
        print(f"✅ appointment saved to database with ticket {ticket_number}!")

        return True
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False

# Function to cancel an appointment
def cancel_appointment(text: str) -> str:
    """Cancel an appointment by updating its status in the database."""
    global is_staff_mode
    
    if not is_staff_mode:
        return "⛔ You need staff authentication to cancel appointments. Please enter the staff passcode first."
    
    # Try to extract a ticket number
    ticket_match = re.search(r"(?:ticket|number|#)\s*(APPT-\d+)", text, re.IGNORECASE)
    if not ticket_match:
        return "❓ Please provide a valid ticket number to cancel (e.g., 'Cancel ticket APPT-12345')."
    
    ticket = ticket_match.group(1)
    
    try:
        conn = sqlite3.connect('appointmentdb.db')
        cursor = conn.cursor()
        
        # First check if the ticket exists
        cursor.execute("SELECT id, name FROM appointments WHERE ticket_number = ?", (ticket))
        appointment = cursor.fetchone()
        
        if not appointment:
            conn.close()
            return f"❌ No appointment found with ticket number {ticket}."
        
        # Update the status to 'cancel'
        cursor.execute(
            "UPDATE appointments SET status = 'cancel' WHERE ticket_number = ?", 
            (ticket,)
        )
        
        conn.commit()
        conn.close()
        
        return f"✅ Appointment with ticket {ticket} for {appointment[1]} has been successfully cancelled."
    
    except Exception as e:
        print(f"❌ Database cancellation error: {str(e)}")
        return f"⚠️ Error cancelling appointment: {str(e)}"


def query_income(text: str) -> str:
    """Query the database for income information based on various criteria."""
    global is_staff_mode
    
    if not is_staff_mode:
        return "⛔ You need staff authentication to access income information. Please enter the staff passcode first."
    
    try:
        conn = sqlite3.connect('appointmentdb.db')
        cursor = conn.cursor()
        
        # Default query: get total income from all pending appointments
        query = "SELECT SUM(price) FROM appointments WHERE status = 'done'"
        params = []
        
        # Check if query is for a specific date
        date_match = re.search(r"(?:date|on|for)\s+(.+?)(?:,|\.|$)", text, re.IGNORECASE)
        if date_match:
            date_text = date_match.group(1)
            parsed_date = dateparser.parse(date_text)
            if parsed_date:
                query = "SELECT SUM(price) FROM appointments WHERE status = 'done' AND date = ?"
                params = [parsed_date.strftime("%Y-%m-%d")]
        
        # Check if query is for a specific service
        service_match = re.search(r"(?:service|type)\s+(.+?)(?:,|\.|$)", text, re.IGNORECASE)
        if service_match:
            service = service_match.group(1)
            if params:  
                query = query.replace("WHERE", "WHERE service LIKE ? AND")
                params.insert(0, f"%{service}%")
            else:
                query = "SELECT SUM(price) FROM appointments WHERE status = 'done' AND service LIKE ?"
                params = [f"%{service}%"]
        
        # Check for date range queries
        start_date = None
        end_date = None
        
        # Look for "between [date] and [date]" pattern
        range_match = re.search(r"between\s+(.+?)\s+and\s+(.+?)(?:,|\.|$)", text, re.IGNORECASE)
        if range_match:
            start_text = range_match.group(1)
            end_text = range_match.group(2)
            
            start_date = dateparser.parse(start_text)
            end_date = dateparser.parse(end_text)
            
            if start_date and end_date:
                query = "SELECT SUM(price) FROM appointments WHERE status = 'done' AND date BETWEEN ? AND ?"
                params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]
        
        # Execute query
        cursor.execute(query, params)
        total_income = cursor.fetchone()[0] or 0
        
        # Get the count of appointments
        count_query = query.replace("SUM(price)", "COUNT(*)")
        cursor.execute(count_query, params)
        appointment_count = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Format results
        result = f"💰 Total Income: ${total_income:.2f}\n"
        result += f"📊 Appointments: {appointment_count}\n"
        
        if appointment_count > 0:
            result += f"📈 Average per appointment: ${total_income/appointment_count:.2f}"
        
        return result
    
    except Exception as e:
        print(f"❌ Income query error: {str(e)}")
        return f"⚠️ Error querying income data: {str(e)}"


# Define tools list with the new tools
tools = [
    Tool(
        name="extract_info",
        func=extract_appointment_info,
        description="Extract name, email, service, and date from user input."
    ),
    Tool(
        name="check_goal",
        func=check_appointment_goal,
        description="Check if all required information has been provided."
    ),
    Tool(
        name="get_info",
        func=get_current_info,
        description="Get the current status of collected information."
    ),
    Tool(
        name="verify_staff",
        func=verify_staff_passcode,
        description="Verify if the provided passcode grants staff access."
    ),
    Tool(
        name="query_appointments",
        func=query_appointments,
        description="Query appointments in the database (staff only)."
    ),
    Tool(
        name="cancel_appointment",
        func=cancel_appointment,
        description="Cancel an appointment by updating its status (staff only)."
    ),
    Tool(
        name="exit_staff_mode",
        func=exit_staff_mode,
        description="Exit staff mode and return to customer booking mode."
    ),
    Tool(
    name="query_income",
    func=query_income, 
    description="Query income information from appointments (staff only)."
    )
]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True
)

if __name__ == "__main__":
    try:
        # Make sure database initialization happens first and is successful
        print("🔄 Initializing database...")
        initialize_database()
        print("🔄 Checking database schema...")
        update_database_schema()
        print("✅ Database setup complete!")
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        print("⚠️ Creating fresh database...")
 
        try:
            if os.path.exists('appointmentdb.db'):
                os.rename('appointmentdb.db', 'appointmentdb.db.bak')
            initialize_database()
            print("✅ Fresh database created successfully!")
        except Exception as e2:
            print(f"❌ Critical database error: {str(e2)}")
            print("⚠️ Please check file permissions in this directory.")
            exit(1)
    
    print("📝 Welcome! I'm your appointment booking assistant.")
    print("👤 Customers: Please provide your name, email, service, and preferred date.")
    print("🗓️ Note: You must select a future date for your appointments.")
    print("👔 Staff: Enter staff passcode to access appointment information.")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Bye! Good luck.")
            break

        try:
            # First, check if this might be a staff authentication attempt
            if "staff" in user_input.lower() or "passcode" in user_input.lower() or re.search(r"\b[a-zA-Z0-9]{4,}\b", user_input):
                staff_result = verify_staff_passcode(user_input)
                if is_staff_mode:
                    print("Bot:", staff_result)
                    print("🔐 Staff mode activated. You can now query appointment information.")
                    print("Available commands:")
                    print(" - Query appointments by date: 'Show appointments for tomorrow'")
                    print(" - Query by customer: 'Show appointments for John'")
                    print(" - Query by service: 'Show all haircut appointments'")
                    print(" - Query by ticket: 'Show ticket APPT-12345'")
                    print(" - Exit staff mode: 'Exit staff mode'")
                    continue
            
            # If in staff mode, try to process staff-specific commands
            if is_staff_mode:
                if "exit" in user_input.lower() and "staff" in user_input.lower():
                    result = exit_staff_mode(user_input)
                    print("Bot:", result)
                    continue
                
                # Handle appointment queries
                if any(x in user_input.lower() for x in ["show", "get", "list", "find", "appointment", "ticket"]):
                    result = query_appointments(user_input)
                    print("Bot:", result)
                    continue
            
            # If not in staff mode use the normal flow
            if not is_staff_mode:
                extract_result = extract_appointment_info(user_input)
                
                if extract_result and "today or a past date" in extract_result:
                    print("Bot:", extract_result)
                    continue
            
            # Use the agent for a conversational response
            response = agent.invoke({"input": user_input})
            
            print("Bot:", response["output"])
            
            if not is_staff_mode and all(appointment_info.values()):
                # Validate date once more before confirming booking
                if not is_date_valid(appointment_info["date"]):
                    print("⚠️ I noticed you selected today or a past date. Please choose a future date for your appointment.")

                    appointment_info["date"] = None
                    continue
                    
                print("🎉 Appointment info complete!")
                
                ticket_number = f"APPT-{random.randint(10000, 99999)}"
                
                db_result = save_appointment_to_db(
                    appointment_info["name"],
                    appointment_info["email"],
                    appointment_info["service"],
                    appointment_info["date"],
                    ticket_number)
                
                if db_result:
                    print(f"✅ Appointment for {appointment_info['name']} successfully stored in database.")
                    print(f"📅 Your appointment has been confirmed! Ticket #: {ticket_number}")

                    print("\n📝 Ready for new booking. How can I help you?")
                else:
                    print("⚠️ Note: There was an issue with your booking. Please ensure your date is in the future.")
            
        except Exception as e:
            print(f"Sorry, I encountered an error: {str(e)}")


