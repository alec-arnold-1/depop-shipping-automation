# depop_parser.py

import os
import base64
import re
import csv
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup
from gmail_auth import get_gmail_service

def init_db():
    """Setup database to track processed emails"""
    conn = sqlite3.connect('depop_sales.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_orders (
            message_id TEXT PRIMARY KEY,
            buyer_name TEXT,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def is_already_processed(message_id):
    """Checks if the email has already been added to the CSV/DB."""
    conn = sqlite3.connect('depop_sales.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM processed_orders WHERE message_id = ?', (message_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_as_processed(message_id, buyer_name):
    """Logs message ID to database"""
    conn = sqlite3.connect('depop_sales.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO processed_orders (message_id, buyer_name) VALUES (?, ?)', 
                       (message_id, buyer_name))
        conn.commit()
    except sqlite3.IntegrityError:
        pass 
    conn.close()

def split_address(address_string):
    """
    Splits address block into columns comptabile w/ pirate ship.
    expected format:
    Address 1
    (Address 2 - Optional)
    City
    State
    Zipcode
    """
    lines = [l.strip() for l in address_string.splitlines() if l.strip()]
    if not lines:
        return {}

    # Anchor to the bottom
    zipcode = lines[-1]
    state = lines[-2] if len(lines) >= 2 else ""
    city = lines[-3] if len(lines) >= 3 else ""
    
    # everything above city is the street address
    street_lines = lines[:-3] if len(lines) > 3 else [lines[0]]
    
    addr1 = street_lines[0] if len(street_lines) >= 1 else ""
    addr2 = street_lines[1] if len(street_lines) >= 2 else ""
    
    return {
        "Address Line 1": addr1,
        "Address Line 2": addr2,
        "City": city,
        "State": state,
        "Zipcode": zipcode
    }

def parse_email(message):
    """extracts shipping info from Depop HTML emails"""
    try:
        if 'data' in message['payload']['body']:
            raw_html = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        elif 'parts' in message['payload']:
            raw_html = ''
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/html':
                    raw_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        else:
            return None

        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # scrub invisible formatting characters
        full_text = soup.get_text("\n")
        full_text = full_text.replace('\u2007', '').replace('\u200f', '').replace('\u00ad', '')
        
        # locate "Ship to ... Buyer" block
        match = re.search(r"Ship to\s+(.+?)\s+Buyer", full_text, re.S | re.I)
        
        if match:
            ship_content = match.group(1).strip()
            lines = [l.strip() for l in ship_content.splitlines() if l.strip()]
            
            if len(lines) >= 3:
                buyer = lines[0]
                # Keep only actual address lines (no country code)
                address_lines = [l for l in lines[1:] if l.upper() != "US"]
                address = "\n".join(address_lines)
                
                return {'buyer': buyer, 'address': address}
        
        return None

    except Exception as e:
        print(f"Failed to parse email: {e}")
        return None

def save_to_pirate_ship_csv(parsed_orders):
    """Appends unique orders to the CSV file"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"depop_orders_{date_str}.csv"
    
    keys = ["Recipient Name", "Address Line 1", "Address Line 2", "City", "State", "Zipcode"]
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            writer.writeheader()
        for order in parsed_orders:
            details = split_address(order['address'])
            writer.writerow({
                "Recipient Name": order['buyer'],
                "Address Line 1": details.get("Address Line 1", ""),
                "Address Line 2": details.get("Address Line 2", ""),
                "City": details.get("City", ""),
                "State": details.get("State", ""),
                "Zipcode": details.get("Zipcode", "")
            })
    return filename

if __name__ == "__main__":
    print("Running parser test...")
    # manual test
    service = get_gmail_service()
    results = service.users().messages().list(
        userId='me',
        maxResults=3,
        q='from:sold@alerts.depop.com "sale confirmation" "Ship to"'
    ).execute()
    
    messages = results.get('messages', [])
    if messages:
        for msg in messages:
            full_msg = service.users().messages().get(userId='me', id=msg['id']).execute()
            parsed = parse_email(full_msg)
            if parsed:
                print(f"Found Order: {parsed['buyer']}")
    else:
        print("No emails found.")