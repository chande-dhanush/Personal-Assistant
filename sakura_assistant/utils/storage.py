import json
import os
from ..config import CONV_HISTORY_FILE, CONTACTS_FILE

def clear_conversation_history():

    """
    Clears the entire conversation history by overwriting the history file with an empty list.
    """
    try:
        with open(CONV_HISTORY_FILE, 'w') as f:
            json.dump([], f)  # Overwrite with an empty list
        print("Conversation history cleared successfully.")
        return True
    except Exception as e:
        print(f"Error clearing conversation history: {str(e)}")
        return False
    
def load_conversation():
    try:
        if os.path.exists(CONV_HISTORY_FILE):
            with open(CONV_HISTORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading conversation: {str(e)}")
    return []

def save_conversation(history):
    try:
        with open(CONV_HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except Exception as e:
        print(f"Error saving conversation: {str(e)}")

def load_contacts():
    try:
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading contacts: {str(e)}")
    return {}

def save_contacts(contacts):
    try:
        with open(CONTACTS_FILE, 'w') as f:
            json.dump(contacts, f)
    except Exception as e:
        print(f"Error saving contacts: {str(e)}")

def add_contact(name, number):
    if not name or not number:
        return False
    try:
        contacts = load_contacts()
        contacts[name.lower()] = number
        save_contacts(contacts)
        return True
    except Exception as e:
        print(f"Error adding contact: {str(e)}")
        return False 