from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit
import mysql.connector
from yt_dlp import YoutubeDL
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'  # Chave para SocketIO
socketio = SocketIO(app)

# Configurações do MySQL (mude a senha para a sua)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin',  # Substitua pela sua senha do MySQL
    'database': 'youtube_downloader'
}

# Função para conectar ao banco


def connect_db():
    return mysql.connector.connect(**db_config)

# Função de progresso para yt-dlp


def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
        socketio.emit('progress', {'percent': percent}, namespace='/download')
    elif d['status'] == 'finished':
        socketio.emit('progress', {
                      'percent': 100, 'message': 'Download concluído!'}, namespace='/download')

# Rota para a página inicial


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        url = request.form.get("url")
        try:
            ydl_opts = {
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'format': 'best',
                # Adiciona o hook de progresso
                'progress_hooks': [progress_hook],
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Sem título')

            # Salva no banco
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO videos (url, title) VALUES (%s, %s)", (url, title))
            conn.commit()
            cursor.close()
            conn.close()
            message = f"Vídeo '{title}' baixado com sucesso!"
        except Exception as e:
            message = f"Erro: {str(e)}"
            socketio.emit(
                'progress', {'percent': 0, 'message': f'Erro: {str(e)}'}, namespace='/download')

    return render_template("index.html", message=message)

# Rota para mostrar o histórico


@app.route("/historico")
def historico():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url FROM videos")
    videos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("historico.html", videos=videos)


if __name__ == "__main__":
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    socketio.run(app, debug=True)
