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

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install protobuf pytest
```

## クイックスタート

1. **ユニットテストの実行** — 依存関係が揃っていることを `pytest` で確認します。

   ```bash
   pytest
   ```

2. **`proto2ue` を Python から参照可能にする** — `protoc` がローカルコピーの `proto2ue` を読み込めるようにします。開発環境であれば editable インストールするか、`PYTHONPATH` に `src/` を追加してください。

   ```bash
   pip install -e .
   # もしくは: export PYTHONPATH="$(pwd)/src:${PYTHONPATH}"
   ```

3. **`protoc` プラグインの登録** — `proto2ue.plugin` を実行するラッパースクリプトを作成します (例では `~/.local/bin` に配置)。

   ```bash
   cat <<'SCRIPT' > ~/.local/bin/protoc-gen-ue
   #!/usr/bin/env python3
   from proto2ue import plugin

   if __name__ == "__main__":
       plugin.main()
   SCRIPT
   chmod +x ~/.local/bin/protoc-gen-ue
   export PATH="$HOME/.local/bin:$PATH"
   ```

 4. **コード生成** — サンプル proto (`example/person.proto`) を UE 向けに変換します。生成結果は `.proto2ue.h/.cpp` とコンバーター (`.proto2ue.converters.h/.cpp`) です。`--ue_out=<options>:<out_dir>` 形式で出力ディレクトリと生成時オプションを指定できます。

    ```bash
    protoc \
      --plugin=protoc-gen-ue=protoc-gen-ue \
      --ue_out=convert_unsigned_for_blueprint=true:./Intermediate/Proto2UE \
      example/person.proto
    ```

    生成されたヘッダーは `FProtoOptional*` ラッパーや `UE_NAMESPACE_BEGIN/END` ブロックを含みます。`ConvertersTemplate` を利用する場合は、`proto2ue.codegen.converters` を Python から呼び出して `.converters.{h,cpp}` を追生成してください。

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

```bash
protoc \
  --plugin=protoc-gen-ue=protoc-gen-ue \
  --ue_out=rename_overrides_file=./config/rename.txt,reserved_identifiers_file=./config/reserved.txt:./Intermediate/Proto2UE \
  example/person.proto
```

5. **Unreal Engine への統合** — `Intermediate/Proto2UE` 以下を UE プロジェクトに追加し、`Build.cs` から依存ライブラリ (`google::protobuf`) を解決します。詳細な手順は [ユーザーガイド](docs/user-guide/README.md) を参照してください。

## ドキュメント

- [docs/user-guide/](docs/user-guide/README.md): セットアップ手順、ワークフロー、生成コードの読み解き方、コンバーター統合ガイド。
- [docs/research/](docs/research/README.md): Unreal Build Tool 連携、型設計、サポートマトリクスなどの調査ノート。
- [plan/development_plan.md](plan/development_plan.md): フェーズ別進捗と今後のマイルストーン。

## テスト

`pytest` が DescriptorLoader・TypeMapper・コード生成・Python コンバーターをカバーするゴールデンテスト／ラウンドトリップテストを提供します。

```bash
pytest
```

## 制限事項と今後の予定

- 現時点では proto2 のみサポートし、proto3 特有のフィールド (`optional`, `oneof` の挙動差など) は未検証です。
- UE 側の自動ビルド統合 (UBT ターゲット登録、`RunUAT` ワークフロー) は調査段階です。
- 生成コードの整形 (`clang-format`) と増分出力、公式配布パッケージングは未実装です。

## ライセンス

TBD
