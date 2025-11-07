import os
import shutil

# 获取脚本所在目录
base_dir = os.path.dirname(os.path.abspath(__file__))

# 遍历当前目录下的所有文件夹
for folder_name in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder_name)
    if os.path.isdir(folder_path):
        # 构建文件路径：文件夹名.flac
        flac_file = os.path.join(folder_path, f"{folder_name}.flac")
        if os.path.isfile(flac_file):
            # 复制文件到脚本所在目录
            shutil.copy2(flac_file, base_dir)
            print(f"已复制: {flac_file} -> {base_dir}")
            # 删除原文件夹
            shutil.rmtree(folder_path)
            print(f"已删除文件夹: {folder_path}")
        else:
            print(f"未找到 {folder_name}.flac，跳过 {folder_path}")
