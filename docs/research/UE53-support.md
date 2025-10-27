# Unreal Engine 5.3 サポート環境調査

最終更新: 2024-05-27（社内調査）

## 対応プラットフォームとコンパイラ

| プラットフォーム | 推奨 OS / SDK | 推奨コンパイラ / IDE | 備考 |
| --- | --- | --- | --- |
| Windows | Windows 10 21H2 以降 / Windows 11 | Visual Studio 2022 17.6 以降（MSVC 19.36+） | /std:c++20 既定。ツールチェーンに Windows 10 SDK 10.0.22621 付属。 |
| Linux | Ubuntu 22.04 LTS（標準ターゲット） | Clang 15.x（toolchain-bundled） | libc++、LLD 同梱。glibc 2.35+ を想定。 |
| macOS | macOS 13 Ventura | Xcode 15、AppleClang 15 | UE5.3 公式ビルド対象。Metal 対応。 |
| Android | Android 12/13 | Android Studio Giraffe / NDK r25c、Clang | プラグインはホスト側ビルドのみ。 |
| iOS | iOS 16 | Xcode 15、AppleClang 15 | ipa 生成時は Mac 必須。 |
| PlayStation 5 | 専用 SDK | Clang ベース | 社外秘 SDK 情報省略。 |
| Xbox Series X|S | GDK 2023.Q3 | MSVC | NDA 対象のため概要のみ。 |

> **メモ** UE5.3 は C++20 の一部機能を利用しつつ、エンジンコードは C++17 互換を維持している。プラグインコードは `/std:c++20` 環境でのコンパイルを前提とする。

## ビルド要件

- **C++ 標準**: `C++20` (MSVC `/std:c++20`, Clang `-std=c++20`)
- **モジュール依存**: 最低限 `Core`, `CoreUObject`, `Engine`, `Projects`。
- **マクロ**: `UE_BUILD_DEVELOPMENT`, `UE_BUILD_SHIPPING` に応じたログ制御。`PROTO2UE_WITH_PROTOBUF` のようなフラグを検討。
- **ヘッダー依存**: `CoreMinimal.h` を入口にし、`Containers/Array.h`, `Templates/Optional.h`, `Containers/Map.h` などを想定。
- **Windows 固有**: `WIN32_LEAN_AND_MEAN` の再定義に注意。エディタビルドでは `/Zc:__cplusplus` オプションが既定で有効。

## プラグイン提供物への影響

1. **生成コードの互換性**: UE の `UHT`（Header Tool）によるパースを通すため、`USTRUCT(BlueprintType)` 等のマクロは最上部に配置し、`GENERATED_BODY()` を含めたテンプレート展開は避ける。
2. **クロスプラットフォーム**: 生成コードはエンジン標準型（`FString`, `TArray`, `TMap` 等）のみを使用し、標準ライブラリ型（`std::string` 等）は利用しない。
3. **ビルドパイプライン**: `protoc` プラグインはホスト OS 上で動作し、ターゲット毎に生成されたヘッダー／ソースを共有可能。Docker での Linux クロスビルドでは `mono`/`dotnet` 依存がない。

## リスクと未解決事項

- Android/iOS/コンソール向けのフラグやプラットフォーム固有型（`FStringView` 等）の扱いは追加検証が必要。
- UE5.3 の新機能（`Verse`, `Nanite` 拡張等）が生成コードに影響する予定はないが、Editor 拡張との互換性チェックが未実施。
- 今後の UE5.4 以降でツールチェーン更新が発生した場合、MSVC/Clang のバージョン上げに追随する必要がある。
