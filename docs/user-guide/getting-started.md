# セットアップと初期設定

`proto2ue` を使って UE 向けコードを生成するための環境構築と、`protoc` プラグインが正しく呼び出せるかを確認する手順をまとめます。ここで紹介するステップを完了すれば、ヘッダー／ソースのスケルトン生成に加えて、C++/Blueprint 変換ヘルパー (`ConvertersTemplate`) の Python ランタイムによる動作確認まで実施できます。

## 必要なツール

| ツール | 推奨バージョン | 備考 |
| ------ | -------------- | ---- |
| Python | 3.11 以上 | 仮想環境の利用を推奨 |
| protoc | 3.21 以上 | `protoc --version` で確認可能 |
| pip    | 最新版        | `python -m pip install --upgrade pip` |
| Unreal Engine | 5.3 系 | 生成コードのビルド確認時に利用 |

テストや動作確認には以下の Python パッケージを使用します。

```bash
pip install protobuf pytest
```

## 1. Python 環境の準備

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt  # または pip install protobuf pytest
```

プロジェクトルートで `pytest` を実行し、DescriptorLoader・TypeMapper・コード生成・変換ランタイムのテストが通ることを確認します。

```bash
pytest
```

## 2. `protoc` プラグインの登録

`proto2ue.plugin` は標準入力／標準出力で `CodeGeneratorRequest` / `CodeGeneratorResponse` をやり取りするスタンドアロンの Python モジュールです。`protoc` から利用するには実行可能なラッパースクリプトをパス上に配置します。

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

正しく登録できているか、空の入力で `--version` の代わりにヘルプを表示させて確認します。

```bash
protoc --plugin=protoc-gen-ue=protoc-gen-ue --ue_out=/tmp foo.proto 2>&1 | head
```

`foo.proto: File not found.` のようなエラーが表示されればプラグインは起動できています (後段の手順で実際の proto を指定します)。

## 3. サンプル proto の生成確認

テストで使用しているスキーマを参考に、次の `person.proto` を作成します (任意の作業ディレクトリで構いません)。

```bash
mkdir -p examples/example
cat <<'PROTO' > examples/example/person.proto
syntax = "proto2";

package example;

enum Color {
  COLOR_UNSPECIFIED = 0;
  COLOR_RED = 1;
}

message Meta {
  optional string created_by = 1;
}

message Person {
  message Attributes {
    optional string nickname = 1;
  }

  enum Mood {
    MOOD_UNSPECIFIED = 0;
    MOOD_HAPPY = 1;
  }

  message LabelsEntry {
    optional string key = 1;
    optional Meta value = 2;
  }

  optional int32 id = 1;
  repeated float scores = 2;
  repeated LabelsEntry labels = 3;
  optional Color primary_color = 4;
  optional Attributes attributes = 5;
  oneof contact {
    string email = 6;
    string phone = 7;
  }
  optional Mood mood = 8;
}
PROTO
```

出力先は UE プロジェクトに合わせたフォルダ (例: `Intermediate/Proto2UE`) を指定します。以下のコマンドはリポジトリのルートディレクトリで実行してください。

```bash
mkdir -p Intermediate/Proto2UE
protoc \
  --plugin=protoc-gen-ue=protoc-gen-ue \
  --proto_path=examples \
  --ue_out=Intermediate/Proto2UE \
  --descriptor_set_out=Intermediate/Proto2UE/person.pb \
  --include_imports \
  example/person.proto
```

生成される主なファイル:

- `Intermediate/Proto2UE/examples/example/person.proto2ue.h`
- `Intermediate/Proto2UE/examples/example/person.proto2ue.cpp`

ヘッダーファイルには `FProtoOptional*` 構造体 (proto2 の `optional` / `oneof` を Blueprint 互換にするラッパー) や `UE_NAMESPACE_BEGIN(example)` が含まれます。詳細は [基本ワークフロー・チュートリアル](tutorials/basic-workflow.md) を参照してください。

## 4. 変換ヘルパー (`ConvertersTemplate`) の生成

`ConvertersTemplate` は UE 構造体と protobuf メッセージ間の変換関数、エラー収集クラス (`FConversionContext`)、Blueprint から利用可能なシリアライズ API (`UProto2UEBlueprintLibrary`) を生成します。現状は Python から明示的に呼び出して `.proto2ue.converters.{h,cpp}` を出力します。先ほど生成した descriptor set (`Intermediate/Proto2UE/person.pb`) を使ってロードします。

```python
from pathlib import Path
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from proto2ue.descriptor_loader import DescriptorLoader
from proto2ue.type_mapper import TypeMapper
from proto2ue.codegen.converters import ConvertersTemplate

descriptor_path = Path("Intermediate/Proto2UE/person.pb")
descriptor_set = descriptor_pb2.FileDescriptorSet()
descriptor_set.ParseFromString(descriptor_path.read_bytes())

request = plugin_pb2.CodeGeneratorRequest()
request.proto_file.extend(descriptor_set.file)
target = next(
    file_proto for file_proto in descriptor_set.file
    if file_proto.name == "examples/example/person.proto"
)
request.file_to_generate.append(target.name)

loader = DescriptorLoader(request)
loader.load()
ue_file = TypeMapper().map_file(loader.get_file(target.name))
rendered = ConvertersTemplate(ue_file).render()

out_root = Path("Intermediate/Proto2UE")
header_path = out_root / Path(ue_file.name).with_suffix(".proto2ue.converters.h")
source_path = out_root / Path(ue_file.name).with_suffix(".proto2ue.converters.cpp")
header_path.parent.mkdir(parents=True, exist_ok=True)
header_path.write_text(rendered.header)
source_path.write_text(rendered.source)
```

テスト環境では `ConvertersTemplate.python_runtime()` を用いたラウンドトリップ検証が `tests/test_codegen_converters.py` に用意されています。Unreal Engine 側では `.converters.{h,cpp}` をモジュールに追加し、`Build.cs` から protobuf ランタイムへの依存を解決してください。

## 5. Unreal Engine プロジェクトへの組み込み

1. 生成された `.proto2ue.*` ファイルを `Source/<Module>/Private` / `Public` に配置します。Optional ラッパーは複数ファイルで共有されるため、同一ディレクトリ内にまとめます。
2. `Build.cs` に以下の依存を追加します。
   - `PrivateDependencyModuleNames` に `"Core"`, `"CoreUObject"`, `"Engine"`。
   - protobuf ランタイム (例: `ThirdParty/Protobuf`) を `AddThirdPartyPrivateStaticDependencies` で解決。
3. `UProto2UEBlueprintLibrary` を `BlueprintFunctionLibrary` としてエディタに登録し、`ToProtoBytes` / `FromProtoBytes` を Blueprint から呼び出せることを確認します。

## 次のステップ

- 生成されたコードの構造と Unreal オプションのカスタマイズ例は [基本ワークフロー・チュートリアル](tutorials/basic-workflow.md) を参照してください。
- Unreal Build Tool との高度な統合、CI/CD での自動生成フローについては [`docs/research/protoc-ubt-integration.md`](../research/protoc-ubt-integration.md) を参照してください。
