from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os  # To load environment variables

app = Flask(__name__)
CORS(app)

# Load the API keys from environment variables
API_KEY = os.getenv("RAPIDAPI_KEY")
FALLBACK_API = os.getenv("FALLBACK_API")

if not API_KEY:
    raise ValueError("RAPIDAPI_KEY environment variable not set")

@app.route('/get_audio_url', methods=['GET'])
def get_audio_url():
    # Get the 'v' parameter from the request
    video_id = request.args.get('v')
    
    if not video_id:
        return jsonify({"error": "Missing 'v' parameter"}), 400
    
    # Define the URL and headers
    url = "https://youtube-mp36.p.rapidapi.com/dl"
    querystring = {"id": video_id}

    # Try with the primary API key
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"    
    }

    response = requests.get(url, headers=headers, params=querystring)

    # If the primary API key fails, try with the fallback key
    if response.status_code != 200 and FALLBACK_API:
        headers["x-rapidapi-key"] = FALLBACK_API
        response = requests.get(url, headers=headers, params=querystring)

    # Return the JSON response from the external API
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch audio URL"}), response.status_code

if __name__ == '__main__':
    app.run(debug=True, port=8000)
