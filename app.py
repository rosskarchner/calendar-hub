"""Main Flask application for Calendar Hub."""
from flask import Flask, g, request
from config import config
import os


def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    
    # Initialize error handlers and logging
    from utils.error_handlers import init_error_handlers, init_logging
    init_error_handlers(app)
    init_logging(app)
    
    # Register blueprints
    from blueprints.events import events_bp
    from blueprints.newsletters import newsletters_bp
    
    app.register_blueprint(events_bp)
    app.register_blueprint(newsletters_bp)
    
    # Add middleware to inject site context
    @app.before_request
    def load_site_context():
        """Load site configuration based on URL path."""
        # Extract site_slug from path if present
        path_parts = request.path.strip('/').split('/')
        if path_parts and path_parts[0]:
            site = app.config['get_site_by_slug'](path_parts[0])
            if site:
                g.site = site
    
    @app.after_request
    def add_no_index_header(response):
        """Add noindex header to HTML responses."""
        if response.content_type and response.content_type.startswith('text/html'):
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response
    
    # Make get_site_by_slug available to app config
    app.config['get_site_by_slug'] = config[config_name].get_site_by_slug
    
    # Root route
    @app.route('/')
    def index():
        """Redirect to default site."""
        sites = config[config_name].load_sites()
        if sites:
            from flask import redirect
            return redirect(f'/{sites[0]["slug"]}')
        return 'No sites configured', 404
    
    # Health check endpoint
    @app.route('/health')
    def health():
        """Health check endpoint for monitoring."""
        return {'status': 'healthy', 'version': '1.0.0'}, 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
