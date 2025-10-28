## 開発プラン概要 (2024-06 更新)

`proto2ue` は Protocol Buffers (proto2) の定義から Unreal Engine 向けの `USTRUCT` / `UENUM` と変換ヘルパーを自動生成する `protoc` プラグインです。フェーズ 1〜2 の調査を経て、現在はフェーズ 3 の実装とフェーズ 4 のテスト整備が進行中です。

### フェーズ1: 要件定義と調査 ✅ 完了
- UE5.3 をターゲットにしたプラットフォーム／コンパイラ要件の整理 ([UE53-support](../docs/research/UE53-support.md))。
- proto2 の必須機能 (optional/repeated/oneof/map/予約語 等) の洗い出しと優先度付け ([proto2-support-matrix](../docs/research/proto2-support-matrix.md))。
- UE 側型設計とヘルパー API 要件の定義 ([ue-type-design](../docs/research/ue-type-design.md))。
- `protoc` プラグインと UBT の連携方法調査 ([protoc-ubt-integration](../docs/research/protoc-ubt-integration.md))。

### フェーズ2: アーキテクチャ設計 ✅ 完了
- ジェネレータを Descriptor → Type Mapping → Rendering → Emission に分割し、`ITemplateRenderer` 抽象を策定。
- Optional ラッパーと Blueprint メタデータ反映ロジック、ConvertersTemplate の設計。
- Python ベースのテスト戦略 (`pytest` + ゴールデンファイル + PythonConvertersRuntime) を確立。

### フェーズ3: 実装 🚧 進行中
1. **基盤コード** — `DescriptorLoader`, `TypeMapper`, `plugin.generate_code` 実装済み。
2. **型マッピング** — プリミティブ／enum／message／map／optional をカバー。`default`・`deprecated` オプションは未対応。
3. **コード生成** — `DefaultTemplateRenderer` でヘッダー／ソースを出力。Optional ラッパーの依存順序整理済み。
4. **変換ヘルパー** — `ConvertersTemplate` + `PythonConvertersRuntime` 実装済み。`generate_code` からの同梱は未実装。
5. **サポート機能** — 名前衝突回避・予約語処理を実装。差分書き込み／`clang-format` 連携は TODO。

### フェーズ4: テスト戦略 🚧 進行中
- `pytest` によるユニットテスト (DescriptorLoader / TypeMapper / Renderer / Converters) を整備済み。
- 今後の課題: Unreal Automation Tests による C++ ランタイム検証、実プロジェクト proto を使った回帰テストの導入。

### フェーズ5: ツールチェーン & CI/CD 📝 計画中
- `protoc` + Python プラグインを呼び出すビルドステップ (`PreBuildSteps`) のテンプレート化。
- GitHub Actions 等で `pytest` → コード生成 → (将来) UE Headless Build を実行するワークフローの作成。
- `pip` / Wheel 配布やハッシュベースの差分生成サポートを検討。

### フェーズ6: ドキュメントとサンプル 🚧 更新中
- ユーザーガイド (セットアップ、基本ワークフロー、Converters 連携) を最新版へ刷新。
- 将来的にサンプル UE プロジェクト／proto セットを公開し、CI でビルド検証を行う。

### フェーズ7: 拡張計画 (オプション) 📝 計画中
- proto3 対応 (`optional`, `Any`, `JSON` ブリッジ) の検討。
- Blueprint / Gameplay Ability / RPC 連携などの周辺機能拡張。
- Unreal Build Tool とのより深い統合 (マニフェスト生成、差分ビルド、Editor コマンドレット) の整備。
