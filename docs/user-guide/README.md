# 利用者向けガイド

このディレクトリでは `proto2ue` を使って Protocol Buffers (proto2) のスキーマから Unreal Engine 向けコードと変換ヘルパーを生成するための実務情報をまとめています。Descriptor 解析と Unreal Engine 型へのマッピング、`proto2ue.codegen` が出力するヘッダー／ソースの読み方に加え、生成した構造体と protobuf メッセージを相互変換するコンバーター (`ConvertersTemplate`) の統合手順までカバーします。

## コンテンツ

- [セットアップと初期設定](getting-started.md)
  - 推奨環境、`protoc` プラグインのインストール方法、サンプル proto からのコード生成手順。
  - 生成物の配置と Unreal Build Tool での依存解決のポイント。
- [基本ワークフロー・チュートリアル](tutorials/basic-workflow.md)
  - シンプルな proto ファイルを用いた中間表現 (`proto2ue.model`) とコード生成結果の確認手順。
  - Optional ラッパー、`TArray`/`TMap`、`oneof` の展開、`unreal.*` オプションによるメタデータ制御の例。
  - `ConvertersTemplate` から得られる C++/Blueprint 変換ヘルパーのラウンドトリップ検証。

## 更新ポリシー

- CLI オプションやテンプレート構成の変更が入った場合は、必ずセットアップ手順とワークフローの該当箇所を更新します。
- チュートリアルで使用しているコードスニペットは `tests/golden/` の最新出力を基準に保守します。
- Unreal Engine 側の運用ノウハウ (Build.cs 設定、Blueprint での利用例など) は整備でき次第追記します。
