# Phase 2 Architecture Design Notes (2024-06 更新)

実装済みコンポーネントと今後の拡張ポイントを整理します。

## レイヤー構成

1. **Descriptor Loader**
   - `proto2ue.descriptor_loader.DescriptorLoader` が `CodeGeneratorRequest` から `proto2ue.model` へ正規化。
   - 依存解決 (`file.dependency`), `map_entry`, `oneof`, `json_name`, `default_value` を解釈し、`OptionContext` でカスタムオプション検証フックを提供。
2. **Type Mapping**
   - `proto2ue.type_mapper.TypeMapper` が `model.ProtoFile` を UE フレンドリーな `UEProtoFile` へ変換。
   - 名前衝突回避、Optional ラッパー合成、Blueprint メタデータ (`unreal.*`) の適用を担当。
   - 将来的な proto3 対応に備えて `TypeMapper` のプレフィックスやラッパー命名を引数で差し替え可能に。
3. **Rendering**
   - `proto2ue.codegen.DefaultTemplateRenderer` が `.proto2ue.h/.cpp` を生成。依存順序を調整し Optional ラッパーを重複なく出力。
   - `proto2ue.codegen.converters.ConvertersTemplate` が C++ 変換ヘルパーと Blueprint ライブラリを生成。Python 版 (`PythonConvertersRuntime`) を通じてテンプレートの振る舞いをテスト。
4. **Emission**
   - `plugin.generate_code` が renderer から返された `GeneratedFile` を `CodeGeneratorResponse` へ格納。現状は 1 proto → 2 ファイル構成。コンバーター出力は別途スクリプトから呼び出す。

## テンプレート戦略

- Phase 2 では Python の文字列操作でテンプレートを構築。`DefaultTemplateRenderer` / `ConvertersTemplate` それぞれでレンダリング関数を持つ。
- 将来的に Jinja (`inja`) や `fmt` へ移行する場合に備え、`ITemplateRenderer` プロトコルを維持し、追加実装をプラグインできるようにする。
- Converters はテンプレートの分岐が多いため DSL 化も検討。Python 実装でのテストカバレッジが整備されているため置き換えコストが読みやすい。

## CLI / 設定計画

- 現状は `protoc` の `--ue_out` のみをサポート。将来のオプション案:
  - `--ue_opt=emit_converters` で `.converters.*` を同時出力。
  - `--ue_opt=manifest=<path>` で JSON マニフェストを生成し、差分ビルドに利用。
  - `--ue_opt=config=<file>` で YAML/TOML 設定を読み込み、TypeMapper の prefix や Optional ラッパー名をカスタマイズ。
- 設定解決の優先順位: ビルトイン既定 < 設定ファイル < 環境変数 < CLI フラグ。

## 拡張ポイントと今後のタスク

- **proto3 対応**: `proto3_optional`・`Any`・`WellKnownTypes` を扱うための hooks を `DescriptorLoader` に追加。
- **差分出力**: 生成済みファイルのハッシュを記録し、未変更時は `CodeGeneratorResponse` に空のファイルリストを返す。Optional ラッパーの命名が安定しているため、マニフェスト比較が容易。
- **oneof ラッパー**: `UEOneofWrapper` の情報をテンプレートで活用し、`FProto<Msg><Oneof>` 構造体を生成。Blueprint から選択肢を扱えるようにする。
- **エラーレポート**: `DescriptorLoader` にバリデーションフックを追加し、未対応機能 (`extensions`, `group`) を警告またはエラーとして報告。
- **ツールチェーン連携**: Unreal Build Tool の `PreBuildSteps` から Python スクリプトを呼び出すための CLI エントリーポイント (例: `python -m proto2ue.tools.generate --config ...`) を提供。

## テスト戦略

- `pytest` ベースのゴールデンファイルテスト (`tests/golden/example/person.proto2ue.*`) を継続。テンプレート変更時はスナップショット差分で検出。
- `PythonConvertersRuntime` によるラウンドトリップテストで `optional`/`map`/`oneof` の変換ロジックを検証。将来的には C++ 組み込みテスト (Unreal Automation Tests) を追加予定。
- 今後の回帰テスト用に実プロジェクトの proto スキーマを縮小したサンプルセットを `tests/samples/` として整備する。
