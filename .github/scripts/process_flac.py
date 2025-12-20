import os
import json
import shutil
from PIL import Image
from mutagen.flac import FLAC

# 路径配置
REPO_ROOT = os.getcwd()
FLAC_SCAN_DIR = os.path.join(REPO_ROOT, "music")
META_DIR = os.path.join(REPO_ROOT, "meta")
DUP_DIR = os.path.join(REPO_ROOT, "duplicates")
LIST_FILE = os.path.join(REPO_ROOT, "music_list.json")

os.makedirs(META_DIR, exist_ok=True)
os.makedirs(DUP_DIR, exist_ok=True)


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


# 处理单个 FLAC
def process_flac(flac_path: str):
    audio = FLAC(flac_path)

    title = audio.get("title", [os.path.splitext(os.path.basename(flac_path))[0]])[0]
    artist = audio.get("artist", ["Unknown Artist"])[0]
    album = audio.get("album", ["Unknown Album"])[0]

    folder_name = safe_name(f"{title}-{artist}")

    # 移动重复歌曲到 duplicates
    song_dir = os.path.join(META_DIR, folder_name)
    if os.path.exists(song_dir):
        os.makedirs(DUP_DIR, exist_ok=True)
        base_name = os.path.basename(flac_path)
        dup_path = os.path.join(DUP_DIR, base_name)
        count = 1
        name, ext = os.path.splitext(base_name)
        while os.path.exists(dup_path):
            dup_path = os.path.join(DUP_DIR, f"{name}_{count}{ext}")
            count += 1
        shutil.move(flac_path, dup_path)
        print(f"⚠️ 重复文件，已移动到 duplicates: {dup_path}")
        return None, None, None

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
        "music_path": os.path.relpath(flac_path, REPO_ROOT).replace("\\", "/"),
        "lyrics_path": os.path.relpath(lyrics_path, REPO_ROOT).replace("\\", "/"),
        "cover_path": os.path.relpath(cover_path, REPO_ROOT).replace("\\", "/") if cover_path else "",
    }

    info_path = os.path.join(song_dir, "info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    return folder_name, info, os.path.relpath(info_path, REPO_ROOT).replace("\\", "/")


# 主流程
def main():
    valid_meta = set()
    music_list = []

    # 扫描所有 flac
    for root, _, files in os.walk(FLAC_SCAN_DIR):
        for name in files:
            if not name.lower().endswith(".flac"):
                continue

            flac_path = os.path.join(root, name)
            print(f"🎵 处理 FLAC: {flac_path}")

            try:
                folder, info, info_path = process_flac(flac_path)
                if folder is None:
                    continue
                valid_meta.add(folder)

                music_list.append({
                    "title": info["title"],
                    "artist": info["artist"],
                    "path": info_path,
                })
            except Exception as e:
                print("❌ 处理失败:", e)

    # 清理无效 meta
    for name in os.listdir(META_DIR):
        path = os.path.join(META_DIR, name)
        if os.path.isdir(path) and name not in valid_meta:
            print(f"🗑️ 清理孤儿 meta: {name}")
            shutil.rmtree(path)

    # 重建 music_list.json
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(music_list, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成：共处理 {len(music_list)} 首歌")


if __name__ == "__main__":
    main()