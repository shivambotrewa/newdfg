import os
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load the API keys from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
FALLBACK_API = os.getenv("FALLBACK_API")

def get_youtube_redirected_url(video_id, itag='140'):
    """
    Resolve direct URL using free API
    """
    try:
        initial_url = f"https://qtc.ggt.bz/latest_version?id={video_id}&itag={itag}&local=true"
        response = requests.head(initial_url, allow_redirects=True)
        return response.url if response.status_code == 200 else None
    except Exception as e:
        print(f"Free API Error: {e}")
        return None

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

@app.route('/audio_url', methods=['GET'])
def resolve_url():
    video_id = request.args.get('v')
    itag = request.args.get('itag', '140')

    if not video_id:
        return jsonify({"error": "Video ID is required"}), 400

    # First, try free API
    free_url = get_youtube_redirected_url(video_id, itag)
    if free_url:
        return jsonify({
            "video_id": video_id,
            "stream_url": free_url,
            "method": "free_api"
        })

    # If free API fails and RapidAPI key exists, try RapidAPI
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

if __name__ == '__main__':
    app.run(debug=True,port=8000)
