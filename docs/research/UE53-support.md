# Unreal Engine 5.3 サポート環境調査 (2024-06 更新)

## 対応プラットフォームとコンパイラ

| プラットフォーム | 推奨 OS / SDK | 推奨コンパイラ / IDE | 備考 |
| --- | --- | --- | --- |
| Windows | Windows 10 21H2 以降 / Windows 11 | Visual Studio 2022 17.6+ (MSVC 19.36+) | `/std:c++20` 既定。`/Zc:__cplusplus` 有効。 |
| Linux | Ubuntu 22.04 LTS | Clang 15.x (toolchain-bundled) | libc++, LLD 同梱。glibc 2.35+ を想定。 |
| macOS | macOS 13 Ventura | Xcode 15 / AppleClang 15 | Metal 対応。Rosetta 2 でのクロスビルドは非推奨。 |
| Android | Android 12/13 | Android Studio Giraffe + NDK r25c | プラグインはホスト側で生成したコードを利用。 |
| iOS | iOS 16 | Xcode 15 | UE 標準プロファイルを利用。 |
| PlayStation 5 | 専用 SDK | Clang ベース | NDA のため詳細省略。 |
| Xbox Series X|S | GDK 2023.Q3 | MSVC | NDA のため概要のみ。 |

> **メモ** UE5.3 のエンジンコードは C++17 互換を維持しているが、プロジェクト側は `/std:c++20` が既定。生成するコンバーターは `<string>`・`<type_traits>`・`<utility>` などの標準ライブラリヘッダーを使用するため、C++20 サポートを前提とする。

## ビルド要件

- **C++ 標準**: C++20 (MSVC `/std:c++20`, Clang `-std=c++20`).
- **モジュール依存**:
  - 生成コード (`.proto2ue.h/.cpp`): `Core`, `CoreUObject`, `Engine`。
  - コンバーター (`.proto2ue.converters.*`): 上記に加えて `Projects`, `google::protobuf` ランタイム。Blueprint 呼び出しには `Kismet/BlueprintFunctionLibrary.h` を含める。
- **必要ヘッダー**:
  - スケルトン: `CoreMinimal.h`, `Containers/Array.h`, `Containers/Map.h`。
  - コンバーター: `#include "Kismet/BlueprintFunctionLibrary.h"`, `#include "google/protobuf/message.h"`, `#include <string>`, `<type_traits>`, `<utility>`。
- **マクロ/ビルド設定**: `PROTO2UE_WITH_PROTOBUF` のようなトグル定義を導入予定。`UE_NAMESPACE_BEGIN/END` を利用するため UE5.1 以降が必須。

## プラグイン提供物と UE 側設定

1. **生成ヘッダー/ソース** (`.proto2ue.h/.cpp`)
   - `PublicIncludePaths` へ `Intermediate/Proto2UE` を追加。
   - `UHT` が処理できるよう、`ModuleRules` で `bLegacyPublicIncludePaths = false` を維持。
2. **コンバーター** (`.proto2ue.converters.h/.cpp`)
   - `UProto2UEBlueprintLibrary` を `PublicDependencyModuleNames` に追加し Blueprint から呼び出し可能にする。
   - `RuntimeDependencies.Add("$(BinaryOutputDir)/proto2ue/*.pb")` で descriptor set をパッケージング (将来の差分検出に使用)。
3. **Python プラグイン**
   - ビルドマシンに Python 3.11 + `protobuf` を導入。`protoc-gen-ue` ラッパーを `PATH` に配置。
   - CI では `pip install protobuf` を前処理に追加。将来的に `pip install proto2ue` を配布予定。

## リスクとフォローアップ

- Android/iOS コンパイル時の `<string>` 依存や Protobuf ランタイムの ABI を確認する必要がある。
- UHT のバージョン差異 (5.3 vs 5.4 以降) により `UE_NAMESPACE_*` マクロが変更された場合はテンプレート更新が必要。
- `clang-format` 適用や差分書き込みの自動化は未実装のため、大規模プロジェクトでは生成ファイル数増加に注意。
- Python プラグインを配布する際は `pyproject.toml` ベースのホイール提供を検討し、オフライン環境向けの zip 配布も要検討。
