"""
Lambda function for Lex V2 fulfillment - Cyber Risk Dashboard Assistant
Supports company CRUD operations via conversational interface
"""

import json
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection parameters from environment
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'port': 5432
}

# Known company mappings for entity extraction
KNOWN_COMPANIES = {
    'crowdstrike': ('CrowdStrike Holdings', 'CRWD'),
    'crwd': ('CrowdStrike Holdings', 'CRWD'),
    'palo alto': ('Palo Alto Networks', 'PANW'),
    'palo alto networks': ('Palo Alto Networks', 'PANW'),
    'panw': ('Palo Alto Networks', 'PANW'),
    'fortinet': ('Fortinet Inc', 'FTNT'),
    'ftnt': ('Fortinet Inc', 'FTNT'),
    'zscaler': ('Zscaler Inc', 'ZS'),
    'zs': ('Zscaler Inc', 'ZS'),
    'sentinelone': ('SentinelOne Inc', 'S'),
    'sentinel one': ('SentinelOne Inc', 'S'),
    'microsoft': ('Microsoft Corporation', 'MSFT'),
    'msft': ('Microsoft Corporation', 'MSFT'),
    'cisco': ('Cisco Systems', 'CSCO'),
    'csco': ('Cisco Systems', 'CSCO'),
    'okta': ('Okta Inc', 'OKTA'),
    'cloudflare': ('Cloudflare Inc', 'NET'),
    'net': ('Cloudflare Inc', 'NET'),
    'cyberark': ('CyberArk Software', 'CYBR'),
    'cybr': ('CyberArk Software', 'CYBR'),
    'qualys': ('Qualys Inc', 'QLYS'),
    'qlys': ('Qualys Inc', 'QLYS'),
}

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG)

def extract_company_from_utterance(utterance):
    """
    Extract company name/ticker from user utterance
    Returns (company_name, ticker) tuple or (None, None) if not found
    """
    utterance_lower = utterance.lower()

    # Check for known companies
    for keyword, (company_name, ticker) in KNOWN_COMPANIES.items():
        if keyword in utterance_lower:
            return (company_name, ticker)

    # Try to extract ticker pattern (2-5 uppercase letters)
    ticker_match = re.search(r'\b([A-Z]{2,5})\b', utterance)
    if ticker_match:
        ticker = ticker_match.group(1)
        # Return just the ticker, caller can look up company name
        return (None, ticker)

    return (None, None)


def find_company_by_alias(search_term):
    """
    Find company by any alias using database lookup
    Returns (company_id, ticker, company_name) or (None, None, None)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # First try direct match on companies table
        cursor.execute("""
            SELECT id, ticker, company_name
            FROM companies
            WHERE LOWER(ticker) = LOWER(%s)
               OR LOWER(company_name) LIKE LOWER(%s)
        """, (search_term, f'%{search_term}%'))

        row = cursor.fetchone()
        if row:
            cursor.close()
            conn.close()
            return (row['id'], row['ticker'], row['company_name'])

        # Try alias table
        cursor.execute("""
            SELECT c.id, c.ticker, c.company_name
            FROM companies c
            JOIN company_aliases ca ON c.id = ca.company_id
            WHERE LOWER(ca.alias) = LOWER(%s)
               OR LOWER(ca.alias) LIKE LOWER(%s)
        """, (search_term, f'%{search_term}%'))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return (row['id'], row['ticker'], row['company_name'])
        return (None, None, None)

    except Exception as e:
        print(f"Error finding company by alias: {e}")
        return (None, None, None)

def close_response(session_attributes, fulfillment_state, message):
    """Build Lex V2 response"""
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'state': fulfillment_state
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }

def handle_welcome(event):
    """Handle welcome/help intent"""
    message = """Welcome to the Cyber Risk Dashboard Assistant! I can help you with:

- List available companies
- Get information about specific companies
- Check sentiment analysis results
- View forecast predictions
- Check document inventory (SEC filings, transcripts)
- View growth metrics and hiring trends
- Add or remove companies
- Explain dashboard features

Just ask me something like:
- "What companies are available?"
- "Tell me about CrowdStrike"
- "What documents do I have for CRWD?"
- "Show growth metrics for Palo Alto"

