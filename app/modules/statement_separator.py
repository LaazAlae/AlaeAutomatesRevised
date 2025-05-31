from flask import Blueprint, render_template, request, jsonify, send_file, current_app
import os
import re
import fitz
import pandas as pd
import zipfile
from difflib import get_close_matches
from app.utils.validators import validate_file_upload, secure_save_file
from app.utils.pdf_utils import extract_pdf_pages, clean_folder, check_pdf_has_text

bp = Blueprint('statement_separator', __name__)

# US state abbreviations
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
    "VA", "WA", "WV", "WI", "WY", "DC"
]

# Session storage for processing state
processing_state = {}

@bp.route('/')
def index():
    """Statement separator page."""
    return render_template('statement_separator.html')

@bp.route('/upload', methods=['POST'])
def upload():
    """Handle file uploads and initial processing."""
    # Validate files
    if 'pdf_file' not in request.files or 'excel_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Both PDF and Excel files are required'}), 400
    
    pdf_file = request.files['pdf_file']
    excel_file = request.files['excel_file']
    
    # Validate PDF
    valid_pdf, message_pdf = validate_file_upload(pdf_file, {'pdf'})
    if not valid_pdf:
        return jsonify({'status': 'error', 'message': message_pdf}), 400
    
    # Validate Excel
    valid_excel, message_excel = validate_file_upload(excel_file, {'xlsx', 'xls'})
    if not valid_excel:
        return jsonify({'status': 'error', 'message': message_excel}), 400
    
    # Save files
    pdf_path, pdf_filename = secure_save_file(pdf_file, current_app.config['UPLOAD_FOLDER'])
    excel_path, excel_filename = secure_save_file(excel_file, current_app.config['UPLOAD_FOLDER'])
    
    # Check if PDF has text
    if not check_pdf_has_text(pdf_path):
        return jsonify({
            'status': 'error',
            'message': 'The PDF doesn\'t contain readable text. Please ensure the PDF is not scanned.'
        }), 400
    
    # Process files
    result = process_statement_files(pdf_path, excel_path)
    
    # Store processing state
    session_id = os.urandom(16).hex()
    processing_state[session_id] = {
        'pdf_path': pdf_path,
        'excel_path': excel_path,
        'result': result
    }
    
    if result['pending_decisions']:
        return jsonify({
            'status': 'review',
            'session_id': session_id,
            'statements': result['pending_decisions']
        })
    else:
        # No review needed, create PDFs
        create_statement_pdfs(pdf_path, result)
        return jsonify({'status': 'success', 'session_id': session_id})

@bp.route('/review', methods=['POST'])
def review_decision():
    """Handle review decisions."""
    data = request.get_json()
    session_id = data.get('session_id')
    decision = data.get('decision')
    statement_index = data.get('statement_index')
    
    if session_id not in processing_state:
        return jsonify({'status': 'error', 'message': 'Invalid session'}), 400
    
    state = processing_state[session_id]
    statement = state['result']['pending_decisions'][statement_index]
    
    # Process decision
    if decision == 'yes':
        state['result']['dnm_pages'].extend(statement['pages'])
    else:
        # Categorize based on location
        if any(state in line for line in statement['lines'] for state in US_STATES):
            if statement['total_pages'] == 1:
                state['result']['natio_single_pages'].extend(statement['pages'])
            else:
                state['result']['natio_multi_pages'].extend(statement['pages'])
        else:
            state['result']['foreign_pages'].extend(statement['pages'])
    
    # Check if more reviews needed
    if statement_index + 1 < len(state['result']['pending_decisions']):
        return jsonify({'status': 'continue'})
    else:
        # All reviews done, create PDFs
        create_statement_pdfs(state['pdf_path'], state['result'])
        return jsonify({'status': 'complete'})

