from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, send_file
import os
import sys
import tempfile
import shutil
from werkzeug.utils import secure_filename
import xml.etree.ElementTree as ET
import time
import logging
import json

# Add the parent directory to the Python path to import the flight planning modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils import get_coordinates_from_kml, convert_to_float_dict, prompt_generator, convert_waypoints, compute_total_path_length, convert_waypoints_to_dict, PlannerSolution, mode_detector
from solver import response_generator
from osm_img_generator import generate_osm_img
# from img_generator import generate_osm_img
from coach import rule_based_evaluation, llm_evaluation
from update_memory import update_memory, sample_from_memory
from utils import greedy_merge
import simplekml

# Configure logging for Flask app
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key
app.config['UPLOAD_FOLDER'] = os.path.join(APP_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(APP_DIR, 'static'), exist_ok=True)

# Available models from solver.py
AVAILABLE_MODELS = [
    'gpt-4o',
    'gpt-4o-mini', 
    'o3-mini',
    'o3',
    'o4-mini',
    'claude-3-7',
    'claude-3-5',
    'claude-4-sonnet',
    'claude-4-opus',
    'Astar'
]

# Load prompts from JSON file
def load_prompts():
    """Load prompts from the prompts_no_memory.json file"""
    try:
        prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts_no_memory.json')
        with open(prompts_path, 'r') as f:
            prompts = json.load(f)
        return prompts
    except Exception as e:
        logging.error(f"Error loading prompts: {e}")
        return {}

# Load prompts at startup
PROMPTS = load_prompts()
DEFAULT_PROMPT_KEY = 'sys_msg_zero_shot_ours'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'kml'

def extract_polygon_sets_from_kml(kml_path):
    """Extract available polygon sets from KML file using the same workflow as main.py"""
    try:
        # First, we need to get all placemark names from the KML file
        # We'll parse the file directly to get all placemark names first
        import xml.etree.ElementTree as ET
        tree = ET.parse(kml_path)
        root = tree.getroot()
        namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # Get all placemark names first
        all_placemark_names = []
        for elem in root.findall(".//kml:Placemark", namespace):
            name = elem.find("kml:name", namespace)
            if name is not None and name.text:
                all_placemark_names.append(name.text)
        
        # Now categorize them
        polygon_sets = set()
        origins = []
        destinations = []
        for placemark_name in all_placemark_names:
            if placemark_name.startswith('poly'):
                # Extract polygon set number (e.g., poly1-1 -> poly1)
                poly_set = placemark_name.split('-')[0]
                polygon_sets.add(poly_set)
            elif placemark_name.startswith('Origin'):
                origins.append(placemark_name)
            elif placemark_name.startswith('Destination'):
                destinations.append(placemark_name)
            else:
                # Filter out 'FlyZone' from polygon sets
                if placemark_name != 'FlyZone':
                    polygon_sets.add(placemark_name)

            
            
        
        return sorted(list(polygon_sets)), sorted(origins), sorted(destinations)
    except Exception as e:
        print(f"Error extracting from KML: {e}")
        return [], [], []

@app.route('/')
def index():
    print("Index route called")
    return render_template('index.html', models=AVAILABLE_MODELS, prompts=PROMPTS, default_prompt=DEFAULT_PROMPT_KEY)

@app.route('/upload_kml', methods=['POST'])
def upload_kml():
    if 'kml_file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['kml_file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract polygon sets, origins, and destinations
        polygon_sets, origins, destinations = extract_polygon_sets_from_kml(filepath)

        
        return jsonify({
            'success': True,
            'filename': filename,
            'polygon_sets': polygon_sets,
            'origins': origins,
            'destinations': destinations
        })
    else:
        flash('Invalid file type. Please upload a KML file.')
        return jsonify({'success': False, 'error': 'Invalid file type'})

