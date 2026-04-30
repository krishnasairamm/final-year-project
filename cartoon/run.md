# Quick Run Guide

## 1. Activate Environment
```bash
conda activate cartoon_gan
```

## 2. Install Dependencies
```bash
python setup.py
```

## 3. Start App
```bash
python run.py
```

## 4. Open UI
- `http://localhost:5000`

## Current Backend
- Single model only: `akhaliq/AnimeGANv2`
- API key is optional (`HF_TOKEN`) for authenticated remote access.

## Quota Error Fix (This Machine)
- `.env` is set to `FORCE_LOCAL_BACKEND=true` to avoid HuggingFace Space GPU quota errors.
- If you want to try remote AnimeGANv2 again later, set:
```bash
FORCE_LOCAL_BACKEND=false
```

## Use Hugging Face API Key
- Add your token in `.env`:
```bash
HF_TOKEN=hf_xxx_your_token_here
FORCE_LOCAL_BACKEND=false
```
- Keep `ENABLE_LOCAL_FALLBACK=true` so local processing is used if remote fails.
