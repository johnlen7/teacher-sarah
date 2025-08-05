from flask import Flask, request, jsonify
import whisper
import tempfile
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar modelo Whisper
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
DEVICE = os.getenv("DEVICE", "cpu")

logger.info(f"Carregando modelo Whisper {MODEL_SIZE} em {DEVICE}...")
model = whisper.load_model(MODEL_SIZE, device=DEVICE)
logger.info("Modelo carregado com sucesso!")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "model": MODEL_SIZE})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        
        # Salvar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp_file:
            audio_file.save(tmp_file.name)
            temp_path = tmp_file.name
        
        # Transcrever
        result = model.transcribe(
            temp_path,
            language='en',
            task='transcribe'
        )
        
        # Limpar arquivo temporário
        os.unlink(temp_path)
        
        return jsonify({
            "text": result["text"],
            "language": result.get("language", "en")
        })
        
    except Exception as e:
        logger.error(f"Erro na transcrição: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
