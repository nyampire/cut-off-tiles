#!/usr/bin/env python3
"""
cut-off-tiles: XYZタイル形式の画像処理ユーティリティ
連続した白黒画素の検出と欠落タイル検出
"""
import time
import argparse
from pixel_detector import scan_directory
from missing_detector import detect_missing_tiles, generate_html_visualization

def main():
    parser = argparse.ArgumentParser(description='XYZタイル形式の画像処理ユーティリティ')
    parser.add_argument('directory', help='スキャンするディレクトリのパス')

    # モード選択
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--detect-pixels', action='store_true', help='連続した白/黒画素を検出するモード')
    group.add_argument('--detect-missing', action='store_true', help='欠落タイルを検出するモード')

    # 連続画素検出オプション
    parser.add_argument('--threshold', type=int, default=100, help='連続画素の検知閾値（デフォルト: 100）')
    parser.add_argument('--n', action='store_true', help='連続画素検出時に自動的に画像を削除するモード')
    parser.add_argument('--processes', type=int, default=None, help='並列処理に使用するプロセス数（デフォルト: CPUの論理コア数）')

    # 欠落タイル検出オプション
    parser.add_argument('--zoom', type=int, default=None, help='検査する特定のズームレベル（指定しない場合は全レベル）')
    parser.add_argument('--pattern', default=r'(\d+)/(\d+)/(\d+)\.png$',
                    help='タイル名のパターン（デフォルト: z/x/y.png形式）')
    parser.add_argument('--min-neighbors', type=int, default=6, help='欠落と判断するために必要な最低隣接タイル数（デフォルト: 6）')
    parser.add_argument('--padding', type=int, default=1, help='境界からのパディングサイズ（デフォルト: 1）')
    parser.add_argument('--html', default='missing_tiles_visualization.html', help='欠落タイル視覚化のHTML出力ファイル名（デフォルト: missing_tiles_visualization.html）')
    parser.add_argument('--no-html', action='store_true', help='HTMLの視覚化出力を無効にする')

    args = parser.parse_args()

    start_time = time.time()

    if args.detect_pixels:
        # 連続白黒画素の検出モード
        print("連続した白/黒画素の検出モードで実行しています...")
        result = scan_directory(args.directory, args.threshold, args.n, args.processes)

        detected_count = len(result["detected"])
        deleted_count = len(result["deleted"])

        print("\n======= 処理結果 =======")
        print(f"検出された画像: {detected_count}枚")
        print(f"削除された画像: {deleted_count}枚")
        print(f"保持された画像: {detected_count - deleted_count}枚")

    elif args.detect_missing:
        # 欠落タイル検出モード
        print("欠落タイル検出モードで実行しています...")

        # 既存タイルの収集と欠落タイル検出
        missing_tiles, existing_tiles = detect_missing_tiles(
            args.directory,
            args.zoom,
            args.pattern,
            args.min_neighbors,
            args.padding
        )

        # 結果の出力 - HTML視覚化のみ
        if missing_tiles:
            if not args.no_html:
                generate_html_visualization(missing_tiles, existing_tiles, args.html)

    end_time = time.time()
    print(f"処理時間: {end_time - start_time:.2f}秒")

if __name__ == "__main__":
    main()
