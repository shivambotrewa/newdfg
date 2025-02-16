import os
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load the API keys from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
FALLBACK_API = os.getenv("FALLBACK_API")

def process_video_url(video_id, itag='140'):
    """
    Fetches video information and returns a processed URL based on the itag.

    Args:
        video_id (str): The video ID to process
        itag (str): The itag for the desired format (default is 140 for audio)

    Returns:
        str: Processed URL with replaced domain or None if unavailable
    """
    base_url = "https://invidious.nikkosphere.com/api/v1/videos/"
    api_url = f"{base_url}{video_id}"

    try:
        # Make the API request
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        # Get adaptiveFormats
        adaptive_formats = data.get('adaptiveFormats', [])

        # Find matching format based on itag
        matching_format = next(
            (format for format in adaptive_formats if str(format.get('itag')) == itag),
            None
        )

        if not matching_format:
            return None

        # Get the URL from matching format
        url = matching_format.get('url', '')

        # Replace the domain
        processed_url = re.sub(
            r'https://[^/]*\.googlevideo\.com',
            'https://invidious.nikkosphere.com',
            url
        )

        return processed_url

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

@app.route('/audio_url', methods=['GET'])
def resolve_url():
    video_id = request.args.get('v')
    itag = request.args.get('itag', '140')  # Default itag for audio

    if not video_id:
        return jsonify({"error": "Video ID is required"}), 400

    # First, try Invidious API
    invidious_url = process_video_url(video_id, itag)
    if invidious_url:
        return jsonify({
            "video_id": video_id,
            "stream_url": invidious_url,
            "link": invidious_url,
            "method": "invidious_api"
        })

    # If Invidious API fails and RapidAPI key exists, try RapidAPI
    if RAPIDAPI_KEY:
        rapidapi_result = get_audio_url_rapidapi(video_id, RAPIDAPI_KEY)
        if rapidapi_result:
            return jsonify({
                **rapidapi_result,
                "method": "rapidapi"
            })

    # If fallback API exists, try with fallback
    if FALLBACK_API and FALLBACK_API != RAPIDAPI_KEY:
        rapidapi_fallback_result = get_audio_url_rapidapi(video_id, FALLBACK_API)
        if rapidapi_fallback_result:
            return jsonify({
                **rapidapi_fallback_result,
                "method": "rapidapi_fallback"
            })

    return jsonify({"error": "Could not resolve URL"}), 404

def get_audio_url_rapidapi(video_id, api_key):
    """
    Resolve URL using RapidAPI
    """
    url = "https://youtube-mp36.p.rapidapi.com/dl"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"    
    }
    
    try:
        response = requests.get(url, headers=headers, params={"id": video_id})
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"RapidAPI Error: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, port=8000)
