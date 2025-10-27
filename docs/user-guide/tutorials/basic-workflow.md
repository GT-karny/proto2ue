# 基本ワークフロー・チュートリアル

このチュートリアルでは、`proto2ue` がどのように proto2 スキーマを解析し、Unreal Engine で扱いやすいデータ構造へマッピングするのかを段階的に確認します。最終的な C++ コード生成は今後のフェーズで実装される予定ですが、現段階でも中間表現を通じて多くの挙動を検証できます。

## 1. サンプル proto の準備

`inventory.proto` というファイルを作成し、次のようなメッセージと列挙型を定義します。

```proto
syntax = "proto2";

package tutorial;

enum ItemRarity {
  COMMON = 0;
  RARE = 1;
  LEGENDARY = 2;
}

message ItemStat {
  required string name = 1;
  optional int32 value = 2;
}

message InventoryItem {
  required string id = 1;
  required ItemRarity rarity = 2;
  optional string display_name = 3;
  repeated ItemStat stats = 4;
  map<string, string> metadata = 5;

  oneof owner {
    string player_id = 6;
    string npc_id = 7;
  }
}
```

`proto2ue` は `map` フィールドを内部的にメッセージへ展開し、`oneof` に対しても後続の UE コード生成で扱いやすいラッパーを組み立てる設計になっています。

## 2. Descriptor の解析

リポジトリルートで以下のコマンドを実行し、`proto2ue` プラグインを通じて Descriptor が正しく処理されるか確認します。

```bash
protoc \
  --plugin=protoc-gen-proto2ue="python -m proto2ue.plugin" \
  --proto2ue_out=/tmp/proto2ue-out \
  --proto_path=. \
  inventory.proto
```

> `--proto2ue_out` で指定したディレクトリは今後のコード生成フェーズで利用されます。現時点では空ディレクトリが作成されるだけですが、エラーが出ないことを確認してください。

## 3. TypeMapper を用いた名称・型の確認

`TypeMapper` クラスは、Descriptor から得られた中間モデルを Unreal Engine 向けの表現 (`UEProtoFile`, `UEMessage`, `UEEnum` など) に変換します。以下のスクリプトを実行して結果をダンプしてみましょう。

```python
from pathlib import Path
from google.protobuf import descriptor_pb2
from proto2ue.descriptor_loader import DescriptorLoader
from proto2ue.type_mapper import TypeMapper

# descriptor_set.pb を生成
import subprocess
subprocess.run(
    [
        "protoc",
        "--descriptor_set_out=descriptor_set.pb",
        "--include_imports",
        "--proto_path=.",
        "inventory.proto",
    ],
    check=True,
)

request = descriptor_pb2.FileDescriptorSet()
request.ParseFromString(Path("descriptor_set.pb").read_bytes())

# protoc プラグインから渡される CodeGeneratorRequest を模倣
codegen_request = descriptor_pb2.compiler.plugin_pb2.CodeGeneratorRequest()
codegen_request.proto_file.extend(request.file)
codegen_request.file_to_generate.append("inventory.proto")

loader = DescriptorLoader(codegen_request)
proto_file = loader.get_file("inventory.proto")

mapper = TypeMapper()
ue_file = mapper.map_file(proto_file)

for message in ue_file.messages:
    print(f"Message: {message.ue_name}")
    for field in message.fields:
        attrs = []
        if field.is_optional:
            attrs.append("optional")
        if field.is_repeated:
            attrs.append("repeated")
        if field.is_map:
            attrs.append("map")
        attrs_str = f" ({', '.join(attrs)})" if attrs else ""
        print(f"  - {field.name} -> {field.ue_type}{attrs_str}")
    if message.oneofs:
        print("  Oneof groups:")
        for oneof in message.oneofs:
            print(f"    * {oneof.ue_name}")
            for case in oneof.cases:
                print(f"      - {case.field.name} -> {case.field.ue_type}")
```

実行結果の例:

```
Message: FInventoryItem
  - id -> FString
  - rarity -> ETutorialItemRarity
  - display_name -> TOptional<FString> (optional)
  - stats -> TArray<FItemStat> (repeated)
  - metadata -> TMap<FString, FString> (map)
  - owner_player_id -> FString
  - owner_npc_id -> FString
  Oneof groups:
    * FInventoryItemOwner
      - player_id -> FString
      - npc_id -> FString
Message: FItemStat
  - name -> FString
  - value -> TOptional<int32> (optional)
```

- `F` / `E` というプレフィックスは Unreal Engine のコーディング規約に合わせたものです。
- `optional` フィールドは `TOptional` ラッパーで、`repeated` フィールドは `TArray` にマッピングされます。
- `map<string, string>` は `TMap<FString, FString>` に展開され、キー・値の型は `TypeMapper` が自動決定します。
- `oneof owner` は将来的に UE 用のラッパー構造 (`FInventoryItemOwner`) として表現され、各ケースが `UEOneofCase` に対応します。

## 4. UE への組み込みを見据えたベストプラクティス

- **命名衝突の回避**: proto のパッケージ階層は UE 側の名前空間に変換されません。衝突が懸念される場合は `TypeMapper` のプレフィックス設定をカスタマイズする予定です。
- **カスタムオプション**: `DescriptorLoader` はフィールド／メッセージ／列挙型のオプションを保持します。将来のコード生成で `BlueprintType` 等のメタデータにマップできるよう、proto 側の注釈を整備しておくとスムーズです。
- **依存管理**: UE プロジェクトに統合する際は、`protoc` 実行時の `--proto_path` を Unreal Build Tool のヘッダー検索パスと同期させるとビルドトラブルを避けられます。

## 5. 次のステップ

- 変換結果を検証する自動テストは `tests/` 以下のサンプルを参考に追加できます。
- 生成コードのテンプレートが整備された際には、本チュートリアルを拡張して「ビルドできる UE モジュール」を導く予定です。
- サンプル UE プロジェクトは今後公開予定のため、本チュートリアルではコードスニペットで代替しています。

フィードバックや改善提案があれば Issue / Pull Request でお知らせください。
