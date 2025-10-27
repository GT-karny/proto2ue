# `protoc` プラグインと Unreal Build Tool 連携調査

## `protoc` プラグイン基本

- プラグインは標準入力から `CodeGeneratorRequest`（descriptor-2.0.0）を読み取り、標準出力へ `CodeGeneratorResponse` を返す。
- 実装言語候補: C++17 / Rust / Go。UE プロジェクト組み込みを考慮すると **C++17** で実装し、スタンドアロン実行ファイルとして提供する案が無難。
- 依存ライブラリ: `libprotobuf` (host) のみ。サイズ削減のため `lite` ランタイム使用を検討。
- オプション解析: `--proto_path` や `--plugin=protoc-gen-ue=...` を `RunUAT` から設定。

## 出力構成案

```
Intermediate/Proto2UE/
  ├── Generated/
  │   ├── PlayerState.generated.h
  │   ├── PlayerState.proto2ue.h
  │   └── PlayerState.proto2ue.cpp
  └── manifest.json
```

- `manifest.json` に proto ファイルと生成物のマッピングを格納し、再生成判定に利用。

## Unreal Build Tool (UBT) 連携

1. `Proto2UE.Build.cs` にカスタムビルドステップを追加。
   ```csharp
   if (Target.Platform == UnrealTargetPlatform.Win64 || Target.Platform == UnrealTargetPlatform.Linux)
   {
       ExternalMetadata.Add("Proto2UE", new UEBuildExternalMetadata() { ... });
       AdditionalCompilerArguments.Add("-DPROTO2UE_ENABLED");
   }
   ```
2. `RunUAT` の `BuildPlugin` / `BuildTarget` で `-precompile` フラグ利用時に `protoc` を起動。
3. `Target.cs` で `Proto2UE` モジュールを `PreBuildSteps` に追加し、`protoc` 実行コマンドを記述。
   ```csharp
   string ProtoTool = Path.Combine(ModuleDirectory, "Binaries", HostPlatform, "protoc.exe");
   string Plugin = Path.Combine(ModuleDirectory, "Binaries", HostPlatform, "protoc-gen-ue.exe");
   string Arguments = $"--plugin=protoc-gen-ue=\"{Plugin}\" --ue_out=Intermediate/Proto2UE --proto_path={ProtoDir} {ProtoFiles}";
   PreBuildSteps.Add($"\"{ProtoTool}\" {Arguments}");
   ```
4. 生成後に `PublicIncludePaths` へ `Intermediate/Proto2UE/Generated` を追加。`AdditionalDependencies` に生成 `.cpp` を含める。

## クロスプラットフォーム配布

- `Binaries/<Platform>/` にホスト向け `protoc-gen-ue` を配置。Git LFS でバイナリを管理するか、初回ビルド時にダウンロード。
- Linux/Windows/macOS それぞれのシェルスクリプトで `protoc` 呼び出しを包む (`proto2ue.sh`, `proto2ue.bat`)。
- 自動更新: バージョン番号を `proto2ue.version` に記録し、変更時のみ再生成。

## UnrealHeaderTool との連携

- 生成 `.h` は `UHT` が処理するため、`ModuleRules` の `PublicDefinitions` に `PROTO2UE_GENERATED=1` を追加。
- `UHT` の include パスに `Intermediate/Proto2UE/Generated` を追加。`uhtmanifest.json` の `AdditionalHeaders` に登録する。

## リスクと未解決事項

- `PreBuildSteps` はホットリロード時に実行されない場合があるため、エディタ内コマンドレット (`Proto2UERescan`) を併用する案を検討。
- `protoc` が無い環境（CI ランナーなど）への配布手段。`ThirdParty/protobuf` をサブモジュールとして同梱するか検討。
- 大規模プロジェクトでのインクリメンタルビルド最適化（タイムスタンプ vs Manifest ハッシュ比較）。
