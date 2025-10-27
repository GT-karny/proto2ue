## 開発プラン概要
`proto2ue` は Protocol Buffers (proto2) の定義から Unreal Engine 向けの C++ クラス／構造体（USTRUCT/UENUM）と変換ヘルパーを自動生成する `protoc` プラグインを目指しています。



### フェーズ1: 要件定義と調査
- 想定する Unreal Engine バージョン (UE5.3) とサポートするプラットフォーム／コンパイラの確認。
- 対応すべき proto2 機能（optional/repeated/oneof、入れ子型、パッケージ、マップ型、予約語の扱いなど）の洗い出し。
- 生成する UE 側の型設計（USTRUCT、UENUM、UCLASS?、Blueprint サポート有無、命名規約）とヘルパー API の要件整理。
- `protoc` プラグインインターフェース (code generator request/response) と Unreal Build Tool との連携方法の調査。

### フェーズ2: アーキテクチャ設計
- 詳細な設計ノートは [Phase 2 Architecture Design Notes](../docs/research/phase2-architecture.md) を参照。
- ジェネレータのコンポーネント分割
  - Descriptor 解析層
  - UE 型へのマッピングレイヤ
  - テンプレートベースのコード出力層
  - 変換ヘルパー生成ロジック
- テンプレートエンジン選定（手組み、`fmt`, `inja`, 既存コード生成ライブラリなど）。
- 設定ファイル／CLI オプション設計（名前空間の指定、出力ディレクトリ、型マッピングの上書き等）。
- 拡張性（将来の proto3/UE バージョン対応）を見据えたインターフェース設計。

### フェーズ3: 実装
1. **基盤コード**
   - `protoc` プラグインエントリーポイント実装。
   - FileDescriptorSet の読み込みと中間表現構築。
2. **型マッピング**
   - プリミティブ型、文字列、バイナリ、enum を UE 型にマッピング。
   - optional/repeated/oneof、マップ型、入れ子型の展開ロジック。
3. **コード生成**
   - ヘッダー/ソース出力のテンプレート実装。
   - プロパティメタデータ（`UPROPERTY`, `BlueprintType` など）の付与。
   - 変換ヘルパー（Proto ↔ UE）関数の実装。
4. **サポート機能**
   - 名前衝突回避、予約語処理。
   - コメントや注釈の伝播、カスタムオプション対応。
   - 出力ファイルの差分書き込み、整形（clang-format 連携）。

### フェーズ4: テスト戦略
- 単体テスト: Descriptor 入力に対するジェネレータの出力を Golden File 比較で検証。
- 統合テスト: 代表的な proto ファイル群を生成 → UE プロジェクトに組み込み → ビルド確認 (CI 上ではヘッドレスコンパイル)。
- 変換ヘルパーのラウンドトリップテスト（Proto ↔ UE）。
- 将来的な回帰テストのためのサンプル proto コレクション整備。

### フェーズ5: ツールチェーン & CI/CD
- CMake もしくは Bazel 等によるビルド構成。
- `protoc` と UE ヘッダーに依存するための環境セットアップスクリプト整備。
- GitHub Actions などで lint / unit test / (可能なら) UE Headless Build を自動化。
- リリース時のバイナリ配布、`protoc` プラグインのインストール手順整備。

### フェーズ6: ドキュメントとサンプル
- 利用者向け README / チュートリアル / サンプル proto & UE プロジェクト。
- カスタマイズ手順、トラブルシューティング、制限事項の明記。
- プロジェクト内のコーディング規約とコントリビュートガイドライン策定。

### フェーズ7: 拡張計画 (オプション)
- proto3 対応や JSON 変換ヘルパー追加などのロードマップ策定。
- UE Blueprints や RPC (gRPC) 連携など、利用者のフィードバックを反映した機能強化検討。
