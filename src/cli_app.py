import time
import os
import threading
from src.depop_parser import parse_email, save_to_pirate_ship_csv, is_already_processed, mark_as_processed
from src.gmail_auth import get_gmail_service

AUTO_MODE = True

def auto_loop():
    """Background thread that monitors Gmail for depop sale confirmation email"""
    global AUTO_MODE
    
    # Initialize Gmail service
    try:
        service = get_gmail_service()
        print("[SYSTEM] Gmail Service Initialized. Monitoring for sales...")
    except Exception as e:
        print(f"[ERROR] Could not connect to Gmail: {e}")
        return

    while True:
        if AUTO_MODE:
            try:
                # search for Depop emails which contain shipping info for sales
                
                results = service.users().messages().list(
                    userId='me',
                    q='from:sold@alerts.depop.com "sale confirmation" "Ship to"'
                ).execute()

                messages = results.get('messages', [])

                for msg in messages:
                    msg_id = msg['id']
                    
                    #skip if message has been handled before
                    if not is_already_processed(msg_id):
                        #fetch full email content
                        full_msg = service.users().messages().get(userId='me', id=msg_id).execute()
                        
                        #parse HTML for buyer and address
                        parsed = parse_email(full_msg)
                        
                        if parsed:
                        
                            save_to_pirate_ship_csv([parsed])
                            
                            mark_as_processed(msg_id, parsed['buyer'])
                            
                            print(f"[NEW SALE] {parsed['buyer']} added to CSV and Database.")
                        else:
                            # dont mark as processed if parasing fails
                            print(f"[WARNING] Found email {msg_id} but couldn't parse shipping info.")

            except Exception as e:
                print(f"[ERROR] Auto-sync loop encountered an error: {e}")

        # only check for emails every 60s
        time.sleep(60)


def main():
    global AUTO_MODE
    
    # launch gmail monitor in separate daemon thread
    # make background task automatically close when exiting main program
    monitor_thread = threading.Thread(target=auto_loop, daemon=True)
    monitor_thread.start()

    print("\n========================================")
    print("   Depop-to-PirateShip Automation Tool")
    print("========================================\n")
    print("Current Status: Monitoring Active")
    print("\nCommands:")
    print("  'auto on'   - Resume Gmail monitoring")
    print("  'auto off'  - Pause Gmail monitoring")
    print("  'quit'      - Exit the application\n")

    while True:
        cmd = input(">> ").strip().lower()

        if cmd == "auto on":
            AUTO_MODE = True
            print("[INFO] Auto mode enabled.")

        elif cmd == "auto off":
            AUTO_MODE = False
            print("[INFO] Auto mode disabled.")

        elif cmd == "quit":
            print("[INFO] Shutting down. Happy shipping!")
            break

        else:
            print("[?] Unknown command. Try 'auto on', 'auto off', or 'quit'.")

if __name__ == "__main__":
    main()