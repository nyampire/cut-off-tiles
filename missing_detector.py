"""
XYZタイル形式で欠落しているタイルを検出するモジュール
"""
import os
import re
from collections import defaultdict

def detect_missing_tiles(directory_path, zoom_level=None, coordinate_pattern=r'(\d+)/(\d+)/(\d+)\.png$', min_neighbors=6, boundary_padding=1):
    """
    XYZタイル形式の画像で欠落しているタイルを検出する関数

    Parameters:
    - directory_path: XYZタイル画像が格納されているディレクトリパス
    - zoom_level: 特定のズームレベルのみ検査する場合に指定
    - coordinate_pattern: ファイル名からx, y, zを抽出する正規表現パターン（デフォルト: z/x/y.png形式）
    - min_neighbors: 欠落と判断するために必要な最低隣接タイル数（デフォルト: 6）
    - boundary_padding: 境界からのパディングサイズ（誤検知防止用）

    Returns:
    - 欠落タイルの一覧と既存タイルの辞書
    """
    # 存在するタイルの座標を保存
    existing_tiles = defaultdict(set)  # {z: set((x1, y1), (x2, y2), ...)}

    # 有効な座標範囲を追跡
    min_x = defaultdict(lambda: float('inf'))
    max_x = defaultdict(lambda: float('-inf'))
    min_y = defaultdict(lambda: float('inf'))
    max_y = defaultdict(lambda: float('-inf'))

    # ディレクトリ内のすべてのPNGファイルをスキャン
    pattern = re.compile(coordinate_pattern)

    print("既存のタイルを収集しています...")

    # すべてのPNGファイルをスキャン
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.png'):
                file_path = os.path.join(root, file)
                match = pattern.search(file_path)
                if match:
                    try:
                        # パターンによって、座標順序が異なる場合があります
                        z, x, y = map(int, match.groups())

                        # 特定のズームレベルが指定されている場合はフィルタリング
                        if zoom_level is not None and z != zoom_level:
                            continue

                        existing_tiles[z].add((x, y))

                        # 有効範囲を更新
                        min_x[z] = min(min_x[z], x)
                        max_x[z] = max(max_x[z], x)
                        min_y[z] = min(min_y[z], y)
                        max_y[z] = max(max_y[z], y)
                    except ValueError:
                        continue

    if not existing_tiles:
        print("\n有効なタイル画像が見つかりませんでした。パターンが正しいか確認してください。")
        print(f"現在のパターン: {coordinate_pattern}")
        return [], existing_tiles

    missing_tiles = []

    print("欠落タイルを検出しています...")
    # 各ズームレベルで欠落タイルを検出
    for z in existing_tiles:
        print(f"ズームレベル {z} を処理中...")
        print(f"  タイル数: {len(existing_tiles[z])}")

        # 境界から少し内側を検査範囲とする（端タイルの誤検知を防ぐため）
        x_range = range(min_x[z] + boundary_padding, max_x[z] - boundary_padding + 1)
        y_range = range(min_y[z] + boundary_padding, max_y[z] - boundary_padding + 1)

        total_checked = 0
        total_range = len(x_range) * len(y_range)

        for x in x_range:
            for y in y_range:
                total_checked += 1
                if (x, y) not in existing_tiles[z]:
                    # 周囲8方向（上下左右と斜め）のタイルをチェック
                    neighbors = [
                        (x-1, y), (x+1, y),  # 左右
                        (x, y-1), (x, y+1),  # 上下
                        (x-1, y-1), (x-1, y+1),  # 左上、左下
                        (x+1, y-1), (x+1, y+1)   # 右上、右下
                    ]

                    # 隣接するタイルが存在する数をカウント
                    existing_neighbors = sum(1 for nx, ny in neighbors if (nx, ny) in existing_tiles[z])

                    # 最低min_neighbors個の隣接タイルがある場合、このタイルは欠落している可能性が高い
                    if existing_neighbors >= min_neighbors:
                        tile_info = {
                            'z': z,
                            'x': x,
                            'y': y,
                            'neighbors': existing_neighbors,
                            'expected_filename': f"{z}/{x}/{y}.png"  # 予想されるファイル名
                        }
                        missing_tiles.append(tile_info)

                # 進捗表示（1000タイルごと）
                if total_checked % 1000 == 0 or total_checked == total_range:
                    print(f"  進捗: {total_checked}/{total_range} ({total_checked/total_range*100:.1f}%)")

    print(f"合計 {len(missing_tiles)} 個の欠落タイルを検出しました")
    return missing_tiles, existing_tiles

def generate_html_visualization(missing_tiles, existing_tiles, output_file='missing_tiles_visualization.html'):
    """欠落タイルの視覚化HTMLを生成する（テーブル形式のみ）"""
    if not missing_tiles:
        print("視覚化するための欠落タイルがありません")
        return False

    # ズームレベルごとに分類
    tiles_by_zoom = defaultdict(list)
    for tile in missing_tiles:
        tiles_by_zoom[tile['z']].append(tile)

    try:
        with open(output_file, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>欠落タイル視覚化</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #333;
        }
        .zoom-section {
            margin-bottom: 40px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }
        .summary {
            background-color: #f0f8ff;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .info {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .info-item {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            flex: 1;
            min-width: 200px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>欠落タイル視覚化</h1>

        <div class="summary">
            <h3>検出サマリー</h3>
            <p>合計 <strong>""" + str(len(missing_tiles)) + """</strong> 個の欠落タイルを検出しました。</p>
        </div>
    """)

            # 各ズームレベルのセクションを生成
            for z in sorted(tiles_by_zoom.keys()):
                f.write(f"""
        <div class="zoom-section" id="zoom-{z}">
            <h2>ズームレベル {z}</h2>
            <div class="info">
                <div class="info-item">
                    <p><strong>欠落タイル数:</strong> {len(tiles_by_zoom[z])}</p>
                </div>
            </div>

            <h3>欠落タイルリスト</h3>
            <table>
                <thead>
                    <tr>
                        <th>ズームレベル</th>
                        <th>X座標</th>
                        <th>Y座標</th>
                        <th>隣接タイル数</th>
                        <th>予想されるファイル名</th>
                    </tr>
                </thead>
                <tbody>
                """)

                # 現在のズームレベルの欠落タイルを表示
                for tile in tiles_by_zoom[z]:
                    f.write(f"""
                    <tr>
                        <td>{tile['z']}</td>
                        <td>{tile['x']}</td>
                        <td>{tile['y']}</td>
                        <td>{tile['neighbors']}</td>
                        <td>{tile['expected_filename']}</td>
                    </tr>
                    """)

                f.write("""
                </tbody>
            </table>
        </div>
                """)

            f.write("""
    </div>
</body>
</html>
            """)

        print(f"欠落タイルの視覚化を {output_file} に出力しました")
        return True
    except Exception as e:
        print(f"HTML生成エラー: {e}")
        return False
