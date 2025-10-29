# フェーズ1/2 調査成果概要

フェーズ1〜2の調査では以下のドキュメントを整備し、現在は実装のフィードバックを反映した最新版へ更新済みです。

1. [UE53-support.md](UE53-support.md) — UE5.3 でサポートされるプラットフォーム／コンパイラとビルド要件の整理。`ConvertersTemplate` が依存する STL/Protobuf ランタイムや C++20 オプションについての補足を追記しました。
2. [proto2-support-matrix.md](proto2-support-matrix.md) — Proto2 機能の対応状況と優先度、テスト方針。`optional` ラッパー、`map` 展開、`unreal.*` オプションの現状反映済みです。
3. [ue-type-design.md](ue-type-design.md) — 生成する UE 側型とヘルパー API の設計方針。実装済みの命名規約、Optional ラッパー構造、Blueprint メタデータマッピングを詳細化しています。
4. [protoc-ubt-integration.md](protoc-ubt-integration.md) — `protoc` プラグイン実装と Unreal Build Tool との連携方法。コンバーター生成物 (`_proto2ue_converters.*`) の扱いと Blueprint 連携の運用ノートを追加しました。
5. [phase2-architecture.md](phase2-architecture.md) — ジェネレーター／コンバーターの層構造と拡張ポイント。Python でのテスト支援 (`PythonConvertersRuntime`) や今後予定している増分出力の検討を含みます。

これらを前提に、フェーズ3以降では生成器／ランタイム構成の最適化と Unreal Build Tool への統合検証を進めています。優先度やリスクについては各ドキュメントの最終節を参照してください。
