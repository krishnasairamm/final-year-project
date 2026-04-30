# Cartoon GAN Framework (AnimeGANv2 Only)

This project is a single-model cartoonizer using:
- `akhaliq/AnimeGANv2` (Gradio Space)

No Hugging Face model routing or API key input is used.

## End-to-End Processing Flow

### 1. Image Input (Frontend)
- You upload an image in the browser UI.
- Frontend script (`static/js/main.js`) stores the file and sends it to:
  - `POST /cartoonize`

### 2. Request Handling (Backend)
- Flask route in `app.py` receives multipart form-data.
- It validates that `image` exists in request files.
- Raw bytes are read from the uploaded file.

### 3. Model Inference Call (AnimeGANv2)
- Backend function `gradio_space_cartoonize(image_bytes)` runs.
- It writes uploaded bytes to a temporary `.jpg` file.
- It calls Gradio Space client:
  - Space: `akhaliq/AnimeGANv2`
  - API: `/generate`
  - Style: `Version 2`
- If network issues happen, it retries using configured retry settings.

### 4. Getting Model Output
- Space returns a generated image path.
- Backend opens that generated image with Pillow.
- Image is converted to RGB and saved in-memory as JPEG bytes.

### 5. Response Construction
- Backend base64-encodes the JPEG bytes.
- JSON response is returned to frontend with:
  - `cartoon_image` (base64)
  - `backend` (`gradio_space`)
  - `model` (`akhaliq/AnimeGANv2`)

### 6. Display in Browser
- Frontend receives JSON.
- It builds `data:image/jpeg;base64,...` URL.
- Cartoon preview is rendered in the result panel.
- Download button is enabled to save output image.

## How the Cartoon is Generated
- Main generation is done by `akhaliq/AnimeGANv2` remotely.
- Your uploaded image is transformed by the AnimeGANv2 model into a cartoon-style image.
- The app itself does not run deep model weights locally for the main path.

## How Model Works on Your Input
Given one uploaded photo, AnimeGANv2 works like this at a high level:
1. Input image is encoded into internal feature maps (content + texture + edges).
2. Model keeps major structure (face/object shape and layout) from the input.
3. Fine photo textures are suppressed to reduce realism/noise.
4. Edges/contours are emphasized to create illustration-like outlines.
5. Colors are smoothed and flattened into cartoon-style regions.
6. Final stylized image is decoded and returned as output.

In short: it preserves scene composition, but shifts textures, edges, and colors toward an anime/cartoon look.

## Fallback Behavior
If AnimeGANv2 request fails and `ENABLE_LOCAL_FALLBACK=true`:
- Backend uses `local_cartoonize(image_bytes)`.
- Fallback effect uses Pillow operations:
  - smoothing + posterization
  - edge detection mask
  - multiply blend for cartoon-like outlines
- Result is still returned as base64 image so UI works.

## Run
```bash
conda activate cartoon_gan
python setup.py
python run.py
```

Open:
- `http://localhost:5000`

## .env Settings
- `GRADIO_SPACE_ID=akhaliq/AnimeGANv2`
- `GRADIO_SPACE_API=/generate`
- `GRADIO_SPACE_STYLE=Version 2`
- `GRADIO_SPACE_TIMEOUT_SECONDS=90`
- `GRADIO_SPACE_RETRIES=2`
- `GRADIO_SPACE_RETRY_DELAY_SECONDS=2`
- `GRADIO_SPACE_SSL_VERIFY=true`
- `ENABLE_LOCAL_FALLBACK=true`

## Notes
- If you want only exact AnimeGANv2 output, set `ENABLE_LOCAL_FALLBACK=false`.
- If Space is down or rate-limited, fallback keeps the app usable.
