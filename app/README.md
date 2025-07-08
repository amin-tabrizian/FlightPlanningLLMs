# Flight Planning LLM Web Application

A web-based interface for the Flight Planning LLM system that allows users to interactively generate flight plans using various AI models while avoiding wind hazard polygons.

## Features

- **KML File Upload**: Upload KML dataset files containing flight zones, origins, destinations, and hazard polygons
- **Dynamic Configuration**: Automatically extract and select from available polygon sets, origins, and destinations
- **Multiple AI Models**: Choose from various LLM models including GPT, Claude, and A* algorithms
- **Interactive Interface**: User-friendly web interface with real-time feedback
- **Visual Results**: Generated flight plan images with overlaid polygons and paths
- **Evaluation System**: Automatic validation of flight paths with detailed feedback
- **Coach Mode**: Optional human review and feedback system for improving future plans
- **Memory System**: Learn from previous flight planning experiences
- **Download Results**: Export flight plans as KML files

## Installation

1. **Navigate to the app directory**:
   ```bash
   cd app
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (create a `.env` file):
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

4. **Create necessary directories**:
   ```bash
   mkdir -p uploads static
   ```

## Usage

### Starting the Application

1. **Run the Flask application**:
   ```bash
   python app.py
   ```

2. **Open your web browser** and navigate to:
   ```
   http://localhost:8080
   ```

### Using the Web Interface

#### Step 1: Upload KML Dataset

1. Click on the upload area or drag and drop your KML file
2. Supported file format: `.kml`
3. Maximum file size: 16MB
4. The system will automatically parse the file and extract available:
   - Polygon sets (poly1, poly2, etc.)
   - Origin points (Origin1, Origin2, etc.)
   - Destination points (Destination1, Destination2, etc.)

#### Step 2: Configure Flight Parameters

1. **Polygon Set**: Select which set of hazard polygons to avoid (e.g., poly1, poly2)
2. **LLM Model**: Choose from available models:
   - `gpt-4o` - OpenAI GPT-4 Optimized
   - `gpt-4o-mini` - Smaller GPT-4 variant
   - `o3-mini` - OpenAI O3 Mini
   - `o3` - OpenAI O3
   - `o4-mini` - OpenAI O4 Mini
   - `claude-3-7` - Anthropic Claude 3.7
   - `claude-3-5` - Anthropic Claude 3.5
   - `claude-4-sonnet` - Anthropic Claude 4 Sonnet
   - `claude-4-opus` - Anthropic Claude 4 Opus
   - `Astar` - A* pathfinding algorithm

3. **Origin**: Select the starting point for the flight
4. **Destination**: Select the endpoint for the flight
5. **Human Preference/Message**: Enter any specific preferences or instructions for the flight plan
6. **System Message Key**: (Optional) Enter a specific system message key for customized prompts
7. **Enable Memory**: Check to use previous flight planning experiences
8. **Enable Coach Mode**: Check to provide feedback on the generated plan

#### Step 3: Generate Flight Plan

1. Click the "Run Flight Planning" button
2. The system will:
   - Generate a prompt based on your configuration
   - Query the selected AI model
   - Evaluate the generated flight path
   - Create a visual representation
   - Display results

#### Step 4: Review Results

The results panel will show:

1. **Flight Plan Image**: Visual representation showing:
   - Green boundary: Fly zone
   - Yellow polygons: Hazard areas to avoid
   - Green dot: Origin point
   - Blue dot: Destination point
   - Black line: Generated flight path
   - Red line: Any path segments that violate constraints

2. **Metrics**:
   - Total distance in kilometers
   - Number of waypoints
   - AI response time

3. **Evaluation**:
   - Path validity (valid/invalid)
   - Origin/destination connectivity
   - Intersected polygons (if any)
   - Waypoints outside the fly zone (if any)

4. **AI Explanation**: Natural language explanation of the flight plan

5. **Waypoints List**: Detailed coordinates of all waypoints

#### Step 5: Provide Feedback (Coach Mode)

If coach mode is enabled:

1. Review the generated flight plan
2. Enter your feedback in the review text area
3. Click "Submit Review" to save your feedback for future improvements

#### Step 6: Download Results

- Click "Download KML Solution" to save the flight plan as a KML file
- The KML file can be opened in Google Earth or other GIS applications

## File Structure

```
app/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Web interface template
├── static/               # Generated images and KML files
├── uploads/              # Uploaded KML files
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## API Endpoints

- `GET /` - Main web interface
- `POST /upload_kml` - Upload KML file and extract metadata
- `POST /run_planning` - Generate flight plan
- `POST /submit_review` - Submit human feedback (coach mode)

## Troubleshooting

### Common Issues

1. **File Upload Fails**:
   - Ensure the file is a valid KML format
   - Check file size (must be under 16MB)
   - Verify the uploads directory exists and is writable

2. **No Polygon Sets Found**:
   - Ensure your KML file contains placemarks with names starting with "poly"
   - Check that the KML file is properly formatted

3. **AI Model Errors**:
   - Verify your API keys are set correctly
   - Check your internet connection
   - Ensure you have sufficient API credits

4. **Image Generation Fails**:
   - Ensure matplotlib is properly installed
   - Check that the static directory exists and is writable
   - Verify the generated coordinates are valid

### Debug Mode

To run in debug mode for troubleshooting:

```bash
export FLASK_DEBUG=1
python app.py
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for OpenAI models (GPT, O3, O4)
- `ANTHROPIC_API_KEY`: Required for Claude models
- `FLASK_DEBUG`: Set to 1 for debug mode

### Customization

You can customize the application by modifying:

- `app.py`: Backend logic and API endpoints
- `templates/index.html`: Web interface appearance and behavior
- Model selection in the `AVAILABLE_MODELS` list

## Integration with Existing System

This web application integrates with the existing flight planning system by:

- Using the same utility functions from `utils.py`
- Leveraging the same AI models from `solver.py`
- Utilizing the same evaluation system from `coach.py`
- Maintaining compatibility with the memory system

## Security Notes

- Always use HTTPS in production
- Keep API keys secure and never commit them to version control
- Validate and sanitize all user inputs
- Consider implementing user authentication for production use
- Limit file upload sizes to prevent abuse

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the Flask application logs
3. Ensure all dependencies are properly installed
4. Verify API keys and network connectivity 