# proto2ue

`proto2ue` は Protocol Buffers (proto2) のスキーマから Unreal Engine 向けの C++ コードと変換ヘルパーを生成する `protoc` プラグイン／ライブラリです。FileDescriptorSet から独自の中間表現を構築し、UE の命名規約や `UPROPERTY` メタデータに合わせた `USTRUCT` / `UENUM` を出力します。Blueprint 互換の Optional ラッパー、`TArray` / `TMap` を用いたコンテナ展開、`oneof` のメタデータ保持に対応しており、生成コードと protobuf メッセージ間を相互変換する C++ コンバーターと Blueprint 用関数ライブラリも生成できます。

> **Current status**: `DescriptorLoader`・`TypeMapper`・テンプレートレンダラー (`proto2ue.codegen`)・コンバーター生成 (`proto2ue.codegen.converters`) を実装済みです。`pytest` による回帰テストと Python 実装のラウンドトリップ検証で、`optional` / `repeated` / `map` / `oneof` / ネスト型 / カスタム Unreal オプションをカバーしています。Unreal Build Tool との自動統合や公式配布パッケージはこれからです。

---

## 目次

- [主な特徴](#主な特徴)
- [リポジトリ構成](#リポジトリ構成)
- [セットアップ](#セットアップ)
- [クイックスタート](#クイックスタート)
- [ドキュメント](#ドキュメント)
- [テスト](#テスト)
- [制限事項と今後の予定](#制限事項と今後の予定)
- [ライセンス](#ライセンス)

## 主な特徴

- **Descriptor 正規化**: `DescriptorLoader` が `CodeGeneratorRequest` から依存関係を検証しつつ `proto2ue.model` のデータクラスへ変換します。`map_entry` や `oneof` のリンク、カスタムオプション (`unreal.*`) を取り込みます。
- **UE 型マッピング**: `TypeMapper` がメッセージ／列挙を UE 命名規約 (`F`/`E` プレフィックス) に沿って命名し、`optional` を Blueprint 対応のラッパー構造体として合成、`repeated`→`TArray`、`map`→`TMap` に展開します。`UPROPERTY` のメタデータや `BlueprintReadWrite`/`BlueprintReadOnly` も反映します。
- **コード生成**: `DefaultTemplateRenderer` が proto ごとに `.proto2ue.h` / `.proto2ue.cpp` を生成し、名前空間ラッパー (`UE_NAMESPACE_BEGIN/END`) や `RegisterGeneratedTypes` スタブを出力します。
- **変換ヘルパー**: `ConvertersTemplate` が UE 構造体と protobuf メッセージ間の双方向変換関数、エラー収集用コンテキスト、Blueprint 向けのシリアライズ関数 (`UProto2UEBlueprintLibrary`) を生成します。Python 実装の `PythonConvertersRuntime` でテンプレート出力の挙動をテストできます。

## リポジトリ構成

```
src/proto2ue/        ─ コア実装 (descriptor_loader, type_mapper, codegen など)
tests/               ─ pytest ベースのユニットテストと golden ファイル
docs/                ─ 利用ガイド・調査資料
plan/                ─ フェーズ別の開発プラン
```

## セットアップ

Python 3.11 以上と `protobuf` が必要です。開発環境では追加で `pytest` を使用します。

> 以降のコマンド例は特記がない限り、リポジトリのルート ディレクトリ (`proto2ue`) をカレントディレクトリにして PowerShell から実行します。

```powershell
# カレントディレクトリ: リポジトリルート (proto2ue)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install protobuf pytest
```

## クイックスタート

1. **ユニットテストの実行** — 依存関係が揃っていることを `pytest` で確認します。

   ```powershell
   # カレントディレクトリ: リポジトリルート (proto2ue)
   pytest
   ```

2. **`proto2ue` を Python から参照可能にする** — `protoc` がローカルコピーの `proto2ue` を読み込めるようにします。開発環境であれば editable インストールするか、`PYTHONPATH` に `src/` を追加してください。

   ```powershell
   # カレントディレクトリ: リポジトリルート (proto2ue)
   pip install -e .
   # もしくは:
   $env:PYTHONPATH = "${PWD}\src;${env:PYTHONPATH}"
   ```

3. **`protoc` プラグインの登録** — `proto2ue.plugin` を実行するラッパースクリプトを `protoc-gen-ue` という名前で仮想環境内 (`.venv\Scripts`) に作成します。`protoc` は Windows では `.cmd` や `.bat` 拡張子のラッパーを自動解決できるため、以下の例では `protoc-gen-ue.cmd` を生成します。

   ```powershell
   # カレントディレクトリ: リポジトリルート (proto2ue)
   $pluginScript = Join-Path (Resolve-Path ".\.venv\Scripts") "protoc-gen-ue.cmd"
   Set-Content -Path $pluginScript -Encoding ascii -Value @'
@echo off
python -m proto2ue.plugin %*
'@
   ```

   仮想環境をアクティブにすると `.venv\Scripts` が `PATH` に加わるため、`--plugin="protoc-gen-ue=.\.venv\Scripts\protoc-gen-ue.cmd"` のように明示的なパスを渡すだけで仮想環境の Python を用いたプラグインが呼び出せます。簡素化したラッパーと明示的なプラグイン指定は Windows (PowerShell) で動作検証済みです。グローバル Python を使用する場合は、スクリプトを任意のディレクトリに配置し、`PATH` を調整してください。

4. **コード生成** — サンプル proto (`example\person.proto`) を UE 向けに変換します。生成結果は `.proto2ue.h/.cpp` とコンバーター (`_proto2ue_converters.h/.cpp`) です。`--ue_out=<options>:<out_dir>` 形式で出力ディレクトリと生成時オプションを指定できます。

    ```powershell
    # カレントディレクトリ: リポジトリ内の src
    protoc `
      --plugin="protoc-gen-ue=..\.venv\Scripts\protoc-gen-ue.cmd" `
      --proto_path=. `
      --ue_out=convert_unsigned_for_blueprint=true:..\out `
      example\person.proto
    ```

    生成されたヘッダーは `FProtoOptional*` ラッパーや `UE_NAMESPACE_BEGIN/END` ブロックを含みます。上記コマンドは Windows 上でラッパーを `.venv\Scripts` に配置して実行した検証済みの手順です。`ConvertersTemplate` を利用する場合は、`proto2ue.codegen.converters` を Python から呼び出すか、`python -m proto2ue.tools.converter` で `_proto2ue_converters.{h,cpp}` を追生成してください。

## 使用方法

上記のコマンド例で用いた `protoc` 呼び出しを、各パラメーターに分解して確認します。

```powershell
# カレントディレクトリ: リポジトリ内の src
protoc `
  --plugin="protoc-gen-ue=..\.venv\Scripts\protoc-gen-ue.cmd" `   # (1)
  --proto_path=. `   # (2)
  --ue_out=convert_unsigned_for_blueprint=true:..\out `   # (3)
  example\person.proto   # (4)
```

1. **`--plugin=protoc-gen-ue=...`** — `protoc` から `proto2ue` プラグインを呼び出すための登録です。左辺 (`protoc-gen-ue`) がプラグイン名、右辺が実行可能ファイル／スクリプトのパスです。仮想環境を有効化していれば `.venv\Scripts` が `PATH` に入るため名前だけでも参照できますが、上記のように `--plugin="protoc-gen-ue=.\.venv\Scripts\protoc-gen-ue.cmd"` と明示的なパスを渡す方法は Windows で検証済みの手順として推奨されます。
2. **`--proto_path` (`-I`)** — インクルード検索パスを追加します。ここでは `src` をカレントディレクトリにしているため `.` を指定しています。複数指定する場合はオプションを繰り返してください。
3. **`--ue_out=...:<out_dir>`** — Unreal Engine 向けコードの出力先とオプションをまとめて指定します。コロン (`:`) の左側にカンマ区切りのオプション、右側に生成先ディレクトリを記述します。複数の `.proto` を渡した場合でも同じディレクトリに展開されます。
4. **`example\person.proto`** — 入力する proto スキーマのパスです。`-I` オプションでインクルードパスを追加しながら複数ファイルを列挙できます。

### 主なオプションの使い分け

- **`--plugin`**
  - 役割: `protoc` にカスタムコード生成プラグインを登録します。
  - 設定例: `--plugin="protoc-gen-ue=.\.venv\Scripts\protoc-gen-ue.cmd"`。
  - よくある組み合わせ: 仮想環境を有効化し `.venv\Scripts` を `PATH` に追加した状態で `--ue_out` とセットで指定します。PATH を通せない環境でも、検証済みの明示的なパス指定で同様に利用できます。
- **`--ue_out`**
  - 役割: UE 向けコード生成の出力ディレクトリとオプション (`convert_unsigned_for_blueprint` など) をまとめて渡します。
  - 設定例: `--ue_out=convert_unsigned_for_blueprint=true,reserved_identifiers_file=.\config\reserved.txt:.\Intermediate\Proto2UE`。
  - よくある組み合わせ: `--plugin=protoc-gen-ue=...` と同時に指定し、`--descriptor_set_out` や `--proto_path/-I` で入力依存関係を解決しながら実行します。
- **`--descriptor_set_out`**
  - 役割: `protoc` が出力する `FileDescriptorSet` (バイナリ) を保存します。`proto2ue` の追加処理や CI での差分比較に活用できます。
  - 設定例: `--descriptor_set_out=.\Intermediate\Descriptors\example.pb`。
  - よくある組み合わせ: `--include_imports` と一緒に指定して依存 proto をまとめる、`--ue_out` とセットで Unreal 用コードと記述子を同時生成するケースが一般的です。

### 生成物と次のステップ

1. `--ue_out` の出力先 (`.\Intermediate\Proto2UE` など) に、各 proto ごとに `<name>.proto2ue.h/.cpp` とコンバーター補助の `<name>_proto2ue_converters.h/.cpp` が生成されます。
2. 追加のコンバーター機能が必要な場合は `python -m proto2ue.tools.converter` で Blueprint 互換のヘルパーを生成します。
3. 生成コードを Unreal Engine プロジェクトのモジュールに組み込み、`Build.cs` で `protobuf` ライブラリを参照します。詳細は [ユーザーガイド](docs/user-guide/README.md) を参照してください。

### コンバーター CLI (`proto2ue.tools.converter`) の使用例

1. `--descriptor_set_out` で descriptor set を保存すると、複数 proto の依存関係をまとめて後段処理できます。`--include_imports` を併用すると依存 proto も含まれるため、`proto2ue.tools.converter` に渡すだけで済みます。

   ```powershell
   # カレントディレクトリ: リポジトリルート (proto2ue)
   protoc `
     --plugin=protoc-gen-ue=protoc-gen-ue `
     --ue_out=.\Intermediate\Proto2UE `
     --descriptor_set_out=.\Intermediate\Descriptors\person.pb `
     --include_imports `
     example\person.proto
   ```

2. 仮想環境を有効化した状態で CLI を呼び出し、出力ディレクトリを指定します。`--proto` を複数回与えると対象ファイルを絞り込めます (省略時は descriptor set に含まれる全ファイルが対象です)。

   ```powershell
   # カレントディレクトリ: リポジトリルート (proto2ue)
   python -m proto2ue.tools.converter `
     .\Intermediate\Descriptors\person.pb `
     --proto example\person.proto `
     --out .\Intermediate\Proto2UE
   ```

   実行すると生成された `_proto2ue_converters.{h,cpp}` のパスが標準出力に表示されるため、CI ログや差分確認にも活用できます。Python ランタイムで変換結果を検証したい場合は `proto2ue.codegen.converters.ConvertersTemplate.python_runtime()` も併用してください。

3. 出力された `_proto2ue_converters.*` を `.proto2ue.*` と同じフォルダーに配置し、UE プロジェクトのモジュールに追加します。`UProto2UEBlueprintLibrary` を `BlueprintFunctionLibrary` として登録すると、`ToProtoBytes` / `FromProtoBytes` で Blueprint から直ちに利用できます。

## 生成時オプション

`proto2ue` のコード生成は `--ue_out=<option>=<value>,...:<out_dir>` 形式のパラメーターで挙動を切り替えられます。複数指定する場合はカンマ区切り (`,`)、セミコロン (`;`)、パイプ (`|`) のいずれでも区切れます。

| オプション | 型 | 既定値 | 説明 |
| -------- | -- | ------ | ---- |
| `convert_unsigned_for_blueprint` (`convert_unsigned_to_blueprint` 別名) | bool | `false` | `uint32` や `uint64` を Blueprint で扱いやすい符号付き構造体に変換します。 |
| `reserved_identifiers` | list | Unreal の代表的な `FVector` など | UE 側で既に利用されている識別子をカンマ区切りで上書きします。既定値を置き換えたい場合に使用します。 |
| `extra_reserved_identifiers` | list | `[]` | 既定の予約リストに追加したい識別子を列挙します。 |
| `reserved_identifiers_file` | path | — | 1 行 1 識別子形式のファイルを読み込み、予約済み識別子を追加します。`#` から始まる行はコメント扱いです。 |
| `rename_overrides` | list | `{}` | `full.proto.Name:UETypeName` 形式で明示的な UE 名を指定します。複数指定する場合は区切り文字で連結します。 |
| `rename_overrides_file` | path | — | 上記と同じ形式を 1 行ずつ記述したファイルを読み込みます。 |
| `include_package_in_names` | bool | `true` | `example.person.Person` → `FExamplePerson` のようにパッケージ名を UE 側の型に含めるか制御します。 |

CLI でファイルを渡す例:

```powershell
# カレントディレクトリ: リポジトリルート (proto2ue)
protoc `
  --plugin=protoc-gen-ue=protoc-gen-ue `
  --ue_out=rename_overrides_file=.\config\rename.txt,reserved_identifiers_file=.\config\reserved.txt:.\Intermediate\Proto2UE `
  example\person.proto
```

5. **Unreal Engine への統合** — `Intermediate/Proto2UE` 以下を UE プロジェクトに追加し、`Build.cs` から依存ライブラリ (`google::protobuf`) を解決します。詳細な手順は [ユーザーガイド](docs/user-guide/README.md) を参照してください。

## ドキュメント

- [docs/user-guide/](docs/user-guide/README.md): セットアップ手順、ワークフロー、生成コードの読み解き方、コンバーター統合ガイド。
- [docs/research/](docs/research/README.md): Unreal Build Tool 連携、型設計、サポートマトリクスなどの調査ノート。
- [plan/development_plan.md](plan/development_plan.md): フェーズ別進捗と今後のマイルストーン。

## テスト

`pytest` が DescriptorLoader・TypeMapper・コード生成・Python コンバーターをカバーするゴールデンテスト／ラウンドトリップテストを提供します。

```powershell
# カレントディレクトリ: リポジトリルート (proto2ue)
pytest
```

## 制限事項と今後の予定

- 現時点では proto2 のみサポートし、proto3 特有のフィールド (`optional`, `oneof` の挙動差など) は未検証です。
- UE 側の自動ビルド統合 (UBT ターゲット登録、`RunUAT` ワークフロー) は調査段階です。
- 生成コードの整形 (`clang-format`) と増分出力、公式配布パッケージングは未実装です。

## ライセンス

TBD
