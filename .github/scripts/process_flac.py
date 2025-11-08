import os
import json
import shutil
from mutagen.flac import FLAC
from PIL import Image
import io

MUSIC_DIR = "."
LIST_FILE = os.path.join(MUSIC_DIR, "music_list.json")

def compress_to_webp(image_path, quality=80):
    """智能压缩图片为WebP格式"""
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            webp_path = os.path.splitext(image_path)[0] + '.webp'
            img.save(webp_path, 'WEBP', quality=quality, optimize=True)

            original_size = os.path.getsize(image_path)
            webp_size = os.path.getsize(webp_path)
            compression_ratio = (1 - webp_size / original_size) * 100
            
            # 如果WebP文件比原始文件大，删除WebP文件并返回原始路径
            if webp_size > original_size:
                os.remove(webp_path)
                print(f"⚠️  压缩效果不佳，保留原文件: {os.path.basename(image_path)}")
                print(f"   原始大小: {original_size / 1024:.1f}KB, WebP大小: {webp_size / 1024:.1f}KB")
                return image_path
            
            print(f"📊 压缩完成: {os.path.basename(image_path)} -> {os.path.basename(webp_path)}")
            print(f"   原始大小: {original_size / 1024:.1f}KB, WebP大小: {webp_size / 1024:.1f}KB, 压缩率: {compression_ratio:.1f}%")
            
            # 删除原始文件（压缩成功）
            os.remove(image_path)
            return webp_path
    except Exception as e:
        print(f"❌ 压缩失败 {image_path}: {e}")
        return None

def extract_flac_info(file_path):
    audio = FLAC(file_path)
    title = audio.get('title', [os.path.splitext(os.path.basename(file_path))[0]])[0]
    artist = audio.get('artist', ['Unknown Artist'])[0]
    album = audio.get('album', ['Unknown Album'])[0]

    folder_name = f"{title}-{artist}".replace("/", "_")
    folder_path = os.path.join(MUSIC_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    new_flac_path = os.path.join(folder_path, f"{title}-{artist}.flac")
    shutil.move(file_path, new_flac_path)

    cover_path = os.path.join(folder_path, "cover.jpg")
    for pic in audio.pictures:
        if pic.type == 3:
            with open(cover_path, "wb") as f:
                f.write(pic.data)

            webp_path = compress_to_webp(cover_path)
            if webp_path:
                cover_path = webp_path
            break
    else:
        open(cover_path, "wb").close()

    lyrics_path = os.path.join(folder_path, "lyrics.lrc")
    lyrics = audio.get("lyrics", [""])[0]
    with open(lyrics_path, "w", encoding="utf-8") as f:
        f.write(lyrics)

    info = {
        "title": title,
        "artist": artist,
        "album": album,
        "music_path": new_flac_path.replace("\\", "/"),
        "lyrics_path": lyrics_path.replace("\\", "/"),
        "cover_path": cover_path.replace("\\", "/")
    }
    info_path = os.path.join(folder_path, "info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"✅ Processed: {title} - {artist}")
    info_path = os.path.join(folder_path, "info.json")
    return {"title": title, "artist": artist, "path": info_path.replace("\\", "/")}

def load_music_list():
    if os.path.exists(LIST_FILE):
        try:
            with open(LIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_music_list(music_list):
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(music_list, f, ensure_ascii=False, indent=2)

def sync_music_list_and_dirs(music_list):
    dirs = [d for d in os.listdir(MUSIC_DIR) if os.path.isdir(os.path.join(MUSIC_DIR, d))]

    updated_list = []
    for item in music_list:
        folder_name = f"{item['title']}-{item['artist']}".replace("/", "_")
        folder_path = os.path.join(MUSIC_DIR, folder_name)
        if os.path.exists(folder_path):
            updated_list.append(item)
        else:
            print(f"🗑 Remove missing folder from music_list.json: {folder_name}")
    music_list = updated_list

    current_paths = [f"{item['title']}-{item['artist']}".replace("/", "_") for item in music_list]
    for folder in dirs:
        if folder not in current_paths:
            folder_path = os.path.join(MUSIC_DIR, folder)
            shutil.rmtree(folder_path)
            print(f"🗑 Deleted folder from repo: {folder}")

    return music_list

def main():
    flac_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".flac")]
    music_list = load_music_list()

    for f in flac_files:
        file_path = os.path.join(MUSIC_DIR, f)
        new_entry = extract_flac_info(file_path)
        if not any(item['path'] == new_entry['path'] for item in music_list):
            music_list.append(new_entry)

    music_list = sync_music_list_and_dirs(music_list)

    save_music_list(music_list)

if __name__ == "__main__":
    main()