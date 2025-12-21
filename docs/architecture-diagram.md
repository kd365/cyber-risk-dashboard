# CyberRisk Dashboard - AWS Architecture

## Project Overview
**Cyber Risk Assessment Dashboard** - A cloud-native application for analyzing cybersecurity company risk profiles using AWS AI services, SEC filings, and financial data.

**Author:** Kathleen Hill
**Date:** December 2025
**Course:** AI/Cloud Computing Class Assessment

---

## High-Level Architecture Diagram

```
                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                      AWS CLOUD (us-west-2)                  │
                                    │                                                             │
    ┌──────────┐                    │  ┌─────────────────────────────────────────────────────┐   │
    │  Users   │                    │  │                    CloudFront CDN                    │   │
    │ (Browser)│◄──────HTTPS───────►│  │              dnes10oz5czsk.cloudfront.net            │   │
    └──────────┘                    │  │  ┌─────────────────────┬─────────────────────────┐   │   │
                                    │  │  │   Default (/*):     │    API (/api/*):        │   │   │
                                    │  │  │   S3 Origin         │    EC2 Origin           │   │   │
                                    │  │  │   (React SPA)       │    (Flask API)          │   │   │
                                    │  │  └──────────┬──────────┴───────────┬─────────────┘   │   │
                                    │  └─────────────┼──────────────────────┼─────────────────┘   │
                                    │                │                      │                     │
                                    │                ▼                      ▼                     │
                                    │  ┌─────────────────────┐   ┌─────────────────────────────┐  │
                                    │  │      S3 Bucket      │   │     VPC (10.0.0.0/16)       │  │
                                    │  │ ─────────────────── │   │                             │  │
                                    │  │  Frontend Hosting   │   │  ┌─────────────────────────┐│  │
                                    │  │  (React Build)      │   │  │   Public Subnet (AZ-a)  ││  │
                                    │  │                     │   │  │      10.0.0.0/24        ││  │
                                    │  │  cyberrisk-dev-kh-  │   │  │  ┌─────────────────────┐││  │
                                    │  │  frontend-u7tro1vp  │   │  │  │    EC2 Instance     │││  │
                                    │  └─────────────────────┘   │  │  │  (Flask + Gunicorn) │││  │
                                    │                            │  │  │   52.41.126.148     │││  │
                                    │  ┌─────────────────────┐   │  │  │   Port 5000         │││  │
                                    │  │   S3 Bucket         │   │  │  └──────────┬──────────┘││  │
                                    │  │ ─────────────────── │   │  │             │           ││  │
                                    │  │  Artifacts Storage  │◄──┼──┼─────────────┘           ││  │
                                    │  │  (SEC Filings,      │   │  │                         ││  │
                                    │  │   Transcripts)      │   │  │  ┌──────────────────┐   ││  │
                                    │  │                     │   │  │  │   NAT Gateway    │   ││  │
                                    │  │ cyber-risk-artifacts│   │  │  └────────┬─────────┘   ││  │
                                    │  └─────────────────────┘   │  └───────────┼─────────────┘│  │
                                    │                            │              │              │  │
                                    │                            │              ▼              │  │
                                    │                            │  ┌─────────────────────────┐│  │
                                    │                            │  │  Private Subnet (AZ-a)  ││  │
                                    │                            │  │     10.0.10.0/24        ││  │
                                    │                            │  │  ┌─────────────────────┐││  │
                                    │                            │  │  │   RDS PostgreSQL    │││  │
                                    │                            │  │  │   (Cache DB)        │││  │
                                    │                            │  │  │   Port 5432         │││  │
                                    │                            │  │  └─────────────────────┘││  │
                                    │                            │  │  ┌─────────────────────┐││  │
                                    │                            │  │  │  Lambda Function    │││  │
                                    │                            │  │  │  (Lex Fulfillment)  │││  │
                                    │                            │  │  └─────────────────────┘││  │
                                    │                            │  └─────────────────────────┘│  │
                                    │                            │                             │  │
                                    │                            │  ┌─────────────────────────┐│  │
                                    │                            │  │  Private Subnet (AZ-b)  ││  │
                                    │                            │  │     10.0.11.0/24        ││  │
                                    │                            │  │   (RDS Multi-AZ Ready)  ││  │
                                    │                            │  └─────────────────────────┘│  │
                                    │                            └─────────────────────────────┘  │
                                    │                                                             │
                                    │  ┌──────────────────────────────────────────────────────┐   │
                                    │  │                   AWS AI SERVICES                    │   │
                                    │  │  ┌─────────────────┐   ┌─────────────────────────┐   │   │
                                    │  │  │ Amazon          │   │ Amazon Lex V2           │   │   │
                                    │  │  │ Comprehend      │   │ (Chatbot)               │   │   │
                                    │  │  │ ─────────────── │   │ ───────────────────     │   │   │
                                    │  │  │ - Sentiment     │   │ - WelcomeIntent         │   │   │
                                    │  │  │   Analysis      │   │ - CompanyInfoIntent     │   │   │
                                    │  │  │ - Key Phrases   │   │ - SentimentIntent       │   │   │
                                    │  │  │ - Entity        │   │ - ForecastIntent        │   │   │
                                    │  │  │   Detection     │   │ - AddCompanyIntent      │   │   │
                                    │  │  └─────────────────┘   │ - GrowthMetricsIntent   │   │   │
                                    │  │                        └─────────────────────────┘   │   │
                                    │  └──────────────────────────────────────────────────────┘   │
                                    │                                                             │
                                    └─────────────────────────────────────────────────────────────┘
                                                                 │
                                                                 │
                                    ┌────────────────────────────┼────────────────────────────┐
                                    │           EXTERNAL APIs    │                            │
                                    │  ┌─────────────────┐       │     ┌───────────────────┐  │
                                    │  │  SEC EDGAR API  │◄──────┼─────┤   Explorium API   │  │
                                    │  │  (10-K, 10-Q)   │       │     │ (Company Growth)  │  │
                                    │  └─────────────────┘       │     └───────────────────┘  │
                                    │  ┌─────────────────┐       │     ┌───────────────────┐  │
                                    │  │  Yahoo Finance  │◄──────┴─────┤  Alpha Vantage    │  │
                                    │  │  (Stock Data)   │             │  (Sentiment)      │  │
                                    │  └─────────────────┘             └───────────────────┘  │
                                    └─────────────────────────────────────────────────────────┘
```