@bp.route('/results/<session_id>')
def results(session_id):
    """Show results page."""
    if session_id not in processing_state:
        return "Session not found", 404
    
    # Count pages in each category
    result_folder = current_app.config['STATEMENT_RESULT_FOLDER']
    counts = {}
    
    for category in ['DNM', 'NatioSingle', 'NatioMulti', 'Foreign']:
        pdf_path = os.path.join(result_folder, f"{category}.pdf")
        if os.path.exists(pdf_path):
            doc = fitz.open(pdf_path)
            counts[category] = doc.page_count
            doc.close()
        else:
            counts[category] = 0
    
    return render_template('results.html', counts=counts, session_id=session_id)

@bp.route('/download/<session_id>/<category>')
def download(session_id, category):
    """Download individual category PDF."""
    if session_id not in processing_state:
        return "Session not found", 404
    
    file_path = os.path.join(current_app.config['STATEMENT_RESULT_FOLDER'], f"{category}.pdf")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

@bp.route('/download-all/<session_id>')
def download_all(session_id):
    """Download all PDFs as zip."""
    if session_id not in processing_state:
        return "Session not found", 404
    
    result_folder = current_app.config['STATEMENT_RESULT_FOLDER']
    zip_path = os.path.join(result_folder, "all_statements.zip")
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for category in ['DNM', 'NatioSingle', 'NatioMulti', 'Foreign']:
            pdf_path = os.path.join(result_folder, f"{category}.pdf")
            if os.path.exists(pdf_path):
                zipf.write(pdf_path, f"{category}.pdf")
    
    return send_file(zip_path, as_attachment=True)

def process_statement_files(pdf_path, excel_path):
    """Process PDF and Excel files to categorize statements."""
    # Read company names from Excel
    df = pd.read_excel(excel_path)
    company_names = df.iloc[:, 0].dropna().tolist()
    
    # Initialize result
    result = {
        'dnm_pages': [],
        'natio_single_pages': [],
        'natio_multi_pages': [],
        'foreign_pages': [],
        'pending_decisions': []
    }
    
    # Process PDF
    doc = fitz.open(pdf_path)
    start_markers = ["914.949.9618", "302.703.8961", "www.unitedcorporate.com"]
    end_marker = "STATEMENT OF OPEN INVOICE(S)"
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        # Extract statement info
        page_match = re.search(r'Page\s*(\d+)\s*of\s*(\d+)', text, re.IGNORECASE)
        if page_match:
            current_page = int(page_match.group(1))
            total_pages = int(page_match.group(2))
        else:
            current_page, total_pages = 1, 1
        
        # Find company name between markers
        start_idx = -1
        for marker in start_markers:
            idx = text.find(marker)
            if idx != -1:
                start_idx = idx
                break
        
        end_idx = text.find(end_marker)
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            extracted_text = text[start_idx:end_idx].strip()
            lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
            
            if lines:
                company_name = lines[0]
                pages = list(range(page_num + 1, page_num + 1 + total_pages))
                
                # Check for exact match
                if company_name in company_names:
                    result['dnm_pages'].extend(pages)
                else:
                    # Check for close match
                    close_matches = get_close_matches(company_name, company_names, n=1, cutoff=0.8)
                    if close_matches:
                        result['pending_decisions'].append({
                            'company_name': company_name,
                            'close_match': close_matches[0],
                            'page_num': page_num + 1,
                            'total_pages': total_pages,
                            'pages': pages,
                            'lines': lines
                        })
                    else:
                        # Auto-categorize
                        if any(state in ' '.join(lines) for state in US_STATES):
                            if total_pages == 1:
                                result['natio_single_pages'].extend(pages)
                            else:
                                result['natio_multi_pages'].extend(pages)
                        else:
                            result['foreign_pages'].extend(pages)
    
    doc.close()
    return result

def create_statement_pdfs(pdf_path, result):
    """Create separate PDFs for each category."""
    result_folder = current_app.config['STATEMENT_RESULT_FOLDER']
    clean_folder(result_folder)
    
    categories = {
        'DNM': result['dnm_pages'],
        'NatioSingle': result['natio_single_pages'],
        'NatioMulti': result['natio_multi_pages'],
        'Foreign': result['foreign_pages']
    }
    
    for category, pages in categories.items():
        if pages:
            output_path = os.path.join(result_folder, f"{category}.pdf")
            extract_pdf_pages(pdf_path, pages, output_path)