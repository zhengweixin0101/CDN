import os
import json
import shutil
from mutagen.flac import FLAC

MUSIC_DIR = "music"
LIST_FILE = os.path.join(MUSIC_DIR, "music_list.json")

def extract_flac_info(file_path):
    audio = FLAC(file_path)
    title = audio.get('title', [os.path.basename(file_path).replace('.flac', '')])[0]
    artist = audio.get('artist', ['Unknown Artist'])[0]
    album = audio.get('album', ['Unknown Album'])[0]

    folder_name = f"{title}-{artist}".replace("/", "_")
    folder_path = os.path.join(MUSIC_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    new_flac_path = os.path.join(folder_path, f"{title}.flac")
    shutil.copy2(file_path, new_flac_path)

    cover_path = os.path.join(folder_path, "cover.jpg")
    for pic in audio.pictures:
        if pic.type == 3:
            with open(cover_path, "wb") as f:
                f.write(pic.data)
            break
    else:
        with open(cover_path, "wb") as f:
            pass

    lyrics_path = os.path.join(folder_path, "lyrics.lrc")
    if "lyrics" in audio:
        lyrics = audio["lyrics"][0]
    else:
        lyrics = ""
    with open(lyrics_path, "w", encoding="utf-8") as f:
        f.write(lyrics)

    info = {
        "title": title,
        "artist": artist,
        "album": album,
        "music_path": new_flac_path.replace("\\", "/"),
        "lyrics_path": lyrics_path.replace("\\", "/"),
        "cover_path": cover_path.replace("\\", "/"),
    }

    info_path = os.path.join(folder_path, "info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"✅ Processed: {title} - {artist}")

    return {
        "title": title,
        "artist": artist,
        "path": new_flac_path.replace("\\", "/")
    }

def update_music_list(new_entry):
    if not os.path.exists(LIST_FILE):
        music_list = []
    else:
        with open(LIST_FILE, "r", encoding="utf-8") as f:
            try:
                music_list = json.load(f)
            except json.JSONDecodeError:
                music_list = []

    for item in music_list:
        if item["path"] == new_entry["path"]:
            return

    music_list.append(new_entry)

    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(music_list, f, ensure_ascii=False, indent=2)

def main():
    flac_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".flac")]
    if not flac_files:
        print("No FLAC files found.")
        return

    for filename in flac_files:
        file_path = os.path.join(MUSIC_DIR, filename)
        new_entry = extract_flac_info(file_path)
        update_music_list(new_entry)

if __name__ == "__main__":
    main()