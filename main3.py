import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import base64
from google import genai
from google.genai import types

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_files(folder):
    files = []
    for filename in os.listdir(folder):
        if allowed_file(filename):
            files.append(filename)
    files.sort(reverse=True)
    return files

# Google genai LLM API integration
def generate(filename, prompt):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    files = [
        # Make the file available in local system working directory
        client.files.upload(file=filename),
    ]
    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=files[0].uri,
                    mime_type=files[0].mime_type,
                ),
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    print(response)
    return response.text


@app.route('/')
def index():
    files = get_files(UPLOAD_FOLDER)  # Files from the 'uploads' folder
    return render_template('index.html', files=files)


@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)

    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file:
        filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        prompt = """
        Please provide an exact trascript for the audio and share your opinion on what is said in the audio. Follow this with a sentiment analysis and why sentiment came out like that

        Your response should follow the format:

        Text: USERS SPEECH TRANSCRIPTION
        Your opinion
        Sentiment Analysis: positive|neutral|negative
        Why sentiment came out like that
        """

        response = generate(file_path, prompt)

        print(response)

        f = open(file_path + '.txt','w')
        f.write(response)
        f.close()

    return redirect('/')  # success

# Route to serve files from either uploads or tts folder
@app.route('/<folder>/<filename>')
def uploaded_file(folder, filename):
    if folder not in ['uploads', 'tts']:
        return "Invalid folder", 404

    folder_path = os.path.join(folder, filename)
    if os.path.exists(folder_path):
        return send_from_directory(folder, filename)
    else:
        return "File not found", 404


@app.route('/script.js', methods=['GET'])
def scripts_js():
    return send_from_directory('', 'script.js')


if __name__ == '__main__':
    app.run(debug=True, port=8080)
