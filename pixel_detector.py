"""
連続した白色または黒色の画素を検出するモジュール
"""
import os
import numpy as np
import subprocess
import time
import multiprocessing
from functools import partial
from PIL import Image

def check_consecutive_pixels(image_path, threshold=100, colors=[(255, 255, 255), (0, 0, 0)]):
    """
    画像内に一定以上連続した白色または黒色の画素が含まれるかを検知する関数

    Parameters:
    - image_path: 画像ファイルのパス
    - threshold: 連続した同色画素の検知閾値
    - colors: 検知する色リスト。デフォルトは白[(255, 255, 255)]と黒[(0, 0, 0)]

    Returns:
    - 検知結果の辞書（検知された色と最大連続数）またはNone（エラー時）
    """
    try:
        # 画像を開く
        img = Image.open(image_path)
        # NumPy配列に変換
        img_array = np.array(img)

        # RGBのみを扱う場合（アルファチャンネルを除く）
        if img_array.ndim == 3 and img_array.shape[2] >= 3:
            img_array = img_array[:, :, :3]

        result = {}

        # 各色について連続検知
        for color in colors:
            color_array = np.array(color)
            max_consecutive = 0

            # 横方向の連続検知
            for row in img_array:
                consecutive_count = 0
                for pixel in row:
                    if np.array_equal(pixel, color_array):
                        consecutive_count += 1
                        max_consecutive = max(max_consecutive, consecutive_count)
                    else:
                        consecutive_count = 0

            # 縦方向の連続検知
            for col_idx in range(img_array.shape[1]):
                consecutive_count = 0
                for row_idx in range(img_array.shape[0]):
                    pixel = img_array[row_idx, col_idx]
                    if np.array_equal(pixel, color_array):
                        consecutive_count += 1
                        max_consecutive = max(max_consecutive, consecutive_count)
                    else:
                        consecutive_count = 0

            color_name = "white" if color == (255, 255, 255) else "black" if color == (0, 0, 0) else str(color)
            result[color_name] = max_consecutive

        return {
            "file": image_path,
            "result": result,
            "status": "success"
        }

    except Exception as e:
        return {
            "file": image_path,
            "error": str(e),
            "status": "error"
        }

def process_file(file_path, threshold=100):
    """ファイル1つを処理する関数（並列処理用）"""
    if file_path.lower().endswith('.png'):
        return check_consecutive_pixels(file_path, threshold)
    return None

def open_with_preview(file_path):
    """
    MacのPreviewで画像を開く関数

    Parameters:
    - file_path: 開く画像ファイルのパス
    """
    try:
        # 'open'コマンドでPreviewを使って画像を開く
        subprocess.run(['open', '-a', 'Preview', file_path])
        return True
    except Exception as e:
        print(f"Previewで画像を開けませんでした: {e}")
        return False

def delete_file(file_path):
    """
    ファイルを削除する関数

    Parameters:
    - file_path: 削除するファイルのパス
    """
    try:
        os.remove(file_path)
        print(f"削除しました: {file_path}")
        return True
    except Exception as e:
        print(f"ファイルを削除できませんでした: {e}")
        return False

def get_user_decision(file_path):
    """
    ユーザーに画像を保持するか削除するか問い合わせる関数

    Parameters:
    - file_path: 問い合わせる画像ファイルのパス

    Returns:
    - boolean: 削除する場合はTrue、保持する場合はFalse
    """
    while True:
        decision = input(f"\n画像 '{os.path.basename(file_path)}' を保持しますか？ (y=保持/n=削除/s=スキップ): ").lower()
        if decision in ['y', 'yes']:
            print(f"保持します: {file_path}")
            return False
        elif decision in ['n', 'no']:
            return True
        elif decision in ['s', 'skip']:
            print(f"スキップします: {file_path}")
            return False
        else:
            print("'y'（保持）、'n'（削除）、または's'（スキップ）を入力してください。")

def scan_directory(directory_path, threshold=100, auto_delete=False, num_processes=None):
    """
    ディレクトリ内のすべてのPNG画像を並列処理でスキャンし、閾値以上の連続画素を持つ画像を検出

    Parameters:
    - directory_path: スキャンするディレクトリのパス
    - threshold: 連続画素の閾値
    - auto_delete: 自動削除モードの有効/無効
    - num_processes: 並列処理に使用するプロセス数（None=CPU数）

    Returns:
    - 処理結果のサマリー（検出数、削除数など）
    """
    # すべてのPNGファイルのパスを収集
    all_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.png'):
                all_files.append(os.path.join(root, file))

    total_files = len(all_files)
    print(f"合計 {total_files} 個のPNGファイルをスキャンします...")

    # デフォルト値がNoneの場合、使用可能なCPU数を使用
    if num_processes is None:
        num_processes = multiprocessing.cpu_count()

    print(f"{num_processes} プロセスで並列処理を実行します")

    # プロセスプールを作成
    with multiprocessing.Pool(processes=num_processes) as pool:
        # 部分関数を作成して引数を固定
        process_func = partial(process_file, threshold=threshold)

        # 進捗表示のための変数
        completed = 0

        # 並列処理結果を収集
        results = []
        for result in pool.imap_unordered(process_func, all_files):
            completed += 1
            if completed % 100 == 0 or completed == total_files:
                print(f"進捗: {completed}/{total_files} ファイル処理完了 ({completed/total_files*100:.1f}%)")

            if result and result.get("status") == "success":
                detection_result = result.get("result", {})
                file_path = result.get("file")

                # 検出条件をチェック
                if (detection_result.get("white", 0) >= threshold or
                    detection_result.get("black", 0) >= threshold):
                    results.append(result)

    # 検出された画像に対するユーザー判断処理
    detected_images = []
    deleted_images = []

    for result in results:
        file_path = result.get("file")
        detection_result = result.get("result", {})

        detected_images.append({
            "file": file_path,
            "result": detection_result
        })

        print(f"\n検知: {file_path}")
        print(f"  - 白色の最大連続数: {detection_result.get('white', 0)}")
        print(f"  - 黒色の最大連続数: {detection_result.get('black', 0)}")

        if auto_delete:
            # 自動削除モードの場合
            print(f"自動削除モード: 画像を削除します")
            if delete_file(file_path):
                deleted_images.append(file_path)
        else:
            # プレビューで画像を開く
            if open_with_preview(file_path):
                # ユーザーに確認
                time.sleep(0.5)  # プレビューが開くまで少し待つ
                if get_user_decision(file_path):
                    if delete_file(file_path):
                        deleted_images.append(file_path)

    return {
        "detected": detected_images,
        "deleted": deleted_images
    }
