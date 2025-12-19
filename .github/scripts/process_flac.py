import os
import json
from PIL import Image
from mutagen.flac import FLAC

BASE_DIR = "music"
LIST_FILE = os.path.join(BASE_DIR, "music_list.json")


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


def process_flac(flac_path: str):
    audio = FLAC(flac_path)

    title = audio.get("title", [os.path.splitext(os.path.basename(flac_path))[0]])[0]
    artist = audio.get("artist", ["Unknown Artist"])[0]
    album = audio.get("album", ["Unknown Album"])[0]

    folder_name = safe_name(f"{title}-{artist}")
    song_dir = os.path.join(BASE_DIR, folder_name)
    os.makedirs(song_dir, exist_ok=True)

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
        "music_path": flac_path.replace("\\", "/"),
        "lyrics_path": lyrics_path.replace("\\", "/"),
        "cover_path": cover_path.replace("\\", "/") if cover_path else "",
    }

    info_path = os.path.join(song_dir, "info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    return folder_name, info, info_path.replace("\\", "/")


def main():
    flac_map = {}
    music_list = []

    # 扫描 flac
    for root, _, files in os.walk(BASE_DIR):
        for f in files:
            if f.lower().endswith(".flac"):
                flac_path = os.path.join(root, f)
                folder, info, info_path = process_flac(flac_path)
                flac_map[folder] = flac_path

                music_list.append({
                    "title": info["title"],
                    "artist": info["artist"],
                    "path": info_path,
                })

    # 清理多余目录
    for name in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, name)
        if os.path.isdir(folder_path) and name not in flac_map:
            print(f"🗑️ 删除无效歌曲目录: {name}")
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for f in files:
                    os.remove(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            os.rmdir(folder_path)

    # 生成 music_list.json
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(music_list, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()