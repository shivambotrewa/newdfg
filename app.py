from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Define the YouTube API endpoint and default parameters
YOUTUBE_API_URL = "https://www.youtube.com/youtubei/v1/player"
DEFAULT_PARAMS = {
    'key': "AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc",
    'prettyPrint': "false"
}

# Default headers (same as original)
HEADERS = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; rv:96.0) Gecko/20100101 Firefox/96.0",
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/json",
    'x-youtube-client-name': "IOS",
    'x-goog-visitor-id': "CgtQU0p0SmN6ODgtZyiVr6C_BjIKCgJJThIEGgAgEA%3D%3D",
    'sec-fetch-mode': "navigate",
    'accept-language': "en-US,en;q=0.5",
    'origin': "https://www.youtube.com",
    'x-youtube-client-version': "19.29.1",
    'Cookie': "YSC=lxImLoRvSo8; __Secure-YEC=; VISITOR_INFO1_LIVE=PSJtJcz88-g; VISITOR_PRIVACY_METADATA=CgJJThIEGgAgEA%3D%3D; __Secure-ROLLOUT_TOKEN=CInt6pfsrtuVkwEQkoX4jtOvjAMYkoX4jtOvjAM%3D; PREF=hl=en; SOCS=CAI; GPS=1"
}

def create_payload(video_id):
    """Create the payload dictionary with the given video ID"""
    return {
        "context": {
            "client": {
                "clientName": "IOS",
                "clientVersion": "19.29.1",
                "deviceMake": "Apple",
                "deviceModel": "iPhone16,2",
                "hl": "en",
                "osName": "iPhone",
                "osVersion": "17.5.1.21F90",
                "timeZone": "UTC",
                "userAgent": "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)",
                "gl": "US",
                "utcOffsetMinutes": 0
            }
        },
        "videoId": video_id,
        "playbackContext": {
            "contentPlaybackContext": {
                "html5Preference": "HTML5_PREF_WANTS"
            }
        }
    }

@app.route('/audio_url', methods=['GET'])
def get_audio_url():
    """Endpoint to get one audio URL from YouTube video"""
    # Get video_id from query parameter
    video_id = request.args.get('v')
    
    if not video_id:
        return jsonify({'error': 'Missing video_id parameter'}), 400
    
    try:
        # Create payload with provided video_id
        payload = create_payload(video_id)
        
        # Make the API request
        response = requests.post(
            YOUTUBE_API_URL,
            params=DEFAULT_PARAMS,
            data=json.dumps(payload),
            headers=HEADERS
        )
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            # Extract the first audio format with mimeType starting with "audio/mp4"
            for format in data.get('streamingData', {}).get('adaptiveFormats', []):
                if format.get('mimeType', '').startswith('audio/mp4'):
                    return jsonify({
                        'status': 'success',
                        "video_id": video_id,
                        "itag": "140",
                        'mimeType': format['mimeType'],
                        'stream_url': format['url']
                    })
            return jsonify({
                'status': 'error',
                'message': 'No audio/mp4 format found'
            }), 404
        else:
            return jsonify({
                'status': 'error',
                'message': f'API request failed with status code {response.status_code}',
                'response': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
