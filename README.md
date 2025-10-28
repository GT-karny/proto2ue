# proto2ue

`proto2ue` は Protocol Buffers (proto2) の定義から Unreal Engine 向けの C++ 構造体／列挙体と変換ヘルパーを自動生成する `protoc` プラグインを目指すプロジェクトです。メッセージを `USTRUCT`、列挙型を `UENUM` として出力し、`optional` / `repeated` / `oneof` / `map` といった言語機能に対応した UE ネイティブな型を生成できるよう設計しています。

> **Status**: `protoc` プラグインのエントリーポイントと Descriptor 解析、中間表現の構築、Unreal Engine 型へのマッピング (`TypeMapper`) までを実装済みです。C++ コード生成や Unreal Build Tool との統合は次のフェーズで提供予定です。

---

## 目次

- [主な機能](#主な機能)
- [プロジェクトのゴール](#プロジェクトのゴール)
- [要件](#要件)
- [セットアップ](#セットアップ)
- [クイックスタート](#クイックスタート)
- [チュートリアルとドキュメント](#チュートリアルとドキュメント)
- [テスト](#テスト)
- [制限事項と今後の予定](#制限事項と今後の予定)
- [ライセンス](#ライセンス)

## 主な機能

- `CodeGeneratorRequest` からの Descriptor 解析と、依存関係を解決した中間モデル (`proto2ue.model`) の構築。
- Unreal Engine の命名規則に合わせて `F`/`E` プレフィックス付きの型名を生成するマッピングレイヤ (`proto2ue.type_mapper`).
- `optional` / `repeated` / `map` / `oneof` を含む複雑なフィールド構造を UE の `TOptional` / `TArray` / `TMap` / ラッパー構造へ変換する仕組み。
- カスタムオプションを保持したまま中間表現へ転写できるように設計されたオプション正規化ロジック。

## プロジェクトのゴール

- Unreal Engine 5.3 をターゲットに、proto2 のメッセージ／列挙定義から UE 側の C++ コードを自動生成。
- 生成コードに Proto ↔ UE の双方向変換ヘルパーを付与し、ネットワークや保存データとの相互運用を容易にする。
- 将来的には `clang-format` 連携や Blueprint で扱いやすい API の提供も視野に入れています。

## 要件

- Python 3.11 以上
- `protoc` (Protocol Buffers Compiler) 3.21 以上
- Python パッケージ: `protobuf`, `pytest` (テスト実行時)
  - `json_format.MessageToDict` のシグネチャ変更が入った protobuf 4.26 以降にも対応する互換性修正を含みます。

> UE プロジェクトとの統合や `clang-format` の利用は後続フェーズで手順を提供する予定です。

## セットアップ

1. リポジトリをクローンします。

   ```bash
   git clone https://github.com/your-org/proto2ue.git
   cd proto2ue
   ```

2. 仮想環境を作成・有効化して依存パッケージをインストールします。

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows の場合は .venv\Scripts\activate
   pip install --upgrade pip
   pip install protobuf pytest
   ```

3. `protoc` がパスに入っていることを確認します。

   ```bash
   protoc --version
   ```

## クイックスタート

1. proto ファイルを用意します。例として `address_book.proto` を作成します。

   ```proto
   syntax = "proto2";

   package demo;

   message Person {
     required string name = 1;
     optional string email = 2;
   }

   message AddressBook {
     repeated Person people = 1;
   }
   ```

2. `protoc` でプラグインを呼び出します（現時点では UE コードを出力する代わりに、Descriptor を解析して問題がないか検証するステップとなります）。

   ```bash
   protoc \
     --plugin=protoc-gen-proto2ue="python -m proto2ue.plugin" \
     --proto2ue_out=. \
     --proto_path=. \
     address_book.proto
   ```

   生成フェーズは今後追加予定のため、上記コマンドでは空のレスポンスが返却されます。Descriptor 解析が成功すれば、標準出力にエラーが表示されず終了ステータス 0 となります。

3. Unreal Engine 型へのマッピングを確認したい場合は、`tests/test_type_mapper.py` を参考に Python スクリプトを記述し、`TypeMapper` による名称／型変換ロジックを実行できます。

## チュートリアルとドキュメント

- [利用者向けガイド](docs/user-guide/README.md)
  - [セットアップと初期設定](docs/user-guide/getting-started.md)
  - [基本ワークフロー・チュートリアル](docs/user-guide/tutorials/basic-workflow.md)
- 開発背景とアーキテクチャ設計メモは [`docs/research`](docs/research) を参照してください。

サンプルの proto ファイルと UE プロジェクトは今後のリリースで提供予定です。本ドキュメントでは、同等の内容をチュートリアル内で段階的に説明しています。

## テスト

単体テストは `pytest` で実行できます。

```bash
pytest
```

## 制限事項と今後の予定

- UE C++ コードの自動生成は実装途中であり、現状は Descriptor → 中間表現までをサポートします。
- Blueprint 対応、`clang-format` 連携、パッケージング方法などは現在のロードマップに沿って順次整備予定です。
- サンプル UE プロジェクトは整備中です。チュートリアルで代替手順を提供しています。

## ライセンス

ライセンスは今後の公開に合わせて決定予定です。現段階では社内利用のみを想定しています。
