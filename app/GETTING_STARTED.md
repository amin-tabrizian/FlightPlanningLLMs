# Getting Started with Flight Planning LLM Web Application

## Quick Start Guide

### 1. Initial Setup

```bash
# Navigate to the app directory
cd app

# Run the setup script
./setup.sh

# Edit the .env file with your API keys
nano .env
```

### 2. Configure API Keys

Edit the `.env` file and replace the placeholder values:

```env
OPENAI_API_KEY=sk-your-actual-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key-here
```

### 3. Start the Application

```bash
# Method 1: Using the run script (recommended)
python run.py

# Method 2: Direct Flask execution
python app.py
```

### 4. Access the Web Interface

**For local access:**
Open your browser and navigate to: **http://localhost:5000**

**For SSH access:**
1. Find your server's IP address: `hostname -I` or `ip addr show`
2. Open your browser and navigate to: **http://YOUR-SERVER-IP:5000**
3. Make sure port 5000 is open in your firewall

**SSH Port Forwarding (Alternative):**
If direct access doesn't work, you can use SSH port forwarding:
```bash
# On your local machine
ssh -L 5000:localhost:5000 username@your-server-ip
# Then access http://localhost:5000 on your local machine
```

### 5. Using the Interface

#### Step-by-Step Workflow:

1. **Upload KML File**
   - Click the upload area or drag & drop your KML dataset file
   - The system will automatically extract polygon sets, origins, and destinations

2. **Configure Flight Parameters**
   - Select polygon set (e.g., poly1, poly2, ...)
   - Choose AI model (GPT, Claude, or A*)
   - Select origin and destination points
   - Enter human preferences (optional)
   - Enable memory/coach mode if desired

3. **Generate Flight Plan**
   - Click "Run Flight Planning"
   - Wait for the AI to generate the flight plan
   - View the results including metrics, evaluation, and visual map

4. **Review and Download**
   - Review the generated waypoints and evaluation
   - Provide feedback if coach mode is enabled
   - Download the KML solution file

## Sample Data

You can use the provided `dataset.kml` file from the parent directory as a test dataset. It contains:

- Multiple polygon sets (poly1 through poly9)
- 5 origin points (Origin1-Origin5)
- 5 destination points (Destination1-Destination5)
- A defined fly zone boundary

## Troubleshooting

### Common Issues:

1. **"Module not found" errors**
   - Ensure you're running from the `app` directory
   - Check that all dependencies are installed: `pip install -r requirements.txt`

2. **API key errors**
   - Verify your API keys in the `.env` file
   - Check that you have sufficient API credits

3. **File upload fails**
   - Ensure the file is a valid KML format
   - Check file size (max 16MB)

4. **Images not displaying**
   - Check that the `static` directory exists and is writable
   - Verify matplotlib is properly installed

### Getting Help:

- Check the full README.md for detailed documentation
- Review Flask application logs for error messages
- Ensure all required directories exist (uploads/, static/)

## Features Overview

✅ **Drag & drop KML file upload**  
✅ **Automatic polygon set detection**  
✅ **Multiple AI model support**  
✅ **Interactive parameter configuration**  
✅ **Real-time flight plan generation**  
✅ **Visual results with overlaid maps**  
✅ **Automatic path validation**  
✅ **Human feedback system (coach mode)**  
✅ **Memory system for learning**  
✅ **KML export of solutions**  

## Next Steps

- Explore different AI models to compare performance
- Try various polygon sets and origin/destination combinations
- Use coach mode to provide feedback and improve future plans
- Export solutions and view them in Google Earth or other GIS software

Happy flight planning! ✈️ 