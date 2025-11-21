from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import yt_dlp
import os
from pathlib import Path
import uuid
from typing import Any, Dict, List

app = FastAPI(title="YouTube Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_FOLDER = Path("downloads")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "YouTube Downloader API",
        "endpoints": {
            "POST /download": "Télécharger une vidéo",
            "GET /inspect": "Inspecter les métadonnées"
        }
    }

@app.post("/download")
async def download_video(url: str = Form(...)):
    if not url:
        raise HTTPException(status_code=400, detail="URL manquante")
    
    file_name = f"{uuid.uuid4()}.mp4"
    file_path = DOWNLOAD_FOLDER / file_name
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': str(file_path),
        'merge_output_format': 'mp4'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")
    
    return FileResponse(str(file_path), media_type='video/mp4', filename=file_name)

@app.get("/inspect")
async def inspect(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL manquante")
    
    ydl_opts: Dict[str, Any] = {'skip_download': True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")
    
    subtitles = info.get('subtitles') or {}
    auto_captions = info.get('automatic_captions') or {}
    manual_langs: List[str] = sorted(list(subtitles.keys()))
    auto_langs: List[str] = sorted(list(auto_captions.keys()))
    
    formats = info.get('formats') or []
    video_formats: List[Dict[str, Any]] = []
    audio_formats: List[Dict[str, Any]] = []
    
    for f in formats:
        vcodec = f.get('vcodec')
        acodec = f.get('acodec')
        if vcodec and vcodec != 'none':
            video_formats.append({
                'id': f.get('format_id'),
                'ext': f.get('ext'),
                'height': f.get('height'),
                'width': f.get('width'),
                'fps': f.get('fps'),
                'tbr': f.get('tbr'),
            })
        elif acodec and acodec != 'none':
            audio_formats.append({
                'id': f.get('format_id'),
                'ext': f.get('ext'),
                'abr': f.get('abr'),
                'tbr': f.get('tbr'),
            })
    
    return {
        'title': info.get('title'),
        'duration': info.get('duration'),
        'uploader': info.get('uploader'),
        'has_subtitles': len(manual_langs) > 0 or len(auto_langs) > 0,
        'manual_subtitle_languages': manual_langs,
        'auto_subtitle_languages': auto_langs,
        'video_formats': video_formats,
        'audio_formats': audio_formats,
        'language': info.get('language'),
    }