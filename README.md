# Project Overview

This project is a Python based automation tool designed to streamline the fulfillment process for Depop sellers. It monitors a linked Gmail account for specific USPS shipping notification emails, parses the recipient data from email's HTML body, and exports the information into a CSV format compatible with Pirate Ship's bulk import tool.

# Core Functionality

**Asynchronous Monitoring:** Utilizes Python's threading library to run a background loop that polls the Gmail API without blocking the Command Line Interface.

** Relational Data Tracking: ** Implements SQLite to maintain a persistent database of processed email Ids, preventing duplicate label generation across different sessions.

**Data Extraction:** Employs BeautifulSoup4 and Regex to navigate nested HTML structures and extract buyer names and shipping addresses.

**OAuth2 Authentication:** Uses the Google Cloud Console and OAuth2 protocols to securely handle user credentials and session tokens.

# Technical Stack

**Language:** Python 3.11

**APIs:** Google Gmail API

**Database:** SQLite3

**Libraries**: BeautifulSoup4, google-api-python-client, google-auth-oauthlib
