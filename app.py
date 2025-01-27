import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load the API keys from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
FALLBACK_API = os.getenv("FALLBACK_API")

# Analytics tracking
analytics = {
    "free_api": {
        "success_count": 0,
        "error_count": 0,
        "last_success": None
    },
    "rapidapi": {
        "success_count": 0,
        "error_count": 0,
        "last_success": None
    },
    "rapidapi_fallback": {
        "success_count": 0,
        "error_count": 0,
        "last_success": None
    }
}

def update_analytics(method, success):
    """
    Update analytics for the specified method
    """
    if success:
        analytics[method]["success_count"] += 1
        analytics[method]["last_success"] = datetime.now().isoformat()
    else:
        analytics[method]["error_count"] += 1

def get_youtube_redirected_url(video_id, itag='140'):
    """
    Resolve direct URL using free API
    """
    try:
        initial_url = f"https://qtc.ggt.bz/latest_version?id={video_id}&itag={itag}&local=true"
        response = requests.head(initial_url, allow_redirects=True)
        success = response.status_code == 200
        update_analytics("free_api", success)
        return response.url if success else None
    except Exception as e:
        print(f"Free API Error: {e}")
        update_analytics("free_api", False)
        return None

def get_audio_url_rapidapi(video_id, api_key, method="rapidapi"):
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
        success = response.status_code == 200
        update_analytics(method, success)
        return response.json() if success else None
    except Exception as e:
        print(f"RapidAPI Error: {e}")
        update_analytics(method, False)
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
        rapidapi_fallback_result = get_audio_url_rapidapi(video_id, FALLBACK_API, "rapidapi_fallback")
        if rapidapi_fallback_result:
            return jsonify({
                **rapidapi_fallback_result,
                "method": "rapidapi_fallback"
            })

    return jsonify({"error": "Could not resolve URL"}), 404

@app.route('/info', methods=['GET'])
def get_info():
    """
    Get analytics information about API usage
    """
    total_requests = sum(method["success_count"] + method["error_count"] 
                        for method in analytics.values())
    
    successful_requests = sum(method["success_count"] for method in analytics.values())
    
    return jsonify({
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
        "methods": {
            "free_api": {
                "success_count": analytics["free_api"]["success_count"],
                "error_count": analytics["free_api"]["error_count"],
                "last_success": analytics["free_api"]["last_success"],
                "success_rate": (analytics["free_api"]["success_count"] / 
                    (analytics["free_api"]["success_count"] + analytics["free_api"]["error_count"]) * 100
                    if (analytics["free_api"]["success_count"] + analytics["free_api"]["error_count"]) > 0 
                    else 0
                )
            },
            "rapidapi": {
                "success_count": analytics["rapidapi"]["success_count"],
                "error_count": analytics["rapidapi"]["error_count"],
                "last_success": analytics["rapidapi"]["last_success"],
                "success_rate": (analytics["rapidapi"]["success_count"] / 
                    (analytics["rapidapi"]["success_count"] + analytics["rapidapi"]["error_count"]) * 100
                    if (analytics["rapidapi"]["success_count"] + analytics["rapidapi"]["error_count"]) > 0 
                    else 0
                )
            },
            "rapidapi_fallback": {
                "success_count": analytics["rapidapi_fallback"]["success_count"],
                "error_count": analytics["rapidapi_fallback"]["error_count"],
                "last_success": analytics["rapidapi_fallback"]["last_success"],
                "success_rate": (analytics["rapidapi_fallback"]["success_count"] / 
                    (analytics["rapidapi_fallback"]["success_count"] + analytics["rapidapi_fallback"]["error_count"]) * 100
                    if (analytics["rapidapi_fallback"]["success_count"] + analytics["rapidapi_fallback"]["error_count"]) > 0 
                    else 0
                )
            }
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=8000)
