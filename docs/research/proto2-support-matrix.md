# proto2 機能サポート調査

## 対象機能一覧

| 機能 | 対応方針 | 説明 / メモ |
| --- | --- | --- |
| `optional` フィールド | **対応** | 未設定判定には `TOptional` または UE5.3 で導入された `FProto2Optional`（仮称）ラッパーを生成。既定値は Reflection 情報から初期化。 |
| `required` フィールド | **対応** | UE 側では必須チェック API を生成 (`ValidateRequiredFields`)。未設定時はエディタ警告または `ensureMsgf`。 |
| `repeated` フィールド | **対応** | `TArray` または `TArray<TSharedPtr<...>>`（メッセージ型の場合）で表現。`AddDefaulted` ヘルパーを提供。 |
| `oneof` | **対応（高優先）** | `variant` 代替として `FProto2Oneof` 構造体を自動生成し、アクティブ分岐の `enum` と `TOptional` メンバーを持つ。未設定時の状態を `None` とする。 |
| 入れ子型 | **対応** | 外側 `USTRUCT` 内に `USTRUCT()` をネスト。命名は `外側名_内側名` にキャメルケースで生成し、`GENERATED_BODY()` を各構造体に付与。 |
| `enum` | **対応** | `UENUM(BlueprintType)` で生成。予約語衝突時は `_` サフィックスを付ける。未指定値 (`0`) への `MAX` 定義も生成。 |
| `package` | **対応** | UE モジュール命名 (`Proto::<Package>::`) に基づき名前空間風の `namespace Proto2UE::<Package>` を生成し、`UHT` 互換の `UE_NAMESPACE_BEGIN` を利用。 |
| `map<K,V>` | **対応（制約あり）** | UE5.3 の `TMap` を利用。キーは `string`/整数/enum のみを優先対応。浮動小数キーは未対応（`Proto` でも非推奨）。 |
| `extensions` | **将来検討** | UE 側でランタイム差し込みが困難なため、非対応とし Warning を出す。 |
| `group` | **非対応** | `group` は proto2 でも非推奨。検出時にエラー。 |
| 予約語 | **対応** | `UHT` 予約語（`BlueprintType`, `Component`, `Texture` 等）を一覧化し、`Proto2` 接尾辞や `_Field` 接尾辞で回避。 |
| `default` 値 | **対応** | UE 型に合わせたデフォルト初期化コードを生成。`optional` で明示指定時は `TOptional` を `IsSet=true` として初期化。 |
| `json_name` | **部分対応** | JSON ブリッジ API を後続フェーズで検討。現時点では生成コードにメタデータとして保持。 |
| `deprecated` | **対応** | `UE_DEPRECATED` マクロを付与し、Blueprint では `BlueprintReadOnly, meta=(DeprecatedFunction)` を追加。 |

## 優先度分類

- **P0**: `optional`, `required`, `repeated`, `enum`, 入れ子型, `oneof`
- **P1**: `map`, `package`, 予約語回避, `default`
- **P2**: `json_name`, `deprecated`
- **P3**: `extensions`（警告のみ）, `group`（エラー）

## テストカバレッジ案

1. `proto2ue/tests/golden/` にフェーズ1で洗い出した各ケースを配置。
2. 生成コードの `UHT` 実行を CI に組み込み、`UnrealHeaderTool` がエラーを出さないことを確認。
3. プロトタイプレベルで `optional`/`oneof` のアクティブ分岐をランタイム検証する自動テストを作成。

## リスクと課題

- `oneof` の空状態と UE の `Blueprint` 表現の整合性。
- `required` フィールド未設定時の挙動をどこで検証するか（生成コード vs ランタイム API）。
- `extensions` 非対応に伴う既存 proto 資産との互換性評価。
