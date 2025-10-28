# `protoc` プラグインと Unreal Build Tool 連携調査 (更新版)

## プラグイン構成と起動

- 実装言語: Python 3 (`proto2ue.plugin.main`)。`protoc` から呼び出すためにホスト側で実行可能なシェル／バッチラッパー (`protoc-gen-ue`) を提供する。
- I/O: 標準入力から `CodeGeneratorRequest` (descriptor-2.0.0) を受け取り、標準出力に `CodeGeneratorResponse` を返す。
- オプション: `--ue_out=<output_dir>` のみを解釈し、相対パスは `CodeGeneratorRequest` 内の proto ファイル構造を維持する。
- 依存: `google.protobuf` ランタイム (Python) のみ。ホスト環境には Python 3.11 以上と `pip install protobuf` が必要。

### 推奨ディレクトリ構成

```
Intermediate/Proto2UE/
  ├── examples/example/person.proto2ue.h
  ├── examples/example/person.proto2ue.cpp
  ├── examples/example/person.proto2ue.converters.h  # ConvertersTemplate で追加生成
  ├── examples/example/person.proto2ue.converters.cpp
  └── person.pb  # descriptor_set_out
```

`.proto2ue.converters.*` は `ConvertersTemplate` による後処理で生成する。今後テンプレートを `generate_code` に統合する場合はオプションで出し分ける。

## Unreal Build Tool (UBT) 連携方針

1. **モジュールルール (`ModuleRules`)**
   - `PublicIncludePaths`/`PrivateIncludePaths` に `Intermediate/Proto2UE` を追加。
   - `PrivateDependencyModuleNames` に `"Core"`, `"CoreUObject"`, `"Engine"`, `"Projects"` を含める。
   - protobuf ランタイムを `ThirdParty` としてリンク (`AddThirdPartyPrivateStaticDependencies` など)。
   - 生成 `.cpp` を `PrivateDependencyModuleNames` に追加するのではなく、`RuntimeDependencies` として登録するか `PreBuildSteps` で `.Target.cs` に明示する。

2. **PreBuildSteps / UnrealBuildTool タスク**
   - `Target.cs` で `PreBuildSteps` に Python 実行を登録。
     ```csharp
     string ProtoRoot = Path.Combine(ProjectDirectory, "Proto");
     string OutputDir = Path.Combine(ProjectIntermediateDirectory, "Proto2UE");
     string PluginExe = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".local", "bin", "protoc-gen-ue");
     string Protoc = Path.Combine(PluginDirectory, "Binaries", HostPlatform, "protoc");
     string Arguments = $"--plugin=protoc-gen-ue=\"{PluginExe}\" --ue_out=\"{OutputDir}\" --descriptor_set_out=\"{OutputDir}/bundle.pb\" --include_imports";
     string ProtoFiles = string.Join(" ", Directory.GetFiles(ProtoRoot, "*.proto", SearchOption.AllDirectories));
     PreBuildSteps.Add($"\"{Protoc}\" {Arguments} {ProtoFiles}");
     ```
   - コンバーター生成は `python -m proto2ue.tools.generate_converters bundle.pb` のような補助スクリプトで自動化する想定 (実装予定)。現状はビルド前に `ConvertersTemplate` を呼ぶ Python スクリプトを追加する。

3. **Blueprint からの利用**
   - `UProto2UEBlueprintLibrary` を `PublicDependencyModuleNames` に公開し、任意のモジュールから `ToProtoBytes` / `FromProtoBytes` を呼べるようにする。
   - 変換エラーは `FConversionContext` → `FString FormatConversionErrors` の順で文字列化され、Blueprint に `Error` 出力ピンとして返る。エディタでの UX を向上させるには、`Context.GetErrors()` を詳細パネルに表示するウィジェット拡張も検討。

## 自動再生成と差分検出

- `descriptor_set_out` で出力した `.pb` ファイルのハッシュを `Intermediate/Proto2UE/manifest.json` に保存し、proto が変更された場合のみ再生成する仕組みを想定。現状は未実装だが、`TypeMapper` にファイル ID を渡して Optional ラッパー名を安定化させているため差分検出が容易。
- UBT の `ExternalExecution` を利用し、ビルドと同時に Python スクリプトを呼ぶ場合は環境変数 (`PYTHONPATH`) を明示する。

## クロスプラットフォーム配布

- Python 版プラグインの利点として、ホスト OS ごとにバイナリを配布する必要が無い。CI 上では `pip install proto2ue` (将来的なパッケージ化後) で対応可能。
- 代替案: C++17 版のスタンドアロンバイナリを `Binaries/<Host>/protoc-gen-ue` に同梱し、Python を不要にする。ただし現在は Python 実装でテストをカバーしているため優先度は低い。

## リスクと今後の課題

- **環境依存**: UE Build Machine に Python 3.11 が存在しない場合、追加インストールが必要。長期的にはネイティブバイナリ化も検討する。
- **生成物の整形**: `clang-format` の自動適用と差分書き込みの最適化が未実装。`manifest.json` に最終出力のハッシュを記録して増分化する案を評価。
- **ホットリロード**: `PreBuildSteps` は Editor ホットリロード時に実行されないため、エディタコマンドレット (`Proto2UERescan`) を提供して手動再生成できるようにする。
- **コンバーター統合**: 現状 `ConvertersTemplate` は Python スクリプト経由で呼び出す必要がある。将来的に `--ue_out` の追加オプション (例: `--ue_opt=emit_converters`) で自動生成する設計を検討。