@app.route('/run_planning', methods=['POST'])
def run_planning():
    try:
        # Get form data
        data = request.get_json()
        
        kml_filename = data.get('kml_filename')
        polygon_sets = data.get('polygon_set', [])  # Now expecting a list
        origin = data.get('origin')
        destination = data.get('destination')
        model_name = data.get('model')
        human_msg = data.get('human_msg', '')
        memory_enabled = data.get('memory', False)
        coach_enabled = data.get('coach', False)
        prompt_key = data.get('prompt_key', DEFAULT_PROMPT_KEY)
        
        
        if not all([kml_filename, polygon_sets, origin, destination, model_name]) or len(polygon_sets) == 0:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        # Get the system message from prompts
        # system_message = PROMPTS.get(prompt_key, PROMPTS.get(DEFAULT_PROMPT_KEY, ''))
        
        # Construct file paths
        kml_path = os.path.join(app.config['UPLOAD_FOLDER'], kml_filename)
        
        # Create unique filenames for this run
        timestamp = str(int(time.time()))
        solution_path = os.path.join(APP_DIR, f"static/solution_{timestamp}.kml")
        image_path = os.path.join(APP_DIR, f"static/flight_plan_{timestamp}.png")
        text_path = os.path.join(APP_DIR, f"static/flight_plan_{timestamp}.txt")
        
        if not os.path.exists(kml_path):
            return jsonify({'success': False, 'error': 'KML file not found'})
        
        # Extract place marks - find all polygons with the selected sets
        place_marks = polygon_sets + [origin, destination]
        
        # Extract and convert coordinates
        coordinates_dict = get_coordinates_from_kml(kml_path, place_marks)
        float_coordinates = convert_to_float_dict(coordinates_dict, approx=False)
        
        if not float_coordinates:
            return jsonify({'success': False, 'error': 'No coordinates found in KML file'})
        
        # Sample from memory if enabled (same as main.py line 81-82)
        if memory_enabled:
            memory_db_path = os.path.join(PROJECT_ROOT, 'memory_database.json')
            # Use the first polygon set for memory sampling
            if 'poly' in polygon_sets[0]:
                sample_from_memory(polygon_sets[0], memory_path=memory_db_path, n_samples=2)
            else:
                sample_from_memory(polygon_sets, memory_path=memory_db_path, n_samples=2)
        
        # Generate prompt for flight planning
        prompt = prompt_generator(float_coordinates, place_marks, human_msg, samples=False, system_message=prompt_key)
        
        # Generate flight plan
        start_time = time.time()
        response = response_generator(prompt, model_name, memory_enabled, float_coordinates)
        end_time = time.time()
        
        if not response or not response.waypoints:
            return jsonify({'success': False, 'error': 'Failed to generate flight plan'})
        
        waypoints_list = convert_waypoints(response.waypoints)
        
        # Calculate total path length
        total_length = compute_total_path_length(waypoints_list)
        
        # Evaluate the path planning
        evaluation = rule_based_evaluation(waypoints_list, float_coordinates)
        
        # Generate simplified waypoints if valid (same as main.py lines 98-101)
        simplified_waypoints = None
        image_generated = False
        
        if evaluation.valid:
            simplified_waypoints = greedy_merge(waypoints_list, float_coordinates)
            image_generated = generate_osm_img(float_coordinates, simplified_waypoints, image_path, evaluation)
        else:
            image_generated = generate_osm_img(float_coordinates, waypoints_list, image_path, evaluation)
        
        # Log image generation status
        if image_generated:
            logging.info(f"Flight plan image generated successfully: {image_path}")
        else:
            logging.warning(f"Failed to generate flight plan image: {image_path}")
            # Image path will still be sent to frontend, but file won't exist
        
        # Use simplified waypoints if available, otherwise use raw waypoints
        final_waypoints = simplified_waypoints if simplified_waypoints else waypoints_list
        final_waypoint_count = len(simplified_waypoints) if simplified_waypoints else len(response.waypoints)
        
        # Recalculate total path length with final waypoints
        final_total_length = compute_total_path_length(final_waypoints)
        
        # Create KML file with results
        import simplekml
        polygon_kml = simplekml.Kml()
        
        # Add points/polygons based on placemark names
        if float_coordinates:
            for name, coords in float_coordinates.items():
                if 'Origin' in name:
                    polygon_kml.newpoint(name=name, coords=coords)
                elif 'Destination' in name:
                    polygon_kml.newpoint(name=name, coords=coords)
                elif name == 'FlyZone':
                    polygon = polygon_kml.newpolygon(name=name, outerboundaryis=coords)
                    polygon.style.polystyle.color = simplekml.Color.changealphaint(51, simplekml.Color.red)
                else:
                    polygon_kml.newpolygon(name=name, outerboundaryis=coords)
        
        # Add the flight plan as a linestring using final waypoints
        line = polygon_kml.newlinestring(name="PolySolution", coords=final_waypoints)
        line.style.linestyle.color = simplekml.Color.green
        line.style.linestyle.width = 5
        
        # Save KML file
        polygon_kml.save(solution_path)
        
        # Create Mission Planner format text file
        with open(text_path, 'w') as f:
            # Header line
            f.write("QGC WPL 110\n")
            
            # Find origin coordinates for takeoff and return to launch
            origin_coords = None
            for name, coords in float_coordinates.items():
                if 'Origin' in name:
                    origin_coords = coords[0]  # Take first coordinate pair [lon, lat]
                    break
            
            if origin_coords is None:
                # Fallback to first waypoint if no origin found
                origin_coords = final_waypoints[0]
            
            # First waypoint: Takeoff to 90m at origin
            f.write(f"0\t1\t0\t22\t0\t0\t0\t0\t{origin_coords[1]}\t{origin_coords[0]}\t90\t1\n")
            
            # Navigation waypoints (skip first waypoint which is origin, start from index 1)
            waypoint_index = 1
            for wp in final_waypoints[1:]:  # Skip the first waypoint (origin)
                f.write(f"{waypoint_index}\t0\t3\t16\t0\t0\t0\t0\t{wp[1]}\t{wp[0]}\t90\t1\n")
                waypoint_index += 1
            
            # Return to launch
            f.write(f"{waypoint_index}\t0\t3\t20\t0\t0\t0\t0\t0\t0\t0\t1\n")
        
        # Initialize human_review logic (same as main.py lines 131-134)
        if not hasattr(evaluation, 'human_review') or evaluation.human_review == "":
            evaluation.human_review = "True"
        else:
            evaluation.human_review = "False"
        
        solution = PlannerSolution()
        solution.core_metrics = {
            "distance_km": final_total_length,       
            "num_waypoints": final_waypoint_count,      
            "response_time_s": end_time - start_time,   
            "energy": 0.0,           
            "is_valid": evaluation.valid,        
            "orig_dest": evaluation.orig_dest_ok,       
            "fly_zone": evaluation.out_pts,        
            "avoid_polygons": evaluation.polys,  
            "model": model_name,
            # "mode": mode_detector(place_marks),              
            "memory": memory_enabled,
            "solution_waypoints": final_waypoints, 
            "polygon_number": polygon_sets,   
            "human_preference": human_msg,
            "orig_dest": [place_marks[-2], place_marks[-1]],
            "aligned_with_human_preference": evaluation.human_review
        }
        
        # Prepare results for web response
        result = {
            'success': True,
            'explanation': response.explanation,
            'total_length': round(final_total_length, 2),
            'response_time': round(end_time - start_time, 2),
            'evaluation': {
                'valid': evaluation.valid,
                'intersected_polygons': evaluation.polys,
                'origin_dest_ok': evaluation.orig_dest_ok,
                'out_of_flyzone': evaluation.out_pts
            },
            'image_path': f"/static/flight_plan_{timestamp}.png",
            'solution_path': f"/static/solution_{timestamp}.kml",
            'text_path': f"/static/flight_plan_{timestamp}.txt",
            'coach_enabled': coach_enabled,
            'solution_metrics': solution.core_metrics,
            'float_coordinates': float_coordinates,
            'simplified_waypoints': simplified_waypoints if simplified_waypoints else None,
            'response_waypoints': final_waypoints,
            'human_msg': human_msg
        }
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error in run_planning: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/submit_review', methods=['POST'])
def submit_review():
    try:
        data = request.get_json()
        human_review = data.get('review', '')
        # The frontend will need to pass the necessary data to replicate main.py lines 123-130
        float_coordinates = data['flight_plan_data'].get('float_coordinates', {})
        simplified_waypoints = data['flight_plan_data'].get('simplified_waypoints')
        response_waypoints = data['flight_plan_data'].get('response_waypoints', {})
        evaluation_data = data['flight_plan_data'].get('evaluation', {})
        human_msg = data['flight_plan_data'].get('human_msg', '')
        
        if not human_review:
            return jsonify({'success': False, 'error': 'Missing review data'})
        
        # Create evaluation object from data
        from coach import Evaluation
        evaluation = Evaluation(
            valid=evaluation_data.get('valid', False),
            polys=evaluation_data.get('intersected_polygons', []),
            segs=[],
            orig_dest_ok=evaluation_data.get('origin_dest_ok', [False, False]),
            out_pts=evaluation_data.get('out_of_flyzone', []),
            human_review=human_review
        )
        
        # Follow exact main.py workflow (lines 123-130)
        if simplified_waypoints:
            update_memory(float_coordinates, convert_waypoints_to_dict(simplified_waypoints), evaluation, human_msg)
        else:
            update_memory(float_coordinates, convert_waypoints_to_dict(response_waypoints), evaluation, human_msg)
        
        logging.info(f"Memory updated with evaluation results - Human review: {human_review}")
        
        return jsonify({'success': True, 'message': 'Review submitted and memory updated successfully'})
        
    except Exception as e:
        logging.error(f"Error in submit_review: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Use run.py instead for proper configuration
    print("Please use 'python run.py' to start the application")
    print("This ensures proper environment configuration and SSH access")
    
    # For production deployment, run directly
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)

 