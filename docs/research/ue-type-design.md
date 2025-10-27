# UE 側型設計とヘルパー API 要件

## 命名規約

- 生成 `USTRUCT` は `FProto` 接頭辞 + PascalCase。例: `message PlayerState` → `USTRUCT(BlueprintType) struct FProtoPlayerState`。
- 生成 `UENUM` は `EProto` 接頭辞 + PascalCase。
- `oneof` を表す補助構造体は `FProto<Player>_OneOf_<Field>` のような `F` 接頭辞。
- 内部ヘルパー関数や名前空間は `Proto2UE` で統一。

## リフレクション属性

- `USTRUCT(BlueprintType)` + `GENERATED_BODY()` を付与。エディタ公開用には `UPROPERTY(BlueprintReadWrite)`。
- `optional` 等で Blueprint 露出が不要な場合は `BlueprintReadOnly` を検討。非公開フィールドは `VisibleAnywhere` を使用。
- `UENUM(BlueprintType)` とし、`UMETA(DisplayName="...")` を付けて proto 定義のコメントを転用可能にする。

## フィールド型マッピング

| Proto 型 | UE 型 | ノート |
| --- | --- | --- |
| `int32`/`sint32`/`sfixed32` | `int32` | 範囲は `INT32_MIN..INT32_MAX`。`sint`/`sfixed` はエンコード方式のみの差で UE 側は統一。 |
| `int64`/`sint64`/`sfixed64` | `int64` | Blueprint 公開時は `int64` をラップする `FProtoInt64` を検討。 |
| `uint32` | `uint32` | Blueprint ではサポート外のため `int32` にフォールバックするかラッパー生成。 |
| `uint64` | `uint64` | Blueprint 非対応。`FProtoUInt64` ラッパー案。 |
| `fixed32`/`fixed64` | `uint32`/`uint64` | Encode 差異は変換ヘルパーで吸収。 |
| `float` | `float` | `UPROPERTY` で `meta=(ClampMin, ClampMax)` などをコメントから生成可能。 |
| `double` | `double` | Blueprint で `double` 非対応のため `FProtoDouble` ラッパー案。 |
| `bool` | `bool` | そのまま利用。 |
| `string` | `FString` | UTF-8 ↔ UTF-16 変換はヘルパーに集約。 |
| `bytes` | `TArray<uint8>` | `TArray64` は不要。 |
| `enum` | `TEnumAsByte<EProto...>` | Blueprint 化時は `UPROPERTY(BlueprintReadWrite)` で `TEnumAsByte` を利用。 |
| メッセージ型 | `FProto<Msg>` | 値型をそのままメンバーとして含む。 |

## Optional / Oneof の表現

- `optional` フィールドは `FProtoOptional<T>`（テンプレート）を生成し、`TOptional` に Blueprint メタデータを付加。
- `oneof` は `struct FProtoOneof_<Name>` を作成し、内部に `E<Name>Case` 列挙と各フィールドの `FProtoOptional` を持つ。
- `required` は単純なメンバー + 検証用メソッド。

## 変換ヘルパー API

### 共通コンセプト

- 名前空間: `namespace Proto2UE::Converters`
- 関数命名: `void ToProto(const FProtoPlayerState& Source, proto::PlayerState& Out);`
- 逆変換: `bool FromProto(const proto::PlayerState& Source, FProtoPlayerState& Out, FProtoValidationContext* Context = nullptr);`

### エラーハンドリング

- `Context` に `AddError(FString Message, const void* FieldDescriptor)` のようなメソッドを用意。未設定 required フィールドや enum 未知値を記録。
- Fatal エラーは `ensureMsgf(false, TEXT("..."))` で Editor のみ停止。

### Blueprint サポート

- `UBlueprintFunctionLibrary` (`UProto2UEBlueprintLibrary`) を生成し、`UFUNCTION(BlueprintCallable)` で `ToProtoBytes` / `FromProtoBytes` を提供。
- `TArray<uint8>` と `FString` を入出力に使い、ゲームコード側で簡易に呼べるようにする。

## ドキュメント化すべきルール

1. 生成コードはヘッダーのみ（`.generated.h` + `.h`）とし、`.cpp` はヘルパー API のみ。`Inline` 化でインクルードサイクルを避ける。
2. `#pragma once` の直後に自動生成警告コメントを挿入し、手動編集を防止。
3. `UE_DISABLE_OPTIMIZATION` 等のマクロは原則使用しない。必要なら `#ifdef WITH_EDITOR` で切り替える。

## 未確定事項

- 大規模 `map` や `repeated` に対するムーブ最適化（`TArray::Reset`）をどこまで自動生成するか。
- Blueprint 専用ラッパー型 (`FProtoInt64` 等) の API 仕様とシリアライズ対応。
- `FInstancedStruct` 等の UE5.3 新機能を活かした柔軟な `oneof` 実装の可否。
