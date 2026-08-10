# -*- coding: utf-8 -*-
"""
Sube el ultimo video generado a una carpeta de Google Drive, para que
Repurpose lo detecte y lo publique en TikTok + Instagram.
Reutiliza el mismo cliente OAuth que YouTube (YT_CLIENT_ID / YT_CLIENT_SECRET),
pero con un token propio de Drive (GDRIVE_REFRESH_TOKEN) y una carpeta destino
(GDRIVE_FOLDER_ID). Si falta cualquiera de estos, no hace nada (no rompe el flujo).
"""
import os, sys

def main():
    need = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN", "GDRIVE_FOLDER_ID")
    if any(not os.environ.get(k) for k in need):
        print("[drive] faltan datos de Drive (token o carpeta); me salto la subida a Drive.")
        return

    BASE = os.path.dirname(os.path.abspath(__file__))
    OUTPUT = os.path.join(BASE, "output")
    latest = os.path.join(OUTPUT, "_latest.txt")
    if not os.path.exists(latest):
        print("[drive] no hay output/_latest.txt; nada que subir.")
        return
    vid_id = open(latest, encoding="utf-8").read().strip()
    path = os.path.join(OUTPUT, f"{vid_id}.mp4")
    if not os.path.exists(path):
        print(f"[drive] no existe {path}; nada que subir.")
        return

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=os.environ["GDRIVE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    drv = build("drive", "v3", credentials=creds)
    meta = {"name": f"{vid_id}.mp4", "parents": [os.environ["GDRIVE_FOLDER_ID"]]}
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True)
    f = drv.files().create(body=meta, media_body=media,
                           supportsAllDrives=True, fields="id").execute()
    print(f"[drive] subido a Drive OK (id={f.get('id')})")

if __name__ == "__main__":
    main()
