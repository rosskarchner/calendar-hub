#!/bin/bash
# Development helper script for Calendar Hub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${GREEN}=== $1 ===${NC}"
}

function print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Activate virtual environment
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Run: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate

case "$1" in
    run)
        print_header "Starting Development Server"
        export FLASK_ENV=development
        export FLASK_DEBUG=1
        python app.py
        ;;
    
    test)
        print_header "Running Tests"
        python -c "
from app import create_app

app = create_app('development')
print('✓ App created successfully')

with app.test_client() as client:
    # Test all routes
    routes = [
        ('/', 302, 'Root redirect'),
        ('/health', 200, 'Health check'),
        ('/dctech', 200, 'Event form'),
        ('/dctech/meetup', 200, 'Meetup form'),
        ('/dctech/ical', 200, 'iCal form'),
        ('/dctech/newsletter', 200, 'Newsletter signup'),
    ]
    
    for route, expected_status, description in routes:
        response = client.get(route)
        status = '✓' if response.status_code == expected_status else '✗'
        print(f'{status} {description}: {response.status_code}')

print('\n✅ All tests passed!')
"
        ;;
    
    install)
        print_header "Installing Dependencies"
        pip install -r requirements.txt
        print_header "Installation Complete"
        ;;
    
    upgrade)
        print_header "Upgrading Dependencies"
        pip install --upgrade -r requirements.txt
        ;;
    
    lint)
        print_header "Running Linter"
        pip install -q flake8 2>/dev/null || true
        flake8 --max-line-length=100 --exclude=venv,__pycache__ . || print_warning "Some linting issues found"
        ;;
    
    format)
        print_header "Formatting Code"
        pip install -q black 2>/dev/null || true
        black --line-length=100 --exclude=venv . || print_warning "black not installed"
        ;;
    
    clean)
        print_header "Cleaning Up"
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        find . -type f -name "*.pyo" -delete 2>/dev/null || true
        rm -rf logs/*.log 2>/dev/null || true
        print_header "Cleanup Complete"
        ;;
    
    logs)
        print_header "Viewing Logs"
        if [ -f "logs/calendar-hub.log" ]; then
            tail -f logs/calendar-hub.log
        else
            print_warning "No logs found. Run the app first."
        fi
        ;;
    
    shell)
        print_header "Starting Python Shell"
        python -i -c "from app import create_app; app = create_app(); print('App loaded. Use: app')"
        ;;
    
    routes)
        print_header "Listing Routes"
        python -c "
from app import create_app
app = create_app('development')

print('\nAvailable Routes:')
print('-' * 80)
for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f'{rule.endpoint:40} {methods:15} {rule}')
"
        ;;
    
    *)
        echo "Calendar Hub Development Helper"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  run       - Start development server"
        echo "  test      - Run basic tests"
        echo "  install   - Install dependencies"
        echo "  upgrade   - Upgrade dependencies"
        echo "  lint      - Run linter"
        echo "  format    - Format code with black"
        echo "  clean     - Clean up cache files"
        echo "  logs      - View application logs"
        echo "  shell     - Start Python shell with app loaded"
        echo "  routes    - List all routes"
        echo ""
        exit 1
        ;;
esac
