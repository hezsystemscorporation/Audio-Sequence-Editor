import json
import io
import zipfile
from flask import Flask, request, send_file, send_from_directory, Response
from flask_cors import CORS
import os

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
CORS(app)


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "index.html")


@app.route("/api/export-zip", methods=["POST"])
def export_zip():
    sequence_json = request.form.get("sequenceJson", "{}")
    files = request.files.getlist("files")

    file_map = {}
    for f in files:
        if f.filename:
            file_map[f.filename] = f.read()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("config.json", sequence_json)

        try:
            config = json.loads(sequence_json)
        except json.JSONDecodeError:
            config = {}

        audio_files = set()
        image_files = set()

        def collect_audio(val):
            if isinstance(val, list):
                for v in val:
                    if v:
                        audio_files.add(v)
            elif isinstance(val, dict):
                for v in val.values():
                    if isinstance(v, list):
                        for f in v:
                            if f:
                                audio_files.add(f)
                    elif isinstance(v, str) and v:
                        audio_files.add(v)
            elif isinstance(val, str) and val:
                audio_files.add(val)

        for step in config.get("steps", []):
            for action in step.get("actions", []):
                collect_audio(action.get("audioFileNames", []))
                collect_audio(action.get("subAudioFileName"))
                img = action.get("imageFileName")
                if img:
                    image_files.add(img)

        for ob in config.get("otherBroadcasts", []):
            collect_audio(ob.get("audioFileName"))

        for name in audio_files:
            if name in file_map:
                zf.writestr(f"audio/{name}", file_map[name])

        for name in image_files:
            if name in file_map:
                zf.writestr(f"image/{name}", file_map[name])

    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="sequence_pkg.zip",
    )


if __name__ == "__main__":
    app.run(debug=True, port=6532)
