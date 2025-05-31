from flask import Blueprint, render_template, request, jsonify, current_app
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import threading
import time
from app.utils.validators import validate_file_upload, secure_save_file

bp = Blueprint('cc_batch_demo', __name__)

# Global driver reference for cleanup
active_driver = None

@bp.route('/')
def index():
    """CC Batch demo page."""
    return render_template('cc_batch_demo.html')

@bp.route('/process', methods=['POST'])
def process_excel():
    """Process Excel file and automate web form filling."""
    global active_driver
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    
    file = request.files['file']
    valid, message = validate_file_upload(file, {'xlsx', 'xls'})
    
    if not valid:
        return jsonify({'status': 'error', 'message': message}), 400
    
    # Save and process file
    filepath, filename = secure_save_file(file, current_app.config['UPLOAD_FOLDER'])
    
    try:
        # Read Excel data
        df = pd.read_excel(filepath)
        
        if df.empty or len(df.columns) < 3:
            return jsonify({'status': 'error', 'message': 'Excel file must have at least 3 columns with data'}), 400
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Initialize driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        active_driver = driver
        
        # Navigate to demo calculator
        url = "https://www.calculator.net/grade-calculator.html"
        driver.get(url)
        
        # Calculate rows needed
        rows_needed = max(0, len(df) - 8)
        
        # Add extra rows if needed
        for _ in range(rows_needed // 3):
            try:
                add_button = driver.find_element(By.LINK_TEXT, "+ add more rows")
                add_button.click()
                time.sleep(0.5)
            except:
                break
        
        # Fill form with data
        for index, row in df.iterrows():
            try:
                # Fill assignment name
                d_input = driver.find_element(By.NAME, f'd{index + 1}')
                d_input.clear()
                d_input.send_keys(str(row.iloc[0]))
                
                # Fill score
                s_input = driver.find_element(By.NAME, f's{index + 1}')
                s_input.clear()
                s_input.send_keys(str(row.iloc[1]))
                
                # Fill weight
                w_input = driver.find_element(By.NAME, f'w{index + 1}')
                w_input.clear()
                w_input.send_keys(str(row.iloc[2]))
                
            except Exception as e:
                print(f"Error filling row {index + 1}: {e}")
                continue
        
        # Keep browser alive
        keep_alive_thread = threading.Thread(target=keep_browser_alive, args=(driver,))
        keep_alive_thread.daemon = True
        keep_alive_thread.start()
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully filled {len(df)} entries in the grade calculator.',
            'url': url
        })
        
    except Exception as e:
        # Clean up on error
        if active_driver:
            active_driver.quit()
            active_driver = None
        
        # Clean up file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({'status': 'error', 'message': f'Processing error: {str(e)}'}), 500

def keep_browser_alive(driver):
    """Keep browser session alive with periodic activity."""
    try:
        while True:
            # Small scroll to keep session active
            driver.execute_script("window.scrollBy(0, 10);")
            time.sleep(60)  # Every minute
    except:
        pass  # Browser closed

@bp.route('/close-browser', methods=['POST'])
def close_browser():
    """Close active browser session."""
    global active_driver
    if active_driver:
        try:
            active_driver.quit()
        except:
            pass
        active_driver = None
    return jsonify({'status': 'success'})