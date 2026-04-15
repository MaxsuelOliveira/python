from vosk import Model, KaldiRecognizer
import wave
import json

from pydub import AudioSegment

# Converte MP3 para WAV
audio = AudioSegment.from_mp3("audio.mp3")
audio = audio.set_channels(1).set_frame_rate(16000)
audio.export("audio.wav", format="wav")

# Carrega o modelo (baixado previamente)
model = Model("./modelos/vosk-model-small-pt-0.3")  # Caminho para o modelo em português

# Abre o áudio
wf = wave.open("audio.mp3", "rb")
rec = KaldiRecognizer(model, wf.getframerate())

transcricao = ""

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        transcricao += result.get("text", "") + " "

print("Transcrição:", transcricao)
