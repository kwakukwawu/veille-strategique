# AI Coding Agent Instructions for Veille Strategique

## Project Overview
Veille Strategique is a strategic intelligence monitoring system that scrapes data from multiple sources (government agencies, UN, GIZ, education platforms) and exposes it via an API. The system runs continuous keyword-based monitoring with scheduled scraping tasks.

**Core Architecture:**
- **Frontend Layer**: API routes with authentication (backend/api/)
- **Data Collection Layer**: Pluggable scrapers and keyword management (backend/scraping/)
- **Data Layer**: SQLAlchemy models and database migrations (backend/database/)
- **Core**: Flask application with environment-based configuration (app.py, config.py)

## Key Architectural Patterns

### Multi-Source Scraper Pattern
- Base abstract scraper in [backend/scraping/scrapers/base_scraper.py](backend/scraping/scrapers/base_scraper.py) defines `scrape()` contract
- Concrete scrapers ([backend/scraping/scrapers/](backend/scraping/scrapers/)) inherit and implement source-specific logic
- Each scraper targets a distinct data source (GIZ, government portals, UN platforms, education sites)
- Scrapers are instantiated and orchestrated by [backend/scraping/scheduler.py](backend/scraping/scheduler.py)

**When adding a new data source:** Create new scraper class in backend/scraping/scrapers/, inherit from base_scraper, implement `scrape()`, register in scheduler

### Keyword-Driven Monitoring
- [backend/scraping/keyword_manager.py](backend/scraping/keyword_manager.py) manages search terms and monitoring parameters
- Keywords drive scraper queries—changes here cascade to all scraping tasks
- Scheduler uses keywords to customize scraper behavior per monitoring campaign

### API & Authentication
- [backend/api/routes.py](backend/api/routes.py) defines REST endpoints
- [backend/api/auth.py](backend/api/auth.py) handles authentication logic
- [backend/api/middleware.py](backend/api/middleware.py) enforces auth on routes (likely token/session validation)

### Database & Migrations
- Models in [backend/database/models.py](backend/database/models.py) define schema
- [backend/database/database.py](backend/database/database.py) initializes connection and session management
- Migrations in [backend/database/migrations/](backend/database/migrations/) are versioned; apply before schema changes

**Pattern:** Always create migration before altering models. Test migrations locally before deployment.

## Critical Workflows

### Running the System Locally
```bash
# Install dependencies from backend/requirements.txt
pip install -r backend/requirements.txt

# Configure via backend/config.py (check for environment variables)
# Start Flask app
python backend/app.py

# Schedulers defined in backend/scraping/scheduler.py auto-start on app boot
```

### Adding a New Data Source
1. Create scraper class in `backend/scraping/scrapers/{source}_scraper.py`
2. Inherit from `BaseScaper` (implement `scrape()` method)
3. Register in `backend/scraping/scheduler.py` initialization
4. Add keywords relevant to the source in `keyword_manager.py`
5. Test with mock data before deploying

### Database Changes
1. Modify model in `backend/database/models.py`
2. Create migration in `backend/database/migrations/`
3. Apply and test locally before committing
4. Include migration in deployment sequence

## Project-Specific Conventions

- **Environment Variables**: Loaded in [backend/config.py](backend/config.py) (check for pattern: `os.getenv('KEY', default)`)
- **Scraper Errors**: Assume scrapers handle HTTP timeouts and parse failures gracefully; don't assume 100% success
- **Scheduler**: Runs asynchronously; check for task queuing/celery patterns or simple APScheduler usage
- **API Response Format**: Likely JSON; authentication tokens likely required for protected endpoints
- **Keyword Updates**: Are dynamic—don't hard-code search terms in scrapers; always reference keyword_manager

## Integration Points & Dependencies

- **External APIs**: GIZ, government portals, UN databases, education career platforms (implementation in respective scrapers)
- **Database**: Check requirements.txt for SQLAlchemy version; migrations must be compatible
- **Task Scheduling**: Scheduler runs scrapers on intervals; check requirements.txt for APScheduler or Celery
- **Auth Framework**: Flask-Login, JWT, or session-based (see api/auth.py and middleware.py)

## When Stuck
1. Check `backend/config.py` for initialization patterns and configuration keys
2. Review `BaseScaper` in `backend/scraping/scrapers/base_scraper.py` for expected interface
3. Examine one concrete scraper (e.g., `gov_scraper.py`) to see implementation patterns
4. Check `backend/api/routes.py` for endpoint structure and response conventions
5. Look at `backend/database/models.py` for data relationships and constraints
