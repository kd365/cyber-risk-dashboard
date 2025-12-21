from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
import sys
import os

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.s3_service import S3ArtifactService
from backend.services.comprehend_service import ComprehendService
from backend.services.sentiment_cache import SentimentCache
from backend.services.forecast_cache import ForecastCache
from backend.services.growth_cache import GrowthCache
from backend.services.explorium_service import ExploriumService, get_company_domain
from backend.services.lex_service import LexService
from backend.services.database_service import db_service
from backend.models.time_series_forecaster import CyberRiskForecaster
import traceback

app = Flask(__name__)
CORS(app)

# Initialize services
s3_service = S3ArtifactService()
comprehend_service = ComprehendService()
sentiment_cache = SentimentCache(ttl_seconds=86400)  # 24 hour cache (now RDS-backed)
forecast_cache = ForecastCache()  # RDS-backed forecast cache
growth_cache = GrowthCache(cache_ttl_hours=24)  # RDS-backed growth/Explorium cache
explorium_service = ExploriumService()  # API key from EXPLORIUM_API_KEY env var
lex_service = LexService()  # Bot ID/Alias from env vars or Terraform outputs
forecasters = {}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'cyber-risk-api'})

# ============================================================================
# ARTIFACT PROXY - Allow frontend to access S3 documents
# ============================================================================

