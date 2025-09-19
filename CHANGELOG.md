# Changelog

All notable changes to the VIEWS Forecast API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open-source release
- MIT License for educational use
- Contributing guidelines
- Code of Conduct
- Security policy
- GitHub issue and PR templates
- CI/CD workflow with GitHub Actions

## [1.0.0] - 2025-09-19

### Added
- Core REST API with FastAPI framework
- Grid-cell level conflict predictions with 13 metrics
- Support for MAP (Most Accurate Prediction)
- Confidence intervals (50%, 90%, 99%)
- Probability thresholds for different fatality levels
- Country-based filtering with ISO codes
- Grid cell ID filtering
- Time period filtering (months and ranges)
- Multiple response formats (JSON, NDJSON)
- Streaming support for large datasets
- LRU caching for improved performance
- Health check endpoints (`/health`, `/ready`)
- Interactive API documentation (Swagger UI)
- OpenAPI schema generation
- Docker support with Dockerfile and docker-compose
- Bruno API workspace for testing
- Local data storage support
- Cloud storage integration (S3, GCS, Azure)
- Parquet data format for efficiency
- VIEWS data import pipeline
- Comprehensive test suite
- Environment-based configuration
- API key authentication
- CORS support
- Logging infrastructure
- Sample data generation

### Documentation
- Complete README with setup instructions
- API endpoint documentation
- VIEWS data processing guide
- Development workflow documentation
- Deployment guidelines
- Security best practices

### Infrastructure
- Makefile for common operations
- Python package management with pip
- Virtual environment setup
- Pytest testing framework
- Code quality tools integration

## [0.9.0] - 2025-09-19 (First Version to speed things up in the hackaton)

### Added
- Initial hackathon submission for JunctionX Oulu 2025
- Basic API functionality
- Core prediction endpoints
- Data processing pipeline
- Basic documentation

### Notes
- Created for VIEWS Challenge: Turning Conflict Forecasts into Accessible APIs
- Developed by Risto Holappa and Sillah Babar

---

## Version Guidelines

### Version Numbering
- **Major (X.0.0)**: Breaking API changes
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes, backwards compatible

### How to Update This File
1. Add new entry under `[Unreleased]` during development
2. When releasing, move items to new version section
3. Include date in ISO format (YYYY-MM-DD)
4. Link version comparisons at bottom of file

### Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes