import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max file size
    
    # Upload folders
    UPLOAD_FOLDER = os.path.abspath('uploads')
    RESULT_FOLDER = os.path.abspath('separate_results')
    STATEMENT_RESULT_FOLDER = os.path.abspath('results')
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls'}
    
    # Create directories if they don't exist
    for folder in [UPLOAD_FOLDER, RESULT_FOLDER, STATEMENT_RESULT_FOLDER]:
        os.makedirs(folder, exist_ok=True)