@app.route('/api/artifact-proxy', methods=['GET'])
def artifact_proxy():
    """Proxy for accessing S3 documents with presigned URLs"""
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400

        # If it's already a full S3 URL, redirect to it
        if url.startswith('http'):
            return redirect(url, code=302)

        # Otherwise, it might be an S3 key - get presigned URL
        presigned = s3_service.get_presigned_url(url)
        if presigned:
            return redirect(presigned, code=302)
        else:
            return jsonify({'error': 'Could not generate presigned URL'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/artifact-url', methods=['GET'])
def artifact_url():
    """Get presigned S3 URL as JSON (for frontend to handle redirect)"""
    try:
        s3_key = request.args.get('key')
        if not s3_key:
            return jsonify({'error': 'No S3 key provided'}), 400

        # Generate presigned URL
        presigned = s3_service.get_presigned_url(s3_key)
        if presigned:
            return jsonify({'url': presigned})
        else:
            return jsonify({'error': 'Could not generate presigned URL'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ARTIFACT ENDPOINTS
# ============================================================================

@app.route('/api/artifacts', methods=['GET'])
def get_artifacts():
    """Get all artifacts from database (with S3 fallback)"""
    try:
        # Try database first
        artifacts = db_service.get_all_artifacts()
        if artifacts:
            return jsonify(artifacts)

        # Fallback to S3 if database is empty
        artifacts = s3_service.get_artifacts_table()
        return jsonify(artifacts)
    except Exception as e:
        print(f"Error getting artifacts: {e}")
        traceback.print_exc()
        # Fallback to S3 on any error
        try:
            artifacts = s3_service.get_artifacts_table()
            return jsonify(artifacts)
        except:
            return jsonify({'error': str(e)}), 500

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Get company list from database (with S3 fallback)"""
    try:
        # Try database first (includes dynamically added companies)
        db_companies = db_service.get_all_companies()
        if db_companies:
            # Transform to frontend format (use 'name' instead of 'company_name')
            companies = []
            for db_c in db_companies:
                company = {
                    'name': db_c.get('company_name'),
                    'ticker': db_c.get('ticker', '').upper(),
                    'description': db_c.get('description', ''),
                    'exchange': db_c.get('exchange', ''),
                    'location': db_c.get('location', ''),
                    'sector': db_c.get('sector', 'Cybersecurity'),
                    'alternate_names': db_c.get('alternate_names', '')
                }
                companies.append(company)

            return jsonify(companies)

        # Fallback to S3 if database is empty
        companies = s3_service.get_companies()
        return jsonify(companies)
    except Exception as e:
        print(f"Error getting companies: {e}")
        traceback.print_exc()
        # Fallback to S3 on any error
        try:
            companies = s3_service.get_companies()
            return jsonify(companies)
        except:
            return jsonify({'error': str(e)}), 500

# ============================================================================
# COMPANY CRUD ENDPOINTS (Database-backed)
# ============================================================================

@app.route('/api/companies/db', methods=['GET'])
def get_companies_db():
    """Get all companies from database"""
    try:
        companies = db_service.get_all_companies()
        return jsonify(companies)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/companies/db/<ticker>', methods=['GET'])
def get_company_db(ticker):
    """Get a specific company by ticker from database"""
    try:
        company = db_service.get_company(ticker.upper())
        if company:
            return jsonify(company)
        else:
            return jsonify({'error': f'Company not found: {ticker}'}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/companies/db', methods=['POST'])
def create_company():
    """
    Create a new company in the database

    Request body:
        {
            "company_name": "Company Full Name",
            "ticker": "TICK",
            "sector": "Cybersecurity"  (optional)
        }

    Returns:
        Created company or error
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        company_name = data.get('company_name')
        ticker = data.get('ticker')
        sector = data.get('sector', 'Cybersecurity')

        if not company_name or not ticker:
            return jsonify({'error': 'company_name and ticker are required'}), 400

        # Check if company already exists
        if db_service.company_exists(ticker):
            return jsonify({'error': f'Company already exists: {ticker}'}), 409

        company = db_service.create_company(company_name, ticker, sector)
        if company:
            return jsonify({
                'status': 'success',
                'message': f'Company {ticker} created successfully',
                'company': company
            }), 201
        else:
            return jsonify({'error': 'Failed to create company'}), 500

    except Exception as e:
        print(f"Error creating company: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/companies/db/<ticker>', methods=['PUT'])
def update_company(ticker):
    """
    Update a company in the database

    Request body:
        {
            "company_name": "New Name",  (optional)
            "sector": "New Sector"  (optional)
        }

    Returns:
        Updated company or error
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        company_name = data.get('company_name')
        sector = data.get('sector')

        company = db_service.update_company(ticker, company_name, sector)
        if company:
            return jsonify({
                'status': 'success',
                'message': f'Company {ticker} updated successfully',
                'company': company
            })
        else:
            return jsonify({'error': f'Company not found: {ticker}'}), 404

    except Exception as e:
        print(f"Error updating company: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/companies/db/<ticker>', methods=['DELETE'])
def delete_company(ticker):
    """Delete a company from the database"""
    try:
        deleted = db_service.delete_company(ticker)
        if deleted:
            return jsonify({
                'status': 'success',
                'message': f'Company {ticker} deleted successfully'
            })
        else:
            return jsonify({'error': f'Company not found: {ticker}'}), 404

    except Exception as e:
        print(f"Error deleting company: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-artifacts', methods=['GET'])
def get_all_artifacts():
    """Get all artifacts from all companies (database with S3 fallback)"""
    try:
        # Try database first
        artifacts = db_service.get_all_artifacts()
        if artifacts:
            return jsonify(artifacts)

        # Fallback to S3
        artifacts = s3_service.get_artifacts_table()
        return jsonify(artifacts)
    except Exception as e:
        print(f"Error getting all artifacts: {e}")
        try:
            artifacts = s3_service.get_artifacts_table()
            return jsonify(artifacts)
        except:
            return jsonify({'error': str(e)}), 500

@app.route('/api/artifacts/<ticker>', methods=['GET'])
def get_company_artifacts(ticker):
    """Get artifacts for specific company (database with S3 fallback)"""
    try:
        # Try database first
        artifacts = db_service.get_artifacts_by_ticker(ticker.upper())
        if artifacts:
            return jsonify(artifacts)

        # Fallback to S3
        artifacts = s3_service.get_artifacts_by_ticker(ticker.upper())
        return jsonify(artifacts)
    except Exception as e:
        print(f"Error getting artifacts for {ticker}: {e}")
        try:
            artifacts = s3_service.get_artifacts_by_ticker(ticker.upper())
            return jsonify(artifacts)
        except:
            return jsonify({'error': str(e)}), 500

@app.route('/api/artifacts/status/<ticker>', methods=['GET'])
def get_artifact_status(ticker):
    """Get status of what documents exist for a ticker"""
    try:
        status = s3_service.check_existing_documents(ticker.upper())
        needed = s3_service.get_documents_to_fetch(ticker.upper())
        
        return jsonify({
            'status': status,
            'to_fetch': needed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/document/<path:filename>', methods=['GET'])
def get_document(filename):
    """Get presigned URL for document"""
    try:
        # Determine if SEC or transcript based on filename
        if '_10-K_' in filename or '_10-Q_' in filename:
            s3_key = f'raw/sec/{filename}'
        else:
            s3_key = f'raw/transcripts/{filename}'
        
        url = s3_service.get_presigned_url(s3_key)
        
        if url:
            return jsonify({'url': url, 'filename': filename})
        else:
            return jsonify({'error': 'Document not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FORECAST ENDPOINTS
# ============================================================================

@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    """
    Get Prophet forecast for a ticker

    Query params:
        ticker: Stock ticker symbol (default: MSFT)
        days: Forecast horizon in days (default: 30)
        refresh: If 'true', force recomputation (bypass cache)
    """
    ticker = request.args.get('ticker', 'MSFT').upper()
    days = int(request.args.get('days', 30))
    refresh = request.args.get('refresh', 'false').lower() == 'true'

    try:
        # Check cache first (unless refresh is requested)
        if not refresh:
            cached_data = forecast_cache.get(ticker, days)
            if cached_data:
                cached_data['from_cache'] = True
                return jsonify(cached_data)

        # If refresh requested, invalidate cache for this ticker
        if refresh:
            forecast_cache.invalidate(ticker)
            # Also clear in-memory model to force retrain
            if ticker in forecasters:
                del forecasters[ticker]

        # Train model if needed
        if ticker not in forecasters:
            print(f"Training new model for {ticker}...")
            forecasters[ticker] = CyberRiskForecaster(ticker)
            forecasters[ticker].fetch_stock_data(period='2y')
            forecasters[ticker].add_cybersecurity_sentiment(mock=False)  # Use real sentiment
            forecasters[ticker].add_volatility_regressor()
            forecasters[ticker].train()
            print(f"Model ready for {ticker}")

        results = forecasters[ticker].forecast(days_ahead=days)

        # Convert forecast DataFrame to list
        forecast_data = results['forecast_df'][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict('records')

        # Convert historical DataFrame to list
        historical_data = results['historical_df'].to_dict('records')

        # Get today's date as the cutoff between historical and forecast
        import datetime
        today = datetime.date.today().isoformat()

        response_data = {
            'ticker': ticker,
            'current_price': float(results['current_price']),
            'predicted_price': float(results['predicted_price']),
            'expected_return_pct': float(results['expected_return_pct']),
            'confidence_interval': {
                'lower': float(results['confidence_lower']),
                'upper': float(results['confidence_upper'])
            },
            'forecast': forecast_data,
            'historical': historical_data,
            'today': today,
            'from_cache': False
        }

        # Cache the results
        forecast_cache.set(ticker, days, response_data)

        return jsonify(response_data)

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/evaluate/<ticker>', methods=['GET'])
def evaluate_model(ticker):
    """Get model evaluation metrics"""
    ticker = ticker.upper()
    
    try:
        if ticker not in forecasters:
            return jsonify({'error': 'Model not trained yet. Call /api/forecast first.'}), 404
        
        evaluation = forecasters[ticker].evaluate(test_days=30)
        
        return jsonify({
            'ticker': ticker,
            'mape': float(evaluation['mape']),
            'rmse': float(evaluation['rmse']),
            'mae': float(evaluation['mae']),
            'directional_accuracy': float(evaluation['directional_accuracy']),
            'test_days': evaluation['test_days']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SCRAPING STATUS ENDPOINT (Placeholder)
# ============================================================================

@app.route('/api/scraping/status', methods=['GET'])
def get_scraping_status():
    """Get scraping progress status"""
    scrape_type = request.args.get('type', 'sec')
    
    # TODO: Read from S3 status files
    # For now, return mock status
    return jsonify({
        'running': False,
        'progress': 100,
        'message': 'No scraping in progress',
        'type': scrape_type
    })

@app.route('/api/scraping/start', methods=['POST'])
def start_scraping():
    """Start scraping process"""
    data = request.json
    scrape_type = data.get('type', 'sec')
    companies = data.get('companies', [])

    # TODO: Trigger scraping scripts
    # For now, return success
    return jsonify({
        'status': 'started',
        'type': scrape_type,
        'companies': companies,
        'message': 'Scraping initiated (not yet implemented)'
    })

# ============================================================================
# SENTIMENT ANALYSIS ENDPOINTS (AWS Comprehend NLP)
# ============================================================================

@app.route('/api/sentiment/<ticker>', methods=['GET'])
def get_sentiment_analysis(ticker):
    """
    Get comprehensive sentiment analysis for a ticker using AWS Comprehend

    Query params:
        include_entities: Include entity recognition (default: true)
        refresh: If 'true', force recomputation (bypass cache)

    Returns:
        - Overall sentiment across all documents
        - Word frequency analysis
        - Entity recognition (organizations, people, products)
        - Key phrases
        - SEC vs Transcript comparison
        - Sentiment timeline
    """
    try:
        ticker = ticker.upper()
        refresh = request.args.get('refresh', 'false').lower() == 'true'

        # Get all artifacts for this ticker
        artifacts = s3_service.get_artifacts_table()

        # If refresh requested, invalidate cache for this ticker
        if refresh:
            sentiment_cache.invalidate(ticker)

        # Check cache first (unless refresh is requested)
        if not refresh:
            cached_data = sentiment_cache.get(ticker, artifacts)
            if cached_data:
                cached_data['from_cache'] = True
                return jsonify(cached_data)

        # Perform comprehensive sentiment analysis
        print(f"Analyzing sentiment for {ticker}...")

        # Check if entities should be included
        include_entities = request.args.get('include_entities', 'true').lower() == 'true'

        sentiment_data = comprehend_service.analyze_ticker_sentiment(
            ticker,
            artifacts,
            include_entities=include_entities
        )

        if not sentiment_data:
            return jsonify({
                'error': 'No documents found for sentiment analysis',
                'ticker': ticker
            }), 404

        sentiment_data['from_cache'] = False

        # Cache the results
        sentiment_cache.set(ticker, artifacts, sentiment_data)

        print(f"Sentiment analysis complete for {ticker}")
        return jsonify(sentiment_data)

    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sentiment/<ticker>/timeline', methods=['GET'])
def get_sentiment_timeline(ticker):
    """Get sentiment timeline for a specific ticker"""
    try:
        ticker = ticker.upper()
        artifacts = s3_service.get_artifacts_table()

        sentiment_data = comprehend_service.analyze_ticker_sentiment(ticker, artifacts)

        if not sentiment_data:
            return jsonify({'error': 'No documents found'}), 404

        return jsonify({
            'ticker': ticker,
            'timeline': sentiment_data.get('timeline', [])
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sentiment/<ticker>/words', methods=['GET'])
def get_word_frequency(ticker):
    """Get word frequency analysis for a ticker"""
    try:
        ticker = ticker.upper()
        top_n = int(request.args.get('top_n', 50))

        artifacts = s3_service.get_artifacts_table()
        sentiment_data = comprehend_service.analyze_ticker_sentiment(ticker, artifacts)

        if not sentiment_data:
            return jsonify({'error': 'No documents found'}), 404

        return jsonify({
            'ticker': ticker,
            'words': sentiment_data.get('wordFrequency', [])[:top_n]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sentiment/<ticker>/targeted', methods=['GET'])
def get_targeted_sentiment(ticker):
    """
    Get AWS Comprehend Targeted Sentiment Analysis

    Identifies specific entities (people, products, organizations) and
    determines sentiment toward each one

    Returns:
        Entity-specific sentiment analysis
    """
    try:
        ticker = ticker.upper()
        artifacts = s3_service.get_artifacts_table()

        # Filter for transcripts only (better quality text than SEC PDFs)
        ticker_artifacts = [
            a for a in artifacts
            if a.get('ticker') == ticker
            and 'transcript' in a.get('type', '').lower()
            and a.get('s3_key', '').endswith('.txt')  # Alpha Vantage transcripts only
        ]

        if not ticker_artifacts:
            return jsonify({
                'error': 'No Alpha Vantage transcripts found for targeted sentiment',
                'ticker': ticker
            }), 404

        print(f"Running targeted sentiment analysis for {ticker}...")

        all_targeted_entities = []
        docs_analyzed = 0

        # Analyze a sample of transcripts (targeted sentiment is more expensive)
        for artifact in ticker_artifacts[:5]:  # Limit to 5 docs for cost
            s3_key = artifact.get('s3_key')
            doc_type = artifact.get('type', '')

            if not s3_key:
                continue

            print(f"  Analyzing: {s3_key}")

            text = comprehend_service.get_document_text(s3_key)
            if not text or len(text) < 100:
                continue

            # Analyze first 5000 chars
            sample_text = text[:5000]
            targeted_entities = comprehend_service.detect_targeted_sentiment(sample_text)

            if targeted_entities:
                all_targeted_entities.extend(targeted_entities)
                docs_analyzed += 1

        if not all_targeted_entities:
            return jsonify({
                'error': 'No targeted sentiment data extracted',
                'ticker': ticker
            }), 404

        # Summarize targeted sentiment
        entity_sentiments = comprehend_service._summarize_targeted_sentiment(all_targeted_entities)

        print(f"Extracted targeted sentiment for {len(entity_sentiments)} entities")

        return jsonify({
            'ticker': ticker,
            'documents_analyzed': docs_analyzed,
            'entity_count': len(entity_sentiments),
            'entities': entity_sentiments
        })

    except Exception as e:
        print(f"Error in targeted sentiment: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sentiment/<ticker>/alphavantage', methods=['GET'])
def get_alphavantage_sentiment(ticker):
    """
    Get Alpha Vantage sentiment scores over time for earnings call transcripts

    Returns:
        Timeline of sentiment scores from Alpha Vantage API embedded in transcripts
    """
    try:
        ticker = ticker.upper()
        artifacts = s3_service.get_artifacts_table()

        # Filter for Alpha Vantage transcripts (.txt files)
        transcript_artifacts = [
            a for a in artifacts
            if a.get('ticker') == ticker
            and 'transcript' in a.get('type', '').lower()
            and a.get('s3_key', '').endswith('.txt')  # Alpha Vantage transcripts
        ]

        if not transcript_artifacts:
            return jsonify({
                'error': 'No Alpha Vantage transcripts found',
                'ticker': ticker
            }), 404

        timeline = []

        for artifact in transcript_artifacts:
            s3_key = artifact.get('s3_key')
            date = artifact.get('date')

            print(f"  Extracting Alpha Vantage sentiment from {s3_key}")

            sentiment_data = comprehend_service.extract_alphavantage_sentiment(s3_key)

            if sentiment_data:
                timeline.append({
                    'date': date,
                    's3_key': s3_key,
                    'quarter': s3_key.split('_')[1].replace('transcript.txt', '').strip('_'),
                    'sentiment': sentiment_data
                })

        if not timeline:
            return jsonify({
                'error': 'Could not extract sentiment from transcripts',
                'ticker': ticker
            }), 404

        # Sort by date
        timeline.sort(key=lambda x: x['date'])

        # Calculate overall statistics
        overall_scores = [t['sentiment']['overall_score'] for t in timeline]

        return jsonify({
            'ticker': ticker,
            'timeline': timeline,
            'overall': {
                'average_score': sum(overall_scores) / len(overall_scores),
                'min_score': min(overall_scores),
                'max_score': max(overall_scores),
                'transcript_count': len(timeline)
            }
        })

    except Exception as e:
        print(f"Error extracting Alpha Vantage sentiment: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sentiment/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get sentiment cache statistics"""
    try:
        stats = sentiment_cache.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sentiment/cache/clear', methods=['POST'])
def clear_cache():
    """Clear sentiment cache (optional: specific ticker)"""
    try:
        ticker = request.args.get('ticker')
        sentiment_cache.invalidate(ticker)

        return jsonify({
            'status': 'success',
            'message': f'Cache cleared for {ticker}' if ticker else 'All cache cleared'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FINANCIAL DATA ENDPOINTS (AWS Textract SEC Filing Extraction)
# ============================================================================

@app.route('/api/financials/<ticker>', methods=['GET'])
def get_financials(ticker):
    """
    Extract financial metrics from SEC filings using AWS Textract

    Returns:
        - Revenue, Subscription Revenue, ARR, Net Income, Operating Income, EPS
        - 4-quarter rolling averages for key metrics
        - Timeline of financial data from 10-K and 10-Q filings
    """
    try:
        ticker = ticker.upper()

        # Get all artifacts for this ticker
        artifacts = s3_service.get_artifacts_table()

        # Import and initialize financial extractor
        # Using HTML extractor for modern iXBRL filings (more reliable than Textract)
        from backend.services.financial_html_extractor import FinancialHtmlExtractor
        extractor = FinancialHtmlExtractor()

        print(f"Extracting financial data for {ticker}...")

        # Extract financial data from SEC filings
        financials = extractor.extract_all_financials_for_ticker(ticker, artifacts)

        if not financials:
            return jsonify({
                'error': 'No financial data extracted',
                'ticker': ticker,
                'message': 'No SEC filings found or extraction failed'
            }), 404

        # Calculate rolling averages
        financials_with_avg = extractor.calculate_rolling_averages(financials, window=4)

        # Calculate summary statistics
        latest = financials_with_avg[-1] if financials_with_avg else {}

        summary = {
            'ticker': ticker,
            'latest_filing': {
                'date': latest.get('date'),
                'type': latest.get('type'),
                'revenue': latest.get('revenue'),
                'subscription_revenue': latest.get('subscription_revenue'),
                'arr': latest.get('arr'),
                'net_income': latest.get('net_income'),
                'operating_income': latest.get('operating_income'),
                'eps': latest.get('eps')
            },
            'rolling_averages': {
                'revenue_4q_avg': latest.get('revenue_rolling_avg'),
                'subscription_revenue_4q_avg': latest.get('subscription_revenue_rolling_avg'),
                'net_income_4q_avg': latest.get('net_income_rolling_avg'),
                'operating_income_4q_avg': latest.get('operating_income_rolling_avg')
            },
            'timeline': financials_with_avg,
            'filing_count': len(financials_with_avg)
        }

        print(f"Extracted {len(financials_with_avg)} financial data points")

        return jsonify(summary)

    except Exception as e:
        print(f"Error extracting financials: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# COMPANY GROWTH ENDPOINTS (Explorium API)
# ============================================================================

@app.route('/api/company-growth/<ticker>', methods=['GET'])
def get_company_growth(ticker):
    """
    Get company growth metrics from Explorium API (with RDS caching)

    Query params:
        - refresh: Set to 'true' to bypass cache and fetch fresh data

    Returns:
        - Employee count and headcount history
        - Job posting velocity and trends
        - Employee tenure statistics
        - Hiring trends by department
        - from_cache: Boolean indicating if data came from cache
    """
    refresh = request.args.get('refresh', 'false').lower() == 'true'

    try:
        ticker = ticker.upper()
        request_params = {'ticker': ticker, 'type': 'growth_analysis'}

        # If refresh requested, invalidate cache for this ticker
        if refresh:
            growth_cache.invalidate(ticker)
            print(f"🔄 Refresh requested - cleared growth cache for {ticker}")

        # Check cache first (unless refresh is requested)
        if not refresh:
            cached_data = growth_cache.get_cached_explorium_response(ticker, request_params)
            if cached_data:
                # Ensure it's a dict (might be returned as JSON string)
                if isinstance(cached_data, str):
                    import json
                    cached_data = json.loads(cached_data)
                cached_data['from_cache'] = True
                return jsonify(cached_data)

        print(f"Fetching Explorium growth data for {ticker}...")

        # Get comprehensive growth analysis from Explorium API
        growth_data = explorium_service.get_company_growth_analysis(ticker)

        if not growth_data or not growth_data.get('company'):
            return jsonify({
                'error': 'Company not found in Explorium',
                'ticker': ticker
            }), 404

        response_data = {
            'ticker': ticker,
            'company': growth_data['company'],
            'employee_count': growth_data['employee_count'],
            'headcount_history': growth_data.get('headcount_history', []),
            'job_velocity': growth_data['job_velocity'],
            'tenure_stats': growth_data['tenure_stats'],
            'workforce_trends': growth_data.get('workforce_trends', {}),
            'recent_events': growth_data.get('recent_events', []),
            'data_freshness': growth_data['data_freshness'],
            'from_cache': False
        }

        # Cache the results in RDS
        growth_cache.cache_explorium_response(ticker, request_params, response_data)

        # Also store employee count for historical tracking
        if growth_data.get('employee_count'):
            growth_cache.store_employee_count(ticker, growth_data['employee_count'])

        return jsonify(response_data)

    except Exception as e:
        print(f"Error fetching company growth: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-growth/<ticker>/jobs', methods=['GET'])
def get_company_jobs(ticker):
    """
    Get job posting/hiring events for a company

    Query params:
        - days_back: How many days of events to fetch (default: 90)
    """
    try:
        ticker = ticker.upper()
        days_back = int(request.args.get('days_back', 90))

        # Get company data first
        business = explorium_service.get_business_by_ticker(ticker)
        company_name = business.get('company_name', ticker) if business else ticker

        print(f"Fetching hiring events for {company_name}...")

        # Get business events (includes hiring)
        explorium_id = business.get('explorium_business_id') if business else None
        domain = business.get('domain') if business else get_company_domain(ticker)

        events = explorium_service.get_business_events(
            explorium_id=explorium_id,
            domain=domain,
            days_back=days_back
        )

        # Filter for hiring-related events
        hiring_events = []
        for event in (events or []):
            event_type = str(event.get('event_type', '')).lower()
            if any(x in event_type for x in ['hiring', 'job', 'recruit', 'employee']):
                hiring_events.append({
                    'title': event.get('title', event.get('event_type')),
                    'department': event.get('department', 'N/A'),
                    'location': event.get('location', 'N/A'),
                    'created': event.get('timestamp', event.get('date')),
                    'description_preview': (event.get('description', '') or '')[:200],
                    'url': event.get('url')
                })

        return jsonify({
            'ticker': ticker,
            'company_name': company_name,
            'jobs': hiring_events,
            'total': len(hiring_events),
            'days_back': days_back
        })

    except Exception as e:
        print(f"Error fetching jobs: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-growth/<ticker>/employees', methods=['GET'])
def get_company_employees(ticker):
    """
    Get employee/workforce statistics for a company from Explorium
    """
    try:
        ticker = ticker.upper()

        # Get company data
        business = explorium_service.get_business_by_ticker(ticker)
        company_name = business.get('company_name', ticker) if business else ticker

        print(f"Fetching workforce data for {company_name}...")

        # Get workforce trends from Explorium
        explorium_id = business.get('explorium_business_id') if business else None
        domain = business.get('domain') if business else get_company_domain(ticker)

        workforce = explorium_service.get_workforce_trends(
            explorium_id=explorium_id,
            domain=domain
        )

        # Extract department breakdown from workforce trends
        department_breakdown = {}
        if workforce:
            for key, value in workforce.items():
                if isinstance(value, (int, float)):
                    # Clean up key name for display
                    clean_key = key.replace('_', ' ').title()
                    department_breakdown[clean_key] = value

        # Get tenure stats (Explorium may not have this directly)
        tenure_stats = {
            'avg_tenure_months': None,
            'median_tenure_months': None,
            'sample_size': 0
        }

        return jsonify({
            'ticker': ticker,
            'company_name': company_name,
            'tenure_stats': tenure_stats,
            'department_breakdown': department_breakdown,
            'workforce_trends': workforce or {},
            'sample_size': len(department_breakdown)
        })

    except Exception as e:
        print(f"Error fetching employees: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# LEX CHATBOT ENDPOINTS (Amazon Lex V2 Integration)
# ============================================================================

@app.route('/api/lex/message', methods=['POST'])
def lex_message():
    """
    Send a message to the Lex chatbot and get a response

    Request body:
        {
            "message": "user's message text",
            "sessionId": "optional session ID for conversation context"
        }

    Returns:
        {
            "message": "bot's response",
            "sessionId": "session ID for follow-up messages",
            "intent": "detected intent name",
            "slots": {}
        }
    """
    try:
        data = request.json
        message = data.get('message', '')
        session_id = data.get('sessionId')

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        response = lex_service.send_message(message, session_id)
        return jsonify(response)

    except Exception as e:
        print(f"Error in Lex message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/lex/session', methods=['DELETE'])
def lex_end_session():
    """End a Lex conversation session"""
    try:
        session_id = request.args.get('sessionId')
        if not session_id:
            return jsonify({'error': 'sessionId is required'}), 400

        success = lex_service.end_session(session_id)
        return jsonify({
            'success': success,
            'message': 'Session ended' if success else 'Failed to end session'
        })

    except Exception as e:
        print(f"Error ending Lex session: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Database migrations and maintenance
# ============================================================================

@app.route('/api/admin/migrate', methods=['POST'])
def run_migration():
    """Run database migrations - add alternate_names column to companies"""
    try:
        conn = db_service._get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Add alternate_names column if it doesn't exist
        cursor.execute("""
            ALTER TABLE companies
            ADD COLUMN IF NOT EXISTS alternate_names TEXT
        """)
        conn.commit()

        cursor.close()
        return jsonify({
            'success': True,
            'message': 'Migration completed - alternate_names column added'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/companies/<ticker>/alternate-names', methods=['PUT'])
def set_alternate_names(ticker):
    """Set alternate names for a company"""
    try:
        data = request.get_json()
        alternate_names = data.get('alternate_names', '')

        conn = db_service._get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE companies
            SET alternate_names = %s
            WHERE ticker = %s
        """, (alternate_names, ticker.upper()))
        conn.commit()

        updated = cursor.rowcount
        cursor.close()

        if updated > 0:
            return jsonify({
                'success': True,
                'ticker': ticker.upper(),
                'alternate_names': alternate_names
            })
        else:
            return jsonify({'error': f'Company {ticker} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Cyber Risk Dashboard API...")
    print("Endpoints:")
    print("   - GET  /health")
    print("   - GET  /api/artifacts")
    print("   - GET  /api/companies")
    print("   - GET  /api/artifacts/<ticker>")
    print("   - GET  /api/document/<filename>")
    print("   - GET  /api/forecast?ticker=CRWD&days=30")
    print("   - GET  /api/evaluate/<ticker>")
    print("   - GET  /api/sentiment/<ticker>")
    print("   - GET  /api/sentiment/<ticker>/timeline")
    print("   - GET  /api/sentiment/<ticker>/words")
    print("   - GET  /api/sentiment/cache/stats")
    print("   - POST /api/sentiment/cache/clear")
    print("   - GET  /api/financials/<ticker>")
    print("   - GET  /api/company-growth/<ticker>")
    print("   - GET  /api/company-growth/<ticker>/jobs")
    print("   - GET  /api/company-growth/<ticker>/employees")
    print("   - POST /api/lex/message")
    print("   - DELETE /api/lex/session")
    app.run(host='0.0.0.0', port=5000, debug=True)