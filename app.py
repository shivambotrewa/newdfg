from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse, parse_qs
import threading
import time
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Global variables
invidious_urls = []
last_refresh_time = 0
REFRESH_INTERVAL = 15 * 60  # 15 minutes in seconds

# First RapidAPI (ytjar) configuration
RAPIDAPI_URL_1 = "https://youtube-mp36.p.rapidapi.com/dl"
RAPIDAPI_HEADERS_1 = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
    "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
}

# Second fallback API configuration (example - replace with your actual API)
RAPIDAPI_URL_2 = "https://youtube-mp36.p.rapidapi.com/dl"  # Hypothetical URL
RAPIDAPI_HEADERS_2 = {
    "x-rapidapi-key": os.getenv("FALLBACK_API"),
    "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
}

def is_url_accessible(url):
    """
    Checks if a URL is accessible by making a HEAD request.
    Returns True if the status code is 200, otherwise False.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.head(url, headers=headers, allow_redirects=True)
        if response.status_code == 200:
            return True
    except requests.RequestException:
        return False


def extract_videoplayback_params(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    videoplayback_params = {key: value[0] for key, value in query_params.items()}
    print(videoplayback_params)
    return "videoplayback?" + "&".join([f"{key}={value}" for key, value in videoplayback_params.items()])

def fetch_invidious_urls():
    URL_1 = "https://raw.githubusercontent.com/NitinBot001/Uma/refs/heads/main/dynamic_instances.json"
    URL_2 = "https://raw.githubusercontent.com/n-ce/Uma/refs/heads/main/dynamic_instances.json"
    all_instances = set()
    
    for url in [URL_1, URL_2]:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                instances = data.get("invidious", [])
                all_instances.update(instances)
                print(all_instances)
        except requests.RequestException:
            continue
    
    return list(all_instances)

def refresh_urls():
    global invidious_urls, last_refresh_time
    while True:
        invidious_urls = fetch_invidious_urls()
        last_refresh_time = time.time()
        print(f"URLs refreshed at {time.ctime()}. Found {len(invidious_urls)} instances")
        time.sleep(REFRESH_INTERVAL)

def get_audio_url(video_id):
    global invidious_urls, last_refresh_time
    
    # Refresh URLs if needed
    if not invidious_urls or (time.time() - last_refresh_time > REFRESH_INTERVAL):
        invidious_urls = fetch_invidious_urls()
        last_refresh_time = time.time()
    
    # Try Invidious instances first
    if invidious_urls:
        for base_url in invidious_urls:
            api_url = f"{base_url}/api/v1/videos/{video_id}"
            try:
                response = requests.get(api_url)
                # print(response)
                if response.status_code == 200:
                    data = response.json()
                    # print(data)
                    adaptive_formats = data.get("adaptiveFormats", [])
                    for format in adaptive_formats:
                        # print(format)
                        itag = format.get("itag")
                        if itag == 140 or 139 or 251:
                            audio_url = format.get("url")
                            proxy_url = f"{base_url}/{extract_videoplayback_params(audio_url)}"
                            if is_url_accessible(proxy_url):
                                # print(proxy_url)
                                return proxy_url, itag, None, "invidious_api"
            except requests.RequestException:
                continue
    
    # First fallback: RapidAPI 1 (ytjar)
    try:
        if RAPIDAPI_HEADERS_1["x-rapidapi-key"] == "default_key_if_not_set":
            pass  # Skip to next fallback if key not set
        else:
            querystring = {"id": video_id}
            response = requests.get(RAPIDAPI_URL_1, headers=RAPIDAPI_HEADERS_1, params=querystring, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    return data.get("link"), "140", None, "ytjar"
                elif "quota" in data.get("msg", "").lower():
                    pass  # Quota exceeded, try next fallback
                else:
                    return None, None, f"RapidAPI 1 failed: {data.get('msg', 'Unknown error')}", None
            elif response.status_code == 429:  # Too Many Requests (quota exceeded)
                pass  # Try next fallback
    except requests.RequestException as e:
        pass  # Continue to next fallback on network error
    
    # Second fallback: RapidAPI 2 (replace with your actual API response handling)
    try:
        if RAPIDAPI_HEADERS_2["x-rapidapi-key"] == "default_key_if_not_set":
            return None, None, "No fallback API keys configured", None
            
        querystring = {"id": video_id}  # Adjust parameters based on actual API
        response = requests.get(RAPIDAPI_URL_2, headers=RAPIDAPI_HEADERS_2, params=querystring, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Adjust this part based on your second API's actual response format
            if data.get("status") == "ok":  # Assuming similar response structure
                return data.get("link"), "140", None, "ytjar2"  # Use a different method name
            return None, None, f"RapidAPI 2 failed: {data.get('msg', 'Unknown error')}", None
        elif response.status_code == 429:
            return None, None, "All API quotas exceeded", None
    except requests.RequestException as e:
        return None, None, f"RapidAPI 2 request failed: {str(e)}", None
    
    return None, None, "No suitable accessible audio URL found", None

@app.route('/audio_url', methods=['GET'])
def audio_url():
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": "Please provide a video_id using the 'v' parameter"}), 400
    
    stream_url, itag, error, method = get_audio_url(video_id)
    
    if error:
        return jsonify({"error": error}), 404
        
    return jsonify({
        "method": method or "unknown",
        "stream_url": stream_url,
        "status": 200,
        "video_id": video_id,
        "itag": itag
    })

if __name__ == '__main__':
    refresh_thread = threading.Thread(target=refresh_urls, daemon=True)
    refresh_thread.start()
    
    invidious_urls = fetch_invidious_urls()
    last_refresh_time = time.time()
    
    app.run(debug=True, host='0.0.0.0', port=8000)
