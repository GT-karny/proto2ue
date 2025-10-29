# proto2 機能サポート状況 (2024-06 更新)

`DescriptorLoader` / `TypeMapper` / `DefaultTemplateRenderer` / `ConvertersTemplate` の実装を踏まえた最新ステータスです。優先度とテスト状況を併記します。

## 機能一覧

| 機能 | 対応状況 | 説明 / 備考 | 優先度 |
| --- | --- | --- | --- |
| `optional` フィールド | ✅ 実装済み | `FProtoOptional<File><Type>` 構造体を合成し、`bIsSet`/`Value` を Blueprint 公開。`ConvertersTemplate` で自動的にラップ／アンラップ。 | P0 |
| `required` フィールド | ⚠️ 基本対応のみ | UE 側では通常のメンバーとして生成。必須チェックは未実装 (将来 `FConversionContext` で検証予定)。 | P0 |
| `repeated` フィールド | ✅ 実装済み | `TArray<要素型>` に展開。Converters で `Add` / `Append` を行い、空配列は空の `TArray` を生成。 | P0 |
| `oneof` | ⚠️ メタデータのみ | 中間表現でケース情報を保持しコメントを出力。Optional ラッパーにより選択状態を管理。専用ラッパー構造体は未生成。 | P0 |
| 入れ子型 (message/enum) | ✅ 実装済み | 親メッセージ内にネストした `USTRUCT` / `UENUM` を生成し、命名はパッケージ相対パスを PasalCase 化。 | P0 |
| `enum` | ✅ 実装済み | `UENUM(BlueprintType)` で `enum class` を生成。予約語衝突時は `Proto` を挿入。 | P0 |
| `package` | ✅ 実装済み | `namespace package { ... }` で名前空間化 (セグメントごとにネスト)。 | P1 |
| `map<K,V>` | ✅ 実装済み | `TMap<Key, Value>` に展開。キーは protobuf の制約に従いスカラ／enum をサポート。 | P1 |
| 予約語回避 | ✅ 実装済み | UE の予約語テーブルを持ち、衝突時に `Proto` を挿入。 | P1 |
| `default` 値 | ⚠️ 未マッピング | `DescriptorLoader` で値を保持するが、現在は生成コードに反映していない。Converters での初期化も未実装。 | P1 |
| `json_name` | ⚠️ メタデータ保持 | `model.Field.json_name` に格納。生成コードでは未使用。 | P2 |
| `deprecated` | ⚠️ 未対応 | 将来的に `UE_DEPRECATED` や Blueprint メタデータを付与予定。現状は情報のみ保持。 | P2 |
| `extensions` | ❌ 非対応 | 解析段階で検出した場合はエラーを投げる (実装予定)。 | P3 |
| `group` | ❌ 非対応 | proto2 でも非推奨。検出時にエラー予定 (未テスト)。 | P3 |

## テストカバレッジ

- `tests/test_type_mapper.py` で Optional / Map / Repeated / Oneof / ネスト型のマッピングを検証。
- `tests/test_codegen_renderer.py` で生成された `.proto2ue.h/.cpp` をゴールデン比較。
- `tests/test_codegen_converters.py` で Python 版コンバーターのラウンドトリップ (`optional` + `oneof` + `map`) を実行。
- `DescriptorLoader` の単体テストで `json_name` や `map_entry` の正規化を確認。

## 今後の課題

- `default` 値の初期化ロジックを Optional ラッパーと Converters 双方に反映する。
- `deprecated` オプションから UE のメタデータ (`meta=(DeprecatedFunction)`) を自動付与。
- `oneof` の選択状態を Blueprint から操作しやすくするためのラッパー生成 (UE5.3 の `FInstancedStruct` 活用を検討)。
- `extensions` / `group` を検出した際のエラーメッセージとドキュメント整備。
