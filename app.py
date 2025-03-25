import os
import requests
import re
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load API keys from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
FALLBACK_API = os.getenv("FALLBACK_API")

# URL to fetch dynamic Invidious instances
DYNAMIC_INVIDIOUS_URL = "https://raw.githubusercontent.com/NitinBot001/Uma/refs/heads/main/dynamic_instances.json"

# Global variable to store cached Invidious API URLs
INVIDIOUS_API_CACHE = []

def fetch_invidious_instances():
    """
    Fetches the list of Invidious instances dynamically from the JSON file.
    Returns a list of Invidious API base URLs.
    """
    try:
        response = requests.get(DYNAMIC_INVIDIOUS_URL)
        response.raise_for_status()
        data = response.json()
        invidious_instances = data.get("invidious", [])
        return [f"{instance}/api/v1/videos/" for instance in invidious_instances]
    except requests.RequestException as e:
        print(f"Error fetching dynamic Invidious instances: {e}")
        return []

def refresh_invidious_cache():
    """
    Refreshes the cached list of Invidious API URLs.
    """
    global INVIDIOUS_API_CACHE
    INVIDIOUS_API_CACHE = fetch_invidious_instances()
    print("Refreshed Invidious API cache:", INVIDIOUS_API_CACHE)

def schedule_invidious_refresh():
    """
    Schedules the Invidious cache refresh to run every 15 minutes.
    """
    refresh_invidious_cache()  # Refresh immediately
    # Schedule the next refresh in 15 minutes (900 seconds)
    timer = threading.Timer(900, schedule_invidious_refresh)
    timer.daemon = True  # Ensures the timer stops when the main program exits
    timer.start()

def is_url_accessible(url):
    """
    Checks if a URL is accessible by making a GET request and verifying content.
    Returns True if the status code is 200 and content is served, otherwise False.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with requests.get(url, headers=headers, allow_redirects=True, timeout=5, stream=True) as response:
            if response.status_code == 200:
                # Try to read the first byte to confirm the server is serving content
                first_byte = next(response.iter_content(chunk_size=1), None)
                if first_byte is not None:
                    return True
        return False
    except requests.RequestException:
        return False

def process_video_url(video_id, itag='140', max_retries=1):
    """
    Tries multiple Invidious APIs to fetch a working processed URL for a given itag.
    Uses cached URLs and refreshes the cache up to max_retries times if all URLs fail.
    """
    global INVIDIOUS_API_CACHE

    # If cache is empty, refresh it
    if not INVIDIOUS_API_CACHE:
        refresh_invidious_cache()

    # If cache is still empty after refresh, return None
    if not INVIDIOUS_API_CACHE:
        print("No Invidious API URLs available in cache.")
        return None

    # Try each URL in the cache
    for base_url in INVIDIOUS_API_CACHE[:]:  # Use a copy of the list to avoid modifying it during iteration
        api_url = f"{base_url}{video_id}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            # Get adaptiveFormats
            adaptive_formats = data.get('adaptiveFormats', [])

            # Find matching format based on itag
            matching_format = next(
                (format for format in adaptive_formats if str(format.get('itag')) == str(itag)),
                None
            )

            if not matching_format:
                continue  # Try next Invidious API

            # Get the URL from matching format
            url = matching_format.get('url', '')

            # Replace the domain dynamically
            processed_url = re.sub(
                r'https://[^/]*\.googlevideo\.com',
                base_url.replace("/api/v1/videos/", ""),
                url
            )

            # Check if processed_url is accessible
            if is_url_accessible(processed_url):
                return processed_url  # Return working URL

        except requests.exceptions.RequestException as e:
            print(f"Error making API request to {base_url}: {e}")
            # Remove the failed URL from the cache
            INVIDIOUS_API_CACHE.remove(base_url)

    # If retries remain, refresh the cache and try again
    if max_retries > 0:
        refresh_invidious_cache()
        if INVIDIOUS_API_CACHE:
            return process_video_url(video_id, itag, max_retries - 1)
    # If no retries left or cache is empty, give up
    print("All Invidious API URLs failed after retries.")
    return None

def get_audio_url_cobalt(video_id):
    """
    Resolve URL using Cobalt API.
    """
    cobalt_url = "https://cobalt-api.kwiatekmiki.com/"
    headers = {
        "authority": "cobalt-api.kwiatekmiki.com",
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36"
    }
    payload = {
        "url": f"https://youtu.be/{video_id}",
        "downloadMode": "audio",
        "audioFormat": "mp3",
        "filenameStyle": "basic"
    }

    try:
        response = requests.post(cobalt_url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "tunnel":
                stream_url = data.get("url")
                # Check if the stream_url is accessible
                if is_url_accessible(stream_url):
                    return stream_url  # Return the URL if accessible
    except Exception as e:
        print(f"Cobalt API Error: {e}")
    return None

def get_audio_url_rapidapi(video_id, api_key):
    """
    Resolve URL using RapidAPI.
    """
    url = "https://youtube-mp36.p.rapidapi.com/dl"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"    
    }
    
    try:
        response = requests.get(url, headers=headers, params={"id": video_id})
        if response.status_code == 200:
            data = response.json()
            stream_url = data.get("link")
            # Check if the stream_url is accessible
            if is_url_accessible(stream_url):
                return data  # Return the RapidAPI response if accessible
    except Exception as e:
        print(f"RapidAPI Error: {e}")
    return None

@app.route('/audio_url', methods=['GET'])
def resolve_url():
    video_id = request.args.get('v')
    itag = request.args.get('itag', '140')  # Default to itag 140 if not provided

    if not video_id:
        return jsonify({"error": "Video ID is required"}), 400

    # First, try Invidious APIs
    invidious_url = process_video_url(video_id, itag)
    if invidious_url:
        return jsonify({
            "video_id": video_id,
            "stream_url": invidious_url,
            "itag": itag,
            "method": "invidious_api"
        })

    # If Invidious APIs fail, try Cobalt API
    cobalt_url = get_audio_url_cobalt(video_id)
    if cobalt_url:
        return jsonify({
            "video_id": video_id,
            "stream_url": cobalt_url,
            "itag": itag,
            "method": "cobalt_api"
        })

    # If Cobalt API fails and RapidAPI key exists, try RapidAPI
    if RAPIDAPI_KEY:
        rapidapi_result = get_audio_url_rapidapi(video_id, RAPIDAPI_KEY)
        if rapidapi_result:
            return jsonify({
                **rapidapi_result,
                "itag": itag,
                "method": "rapidapi"
            })

    # If fallback API exists, try fallback
    if FALLBACK_API and FALLBACK_API != RAPIDAPI_KEY:
        rapidapi_fallback_result = get_audio_url_rapidapi(video_id, FALLBACK_API)
        if rapidapi_fallback_result:
            return jsonify({
                **rapidapi_fallback_result,
                "itag": itag,
                "method": "rapidapi_fallback"
            })

    return jsonify({"error": "Could not resolve URL"}), 404

if __name__ == '__main__':
    # Start the periodic Invidious cache refresh (every 15 minutes)
    schedule_invidious_refresh()
    # Run the Flask app
    app.run(debug=True, port=8000)
