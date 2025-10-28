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
pip install -r requirements.txt  # or pip install protobuf pytest
```

## クイックスタート

1. **ユニットテストの実行** — 依存関係が揃っていることを `pytest` で確認します。

   ```bash
   pytest
   ```

2. **`protoc` プラグインの登録** — `proto2ue.plugin` を実行するラッパースクリプトを作成します (例では `~/.local/bin` に配置)。

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

3. **コード生成** — サンプル proto (`example/person.proto`) を UE 向けに変換します。生成結果は `.proto2ue.h/.cpp` とコンバーター (`.proto2ue.converters.h/.cpp`) です。

   ```bash
   protoc \
     --plugin=protoc-gen-ue=protoc-gen-ue \
     --ue_out=./Intermediate/Proto2UE \
     example/person.proto
   ```

   生成されたヘッダーは `FProtoOptional*` ラッパーや `UE_NAMESPACE_BEGIN/END` ブロックを含みます。`ConvertersTemplate` を利用する場合は、`proto2ue.codegen.converters` を Python から呼び出して `.converters.{h,cpp}` を追生成してください。

4. **Unreal Engine への統合** — `Intermediate/Proto2UE` 以下を UE プロジェクトに追加し、`Build.cs` から依存ライブラリ (`google::protobuf`) を解決します。詳細な手順は [ユーザーガイド](docs/user-guide/README.md) を参照してください。

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
