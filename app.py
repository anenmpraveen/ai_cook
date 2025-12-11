from flask import Flask, request, render_template, jsonify
import os
import requests
import yt_dlp
import whisper
import re
import torch
from dotenv import load_dotenv

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

app = Flask(__name__, static_folder='static', template_folder='templates')


device = "cuda" if torch.cuda.is_available() else "cpu"

# ---------------------- RECIPE GENERATION ----------------------
@app.route('/')
def home():
    return render_template('homepage.html')

@app.route('/recipe-generator')
def recipe_generator_page():
    return render_template('recipe_generator.html')

@app.route('/generate-recipe', methods=['POST'])
def generate_recipe():
    try:
        data = request.get_json()
        ingredients = data.get('ingredients', [])
        cuisine = data.get('cuisine', 'any')
        difficulty = data.get('difficulty', 'any')
        servings = int(data.get('servings', 4))
        time = int(data.get('time', 30))

        prompt = (f"Generate a detailed recipe using the following:\n"
                  f"- Ingredients: {', '.join(ingredients)}\n"
                  f"- Cuisine: {cuisine}\n"
                  f"- Difficulty: {difficulty}\n"
                  f"- Servings: {servings}\n"
                  f"- Cooking Time: {time} minutes\n"
                  f"Provide a structured list of ingredients and clear step-by-step instructions.")

        mistral_api_url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7
        }

        response = requests.post(mistral_api_url, json=payload, headers=headers)
        response_data = response.json()
        recipe_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "Failed to generate recipe.")

        return jsonify({"recipe": recipe_text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------------- YOUTUBE VIDEO TRANSCRIPTION ----------------------
def download_audio(youtube_url):
    """Download YouTube video as an audio file and return the filename."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'outtmpl': 'static/temp_audio.%(ext)s',
        'quiet': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp3').replace('.m4a', '.mp3')

        if not os.path.exists(filename):
            raise RuntimeError("Error: Audio file was not downloaded properly.")

        return filename

    except Exception as e:
        raise RuntimeError(f"Error downloading audio: {str(e)}")


def clean_transcription(transcription):
    """Convert transcription into structured step-by-step bullet points."""
    if not transcription:
        return "No speech detected."

    cleaned_text = re.sub(r'(?i)(hi everyone|thanks for watching|subscribe|hit the notification).*', '', transcription)
    cleaned_text = re.sub(r'(?i)(if you enjoyed this video|leave a comment|don’t forget).*', '', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    steps = re.split(r'(?<=[.!?])\s+', cleaned_text)

    formatted_steps = [f"• {step.strip()}" for step in steps if step.strip()]

    return "\n".join(formatted_steps) if formatted_steps else "No clear steps found."


def extract_ingredients(text):
    """Extract ingredients using regex."""
    ingredient_pattern = r'(\d+\s*(?:g|grams|ml|l|cups|tbsp|tsp|teaspoons?|tablespoons?)\s+[A-Za-z\s\-]+)'
    matches = re.findall(ingredient_pattern, text, re.IGNORECASE)
    return matches if matches else ["No ingredients detected."]


def transcribe_audio(audio_path):
    """Transcribe and translate audio to English."""
    if not os.path.exists(audio_path):
        raise RuntimeError(f"Error: The file {audio_path} was not found.")

    try:
        model = whisper.load_model("medium", device=device)  # Auto-detects GPU or CPU
        result = model.transcribe(audio_path, task="translate")  

        full_text = clean_transcription(result["text"])
        ingredients = extract_ingredients(full_text)

        return full_text, ingredients

    except Exception as e:
        raise RuntimeError(f"Transcription failed: {str(e)}")


@app.route('/youtube_extractor', methods=['GET', 'POST'])
def youtube_extractor():
    """Handle the YouTube link input and return transcribed text & ingredients."""
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')

        if not youtube_url:
            return jsonify({'error': 'No YouTube URL provided'}), 400

        try:
            audio_path = download_audio(youtube_url)
            transcription, ingredients = transcribe_audio(audio_path)


            if os.path.exists(audio_path):
                os.remove(audio_path)

            return render_template('youtube_extractor.html', transcription=transcription, ingredients=ingredients)

        except Exception as e:
            if os.path.exists(audio_path):
                os.remove(audio_path)  
            return jsonify({'error': str(e)}), 500

    return render_template('youtube_extractor.html', transcription=None, ingredients=None)


if __name__ == '__main__':
    app.run(debug=True)
