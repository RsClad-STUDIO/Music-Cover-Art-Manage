# Music Cover Art Manage

Windows向けの音楽ファイル・カバーアート管理ツールです。

音楽ファイルをスキャンし、カバーアートのJPEG変換やMP3ファイルへの再埋め込みを行えます。

GUI版とCLI版の2種類を提供しています。

[English README](README.md)

---

## Features

* 音楽ファイルのスキャン
* カバーアートのJPEG変換
* JPEG変換したカバーアートのMP3への再埋め込み
* GUIによる操作
* CLIによる操作
* FFmpegによる画像変換
* FFmpegをアプリケーションフォルダへ同梱
* `config.json` の自動生成
* `cache.db` の自動生成
* PyInstallerによる単体配布環境

---

## Download

最新版は [Releases](https://github.com/RsClad-STUDIO/Music-Cover-Art-Manage/releases/latest) からダウンロードできます。

配布版にはFFmpegが同梱されているため、別途FFmpegをインストールする必要はありません。

### GUI版

```text
Music Cover Art Manage/
├── Music Cover Art Manage.exe
├── ffmpeg/
│   └── ffmpeg.exe
└── _internal/
    └── ...
```

### CLI版

```text
Music Cover Art Manage CLI/
├── Music Cover Art Manage CLI.exe
├── ffmpeg/
│   └── ffmpeg.exe
└── _internal/
    └── ...
```

**`.exe` だけを単体で移動せず、フォルダ構成を維持したまま使用してください。**

---

## Requirements

配布版を使用する場合、以下の環境が必要です。

* Windows 10 / Windows 11
* 64-bit環境

PythonやFFmpegを別途インストールする必要はありません。

---

# GUI版

## Usage

`Music Cover Art Manage.exe` を起動してください。

### 1. スキャンパスを指定

音楽ファイルが保存されているフォルダを指定します。パスを直接入力するほか、**Browse...** ボタンからフォルダを選択できます。

例：

```text
C:\Music
```

ネットワークドライブなども使用できます。

例：

```text
Y:\Music
```

### パス入力時の注意

パスはダブルクォーテーションで囲まずに入力することを推奨します。互換性のため、GUI・CLIともに前後の引用符は自動的に除去します。

正しい例：

```text
C:\Music
```

非推奨の例（前後の引用符は自動的に除去されます）：

```text
"C:\Music"
```

---

### 2. スキャン

指定したフォルダをスキャンすると、対象となる音楽ファイルの情報がデータベースへ登録されます。

ファイル数が多い場合は、スキャンに時間がかかる場合があります。

---

### 3. JPEG変換

対象のカバーアートをJPEG形式へ変換できます。

変換処理には同梱されたFFmpegを使用します。

---

### 4. MP3への再埋め込み

JPEG変換したカバーアートをMP3ファイルへ再埋め込みできます。

音楽プレーヤーなどで表示されるカバーアートを更新する場合に使用できます。

音楽ファイルそのものを変更する処理のため、重要なファイルについては事前にバックアップを作成することを推奨します。

---

# CLI版

`Music Cover Art Manage CLI.exe` を起動すると、GUIを使用せずに処理を実行できます。

処理が完了すると、

```text
Finished.
```

と表示されます。

その後、

```text
Press Enter to exit...
```

と表示され、Enterキーを押すまでウィンドウを閉じずに待機します。

---

# Configuration

アプリケーションでは以下のファイルを使用します。

```text
config.json
cache.db
```

これらのファイルは配布時にあらかじめ用意する必要はありません。

初回起動時など、必要になった時点で自動的に生成されます。

そのため、配布フォルダにこれらのファイルが存在しなくても正常です。

### `config.json`

アプリケーションの設定を保存します。

### `cache.db`

スキャン結果などのキャッシュ情報を保存します。

これらを削除した場合でも、アプリケーションを再起動すると必要なファイルが自動的に再生成されます。

ただし、保存されていた設定やキャッシュ情報が失われる場合があります。

---

# FFmpeg

本アプリケーションではカバーアートの変換処理にFFmpegを使用しています。

配布版ではFFmpegを以下の場所に配置しています。

```text
ffmpeg/
└── ffmpeg.exe
```

アプリケーションは同梱されたFFmpegを自動的に検出して使用します。

そのため、ユーザー側でFFmpegをインストールしたり、環境変数 `PATH` を設定したりする必要はありません。

変換処理中にFFmpegのコンソールウィンドウが表示されないようになっています。

---

# Distribution Structure

配布版はPyInstallerの`onedir`形式で構成されています。

```text
Music Cover Art Manage/
├── Music Cover Art Manage.exe
├── ffmpeg/
│   └── ffmpeg.exe
└── _internal/
    └── ...
```

`_internal` フォルダにはアプリケーションの実行に必要なファイルが含まれています。

そのため、削除・移動・一部ファイルの変更は行わないでください。

---

# Development

## Build Environment

* Python 3.11.9
* PyInstaller 6.21.0
* PyInstaller `onedir`
* FFmpeg BtbN win64-lgpl

GUI版とCLI版それぞれにPyInstallerの`.spec`ファイルを使用しています。

```text
packaging/Music Cover Art Manage.spec
packaging/Music Cover Art Manage CLI.spec
```

---

## FFmpeg Distribution

FFmpegはアプリケーション本体へ直接埋め込まず、外部ファイルとして配布フォルダ内に同梱しています。

```text
ffmpeg/
└── ffmpeg.exe
```

これにより、アプリケーション本体とFFmpegを分離した構成になっています。

---

# Project Structure

```text
Music-Cover-Art-Manage/
├── src/music_cover_art_manage/  # GUI・CLI共通のアプリケーション本体
├── assets/                      # アイコン等の静的リソース
├── packaging/                   # PyInstallerビルド定義
├── tests/                       # 自動テスト
├── .github/workflows/           # GitHub Actions
├── main.py                      # CLI互換エントリーポイント
└── gui_main.py                  # GUI互換エントリーポイント
```

設定ファイル・キャッシュDBはアプリケーションの実行ディレクトリに生成されます。FFmpegは従来どおり配布フォルダ直下の `ffmpeg/ffmpeg.exe` を使用します。

---

# Notes

### 配布フォルダについて

`.exe` ファイルだけをコピーして実行することは想定していません。

以下の構成を維持してください。

```text
Music Cover Art Manage/
├── Music Cover Art Manage.exe
├── ffmpeg/
└── _internal/
```

### `config.json` / `cache.db` について

これらはGitHubリポジトリへ配布用データとして含める必要はありません。

ユーザーごとに異なる設定・キャッシュが保存されるため、アプリケーション起動時に自動生成されます。

---

# Tests

設定ファイル、スキャンキャッシュ、キャンセル処理、自動最適化、MP3カバーアートのメタデータ保持を検証する回帰テストを用意しています。

Windows / Python 3.11環境で以下を実行してください。

```powershell
python -m pip install mutagen==1.47.0 pytest==8.4.2
python -m compileall -q src tests main.py gui_main.py
python -m pytest -q
```

GitHub ActionsでもPull Requestごとに同じ検証を実行します。

---

# License

このプロジェクトのライセンスについては、リポジトリ内の`LICENSE`ファイルを参照してください。

本プロジェクトではFFmpegを使用しています。

FFmpegのライセンスおよび配布条件については、使用しているFFmpegビルドのライセンス情報を確認してください。

---

# Credits

* [FFmpeg](https://ffmpeg.org/)
  Used for image conversion and media processing.
* [PyInstaller](https://pyinstaller.org/)
  Used to package the Python application for Windows.
