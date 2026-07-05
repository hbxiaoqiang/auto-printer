import os
import tempfile
import shutil
import threading
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS

from src.config import HOST, PORT, MAX_CONTENT_LENGTH, TEMP_DIR, logger
from src.tasks import task_manager
from src.printer import print_pdf

_base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(_base_dir, "templates"),
    static_folder=os.path.join(_base_dir, "static"),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app, resources={r"/*": {"origins": "*"}})


def allowed_file(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


@app.route("/")
def index():
    return render_template("demo.html")


@app.route("/demo")
def demo():
    return render_template("demo.html")


@app.route("/api/status")
def status():
    return jsonify(
        {
            "status": "running",
            "host": HOST,
            "port": PORT,
            "platform": os.name,
            "recent_tasks": [
                task_manager.to_dict(t) for t in task_manager.list_recent(10)
            ],
        }
    )


@app.route("/api/printers")
def printers():
    from src.printer import get_printers
    try:
        printer_list = get_printers()
        return jsonify({"printers": printer_list})
    except Exception as e:
        logger.exception("Failed to list printers")
        return jsonify({"error": str(e)}), 500


@app.route("/api/print", methods=["POST"])
def handle_print():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are supported"}), 400

    printer_name = request.form.get("printer", None)

    filename = secure_filename(file.filename)
    task = task_manager.create(filename)

    tmp_dir = tempfile.mkdtemp(prefix="job_", dir=TEMP_DIR)
    pdf_path = os.path.join(tmp_dir, filename)
    file.save(pdf_path)
    logger.info(f"Saved uploaded PDF to {pdf_path}, size={os.path.getsize(pdf_path)} bytes")

    def run_print():
        try:
            print_pdf(task.id, pdf_path, filename, printer_name=printer_name)
        finally:
            # 打印完成后清理 PDF 临时目录
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temp dir: {tmp_dir}")
            except Exception:
                pass

    threading.Thread(target=run_print, daemon=True).start()

    return jsonify(
        {
            "job_id": task.id,
            "status": task.status,
            "message": "Print job accepted",
            "printer": printer_name or "default",
        }
    )


@app.route("/api/tasks/<task_id>")
def get_task(task_id):
    task = task_manager.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task_manager.to_dict(task))


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large, max 50MB"}), 413


@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception")
    return jsonify({"error": str(e)}), 500
