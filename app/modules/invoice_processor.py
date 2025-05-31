from flask import Blueprint, render_template, request, jsonify, send_file, current_app
import fitz
import re
import os
import zipfile
from app.utils.validators import validate_file_upload, secure_save_file
from app.utils.pdf_utils import clean_folder

bp = Blueprint('invoice_processor', __name__)

def extract_and_split_invoices(pdf_path, output_folder):
    """Extract invoice numbers and split PDF."""
    doc = fitz.open(pdf_path)
    pattern = r'\b[P|R]\d{6,8}\b'
    pages_by_invoice = {}
    
    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            invoice_numbers = re.findall(pattern, text)
            
            for invoice_number in invoice_numbers:
                if invoice_number not in pages_by_invoice:
                    pages_by_invoice[invoice_number] = []
                pages_by_invoice[invoice_number].append(page_num)
        
        if not pages_by_invoice:
            return False, "No invoices found in PDF"
        
        # Create individual PDFs
        for invoice_number, page_nums in pages_by_invoice.items():
            output_pdf = fitz.open()
            for page_num in page_nums:
                output_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            output_filename = os.path.join(output_folder, f"{invoice_number}.pdf")
            output_pdf.save(output_filename)
            output_pdf.close()
        
        return True, f"Extracted {len(pages_by_invoice)} invoices"
    
    finally:
        doc.close()

@bp.route('/')
def index():
    """Invoice processor page."""
    return render_template('invoice_processor.html')

@bp.route('/upload', methods=['POST'])
def upload():
    """Handle PDF upload and processing."""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    
    file = request.files['file']
    valid, message = validate_file_upload(file, {'pdf'})
    
    if not valid:
        return jsonify({'status': 'error', 'message': message}), 400
    
    # Save file
    filepath, filename = secure_save_file(file, current_app.config['UPLOAD_FOLDER'])
    
    # Create output folder
    base_name = filename.rsplit('.', 1)[0]
    output_folder = os.path.join(current_app.config['RESULT_FOLDER'], base_name)
    os.makedirs(output_folder, exist_ok=True)
    
    # Process PDF
    success, message = extract_and_split_invoices(filepath, output_folder)
    
    if not success:
        return jsonify({'status': 'error', 'message': message}), 400
    
    # Create zip file
    zip_filename = f"{base_name}.zip"
    zip_path = os.path.join(current_app.config['RESULT_FOLDER'], zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_folder)
                zipf.write(file_path, arcname)
    
    # Clean up uploaded file
    os.remove(filepath)
    
    return jsonify({
        'status': 'success',
        'message': message,
        'download_url': f'/invoice/download/{zip_filename}'
    })

@bp.route('/download/<filename>')
def download(filename):
    """Download processed invoices."""
    file_path = os.path.join(current_app.config['RESULT_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'status': 'error', 'message': 'File not found'}), 404

@bp.route('/clear', methods=['POST'])
def clear_results():
    """Clear results folder."""
    clean_folder(current_app.config['RESULT_FOLDER'])
    return jsonify({'status': 'success'})