Tip: I understand variations like "crowdstrike", "CRWD", "crowd strike" - all map to the same company!"""

    return close_response({}, 'Fulfilled', message)

def handle_list_companies(event):
    """List all companies in the database"""
    try:
        # Check if user is asking for a count
        utterance = event.get('inputTranscript', '').lower()
        is_count_query = 'how many' in utterance or 'count' in utterance or 'number of' in utterance

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT DISTINCT company_name, ticker
            FROM companies
            ORDER BY company_name
        """)
        companies = cursor.fetchall()
        cursor.close()
        conn.close()

        if companies:
            count = len(companies)
            if is_count_query:
                message = f"The dashboard currently tracks {count} cybersecurity companies.\n\nSay 'list companies' to see the full list, or ask about a specific company like 'Tell me about CrowdStrike'."
            else:
                company_list = "\n".join([f"- {c['company_name']} ({c['ticker']})" for c in companies])
                message = f"Here are the {count} companies available in the dashboard:\n\n{company_list}\n\nAsk me about any of these companies for more details!"
        else:
            message = "No companies are currently loaded in the database. Please check the data migration status."

    except Exception as e:
        message = f"I'm having trouble accessing the database. The dashboard may still be initializing. Error: {str(e)}"

    return close_response({}, 'Fulfilled', message)

def handle_company_info(event):
    """Get information about a specific company"""
    slots = event['sessionState']['intent']['slots']
    company_name = slots.get('CompanyName', {}).get('value', {}).get('interpretedValue', '')

    if not company_name:
        return close_response({}, 'Failed', "I didn't catch the company name. Could you please specify which company you'd like information about?")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get company info
        cursor.execute("""
            SELECT c.company_name, c.ticker, c.sector,
                   COUNT(DISTINCT a.id) as artifact_count,
                   MIN(a.published_date) as earliest_date,
                   MAX(a.published_date) as latest_date
            FROM companies c
            LEFT JOIN artifacts a ON c.id = a.company_id
            WHERE LOWER(c.company_name) LIKE LOWER(%s)
               OR LOWER(c.ticker) = LOWER(%s)
            GROUP BY c.id, c.company_name, c.ticker, c.sector
        """, (f'%{company_name}%', company_name))

        company = cursor.fetchone()
        cursor.close()
        conn.close()

        if company:
            message = f"""Here's what I know about {company['company_name']} ({company['ticker']}):

Sector: {company['sector'] or 'Cybersecurity'}
Total Documents: {company['artifact_count']}
Data Range: {company['earliest_date']} to {company['latest_date']}

You can view detailed analysis on the dashboard including:
- SEC filings and earnings call transcripts
- Sentiment analysis using AWS Comprehend
- Stock price forecasts using Prophet

Would you like to know about sentiment or forecasts for this company?"""
        else:
            message = f"I couldn't find a company matching '{company_name}'. Try asking me to list all available companies."

    except Exception as e:
        message = f"I encountered an error looking up that company: {str(e)}"

    return close_response({}, 'Fulfilled', message)

