# 基本ワークフロー・チュートリアル

このチュートリアルでは、`proto2ue` が proto2 スキーマをどのように解析し、Unreal Engine で扱いやすいデータ構造へマッピングしてヘッダー／ソースおよび変換ヘルパーを生成するのかを段階的に確認します。`getting-started.md` で作成した `examples/example/person.proto` を題材に、Python から内部モデルを確認しつつ、最終的な C++ 出力とコンバーターを読み解きます。

## 1. DescriptorLoader で中間表現を確認

`DescriptorLoader` は `CodeGeneratorRequest` に含まれる `FileDescriptorProto` 群を `proto2ue.model` のデータクラスへ変換し、依存関係や `map_entry` を解決します。

```python
from pathlib import Path
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from proto2ue.descriptor_loader import DescriptorLoader

# getting-started.md で生成した descriptor set を再利用します。
descriptor_path = Path("Intermediate/Proto2UE/person.pb")
descriptor_set = descriptor_pb2.FileDescriptorSet()
descriptor_set.ParseFromString(descriptor_path.read_bytes())

request = plugin_pb2.CodeGeneratorRequest()
request.proto_file.extend(descriptor_set.file)
request.file_to_generate.append("examples/example/person.proto")

loader = DescriptorLoader(request)
files = loader.load()
person_file = files["examples/example/person.proto"]

print(person_file.package)  # => "example"
print([message.name for message in person_file.messages])  # => ["Meta", "Person"]
print(person_file.messages[1].oneofs[0].fields[0].name)  # => "email"
```

ポイント:

- `DescriptorLoader` は `map` フィールドを `MapEntry` として認識し、キー・値の型情報を保持します。
- `oneof` の所属関係や `json_name`、`default_value`、`unreal.*` カスタムオプション (存在する場合) も `model.Field` に格納されます。

## 2. TypeMapper で UE 向けの型に変換

`TypeMapper` は `proto2ue.model` を Unreal Engine の命名規約と Blueprint メタデータに沿った `UEProtoFile` へ変換します。Optional フィールドや `oneof` メンバーは Blueprint 対応のラッパー構造体へと展開されます。

```python
from proto2ue.type_mapper import TypeMapper

type_mapper = TypeMapper()
ue_file = type_mapper.map_file(person_file)

for enum in ue_file.enums:
    print(enum.ue_name)  # => EColor

for message in ue_file.messages:
    print(message.ue_name)  # => FMeta, FPerson など
    for field in message.fields:
        print(f"  {field.name}: {field.ue_type}")
```

このサンプルでは以下のような変換が行われます。

- `optional` フィールドと `oneof` メンバーは `FProtoOptional<ファイル名><型名>` 形式の USTRUCT として合成され、`BlueprintReadWrite`/`BlueprintReadOnly` が自動付与されます。
- `repeated` フィールドは `TArray<...>`、`map` フィールドは `TMap<Key, Value>` に展開され、`container` プロパティで元のラッパーを参照できます。
- メッセージ／列挙に `unreal` カスタムオプションが指定されている場合 (例: `unreal = { blueprint_type: false }`) は Blueprint メタデータやカテゴリが上書きされます。

## 3. `DefaultTemplateRenderer` の出力を確認

`DefaultTemplateRenderer` は proto ファイルごとに `.proto2ue.h` / `.proto2ue.cpp` を生成します。`tests/golden/example/person.proto2ue.h` に出力済みのスケルトンがあり、以下のような特徴があります。

```cpp
USTRUCT(BlueprintType)
struct FProtoOptionalExamplePersonFString {
    GENERATED_BODY()
    UPROPERTY(BlueprintReadWrite)
    bool bIsSet = false;
    UPROPERTY(BlueprintReadWrite)
    FString Value{};
};

USTRUCT(BlueprintType)
struct FPerson {
    GENERATED_BODY()
    UPROPERTY(BlueprintReadWrite)
    FProtoOptionalExamplePersonInt32 id{};
    UPROPERTY(BlueprintReadWrite)
    TArray<float> scores{};
    UPROPERTY(BlueprintReadWrite)
    TMap<FString, FMeta> labels{};
    // ... 省略 ...
    // oneof contact: email, phone
};
```