---

## Detailed Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND (React SPA)                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  S3 Bucket: cyberrisk-dev-kh-frontend-u7tro1vp                                       │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────────────┐ │   │
│  │  │   index.html  │ │   App.jsx     │ │ Dashboard.jsx │ │ Component Files           │ │   │
│  │  │   (Entry)     │ │ (Router)      │ │ (Main View)   │ │ - SentimentAnalysis.jsx   │ │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘ │ - TimeSeriesForecast.jsx  │ │   │
│  │                                                         │ - CompanyGrowth.jsx       │ │   │
│  │                                                         │ - LexChatbot.jsx          │ │   │
│  │                                                         └───────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              │ HTTPS via CloudFront
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (Flask + Gunicorn)                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  EC2 Instance: t3.micro | Amazon Linux 2023 | IP: 52.41.126.148                      │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────┐ │   │
│  │  │                              app.py (Flask Application)                         │ │   │
│  │  │  ┌───────────────────────────────────────────────────────────────────────────┐  │ │   │
│  │  │  │                           API ENDPOINTS                                   │  │ │   │
│  │  │  │  /api/artifacts         - List SEC filings and transcripts               │  │ │   │
│  │  │  │  /api/companies         - Get companies from S3 artifacts                │  │ │   │
│  │  │  │  /api/companies/db      - CRUD operations on RDS database                │  │ │   │
│  │  │  │  /api/sentiment/{ticker} - AWS Comprehend analysis (cached in RDS)       │  │ │   │
│  │  │  │  /api/forecast          - Prophet time series predictions (cached)       │  │ │   │
│  │  │  │  /api/financials/{ticker} - Extract financials from HTML filings         │  │ │   │
│  │  │  │  /api/company-growth/{ticker} - Explorium API data (cached in RDS)       │  │ │   │
│  │  │  │  /api/lex/message       - Send message to Lex chatbot                    │  │ │   │
│  │  │  └───────────────────────────────────────────────────────────────────────────┘  │ │   │
│  │  │  ┌───────────────────────────────────────────────────────────────────────────┐  │ │   │
│  │  │  │                              SERVICES                                     │  │ │   │
│  │  │  │  s3_service.py          - S3 artifact retrieval and presigned URLs       │  │ │   │
│  │  │  │  comprehend_service.py  - AWS Comprehend NLP analysis                    │  │ │   │
│  │  │  │  sentiment_cache.py     - RDS-backed sentiment caching (24h TTL)         │  │ │   │
│  │  │  │  forecast_cache.py      - RDS-backed forecast caching                    │  │ │   │
│  │  │  │  growth_cache.py        - RDS-backed Explorium data caching              │  │ │   │
│  │  │  │  explorium_service.py   - Company growth/hiring metrics API              │  │ │   │
│  │  │  │  lex_service.py         - Amazon Lex V2 chatbot integration              │  │ │   │
│  │  │  │  database_service.py    - PostgreSQL connection and queries              │  │ │   │
│  │  │  └───────────────────────────────────────────────────────────────────────────┘  │ │   │
│  │  │  ┌───────────────────────────────────────────────────────────────────────────┐  │ │   │
│  │  │  │                               MODELS                                      │  │ │   │
│  │  │  │  time_series_forecaster.py - Prophet-based stock price forecasting       │  │ │   │
│  │  │  └───────────────────────────────────────────────────────────────────────────┘  │ │   │
│  │  └─────────────────────────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA LAYER                                               │
│  ┌────────────────────────────────────┐  ┌────────────────────────────────────────────────┐ │
│  │       RDS PostgreSQL               │  │               S3 Buckets                       │ │
│  │  ────────────────────────────────  │  │  ──────────────────────────────────────────    │ │
│  │  Database: cyberrisk_db            │  │  cyber-risk-artifacts:                         │ │
│  │  Tables:                           │  │    └── data/processed/artifacts.csv            │ │
│  │    - companies (tracked tickers)   │  │    └── raw/sec/{ticker}_{date}_{type}.txt      │ │
│  │    - sentiment_cache               │  │    └── raw/transcripts/{ticker}_{date}.txt     │ │
│  │    - forecast_cache                │  │                                                │ │
│  │    - growth_cache                  │  │  cyberrisk-dev-kh-frontend-u7tro1vp:           │ │
│  │                                    │  │    └── index.html, static/js/*, static/css/*   │ │
│  │  Cache TTL: 24 hours               │  │    └── deploy/backend-deploy.tar.gz            │ │
│  └────────────────────────────────────┘  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Network Architecture (VPC Detail)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               VPC: cyberrisk-dev-kh-vpc                                     │
│                                   CIDR: 10.0.0.0/16                                         │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              AVAILABILITY ZONE A (us-west-2a)                          │ │
│  │  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────┐  │ │
│  │  │     PUBLIC SUBNET: 10.0.0.0/24          │  │    PRIVATE SUBNET: 10.0.10.0/24     │  │ │
│  │  │  ┌───────────────────────────────────┐  │  │  ┌───────────────────────────────┐  │  │ │
│  │  │  │        EC2 Instance               │  │  │  │       RDS PostgreSQL          │  │  │ │
│  │  │  │  ┌─────────────────────────────┐  │  │  │  │  ┌─────────────────────────┐  │  │  │ │
│  │  │  │  │ Private IP: 10.0.0.x        │  │  │  │  │  │ Endpoint: cyberrisk-   │  │  │  │ │
│  │  │  │  │ EIP: 52.41.126.148          │  │──┼──┼──┼──│ dev-kh-postgres...     │  │  │  │ │
│  │  │  │  │ SG: ec2-sg (22,80,443,5000) │  │  │  │  │  │ Port: 5432             │  │  │  │ │
│  │  │  │  └─────────────────────────────┘  │  │  │  │  │ SG: rds-sg (5432)      │  │  │  │ │
│  │  │  └───────────────────────────────────┘  │  │  │  └─────────────────────────┘  │  │  │ │
│  │  │  ┌───────────────────────────────────┐  │  │  │  ┌─────────────────────────┐  │  │  │ │
│  │  │  │        NAT Gateway                │  │  │  │  │  Lambda Function       │  │  │  │ │
│  │  │  │  (For private subnet egress)      │──┼──┼──┼──│  (Lex Fulfillment)     │  │  │  │ │
│  │  │  │  EIP: [NAT EIP]                   │  │  │  │  │  SG: lambda-sg         │  │  │  │ │
│  │  │  └───────────────────────────────────┘  │  │  │  └─────────────────────────┘  │  │  │ │
│  │  └─────────────────────────────────────────┘  └─────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              AVAILABILITY ZONE B (us-west-2b)                          │ │
│  │  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────┐  │ │
│  │  │     PUBLIC SUBNET: 10.0.1.0/24          │  │    PRIVATE SUBNET: 10.0.11.0/24    │  │ │
│  │  │         (Available for scaling)         │  │     (RDS Multi-AZ failover ready)  │  │ │
│  │  └─────────────────────────────────────────┘  └─────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                               ROUTE TABLES                                            │   │
│  │  Public RT:  0.0.0.0/0 → Internet Gateway (igw-xxx)                                  │   │
│  │  Private RT: 0.0.0.0/0 → NAT Gateway (nat-xxx)                                       │   │
│  └──────────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DATA FLOW ARCHITECTURE                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────┐                                                                      ┌─────────────┐
│  User   │                                                                      │ SEC EDGAR   │
│ Browser │                                                                      │    API      │
└────┬────┘                                                                      └──────┬──────┘
     │                                                                                  │
     │ 1. HTTPS Request                                                                 │
     ▼                                                                                  │
┌─────────────────┐                                                                     │
│   CloudFront    │                                                                     │
│   Distribution  │                                                                     │
└────────┬────────┘                                                                     │
         │                                                                              │
    ┌────┴────┐                                                                         │
    │         │                                                                         │
    ▼         ▼                                                                         │
┌───────┐ ┌───────────┐                                                                 │
│  S3   │ │   EC2     │                                                                 │
│(React)│ │ (Flask)   │◄────────────────────────────────────────────────────────────────┘
└───────┘ └─────┬─────┘                     5. Fetch SEC Filings
                │
    ┌───────────┼───────────┬───────────────────────────────────────┐
    │           │           │                                       │
    ▼           ▼           ▼                                       ▼
┌───────┐ ┌─────────┐ ┌───────────┐                         ┌─────────────┐
│  RDS  │ │   S3    │ │ Comprehend│                         │  Explorium  │
│(Cache)│ │Artifacts│ │   (NLP)   │                         │    API      │
└───────┘ └─────────┘ └───────────┘                         └─────────────┘
    │
    │ 2. Check Cache (24h TTL)
    │
    ├──► HIT: Return cached data
    │
    └──► MISS:
         3. Call external API / AWS service
         4. Store result in cache
         5. Return fresh data


FLOW 1: Sentiment Analysis Request
──────────────────────────────────
User → CloudFront → EC2 → RDS (cache check)
                         ├─► HIT → Return cached sentiment
                         └─► MISS → S3 (get document) → Comprehend (analyze)
                                    → RDS (cache result) → Return to user

FLOW 2: Stock Forecast Request
──────────────────────────────
User → CloudFront → EC2 → RDS (cache check)
                         ├─► HIT → Return cached forecast
                         └─► MISS → Yahoo Finance (get prices) → Prophet (forecast)
                                    → RDS (cache result) → Return to user

FLOW 3: Company Growth Request
──────────────────────────────
User → CloudFront → EC2 → RDS (cache check)
                         ├─► HIT → Return cached growth metrics
                         └─► MISS → Explorium API (get data)
                                    → RDS (cache result) → Return to user

FLOW 4: Chatbot Interaction
───────────────────────────
User → CloudFront → EC2 (/api/lex/message) → Lex V2 Bot → Lambda (VPC)
                                                            → RDS (query data)
                                                            → Return to Lex → EC2 → User
```

---

## Security Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   SECURITY LAYERS                                            │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    PERIMETER SECURITY                                        │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  CloudFront Distribution                                                               │  │
│  │    ✓ HTTPS Only (TLS 1.2+)                                                            │  │
│  │    ✓ Origin Access Control for S3                                                     │  │
│  │    ✓ Geo-restriction capable                                                          │  │
│  └───────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    NETWORK SECURITY                                          │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │  EC2 Security Group (ec2-sg)            │  │  RDS Security Group (rds-sg)            │   │
│  │  ─────────────────────────────────      │  │  ─────────────────────────────────      │   │
│  │  Inbound:                               │  │  Inbound:                               │   │
│  │    TCP 22   (SSH) - 0.0.0.0/0          │  │    TCP 5432 - ec2-sg (EC2 only)         │   │
│  │    TCP 80   (HTTP) - 0.0.0.0/0         │  │    TCP 5432 - 10.0.0.0/16 (VPC/Lambda)  │   │
│  │    TCP 443  (HTTPS) - 0.0.0.0/0        │  │  Outbound: All                          │   │
│  │    TCP 5000 (Flask) - 0.0.0.0/0        │  └─────────────────────────────────────────┘   │
│  │  Outbound: All                          │                                               │
│  └─────────────────────────────────────────┘  ┌─────────────────────────────────────────┐   │
│                                               │  Lambda Security Group (lambda-sg)      │   │
│  ┌─────────────────────────────────────────┐  │  ─────────────────────────────────      │   │
│  │  Network Isolation                      │  │  Inbound: None                          │   │
│  │  ─────────────────────────────────      │  │  Outbound: All (for RDS, internet)     │   │
│  │  ✓ RDS in private subnets only         │  └─────────────────────────────────────────┘   │
│  │  ✓ No public IP for RDS                 │                                               │
│  │  ✓ Lambda in VPC private subnets        │                                               │
│  │  ✓ NAT Gateway for private egress       │                                               │
│  └─────────────────────────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       IAM ROLES                                              │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │  EC2 Instance Role                      │  │  Lambda Execution Role                  │   │
│  │  ─────────────────────────────────      │  │  ─────────────────────────────────      │   │
│  │  Permissions:                           │  │  Permissions:                           │   │
│  │    ✓ comprehend:Detect*                 │  │    ✓ ec2:*NetworkInterface              │   │
│  │    ✓ comprehend:BatchDetect*            │  │    ✓ logs:CreateLogGroup/Stream        │   │
│  │    ✓ lex:RecognizeText                  │  │    ✓ logs:PutLogEvents                  │   │
│  │    ✓ s3:GetObject/PutObject/ListBucket  │  │    ✓ comprehend:Detect*                 │   │
│  │    ✓ logs:CreateLogGroup/Stream/Put     │  │    ✓ AWSLambdaVPCAccessExecutionRole   │   │
│  └─────────────────────────────────────────┘  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐                                               │
│  │  Lex Service Role                       │                                               │
│  │  ─────────────────────────────────      │                                               │
│  │  Permissions:                           │                                               │
│  │    ✓ polly:SynthesizeSpeech             │                                               │
│  │    ✓ lambda:InvokeFunction              │                                               │
│  └─────────────────────────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA PROTECTION                                           │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  Encryption:                                                                          │  │
│  │    ✓ S3 - Server-side encryption (SSE-S3)                                            │  │
│  │    ✓ RDS - EBS volume encryption enabled                                             │  │
│  │    ✓ CloudFront - HTTPS/TLS in transit                                               │  │
│  │    ✓ EC2 - EBS volume encryption enabled                                             │  │
│  │                                                                                        │  │
│  │  Credentials:                                                                         │  │
│  │    ✓ Database password via Terraform variables (not in code)                         │  │
│  │    ✓ API keys via environment variables                                              │  │
│  │    ✓ IAM roles (no hardcoded AWS credentials)                                        │  │
│  └───────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## AWS AI Services Integration

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                              AWS AI SERVICES INTEGRATION                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              AMAZON COMPREHEND                                               │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  Purpose: Natural Language Processing for SEC Filings & Earnings Transcripts          │  │
│  │                                                                                        │  │
│  │  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐        │  │
│  │  │  Sentiment Analysis │    │  Key Phrase         │    │  Entity Detection   │        │  │
│  │  │  ─────────────────  │    │  Extraction         │    │  ─────────────────  │        │  │
│  │  │  • POSITIVE         │    │  ─────────────────  │    │  • ORGANIZATION     │        │  │
│  │  │  • NEGATIVE         │    │  Top 20 phrases     │    │  • PERSON           │        │  │
│  │  │  • NEUTRAL          │    │  per document       │    │  • LOCATION         │        │  │
│  │  │  • MIXED            │    │                     │    │  • DATE             │        │  │
│  │  │  + Confidence Score │    │                     │    │  • QUANTITY         │        │  │
│  │  └─────────────────────┘    └─────────────────────┘    └─────────────────────┘        │  │
│  │                                                                                        │  │
│  │  Input: SEC 10-K, 10-Q filings (up to 5000 characters per API call)                   │  │
│  │  Caching: RDS PostgreSQL (24-hour TTL per ticker)                                     │  │
│  └───────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AMAZON LEX V2                                                │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  Bot Name: cyberrisk-dev-kh-bot                                                       │  │
│  │  Bot ID: 7GHDINGVTV                                                                   │  │
│  │                                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                              INTENTS                                              │ │  │
│  │  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐          │ │  │
│  │  │  │  WelcomeIntent     │  │  ListCompanies     │  │  CompanyInfoIntent │          │ │  │
│  │  │  │  "hello", "help"   │  │  "list companies"  │  │  "tell me about X" │          │ │  │
│  │  │  └────────────────────┘  └────────────────────┘  └────────────────────┘          │ │  │
│  │  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐          │ │  │
│  │  │  │  SentimentIntent   │  │  ForecastIntent    │  │  DashboardFeatures │          │ │  │
│  │  │  │  "show sentiment"  │  │  "what's forecast" │  │  "explain dashboard"│          │ │  │
│  │  │  └────────────────────┘  └────────────────────┘  └────────────────────┘          │ │  │
│  │  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐          │ │  │
│  │  │  │  AddCompanyIntent  │  │  RemoveCompany     │  │  DocumentInventory │          │ │  │
│  │  │  │  "add CRWD"        │  │  "delete PANW"     │  │  "what documents"   │          │ │  │
│  │  │  └────────────────────┘  └────────────────────┘  └────────────────────┘          │ │  │
│  │  │  ┌────────────────────┐                                                          │ │  │
│  │  │  │  GrowthMetrics     │                                                          │ │  │
│  │  │  │  "hiring trends"   │                                                          │ │  │
│  │  │  └────────────────────┘                                                          │ │  │
│  │  └──────────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                        │  │
│  │  Lambda Fulfillment: cyberrisk-dev-kh-lex-fulfillment                                 │  │
│  │    - Runs in VPC private subnets                                                      │  │
│  │    - Queries RDS for company/document data                                            │  │
│  │    - Extracts entities from user utterances                                           │  │
│  └───────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Terraform Module Structure

```
cyber-risk-deploy/
├── terraform/
│   ├── main.tf                 # Root module - orchestrates all modules
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Output values
│   ├── terraform.tfvars        # Variable values (gitignored)
│   └── modules/
│       ├── vpc/                # Network infrastructure
│       │   ├── main.tf         # VPC, subnets, IGW, NAT, route tables
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── iam/                # IAM roles and policies
│       │   ├── main.tf         # EC2, Lambda, Lex roles
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── rds/                # PostgreSQL database
│       │   ├── main.tf         # DB instance, subnet group, security group
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── ec2/                # Flask backend server
│       │   ├── main.tf         # EC2 instance, EIP, security group
│       │   ├── user_data.sh    # Bootstrap script (Gunicorn, nginx)
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── s3/                 # Frontend hosting bucket
│       │   ├── main.tf         # S3 bucket with static hosting
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── cloudfront/         # CDN distribution
│       │   ├── main.tf         # Distribution, OAC, behaviors
│       │   ├── variables.tf
│       │   └── outputs.tf
│       └── lex/                # Chatbot
│           ├── main.tf         # Bot, intents, Lambda
│           ├── lambda/         # Fulfillment code
│           │   └── index.py
│           ├── variables.tf
│           └── outputs.tf
```

---

## Deployment Outputs

| Resource | Value |
|----------|-------|
| CloudFront URL | https://dnes10oz5czsk.cloudfront.net |
| EC2 Public IP | 52.41.126.148 |
| RDS Endpoint | cyberrisk-dev-kh-postgres.c05bdkwjrggh.us-west-2.rds.amazonaws.com:5432 |
| S3 Frontend Bucket | cyberrisk-dev-kh-frontend-u7tro1vp |
| S3 Artifacts Bucket | cyber-risk-artifacts |
| Lex Bot ID | 7GHDINGVTV |
| Region | us-west-2 |

---

## Cost Considerations

| Service | Tier/Size | Estimated Monthly Cost |
|---------|-----------|----------------------|
| EC2 | t3.micro | ~$8.50 |
| RDS | db.t3.micro | ~$13.00 |
| S3 | < 5GB storage | ~$0.12 |
| CloudFront | < 1TB transfer | ~$0.00 (free tier) |
| NAT Gateway | Per hour + data | ~$32.00 |
| Comprehend | Per 100 units | ~$1.00 (usage-based) |
| Lex | Per request | ~$0.75/1000 requests |
| **Total** | | **~$55-60/month** |

*Note: NAT Gateway is the largest cost driver. For a class project, consider removing it if Lambda doesn't need internet access.*

---

## Future Enhancements

1. **Auto Scaling Group** - Replace single EC2 with ASG for high availability
2. **Application Load Balancer** - Add ALB in front of EC2/ASG
3. **Multi-AZ RDS** - Enable for production database resilience
4. **WAF** - Add Web Application Firewall to CloudFront
5. **Route 53** - Custom domain with SSL certificate (ACM)
6. **Secrets Manager** - Move database credentials from env vars
7. **CI/CD Pipeline** - GitHub Actions or CodePipeline for automated deployments
