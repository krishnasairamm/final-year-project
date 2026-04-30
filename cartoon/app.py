import base64
import io
import os
import tempfile
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from gradio_client import Client, handle_file
from PIL import Image, ImageChops, ImageFilter, ImageOps

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)


def _env_int(name, default, minimum, maximum):
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"Invalid {name}={raw!r}; using default {default}")
        return default
    return max(minimum, min(maximum, value))


def _env_float(name, default, minimum, maximum):
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        print(f"Invalid {name}={raw!r}; using default {default}")
        return default
    return max(minimum, min(maximum, value))


def _env_bool(name, default):
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


GRADIO_SPACE_ID = os.getenv("GRADIO_SPACE_ID", "akhaliq/AnimeGANv2").strip() or "akhaliq/AnimeGANv2"
GRADIO_SPACE_API = os.getenv("GRADIO_SPACE_API", "/generate").strip() or "/generate"
GRADIO_SPACE_STYLE = os.getenv("GRADIO_SPACE_STYLE", "Version 2").strip() or "Version 2"
HF_TOKEN = os.getenv("HF_TOKEN", "").strip() or os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
GRADIO_SPACE_TIMEOUT_SECONDS = _env_int("GRADIO_SPACE_TIMEOUT_SECONDS", default=90, minimum=30, maximum=300)
GRADIO_SPACE_RETRIES = _env_int("GRADIO_SPACE_RETRIES", default=2, minimum=0, maximum=5)
GRADIO_SPACE_RETRY_DELAY_SECONDS = _env_float(
    "GRADIO_SPACE_RETRY_DELAY_SECONDS", default=2.0, minimum=0.5, maximum=20.0
)
GRADIO_SPACE_SSL_VERIFY = _env_bool("GRADIO_SPACE_SSL_VERIFY", default=True)
ENABLE_LOCAL_FALLBACK = _env_bool("ENABLE_LOCAL_FALLBACK", default=True)
FORCE_LOCAL_BACKEND = _env_bool("FORCE_LOCAL_BACKEND", default=False)
HIDE_REMOTE_ERROR_DETAILS = _env_bool("HIDE_REMOTE_ERROR_DETAILS", default=True)


def _short_error(error_text, max_len=380):
    if not error_text:
        return error_text
    normalized = " ".join(str(error_text).split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."


def _is_space_retryable_error(error_text):
    lowered = (error_text or "").lower()
    return any(
        marker in lowered
        for marker in (
            "handshake operation timed out",
            "read timed out",
            "connect timeout",
            "timed out",
            "ssl",
            "tls",
            "temporary failure in name resolution",
            "name or service not known",
            "connection reset",
            "connection refused",
            "network is unreachable",
        )
    )


def _is_space_quota_error(error_text):
    lowered = (error_text or "").lower()
    return any(
        marker in lowered
        for marker in (
            "exceeded your gpu quota",
            "exceeded your gpu quotas",
            "gpu quota",
            "quota exceeded",
            "too many requests",
            "rate limit",
        )
    )


def _extract_space_result_path(result):
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("path")
    if isinstance(result, (list, tuple)) and result:
        first = result[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("path")
    return None


def gradio_space_cartoonize(image_bytes):
    temp_input_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            temp_input_path = tmp_file.name

        max_attempts = GRADIO_SPACE_RETRIES + 1
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                client_kwargs = {
                    "ssl_verify": GRADIO_SPACE_SSL_VERIFY,
                    "httpx_kwargs": {"timeout": GRADIO_SPACE_TIMEOUT_SECONDS},
                }
                if HF_TOKEN:
                    client_kwargs["token"] = HF_TOKEN

                client = Client(GRADIO_SPACE_ID, **client_kwargs)
                result = client.predict(
                    img=handle_file(temp_input_path),
                    ver=GRADIO_SPACE_STYLE,
                    api_name=GRADIO_SPACE_API,
                )

                result_path = _extract_space_result_path(result)
                if not result_path or not os.path.exists(result_path):
                    raise ValueError(f"Unexpected Space response: {result}")

                with Image.open(result_path) as img:
                    output = io.BytesIO()
                    img.convert("RGB").save(output, format="JPEG", quality=95)
                    return output.getvalue()
            except Exception as exc:
                error_text = _short_error(str(exc))
                last_error = error_text
                if attempt < max_attempts and _is_space_retryable_error(error_text):
                    wait_seconds = min(15.0, GRADIO_SPACE_RETRY_DELAY_SECONDS * attempt)
                    print(
                        "Space network issue "
                        f"attempt {attempt}/{max_attempts}; retrying in {wait_seconds:.1f}s. "
                        f"Error: {error_text}"
                    )
                    time.sleep(wait_seconds)
                    continue
                raise RuntimeError(
                    f"Space {GRADIO_SPACE_ID} failed after {attempt}/{max_attempts} attempt(s): {last_error}"
                ) from exc
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)


def local_cartoonize(image_bytes):
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb = img.convert("RGB")
        smoothed = rgb.filter(ImageFilter.MedianFilter(size=3)).filter(ImageFilter.SMOOTH_MORE)
        poster = ImageOps.posterize(smoothed, bits=4)

        edges = rgb.convert("L").filter(ImageFilter.FIND_EDGES)
        edges = ImageOps.autocontrast(edges)
        edges = edges.point(lambda px: 0 if px > 70 else 255)
        edge_mask_rgb = edges.convert("RGB")

        cartoon = ImageChops.multiply(poster, edge_mask_rgb)

        output = io.BytesIO()
        cartoon.save(output, format="JPEG", quality=95)
        return output.getvalue()


def _fallback_warning(remote_error=None):
    if FORCE_LOCAL_BACKEND:
        return "Remote backend disabled by configuration. Used local fallback."
    if HIDE_REMOTE_ERROR_DETAILS:
        return "AnimeGANv2 remote unavailable. Used local fallback."
    if _is_space_quota_error(remote_error):
        return "AnimeGANv2 remote GPU quota exceeded. Used local fallback."
    return f"AnimeGANv2 remote failed. Used local fallback. Remote error: {remote_error}"


def _local_fallback_response(img_bytes, remote_error=None):
    fallback_bytes = local_cartoonize(img_bytes)
    encoded_image = base64.b64encode(fallback_bytes).decode("utf-8")
    warning = _fallback_warning(remote_error)
    if remote_error:
        print(f"{warning} Remote error: {remote_error}")
    else:
        print(warning)
    return jsonify(
        {
            "cartoon_image": encoded_image,
            "backend": "local_fallback",
            "model": "local_filter",
            "warning": warning,
        }
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/cartoonize", methods=["POST"])
def cartoonize():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    img_bytes = file.read()

    if FORCE_LOCAL_BACKEND:
        return _local_fallback_response(img_bytes)

    try:
        output_bytes = gradio_space_cartoonize(img_bytes)
        encoded_image = base64.b64encode(output_bytes).decode("utf-8")
        return jsonify(
            {
                "cartoon_image": encoded_image,
                "backend": "gradio_space",
                "model": GRADIO_SPACE_ID,
            }
        )
    except Exception as exc:
        remote_error = _short_error(str(exc))

        if ENABLE_LOCAL_FALLBACK:
            return _local_fallback_response(img_bytes, remote_error=remote_error)

        return (
            jsonify(
                {
                    "error": f"AnimeGANv2 inference failed: {remote_error}",
                    "backend": "gradio_space",
                    "model": GRADIO_SPACE_ID,
                }
            ),
            502,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
