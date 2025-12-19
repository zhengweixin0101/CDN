import os
import json
import shutil
import requests
from PIL import Image
from mutagen.flac import FLAC
from urllib.parse import quote

BASE_DIR = "music"
LIST_FILE = os.path.join(BASE_DIR, "music_list.json")

WEBDAV_URL = os.environ.get("WEBDAV_URL").rstrip("/")
WEBDAV_UPLOAD_PATH = os.environ.get("WEBDAV_UPLOAD_PATH", "music").strip("/")
WEBDAV_USER = os.environ.get("WEBDAV_USER")
WEBDAV_PASS = os.environ.get("WEBDAV_PASS")

def safe_name(s: str) -> str:
    return s.replace("/", "_").replace("\\", "_").strip()


# 封面压缩
def compress_to_webp(image_path, quality=80):
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            webp_path = os.path.splitext(image_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=quality, optimize=True)

        if os.path.getsize(webp_path) >= os.path.getsize(image_path):
            os.remove(webp_path)
            return image_path

        os.remove(image_path)
        return webp_path
    except Exception as e:
        print("❌ 封面压缩失败:", e)
        return image_path


# WebDAV
def upload(local_flac: str, remote_base: str):
    filename = os.path.basename(local_flac)
    remote_path = f"{remote_base}/{filename}".strip("/")
    url = f"{WEBDAV_URL}/{quote(remote_path)}"

    print(f"🔗 上传 URL: {url}")

    with open(local_flac, "rb") as f:
        r = requests.put(url, data=f, auth=(WEBDAV_USER, WEBDAV_PASS))
        if r.status_code in (200, 201, 204):
            print("✅ 上传成功")
            return True
        else:
            print(f"❌ 上传失败: {r.status_code}")
            return False


# 处理单个 flac
def process_flac(flac_path):
    audio = FLAC(flac_path)

    title = audio.get("title", [os.path.splitext(os.path.basename(flac_path))[0]])[0]
    artist = audio.get("artist", ["Unknown Artist"])[0]
    album = audio.get("album", ["Unknown Album"])[0]

    folder_name = safe_name(f"{title}-{artist}")
    renamed_flac = os.path.join(BASE_DIR, f"{folder_name}.flac")

    # 重命名
    if flac_path != renamed_flac:
        os.rename(flac_path, renamed_flac)
        print(f"✏️ 重命名: {os.path.basename(flac_path)} → {folder_name}.flac")

    song_dir = os.path.join(BASE_DIR, folder_name)
    os.makedirs(song_dir, exist_ok=True)

    # 复制 flac
    flac_dst = os.path.join(song_dir, f"{folder_name}.flac")
    if not os.path.exists(flac_dst):
        shutil.copy2(renamed_flac, flac_dst)

    # 封面
    cover_path = ""
    for pic in audio.pictures:
        if pic.type == 3:
            jpg = os.path.join(song_dir, "cover.jpg")
            with open(jpg, "wb") as f:
                f.write(pic.data)
            cover_path = compress_to_webp(jpg)
            break

    # 歌词
    lyrics_path = os.path.join(song_dir, "lyrics.lrc")
    with open(lyrics_path, "w", encoding="utf-8") as f:
        f.write(audio.get("lyrics", [""])[0])

    # info.json
    info = {
        "title": title,
        "artist": artist,
        "album": album,
        "music_path": flac_dst.replace("\\", "/"),
        "lyrics_path": lyrics_path.replace("\\", "/"),
        "cover_path": cover_path.replace("\\", "/") if cover_path else "",
    }

    info_path = os.path.join(song_dir, "info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    return {
        "folder": song_dir,
        "folder_name": folder_name,
        "renamed_flac": renamed_flac,
        "info": info,
        "info_path": info_path.replace("\\", "/"),
    }


# music_list
def load_music_list():
    if not os.path.exists(LIST_FILE):
        return []
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_music_list(data):
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 主流程
def main():
    music_list = load_music_list()

    flacs = [
        f for f in os.listdir(BASE_DIR)
        if f.lower().endswith(".flac")
    ]

    for flac in flacs:
        src = os.path.join(BASE_DIR, flac)
        print(f"🎵 发现 FLAC: {flac}")

        try:
            result = process_flac(src)

            # 上传WebDAV并删除
            if upload(
                result["renamed_flac"],
                WEBDAV_UPLOAD_PATH,
            ):
                os.remove(result["renamed_flac"])
                print("✅ WebDAV 上传成功，已删除本地 FLAC")

            # 写入 music_list
            if not any(
                item["path"] == result["info_path"]
                for item in music_list
            ):
                music_list.append({
                    "title": result["info"]["title"],
                    "artist": result["info"]["artist"],
                    "path": result["info_path"],
                })

        except Exception as e:
            print("❌ 上传webdav失败:", e)

    save_music_list(music_list)


if __name__ == "__main__":
    main()