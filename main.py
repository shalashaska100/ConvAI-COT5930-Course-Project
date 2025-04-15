import os
from datetime import datetime
from google.cloud import texttospeech
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import base64
from google import genai
from google.genai import types

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_default_secret_key")

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
BOOK_FOLDER = 'books'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BOOK_FOLDER'] = BOOK_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BOOK_FOLDER, exist_ok=True)

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
def generate(book, audio, prompt):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    files = [
        # Make the file available in local system working directory
        client.files.upload(file=book),
        client.files.upload(file=audio),
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
                types.Part.from_uri(
                    file_uri=files[1].uri,
                    mime_type=files[1].mime_type,
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

# Google Text-to-Speech API integration
tts_client = texttospeech.TextToSpeechClient()
def sample_synthesize_speech(text=None, ssml=None):
    input = texttospeech.SynthesisInput()
    if ssml:
      input.ssml = ssml
    else:
      input.text = text

    voice = texttospeech.VoiceSelectionParams()
    voice.language_code = "en-UK"
    # voice.ssml_gender = "MALE"

    audio_config = texttospeech.AudioConfig()
    audio_config.audio_encoding = "LINEAR16"

    request = texttospeech.SynthesizeSpeechRequest(
        input=input,
        voice=voice,
        audio_config=audio_config,
    )

    response = tts_client.synthesize_speech(request=request)

    return response.audio_content

@app.route('/')
def index():
    files = get_files(UPLOAD_FOLDER)  # Files from the 'uploads' folder
    return render_template('index.html', files=files)


@app.route('/upload', methods=['POST'])
def upload_audio():
    book_file = os.listdir(BOOK_FOLDER)
    if not book_file:
        flash('No book uploaded')
        return redirect(request.url)
    book_path = os.path.join(BOOK_FOLDER, book_file[0])

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
        You are an AI assistant tht receives a book file, an audio file and a prompt
        Listen to the audio file and reply to what is asked
        """
    
        print(book_path)
        print(file_path)
        print(prompt)

        response = generate(book_path, file_path, prompt)
        tts_response = sample_synthesize_speech(response)

        print(response)


    if tts_response:
        #save response as audio
        response_filename = 'LLM Response TTS' + datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        response_file_path = os.path.join(app.config['UPLOAD_FOLDER'], response_filename)

        f = open(response_file_path,'wb')
        f.write(tts_response)
        f.close()

    return redirect('/')  # success

@app.route('/upload_book', methods=['POST'])
def upload_file():
    if 'book_file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['book_file']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file:
        file_path = os.path.join(app.config['BOOK_FOLDER'], file.filename)
        file.save(file_path)
        flash('File uploaded successfully')
        return redirect('/')
    else:
        flash('Invalid file type')
        return redirect(request.url)

# Route to serve files from either uploads or books folder
@app.route('/<folder>/<filename>')
def uploaded_file(folder, filename):
    if folder not in ['uploads', 'books']:
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