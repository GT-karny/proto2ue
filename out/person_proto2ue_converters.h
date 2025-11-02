#pragma once

// Generated conversion helpers by proto2ue. Source: person.proto

#include "CoreMinimal.h"
#include <string>
#include <type_traits>
#include <utility>
#include "Kismet/BlueprintFunctionLibrary.h"
#include "person_proto2ue_92030ff1.h"
#include "person.pb.h"
#include "person_proto2ue_converters.generated.h"

class FExampleProtoConv {
public:
    struct FConversionError { FString Message; FString FieldPath; };
    class FConversionContext {
    public:
        void AddError(const FString& InFieldPath, const FString& InMessage);
        bool HasErrors() const;
        const TArray<FConversionError>& GetErrors() const;
    private:
        TArray<FConversionError> Errors;
    };

    static void ToProto(const FExampleMeta& Source, example::Meta& Out, FConversionContext* Context = nullptr);
    static bool FromProto(const example::Meta& Source, FExampleMeta& Out, FConversionContext* Context = nullptr);

    static void ToProto(const FExamplePerson& Source, example::Person& Out, FConversionContext* Context = nullptr);
    static bool FromProto(const example::Person& Source, FExamplePerson& Out, FConversionContext* Context = nullptr);

    static void ToProto(const FExamplePersonAttributes& Source, example::Person::Attributes& Out, FConversionContext* Context = nullptr);
    static bool FromProto(const example::Person::Attributes& Source, FExamplePersonAttributes& Out, FConversionContext* Context = nullptr);

    static void ToProto(const FExamplePersonLabelsEntry& Source, example::Person::LabelsEntry& Out, FConversionContext* Context = nullptr);
    static bool FromProto(const example::Person::LabelsEntry& Source, FExamplePersonLabelsEntry& Out, FConversionContext* Context = nullptr);

private:
    friend class UProto2UEBlueprintLibrary;

    template <typename, typename = void>
    struct THasIsSet : std::false_type {};
    template <typename T>
    struct THasIsSet<T, std::void_t<decltype(std::declval<const T&>().IsSet())>> : std::true_type {};
    template <typename, typename = void>
    struct THasIsSetMember : std::false_type {};
    template <typename T>
    struct THasIsSetMember<T, std::void_t<decltype(std::declval<const T&>().bIsSet)>> : std::true_type {};
    template <typename, typename = void>
    struct THasNum : std::false_type {};
    template <typename T>
    struct THasNum<T, std::void_t<decltype(std::declval<const T&>().Num())>> : std::true_type {};
    template <typename, typename = void>
    struct THasEquality : std::false_type {};
    template <typename T>
    struct THasEquality<T, std::void_t<decltype(std::declval<const T&>() == std::declval<const T&>())>> : std::true_type {};
    template <typename, typename = void>
    struct THasGetValue : std::false_type {};
    template <typename T>
    struct THasGetValue<T, std::void_t<decltype(std::declval<const T&>().GetValue())>> : std::true_type {};
    template <typename, typename = void>
    struct THasValueMember : std::false_type {};
    template <typename T>
    struct THasValueMember<T, std::void_t<decltype(std::declval<const T&>().Value)>> : std::true_type {};
    template <typename T>
    static bool IsValueProvided(const T& Value) {
        if constexpr (THasIsSet<T>::value) {
            return Value.IsSet();
        } else if constexpr (THasIsSetMember<T>::value) {
            return Value.bIsSet;
        } else if constexpr (THasNum<T>::value) {
            return Value.Num() > 0;
        } else if constexpr (std::is_pointer_v<T>) {
            return Value != nullptr;
        } else if constexpr (THasEquality<T>::value && std::is_default_constructible_v<T>) {
            return Value != T{};
        } else {
            return false;
        }
    }
    template <typename T>
    static decltype(auto) GetFieldValue(const T& Value) {
        if constexpr (THasGetValue<T>::value) {
            return Value.GetValue();
        } else if constexpr (THasValueMember<T>::value) {
            return Value.Value;
        } else {
            return Value;
        }
    }
    static std::string ToProtoString(const FString& Value) {
        FTCHARToUTF8 Converter(*Value);
        return std::string(Converter.Get(), Converter.Length());
    }
    static std::string ToProtoBytes(const TArray<uint8>& Value) {
        return std::string(reinterpret_cast<const char*>(Value.GetData()), Value.Num());
    }
    static FString FromProtoString(const std::string& Value) {
        return FString(UTF8_TO_TCHAR(Value.c_str()));
    }
    static TArray<uint8> FromProtoBytes(const std::string& Value) {
        TArray<uint8> Result;
        Result.Append(reinterpret_cast<const uint8*>(Value.data()), Value.size());
        return Result;
    }
};

UCLASS()
class UProto2UEBlueprintLibrary : public UBlueprintFunctionLibrary {
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Proto2UE")
    static bool ExampleMetaToProtoBytes(const FExampleMeta& Source, TArray<uint8>& OutBytes, FString& Error);
    UFUNCTION(BlueprintCallable, Category="Proto2UE")
    static bool ExampleMetaFromProtoBytes(const TArray<uint8>& InBytes, FExampleMeta& OutData, FString& Error);
    UFUNCTION(BlueprintCallable, Category="Proto2UE")
    static bool ExamplePersonToProtoBytes(const FExamplePerson& Source, TArray<uint8>& OutBytes, FString& Error);
    UFUNCTION(BlueprintCallable, Category="Proto2UE")
    static bool ExamplePersonFromProtoBytes(const TArray<uint8>& InBytes, FExamplePerson& OutData, FString& Error);
};

