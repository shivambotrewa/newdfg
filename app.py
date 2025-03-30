from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse, parse_qs
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global variables (refreshed on-demand in serverless)
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
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("invidious", [])
        return []
    except requests.RequestException as e:
        print(f"Error fetching Invidious URLs: {str(e)}")
        return []

def get_audio_url(video_id):
    global invidious_urls, last_refresh_time
    
    # Refresh URLs if stale or empty
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
                    if itag in [140, 139, 251]:
                        audio_url = format.get("url")
                        proxy_url = f"{base_url}/{extract_videoplayback_params(audio_url)}"
                        return proxy_url, itag, None
        except requests.RequestException as e:
            print(f"Error accessing {api_url}: {str(e)}")
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

# For Vercel: Export the app as a serverless function
handler = app

# For local testing only
if __name__ == '__main__':
    invidious_urls = fetch_invidious_urls()
    last_refresh_time = time.time()
    app.run(debug=True, port=8000)
