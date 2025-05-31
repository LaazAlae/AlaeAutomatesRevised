import os
from werkzeug.utils import secure_filename

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_file_upload(file, allowed_extensions):
    """Validate uploaded file."""
    if not file or file.filename == '':
        return False, "No file selected"
    
    if not allowed_file(file.filename, allowed_extensions):
        return False, f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
    
    return True, "Valid file"

def secure_save_file(file, upload_folder):
    """Securely save uploaded file."""
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    return filepath, filename