def handle_sentiment_analysis(event):
    """Get sentiment analysis for a company"""
    # Try to get company from slots first
    slots = event['sessionState']['intent']['slots'] or {}
    company_name = None
    if slots.get('CompanyName'):
        company_name = slots['CompanyName'].get('value', {}).get('interpretedValue', '')

    # If no slot, extract from utterance
    if not company_name:
        utterance = event.get('inputTranscript', '')
        extracted_name, extracted_ticker = extract_company_from_utterance(utterance)
        if extracted_ticker:
            company_name = extracted_ticker
        elif extracted_name:
            company_name = extracted_name

    if not company_name:
        return close_response({}, 'Failed', "Which company would you like sentiment analysis for? Try saying 'sentiment for CrowdStrike' or 'sentiment for CRWD'.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT c.company_name, c.ticker,
                   AVG(CASE WHEN s.sentiment = 'POSITIVE' THEN 1
                            WHEN s.sentiment = 'NEGATIVE' THEN -1
                            ELSE 0 END) as avg_sentiment,
                   COUNT(*) as analyzed_docs,
                   SUM(CASE WHEN s.sentiment = 'POSITIVE' THEN 1 ELSE 0 END) as positive_count,
                   SUM(CASE WHEN s.sentiment = 'NEGATIVE' THEN 1 ELSE 0 END) as negative_count,
                   SUM(CASE WHEN s.sentiment = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral_count
            FROM companies c
            JOIN artifacts a ON c.id = a.company_id
            JOIN sentiment_analysis s ON a.id = s.artifact_id
            WHERE LOWER(c.company_name) LIKE LOWER(%s)
               OR LOWER(c.ticker) = LOWER(%s)
            GROUP BY c.id, c.company_name, c.ticker
        """, (f'%{company_name}%', company_name))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            sentiment_label = "Positive" if result['avg_sentiment'] > 0.1 else "Negative" if result['avg_sentiment'] < -0.1 else "Neutral"
            message = f"""Sentiment Analysis for {result['company_name']} ({result['ticker']}):

Overall Sentiment: {sentiment_label}
Documents Analyzed: {result['analyzed_docs']}

Breakdown:
- Positive: {result['positive_count']} documents
- Neutral: {result['neutral_count']} documents
- Negative: {result['negative_count']} documents

This analysis is powered by AWS Comprehend, which examines SEC filings and earnings call transcripts to determine market sentiment."""
        else:
            message = f"I don't have sentiment data for '{company_name}'. The company may not be in our database or analysis hasn't been run yet."

    except Exception as e:
        message = f"I encountered an error retrieving sentiment data: {str(e)}"

    return close_response({}, 'Fulfilled', message)

def handle_forecast(event):
    """Get forecast information for a company"""
    # Try to get company from slots first
    slots = event['sessionState']['intent']['slots'] or {}
    company_name = None
    if slots.get('CompanyName'):
        company_name = slots['CompanyName'].get('value', {}).get('interpretedValue', '')

    # If no slot, extract from utterance
    if not company_name:
        utterance = event.get('inputTranscript', '')
        extracted_name, extracted_ticker = extract_company_from_utterance(utterance)
        if extracted_ticker:
            company_name = extracted_ticker
        elif extracted_name:
            company_name = extracted_name

    if not company_name:
        return close_response({}, 'Failed', "Which company would you like a forecast for?")

    message = f"""Forecast information for {company_name}:

The dashboard uses Facebook Prophet for time series forecasting of stock prices. The forecast includes:

- 30-day price predictions
- Confidence intervals (upper and lower bounds)
- Trend analysis and seasonality detection

To view the actual forecast chart and predictions, please visit the Forecast tab on the dashboard and select {company_name} from the dropdown.

Note: Forecasts are for educational purposes and should not be considered financial advice."""

    return close_response({}, 'Fulfilled', message)

def handle_dashboard_features(event):
    """Explain dashboard features"""
    message = """The Cyber Risk Dashboard has four main sections:

1. **Company Overview** - View company metrics, stock prices, and key statistics

2. **Sentiment Analysis** - AWS Comprehend analyzes SEC filings and earnings calls to determine market sentiment, showing positive/negative/neutral trends and key phrases

3. **Forecast** - Prophet-based stock price predictions with 30-day forecasts and confidence intervals

4. **AI Assistant** (You're using it now!) - Amazon Lex-powered chatbot to help navigate the dashboard

Data Sources:
- SEC EDGAR filings (10-K, 10-Q, 8-K)
- Earnings call transcripts
- Historical stock prices

The dashboard focuses on cybersecurity companies: CrowdStrike, Palo Alto Networks, Fortinet, Zscaler, and SentinelOne."""

    return close_response({}, 'Fulfilled', message)

def handle_add_company(event):
    """Handle adding a new company to the database"""
    # Get the user's utterance to extract company info
    utterance = event.get('inputTranscript', '')
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

    # Check if we're in a conversation flow (collecting company details)
    pending_action = session_attributes.get('pending_action')

    if pending_action == 'add_company_name':
        # User is providing company name
        company_name = utterance.strip()
        session_attributes['company_name'] = company_name
        session_attributes['pending_action'] = 'add_company_ticker'
        return elicit_response(session_attributes, "AddCompanyIntent",
            f"Got it! The company name is '{company_name}'. What is the stock ticker symbol? (e.g., CRWD, PANW)")

    elif pending_action == 'add_company_ticker':
        # User is providing ticker
        ticker = utterance.strip().upper()
        company_name = session_attributes.get('company_name', 'Unknown')

        # Clear session state
        session_attributes.pop('pending_action', None)
        session_attributes.pop('company_name', None)

        # Try to add to database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if already exists
            cursor.execute("SELECT * FROM companies WHERE ticker = %s", (ticker,))
            existing = cursor.fetchone()

            if existing:
                cursor.close()
                conn.close()
                return close_response(session_attributes, 'Fulfilled',
                    f"The company {ticker} already exists in the database as '{existing['company_name']}'.")

            # Insert new company
            cursor.execute("""
                INSERT INTO companies (company_name, ticker, sector)
                VALUES (%s, %s, 'Cybersecurity')
                RETURNING id, company_name, ticker
            """, (company_name, ticker))

            new_company = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            message = f"""Successfully added {new_company['company_name']} ({new_company['ticker']}) to the dashboard!

You can now:
- Ask for sentiment analysis: "What is the sentiment for {ticker}?"
- View forecasts: "Show forecast for {ticker}"
- Get company info: "Tell me about {ticker}"

Note: You'll need to add SEC filings and earnings transcripts to S3 before full analysis is available."""

            return close_response(session_attributes, 'Fulfilled', message)

        except Exception as e:
            return close_response(session_attributes, 'Failed',
                f"Sorry, I couldn't add the company. Error: {str(e)}")

    # First interaction - try to extract company from utterance
    company_name, ticker = extract_company_from_utterance(utterance)

    if company_name and ticker:
        # We have both - try to add directly
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if already exists
            cursor.execute("SELECT * FROM companies WHERE ticker = %s", (ticker,))
            existing = cursor.fetchone()

            if existing:
                cursor.close()
                conn.close()
                return close_response(session_attributes, 'Fulfilled',
                    f"Good news! {company_name} ({ticker}) is already in the dashboard. You can start analyzing it right away!")

            # Insert new company
            cursor.execute("""
                INSERT INTO companies (company_name, ticker, sector)
                VALUES (%s, %s, 'Cybersecurity')
                RETURNING id, company_name, ticker
            """, (company_name, ticker))

            new_company = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            message = f"""Successfully added {new_company['company_name']} ({new_company['ticker']}) to the dashboard!

You can now ask me about this company's sentiment analysis or forecasts."""

            return close_response(session_attributes, 'Fulfilled', message)

        except Exception as e:
            return close_response(session_attributes, 'Failed',
                f"Sorry, I couldn't add the company. Error: {str(e)}")

    elif ticker:
        # We have a ticker but need company name
        session_attributes['pending_action'] = 'add_company_ticker'
        session_attributes['company_name'] = f"Company {ticker}"  # Placeholder
        return elicit_response(session_attributes, "AddCompanyIntent",
            f"I found the ticker {ticker}. What is the full company name?")

    else:
        # Need to ask for company details
        session_attributes['pending_action'] = 'add_company_name'
        return elicit_response(session_attributes, "AddCompanyIntent",
            "I'd be happy to help you add a new company! What is the company name?")


def handle_remove_company(event):
    """Handle removing a company from the database"""
    utterance = event.get('inputTranscript', '')
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

    # Check if we're confirming deletion
    pending_action = session_attributes.get('pending_action')

    if pending_action == 'confirm_remove':
        ticker = session_attributes.get('remove_ticker', '')
        company_name = session_attributes.get('remove_company_name', '')

        # Clear session state
        session_attributes.pop('pending_action', None)
        session_attributes.pop('remove_ticker', None)
        session_attributes.pop('remove_company_name', None)

        # Check for confirmation
        if any(word in utterance.lower() for word in ['yes', 'confirm', 'delete', 'remove', 'ok', 'sure']):
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM companies WHERE ticker = %s", (ticker,))
                deleted = cursor.rowcount > 0
                conn.commit()
                cursor.close()
                conn.close()

                if deleted:
                    return close_response(session_attributes, 'Fulfilled',
                        f"Done! {company_name} ({ticker}) has been removed from the dashboard.")
                else:
                    return close_response(session_attributes, 'Fulfilled',
                        f"Hmm, I couldn't find {ticker} in the database. It may have already been removed.")

            except Exception as e:
                return close_response(session_attributes, 'Failed',
                    f"Sorry, I couldn't remove the company. Error: {str(e)}")
        else:
            return close_response(session_attributes, 'Fulfilled',
                f"OK, I won't remove {company_name}. The company will remain in the dashboard.")

    # Try to extract company from utterance
    company_name, ticker = extract_company_from_utterance(utterance)

    if ticker:
        # Look up the company
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM companies WHERE ticker = %s", (ticker,))
            company = cursor.fetchone()
            cursor.close()
            conn.close()

            if company:
                session_attributes['pending_action'] = 'confirm_remove'
                session_attributes['remove_ticker'] = ticker
                session_attributes['remove_company_name'] = company['company_name']
                return elicit_response(session_attributes, "RemoveCompanyIntent",
                    f"Are you sure you want to remove {company['company_name']} ({ticker}) from the dashboard? This will delete any cached data. Reply 'yes' to confirm or 'no' to cancel.")
            else:
                return close_response(session_attributes, 'Fulfilled',
                    f"I couldn't find a company with ticker {ticker} in the database. Use 'list companies' to see available companies.")

        except Exception as e:
            return close_response(session_attributes, 'Failed',
                f"Sorry, I encountered an error: {str(e)}")

    else:
        # Ask which company to remove
        return elicit_response(session_attributes, "RemoveCompanyIntent",
            "Which company would you like to remove? Please provide the company name or ticker symbol.")


def elicit_response(session_attributes, intent_name, message):
    """Build Lex V2 response that elicits more information"""
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ElicitIntent'
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }


def handle_document_inventory(event):
    """Handle document inventory queries - shows what documents are available for a company"""
    utterance = event.get('inputTranscript', '')
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

    # Try to extract company from utterance
    company_name, ticker = extract_company_from_utterance(utterance)

    # If we got a ticker from the static map, try database lookup for more details
    if ticker:
        company_id, db_ticker, db_company_name = find_company_by_alias(ticker)
        if db_ticker:
            ticker = db_ticker
            company_name = db_company_name
    elif not company_name:
        # Try to find any company name in the utterance using database aliases
        words = utterance.lower().split()
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                phrase = ' '.join(words[i:j])
                company_id, db_ticker, db_company_name = find_company_by_alias(phrase)
                if db_ticker:
                    ticker = db_ticker
                    company_name = db_company_name
                    break
            if ticker:
                break

    if not ticker:
        return elicit_response(session_attributes, "DocumentInventoryIntent",
            "Which company would you like to see the document inventory for? Please provide the company name or ticker.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get document inventory
        cursor.execute("""
            SELECT
                artifact_type,
                COUNT(*) as doc_count,
                MIN(published_date) as earliest_date,
                MAX(published_date) as latest_date
            FROM artifacts a
            JOIN companies c ON a.company_id = c.id
            WHERE LOWER(c.ticker) = LOWER(%s)
            GROUP BY artifact_type
            ORDER BY doc_count DESC
        """, (ticker,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if rows:
            doc_list = []
            total_docs = 0
            for row in rows:
                doc_type = row['artifact_type']
                count = row['doc_count']
                total_docs += count
                earliest = row['earliest_date'].strftime('%Y-%m-%d') if row['earliest_date'] else 'N/A'
                latest = row['latest_date'].strftime('%Y-%m-%d') if row['latest_date'] else 'N/A'
                doc_list.append(f"- {doc_type}: {count} documents ({earliest} to {latest})")

            message = f"""Document Inventory for {company_name} ({ticker}):

Total Documents: {total_docs}

{chr(10).join(doc_list)}

You can analyze sentiment on these documents by asking "What is the sentiment for {ticker}?" """
        else:
            message = f"""I don't have any documents for {company_name} ({ticker}) in the database yet.

To add documents, you'll need to:
1. Upload SEC filings (10-K, 10-Q) to S3
2. Upload earnings call transcripts to S3
3. Run the data migration script

Would you like to add a different company instead?"""

        return close_response(session_attributes, 'Fulfilled', message)

    except Exception as e:
        return close_response(session_attributes, 'Failed',
            f"Sorry, I couldn't retrieve the document inventory. Error: {str(e)}")


def handle_growth_metrics(event):
    """Handle growth metrics queries - shows employee and hiring trends"""
    utterance = event.get('inputTranscript', '')
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

    # Try to extract company from utterance
    company_name, ticker = extract_company_from_utterance(utterance)

    if ticker:
        company_id, db_ticker, db_company_name = find_company_by_alias(ticker)
        if db_ticker:
            ticker = db_ticker
            company_name = db_company_name

    if not ticker:
        return elicit_response(session_attributes, "GrowthMetricsIntent",
            "Which company would you like to see growth metrics for? Please provide the company name or ticker.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get the company ID
        cursor.execute("SELECT id FROM companies WHERE LOWER(ticker) = LOWER(%s)", (ticker,))
        company_row = cursor.fetchone()

        if not company_row:
            cursor.close()
            conn.close()
            return close_response(session_attributes, 'Fulfilled',
                f"I couldn't find {ticker} in the database. Try listing companies first.")

        company_id = company_row['id']

        # Get latest employee count
        cursor.execute("""
            SELECT employee_count, snapshot_date
            FROM employee_counts
            WHERE company_id = %s
            ORDER BY snapshot_date DESC
            LIMIT 1
        """, (company_id,))
        emp_row = cursor.fetchone()

        # Get hiring event count (last 90 days)
        cursor.execute("""
            SELECT COUNT(*) as event_count
            FROM hiring_events
            WHERE company_id = %s
              AND event_date >= CURRENT_DATE - 90
              AND event_type = 'job_posting'
        """, (company_id,))
        hiring_row = cursor.fetchone()

        # Get growth trend
        cursor.execute("""
            SELECT trend_classification, trend_value, computed_at
            FROM growth_trends
            WHERE company_id = %s AND metric_type = 'overall'
            ORDER BY computed_at DESC
            LIMIT 1
        """, (company_id,))
        trend_row = cursor.fetchone()

        cursor.close()
        conn.close()

        # Build response message
        parts = [f"Growth Metrics for {company_name} ({ticker}):\n"]

        if emp_row:
            parts.append(f"Employee Count: {emp_row['employee_count']:,} (as of {emp_row['snapshot_date']})")
        else:
            parts.append("Employee Count: Data not yet available")

        if hiring_row:
            event_count = hiring_row['event_count']
            if event_count > 50:
                hiring_status = f"Very Active ({event_count} job postings in last 90 days)"
            elif event_count > 20:
                hiring_status = f"Active ({event_count} job postings in last 90 days)"
            elif event_count > 5:
                hiring_status = f"Moderate ({event_count} job postings in last 90 days)"
            else:
                hiring_status = f"Limited ({event_count} job postings in last 90 days)"
            parts.append(f"Hiring Activity: {hiring_status}")
        else:
            parts.append("Hiring Activity: Data not yet available")

        if trend_row:
            trend = trend_row['trend_classification'].title()
            parts.append(f"Growth Trend: {trend}")
        else:
            parts.append("Growth Trend: Not enough data to calculate")

        parts.append("\nNote: Growth data is sourced from Explorium and updated periodically.")
        parts.append("View the Company Growth tab on the dashboard for detailed charts.")

        message = '\n'.join(parts)
        return close_response(session_attributes, 'Fulfilled', message)

    except Exception as e:
        return close_response(session_attributes, 'Failed',
            f"Sorry, I couldn't retrieve growth metrics. Error: {str(e)}")


def handle_fallback(event):
    """Handle unrecognized input"""
    message = """I'm not sure I understood that. Here are some things you can ask me:

- "What companies are available?"
- "Tell me about CrowdStrike"
- "What is the sentiment for Palo Alto Networks?"
- "Show me the forecast for Fortinet"
- "What features does the dashboard have?"
- "What documents do I have for CRWD?" (NEW!)
- "Show growth metrics for Palo Alto" (NEW!)
- "Add a new company"
- "Remove a company"

Or just say "help" to see all options."""

    return close_response({}, 'Fulfilled', message)

def handler(event, context):
    """Main Lambda handler for Lex V2"""
    print(f"Event: {json.dumps(event)}")

    intent_name = event['sessionState']['intent']['name']

    intent_handlers = {
        'WelcomeIntent': handle_welcome,
        'ListCompaniesIntent': handle_list_companies,
        'CompanyInfoIntent': handle_company_info,
        'SentimentAnalysisIntent': handle_sentiment_analysis,
        'ForecastIntent': handle_forecast,
        'DashboardFeaturesIntent': handle_dashboard_features,
        'AddCompanyIntent': handle_add_company,
        'RemoveCompanyIntent': handle_remove_company,
        'DocumentInventoryIntent': handle_document_inventory,
        'GrowthMetricsIntent': handle_growth_metrics,
        'FallbackIntent': handle_fallback
    }

    handler_func = intent_handlers.get(intent_name, handle_fallback)
    response = handler_func(event)

    # Add intent name to response if not already present
    if 'intent' not in response['sessionState']:
        response['sessionState']['intent'] = {}
    response['sessionState']['intent']['name'] = intent_name

    print(f"Response: {json.dumps(response)}")
    return response
