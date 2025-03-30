from flask import Flask, request
import requests
from urllib.parse import urlparse, parse_qs
import threading
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global variables
invidious_urls = []
last_refresh_time = 0
REFRESH_INTERVAL = 15 * 60  # 15 minutes in seconds

def extract_videoplayback_params(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    videoplayback_params = {key: value[0] for key, value in query_params.items()}
    return "videoplayback?" + "&".join([f"{key}={value}" for key, value in videoplayback_params.items()])

def fetch_invidious_urls():
    url = "https://raw.githubusercontent.com/NitinBot001/Uma/refs/heads/main/dynamic_instances.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("invidious", [])
        return []
    except requests.RequestException:
        return []

def refresh_urls():
    global invidious_urls, last_refresh_time
    while True:
        invidious_urls = fetch_invidious_urls()
        last_refresh_time = time.time()
        print(f"URLs refreshed at {time.ctime()}. Found {len(invidious_urls)} instances")
        time.sleep(REFRESH_INTERVAL)

def get_audio_url(video_id):
    global invidious_urls, last_refresh_time
    
    # If URLs haven't been initialized or it's been too long, refresh immediately
    if not invidious_urls or (time.time() - last_refresh_time > REFRESH_INTERVAL):
        invidious_urls = fetch_invidious_urls()
        last_refresh_time = time.time()
    
    if not invidious_urls:
        return None, None, "No Invidious URLs available"
    
    for base_url in invidious_urls:
        api_url = f"{base_url}/api/v1/videos/{video_id}"
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                adaptive_formats = data.get("adaptiveFormats", [])
                for format in adaptive_formats:
                    itag = format.get("itag")
                    if itag == 140 or 139 or 251:
                        audio_url = format.get("url")
                        proxy_url = f"{base_url}/{extract_videoplayback_params(audio_url)}"
                        return proxy_url, itag, None
        except requests.RequestException:
            continue
    
    return None, None, "No suitable accessible audio URL found"

@app.route('/audio_url', methods=['GET'])
def audio_url():
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": "Please provide a video_id using the 'v' parameter"}), 400
    
    stream_url, itag, error = get_audio_url(video_id)
    
    if error:
        return jsonify({"error": error}), 404
        
    return jsonify({
        "video_id": video_id,
        "stream_url": stream_url,
        "itag": itag,
        "method": "invidious_api"
    })

if __name__ == '__main__':
    # Start the background refresh thread
    refresh_thread = threading.Thread(target=refresh_urls, daemon=True)
    refresh_thread.start()
    
    # Initial fetch
    invidious_urls = fetch_invidious_urls()
    last_refresh_time = time.time()
    
    app.run(debug=True, port=8000)
