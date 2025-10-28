# セットアップと初期設定

`proto2ue` を使用するための環境構築と、`protoc` プラグインが正しく呼び出せるかを確認する手順をまとめています。Unreal Engine プロジェクトへの統合は今後のフェーズで提供予定ですが、ここで紹介する手順を完了しておくと後続作業がスムーズになります。

## 必要なツール

| ツール | 推奨バージョン | 備考 |
| ------ | -------------- | ---- |
| Python | 3.11 以上 | 仮想環境の利用を推奨 |
| protoc | 3.21 以上 | `protoc --version` で確認可能 |
| pip    | 最新版        | `python -m pip install --upgrade pip` |

テストや動作確認には以下の Python パッケージが必要です。

```bash
pip install protobuf pytest
```

## 1. リポジトリの取得

```bash
git clone https://github.com/your-org/proto2ue.git
cd proto2ue
```

社内ミラーを利用する場合は URL を読み替えてください。

## 2. 仮想環境の作成と依存関係のインストール

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install protobuf pytest
```

依存パッケージは現段階では最小限に留めています。コード生成フェーズでテンプレートエンジン等を導入する際は改めて `requirements` ファイルを提供します。

## 3. protoc の動作確認

`protoc` が正しくインストールされているかを確認します。

```bash
protoc --version
```

想定バージョンより古い場合は、[Protocol Buffers の公式配布ページ](https://github.com/protocolbuffers/protobuf/releases) からバイナリを入れ替えてください。

## 4. プラグインの疎通確認

現時点では UE C++ コードの生成は未実装ですが、Descriptor 解析までの処理パイプラインを `protoc` から呼び出すことができます。以下の手順で疎通を確認してください。

1. 任意のディレクトリにサンプルの proto ファイル (`sample.proto`) を用意します。

   ```proto
   syntax = "proto2";

   package quickstart;

   message PlayerProfile {
     required string id = 1;
     optional uint32 level = 2;
     repeated string tags = 3;
   }
   ```

2. `proto2ue` リポジトリのルートで次のコマンドを実行します。

   ```bash
   protoc \
     --plugin=protoc-gen-proto2ue="python -m proto2ue.plugin" \
     --proto2ue_out=. \
     --proto_path=. \
     sample.proto
   ```

   現段階では出力ファイルは生成されませんが、エラーが表示されず終了コードが 0 であればプラグインの呼び出しは成功しています。Descriptor 解析に失敗した場合は、proto の依存解決に問題がないか確認してください。

3. さらに詳細を確認したい場合は、`tests/test_descriptor_loader.py` や `tests/test_type_mapper.py` を参考に Python スクリプトを作成し、中間表現やマッピング結果をログに出力できます。

## 5. 次のステップ

- [基本ワークフロー・チュートリアル](tutorials/basic-workflow.md) で、`TypeMapper` が生成する Unreal Engine 向けの型名・フィールド情報を詳しく確認できます。
- UE プロジェクト向けのテンプレートは今後提供予定です。それまではチュートリアル内のコードスニペットを参考に手動でプロジェクトへ組み込むことを想定しています。

不明点がある場合は Issue でご質問ください。ドキュメントは機能追加のタイミングで順次更新します。

## Blueprint 向け optional ラッパー構造体

`proto2ue` のコード生成では、`optional` フィールドをそのまま `TOptional` で表現するのではなく、Blueprint で安全に扱えるようラッパー構造体
（`FProtoOptional<Type>`）を自動的に合成します。各構造体は次のメンバーを備えています。

- `bool bIsSet` — フィールドが設定済みかどうかを示すフラグ。デフォルト値は `false` です。
- `Type Value` — 実際の値を格納します。`Type` には `TypeMapper` が算出した UE 側の型名が入ります（例: `int32`, `FString`, `FPersonAttributes`）。

同じ基底型に対して生成されるラッパーは 1 つのみで、ヘッダーファイルでは `USTRUCT(BlueprintType)` としてエクスポートされます。そのため Blueprint
からも `bIsSet` と `Value` を直接参照・更新できます。フィールド宣言側では、従来の `TOptional<Type>` の代わりに合成された構造体を使用してください。

カスタムの接頭辞を利用したい場合は、`TypeMapper(optional_wrapper="FMyOptional")` のように初期化することで `FMyOptional<Type>` という命名に切り替えられます。
生成されるメンバー名（`bIsSet` / `Value`）は固定であり、Blueprint 上でのバインディングやシリアライズ処理もこのレイアウトを前提とします。
