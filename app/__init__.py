from flask import Flask
from app.config import Config

def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Register blueprints
    from app.modules.invoice_processor import bp as invoice_bp
    from app.modules.statement_separator import bp as statement_bp
    from app.modules.excel_macros import bp as excel_bp
    from app.modules.cc_batch_demo import bp as cc_batch_bp
    
    app.register_blueprint(invoice_bp, url_prefix='/invoice')
    app.register_blueprint(statement_bp, url_prefix='/statement')
    app.register_blueprint(excel_bp, url_prefix='/excel')
    app.register_blueprint(cc_batch_bp, url_prefix='/cc-batch')
    
    # Register main routes
    from app import routes
    app.register_blueprint(routes.bp)
    
    return app