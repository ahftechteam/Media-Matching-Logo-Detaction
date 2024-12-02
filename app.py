import os
from flask import Flask, request, jsonify, send_from_directory, send_file
from redis import Redis
from rq import Queue, Retry
import requests
from media_monitoring import MediaMonitoring
from flask_cors import cross_origin, CORS
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from config.config import CoolConfig
from database.database import db
from utility.audio_utils import AudioUtils
from utility.video_utils import VideoUtils
from utility.logo_utils import LogoUtils
from datetime import datetime

app = Flask(__name__)

CORS(app)

app.config.from_object(CoolConfig)
db.init_app(app)

migrate = Migrate(app, db)

# Create all tables in the database
with app.app_context():
    try:
        from models.fingerprints import Fingerprint
        db.create_all()
        print("Database tables created successfully!",  flush=True)
    except Exception as e:
        print(f"Error creating database tables: {e}",  flush=True)
        
# Redis and RQ setup
redis_conn = Redis()
q = Queue(connection=redis_conn)

# Set up upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# generate fingerprint
@app.route('/generate-fingerprint-local-path', methods=['POST'])
@cross_origin()
def generate_fingerprint_local():
    """
    Generates fingerprints for audio files with local path.
    """
    try:
        json_data = request.json
        _id = json_data.get('_id')
        name = json_data.get("name")
        start_time = json_data.get("startTime")
        content_url = json_data.get("contentUrl")
        media_type = json_data.get("mediaType").lower() 
        station_name = json_data.get("stationName")

        # Construct filename and file path
        file_extension = 'mp3' if media_type == "radio" else 'mp4'
        filename = f'{content_url}.{file_extension}'
        file_path = f'http://127.0.0.1:3001/{media_type}/{filename}'

        if not file_path:
            return jsonify({'error': 'No selected file'}), 400

        # Check for existing fingerprint
        if Fingerprint.get_by_recording_id(_id):
            return jsonify({"message": "Recording ID already exists in the database", "statusCode": 409})
       
        # Process input values
        time = AudioUtils.extract_time(content_url)
        start_time = AudioUtils.replace_characters(start_time, ':', "-") 
        name = AudioUtils.replace_characters(name, " ", "-") 
        station_name = AudioUtils.replace_characters(station_name, " ", "-")
        fingerprint_destination_path_name = f"{media_type}/{time}/{station_name}/{start_time}-{name}"

        # Set partition and slice sizes
        partition_size = 12
        slice_size = 3

        # Create MediaMonitoring instance and enqueue job
        media_monitoring_instance = MediaMonitoring()
        job = q.enqueue(media_monitoring_instance.make_fingerprint, args=(_id, file_path, partition_size, slice_size, fingerprint_destination_path_name), job_timeout=3600, retry=Retry(max=3))

        fingerprint = Fingerprint.create(_id, fingerprint_destination_path_name, partition_size, 60.00, datetime.now())
        fingerprint_dict = fingerprint.to_dict()
        
        return jsonify({"job_id": job.get_id(), "status": "Job enqueued", "data": fingerprint_dict})
    
    except Exception as e:
        print(f"An exception occurred: {type(e).__name__}: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

# Make Match
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/make-matching', methods=['POST'])
@cross_origin()
def make_matching():
    """
    Matches audio files for advertising detection.
    """
    try:
        
        _id = request.form.get('_id')
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not AudioUtils.allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        print(filename)
        base_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(base_dir, exist_ok=True)
        file_path = os.path.join(base_dir, filename)
        file.save(file_path)

        
        media_monitoring_instance = MediaMonitoring()
        matching_result = media_monitoring_instance.make_matching(_id, file_path)
        # job = q.enqueue(media_monitoring_instance.make_matching, args=(_id, file_path), job_timeout=3600, retry=Retry(max=3))

        print(matching_result)
        
        if isinstance(matching_result, dict) and  matching_result["message"] == "No fingeprint found":
            return jsonify(matching_result),200
       
        result = []
        for match in matching_result:
            partition_number = match[0]
            slice_number = match[1]
            seconds = match[2]

            result.append(AudioUtils.convert_to_hms(int(partition_number), int(slice_number), int(float(seconds))))

        return jsonify(result), 200

        
    except Exception as e:
        print(f"An exception occurred: {type(e).__name__}: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500



# Endpoint to handle image uploads
@app.route('/detect', methods=['POST'])
@cross_origin()
def detect_logo():
    """
    Detects logos in the uploaded video file.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']

        videoInputId = request.form.get('videoInputId')
       
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not VideoUtils.allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        base_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(base_dir, exist_ok=True)
        file_path = os.path.join(base_dir, filename)
        file.save(file_path)

        config = {
            "detection_model_path": "model/AyatLogoTracker.pt",
            "video_path": file_path,  # Use the uploaded file path
            "logo_name": "Ayat Share Company",
            "output_json_path": "utility/detection_output.json",
            "post_url": "http://127.0.0.1:3001/api/v1/logo/report",
            "videoInputId": videoInputId,
        }
        
        res = LogoUtils.process_video(config)
        print(res)
        return jsonify({
            'message': 'Detection completed, result sent to server',
            'result': res
        })

    except Exception as e:
        print(f"An exception occurred: {type(e).__name__}: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

if __name__ == "__main__":
    app.run(debug=True)
