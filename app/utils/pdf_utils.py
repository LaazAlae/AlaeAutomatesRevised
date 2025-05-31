import fitz
import os

def check_pdf_has_text(pdf_path):
    """Check if PDF contains readable text."""
    try:
        doc = fitz.open(pdf_path)
        has_text = any(page.get_text().strip() for page in doc)
        doc.close()
        return has_text
    except Exception:
        return False

def extract_pdf_pages(input_pdf, page_numbers, output_pdf_path):
    """Extract specific pages from PDF."""
    doc = fitz.open(input_pdf)
    output_pdf = fitz.open()
    
    for page_num in page_numbers:
        if 0 <= page_num - 1 < len(doc):
            output_pdf.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
    
    if output_pdf.page_count > 0:
        output_pdf.save(output_pdf_path)
    
    output_pdf.close()
    doc.close()
    
    return output_pdf.page_count > 0

def clean_folder(folder_path):
    """Clean all files in a folder."""
    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")