- Optional ラッパー構造体は Blueprint から直接編集可能な `bIsSet` / `Value` プロパティを持ちます。
- `UE_NAMESPACE_BEGIN(example)` ブロックでパッケージ名がラップされ、`.cpp` 側では `RegisterGeneratedTypes` のスタブ関数が生成されます。
- パッケージに複数のセグメントが含まれる場合 (例: `demo.example`)、それぞれのセグメントに対して `UE_NAMESPACE_BEGIN` / `UE_NAMESPACE_END` が個別に展開され、`UE_NAMESPACE_BEGIN(demo)` → `UE_NAMESPACE_BEGIN(example)` のようにネストされます。
- `oneof` のメンバーはコメントに列挙され、追加のヘルパー生成と組み合わせることで選択状態を管理できます。

## 4. `ConvertersTemplate` で変換ヘルパーを生成

`ConvertersTemplate` を利用すると、上記の UE 構造体と protobuf メッセージをシリアライズ／デシリアライズする C++ 関数群と Blueprint ライブラリを生成できます。Python 実装の `PythonConvertersRuntime` を使うと、C++ をビルドする前に変換ロジックを検証できます。また、descriptor set をまとめて処理したい場合は `python -m proto2ue.tools.converter` CLI を使うと `.proto2ue_converters.{h,cpp}` の出力を自動化できます。

```python
from proto2ue.codegen.converters import ConvertersTemplate

runtime = ConvertersTemplate(ue_file).python_runtime()

ue_value = {
    "id": {"bIsSet": True, "Value": 42},
    "scores": [1.0, 2.5],
    "labels": {"team": {"created_by": {"bIsSet": True, "Value": "system"}}},
    "primary_color": {"bIsSet": True, "Value": 1},
    "attributes": {
        "bIsSet": True,
        "Value": {"nickname": {"bIsSet": True, "Value": "Proto"}},
    },
    "email": {"bIsSet": True, "Value": ""},
    "phone": {"bIsSet": False, "Value": None},
    "mood": {"bIsSet": True, "Value": 1},
}

from google.protobuf import descriptor_pool, message_factory
pool = descriptor_pool.DescriptorPool()
pool.AddSerializedFile(descriptor_path.read_bytes())
person_cls = message_factory.MessageFactory(pool).GetPrototype(
    pool.FindMessageTypeByName("example.Person")
)

proto_msg = runtime.to_proto("example.Person", ue_value, person_cls())
roundtrip = runtime.from_proto("example.Person", proto_msg)
assert roundtrip["email"] == {"bIsSet": True, "Value": ""}
```

生成される C++ 版では、`Proto2UE::Converters::ToProto` / `FromProto` と Blueprint から呼び出せる `UProto2UEBlueprintLibrary::<Name>ToProtoBytes` / `FromProtoBytes` が提供されます。変換中に発生したエラーは `FConversionContext` の `Errors` 配列に蓄積され、Blueprint 向けラッパーではまとめて文字列化して返します。

## 5. Unreal オプションでメタデータをカスタマイズ

proto 定義にカスタムオプション `[(unreal.field) = {...}]` や `[(unreal.message) = {...}]` を追加すると、生成される UE 型の Blueprint 属性やカテゴリを制御できます。たとえば `email` フィールドを Blueprint から読み取り専用にしたい場合は次のように定義します。

```proto
optional string email = 6 [(unreal.field) = {
  blueprint_read_only: true,
  category: "Networking/Contact"
}];
```

TypeMapper は `blueprint_read_only`, `blueprint_exposed`, `specifiers`, `meta`, `category` を解釈し、`UPROPERTY` の引数やメタデータに反映します。詳細なオプション一覧は [`docs/research/ue-type-design.md`](../../research/ue-type-design.md) を参照してください。

---

このワークフローを UE プロジェクトに適用すると、proto スキーマを編集→`protoc` で生成→`ConvertersTemplate` で変換ヘルパーを更新→UE で再ビルド、というループを自動化できます。CI 上での実行例や Unreal Build Tool との統合案は [`docs/research/protoc-ubt-integration.md`](../../research/protoc-ubt-integration.md) を参照してください。
