"""
Smart Parking System - Flask Backend
Provides API endpoints for user registration and license plate detection
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
from detection_yolov5 import LicensePlateDetector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
DATABASE = 'parking.db'

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize license plate detector
detector = LicensePlateDetector()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with required tables"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            license_plate_number TEXT NOT NULL UNIQUE,
            image_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Smart Parking API is running"})

@app.route('/register', methods=['POST'])
def register_user():
    """Register a new user with license plate information"""
    try:
        # Check if all required fields are present
        if 'name' not in request.form or 'license_plate_number' not in request.form:
            return jsonify({"error": "Missing required fields"}), 400
        
        name = request.form['name']
        license_plate_number = request.form['license_plate_number'].upper().strip()
        
        # Validate that a file was uploaded
        if 'photo' not in request.files:
            return jsonify({"error": "No photo uploaded"}), 400
        
        file = request.files['photo']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if file and allowed_file(file.filename):
            # Generate a secure filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = secure_filename(f"{license_plate_number}_{timestamp}")
            ext = file.filename.rsplit('.', 1)[1].lower()
            filepath = os.path.join(UPLOAD_FOLDER, f"{filename}.{ext}")
            
            # Save the uploaded file
            file.save(filepath)
            
            # Check if license plate already exists
            conn = get_db()
            existing = conn.execute(
                'SELECT * FROM users WHERE license_plate_number = ?', 
                (license_plate_number,)
            ).fetchone()
            conn.close()
            
            if existing:
                # If user exists, delete the old image and update
                if os.path.exists(existing['image_path']):
                    os.remove(existing['image_path'])
                
                conn = get_db()
                conn.execute(
                    'UPDATE users SET name = ?, image_path = ? WHERE license_plate_number = ?',
                    (name, filepath, license_plate_number)
                )
                conn.commit()
                conn.close()
                
                return jsonify({
                    "status": "success",
                    "message": f"Updated existing user: {name}",
                    "license_plate": license_plate_number
                }), 200
            
            # Insert new user
            conn = get_db()
            conn.execute(
                'INSERT INTO users (name, license_plate_number, image_path) VALUES (?, ?, ?)',
                (name, license_plate_number, filepath)
            )
            conn.commit()
            conn.close()
            
            logger.info(f"Registered new user: {name} with plate {license_plate_number}")
            
            return jsonify({
                "status": "success",
                "message": f"User {name} registered successfully",
                "license_plate": license_plate_number
            }), 201
        else:
            return jsonify({"error": "Invalid file type"}), 400
            
    except Exception as e:
        logger.error(f"Error in register_user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/detect', methods=['POST'])
def detect_plate():
    """
    Detect license plate from uploaded image and check against database
    Returns annotated image with bounding boxes (green=known, red=unknown)
    """
    try:
        if 'photo' not in request.files:
            return jsonify({"error": "No photo uploaded"}), 400
        
        file = request.files['photo']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if file and allowed_file(file.filename):
            # Save uploaded file temporarily
            filename = secure_filename(f"detect_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
            ext = file.filename.rsplit('.', 1)[1].lower()
            temp_path = os.path.join(UPLOAD_FOLDER, f"{filename}.{ext}")
            file.save(temp_path)
            
            # Get all registered users from database
            conn = get_db()
            users = conn.execute('SELECT id, name, license_plate_number FROM users').fetchall()
            conn.close()
            
            # Build database plates dictionary
            database_plates_dict = {}
            for user in users:
                plate = user['license_plate_number'].upper().strip()
                database_plates_dict[plate] = {
                    'id': user['id'],
                    'name': user['name']
                }
            
            logger.info(f"Checking against {len(database_plates_dict)} registered plates")
            
            # Detect license plate with annotation
            logger.info("Starting license plate detection with annotation...")
            result = detector.detect_and_annotate(temp_path, database_plates_dict)
            
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Log the result
            if result.get('status') == 'known_user':
                logger.info(f"✓ Recognized user: {result.get('name')} - {result.get('license_plate')}")
            elif result.get('status') == 'unknown_user':
                logger.info(f"⚠ Unknown plate detected: {result.get('detected_plate')}")
            else:
                logger.info(f"✗ No plate found in image")
            
            return jsonify(result), 200
        else:
            return jsonify({"error": "Invalid file type"}), 400
            
    except Exception as e:
        logger.error(f"Error in detect_plate: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    """Get all registered users"""
    try:
        conn = get_db()
        users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
        conn.close()
        
        users_list = [dict(user) for user in users]
        
        return jsonify({
            "status": "success",
            "count": len(users_list),
            "users": users_list
        }), 200
    except Exception as e:
        logger.error(f"Error in get_users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user from the database"""
    try:
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
        if not user:
            conn.close()
            return jsonify({"error": "User not found"}), 404
        
        # Delete the image file
        if os.path.exists(user['image_path']):
            os.remove(user['image_path'])
        
        # Delete from database
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted user: {user['name']}")
        return jsonify({"status": "success", "message": f"User {user['name']} deleted"}), 200
    except Exception as e:
        logger.error(f"Error in delete_user: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    logger.info("Starting Smart Parking API on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)



