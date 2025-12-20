import os
import json
import shutil
from PIL import Image
from mutagen.flac import FLAC

# 路径配置
REPO_ROOT = os.getcwd()
ROOT_FLAC_DIR = REPO_ROOT
MUSIC_DIR = os.path.join(REPO_ROOT, "music")
META_DIR = os.path.join(REPO_ROOT, "meta")
DUP_DIR = os.path.join(REPO_ROOT, "duplicates")
LIST_FILE = os.path.join(REPO_ROOT, "music_list.json")

os.makedirs(MUSIC_DIR, exist_ok=True)
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


def load_music_list():
    if not os.path.exists(LIST_FILE):
        return []
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_music_list(data):
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 生成 meta
def generate_meta(audio: FLAC, key: str, flac_path: str):
    song_dir = os.path.join(META_DIR, key)
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

    info = {
        "title": audio.get("title", [""])[0],
        "artist": audio.get("artist", ["Unknown Artist"])[0],
        "album": audio.get("album", ["Unknown Album"])[0],
        "music_path": os.path.relpath(flac_path, REPO_ROOT).replace("\\", "/"),
        "lyrics_path": os.path.relpath(lyrics_path, REPO_ROOT).replace("\\", "/"),
        "cover_path": os.path.relpath(cover_path, REPO_ROOT).replace("\\", "/") if cover_path else "",
    }

    with open(os.path.join(song_dir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    return info


def main():
    music_list = load_music_list()

    # 扫描 flac
    root_flacs = [
        f for f in os.listdir(ROOT_FLAC_DIR)
        if f.lower().endswith(".flac") and os.path.isfile(os.path.join(ROOT_FLAC_DIR, f))
    ]

    for flac_file in root_flacs:
        flac_path = os.path.join(ROOT_FLAC_DIR, flac_file)
        print(f"🎵 处理新上传 FLAC: {flac_file}")

        try:
            audio = FLAC(flac_path)
            title = audio.get("title", [os.path.splitext(flac_file)[0]])[0]
            artist = audio.get("artist", ["Unknown Artist"])[0]

            key = safe_name(f"{title}-{artist}")
            target_flac = os.path.join(MUSIC_DIR, f"{key}.flac")

            if os.path.exists(target_flac):
                shutil.move(flac_path, os.path.join(DUP_DIR, flac_file))
                print(f"⚠️ 重复歌曲，移至 duplicates: {flac_file}")
                continue

            shutil.move(flac_path, target_flac)
            print(f"✅ 新歌归档: {target_flac}")

            info = generate_meta(audio, key, target_flac)

            music_list.append({
                "title": info["title"],
                "artist": info["artist"],
                "path": os.path.join("meta", key, "info.json").replace("\\", "/")
            })

        except Exception as e:
            print("❌ 处理失败:", e)

    # 索引与 music 同步
    music_keys = {
        os.path.splitext(f)[0]
        for f in os.listdir(MUSIC_DIR)
        if f.lower().endswith(".flac")
    }

    new_list = []
    for item in music_list:
        key = safe_name(f'{item["title"]}-{item["artist"]}')
        if key in music_keys:
            new_list.append(item)
        else:
            print(f"🗑️ 歌曲已删除，清理 meta: {key}")
            shutil.rmtree(os.path.join(META_DIR, key), ignore_errors=True)

    save_music_list(new_list)
    print(f"\n✅ 完成：当前共 {len(new_list)} 首歌")


if __name__ == "__main__":
    main()