// Generated conversion helpers by proto2ue. Source: person.proto
#include "person_proto2ue_converters.h"
#include "google/protobuf/message.h"
#include <string>
#include <type_traits>
#include <utility>


void FExampleProtoConv::FConversionContext::AddError(const FString& InFieldPath, const FString& InMessage) {
    Errors.Emplace(FConversionError{InMessage, InFieldPath});
}
bool FExampleProtoConv::FConversionContext::HasErrors() const { return Errors.Num() > 0; }
const TArray<FExampleProtoConv::FConversionError>& FExampleProtoConv::FConversionContext::GetErrors() const { return Errors; }

void FExampleProtoConv::ToProto(const FExampleMeta& Source, example::Meta& Out, FConversionContext* Context) {
    Out.Clear();
    if (IsValueProvided(Source.created_by)) { Out.set_created_by(ToProtoString(GetFieldValue(Source.created_by))); }
}

bool FExampleProtoConv::FromProto(const example::Meta& Source, FExampleMeta& Out, FConversionContext* Context) {
    Out = {};
    bool bOk = true;
    if (Source.has_created_by()) {
        Out.created_by.Value = FromProtoString(Source.created_by());
        Out.created_by.bIsSet = true;
    }
    return bOk && (!Context || !Context->HasErrors());
}

void FExampleProtoConv::ToProto(const FExamplePerson& Source, example::Person& Out, FConversionContext* Context) {
    Out.Clear();
    {
        bool bHasContactValue = false;
        const TCHAR* FieldPath = TEXT("contact");
        if (IsValueProvided(Source.email)) {
            if (bHasContactValue) {
                if (Context) {
                    Context->AddError(FieldPath, TEXT("Multiple values provided for oneof"));
                }
                continue;
            }
            bHasContactValue = true;
            const auto& ActiveValue = GetFieldValue(Source.email);
            Out.set_email(ToProtoString(ActiveValue));
        }
        if (IsValueProvided(Source.phone)) {
            if (bHasContactValue) {
                if (Context) {
                    Context->AddError(FieldPath, TEXT("Multiple values provided for oneof"));
                }
                continue;
            }
            bHasContactValue = true;
            const auto& ActiveValue = GetFieldValue(Source.phone);
            Out.set_phone(ToProtoString(ActiveValue));
        }
    }
    if (IsValueProvided(Source.id)) { Out.set_id(GetFieldValue(Source.id)); }
    for (const auto& Item : Source.scores) { Out.add_scores(Item); }
    for (const auto& Item : Source.labels) {
        auto* Added = Out.add_labels();
        ToProto(Item, *Added, Context);
    }
    if (IsValueProvided(Source.primary_color)) { Out.set_primary_color(static_cast<example::Color>(GetFieldValue(Source.primary_color))); }
    if (IsValueProvided(Source.attributes)) {
        ToProto(GetFieldValue(Source.attributes), *Out.mutable_attributes(), Context);
    }
    if (IsValueProvided(Source.mood)) { Out.set_mood(static_cast<example::Person::Mood>(GetFieldValue(Source.mood))); }
}

bool FExampleProtoConv::FromProto(const example::Person& Source, FExamplePerson& Out, FConversionContext* Context) {
    Out = {};
    bool bOk = true;
    {
        const auto ActiveCase = Source.contact_case();
        switch (ActiveCase) {
        case example::Person::ContactCase::kEmail: {
            Out.email.Value = FromProtoString(Source.email());
            Out.email.bIsSet = true;
            break;
        }
        case example::Person::ContactCase::kPhone: {
            Out.phone.Value = FromProtoString(Source.phone());
            Out.phone.bIsSet = true;
            break;
        }
        default:
            break;
        }
    }
    if (Source.has_id()) {
        Out.id.Value = Source.id();
        Out.id.bIsSet = true;
    }
    for (const auto& Item : Source.scores()) { Out.scores.Add(Item); }
    for (const auto& Item : Source.labels()) {
        auto& Added = Out.labels.Emplace_GetRef();
        bOk = FromProto(Item, Added, Context) && bOk;
    }
    if (Source.has_primary_color()) {
        Out.primary_color.Value = static_cast<EExampleColor>(Source.primary_color());
        Out.primary_color.bIsSet = true;
    }
    if (Source.has_attributes()) {
        auto& Dest = Out.attributes.Value;
        Dest = {};
        Out.attributes.bIsSet = true;
        bOk = FromProto(Source.{field_name}(), Dest, Context) && bOk;
    }
    if (Source.has_mood()) {
        Out.mood.Value = static_cast<EExamplePersonMood>(Source.mood());
        Out.mood.bIsSet = true;
    }
    return bOk && (!Context || !Context->HasErrors());
}

void FExampleProtoConv::ToProto(const FExamplePersonAttributes& Source, example::Person::Attributes& Out, FConversionContext* Context) {
    Out.Clear();
    if (IsValueProvided(Source.nickname)) { Out.set_nickname(ToProtoString(GetFieldValue(Source.nickname))); }
}

bool FExampleProtoConv::FromProto(const example::Person::Attributes& Source, FExamplePersonAttributes& Out, FConversionContext* Context) {
    Out = {};
    bool bOk = true;
    if (Source.has_nickname()) {
        Out.nickname.Value = FromProtoString(Source.nickname());
        Out.nickname.bIsSet = true;
    }
    return bOk && (!Context || !Context->HasErrors());
}

void FExampleProtoConv::ToProto(const FExamplePersonLabelsEntry& Source, example::Person::LabelsEntry& Out, FConversionContext* Context) {
    Out.Clear();
    if (IsValueProvided(Source.key)) { Out.set_key(ToProtoString(GetFieldValue(Source.key))); }
    if (IsValueProvided(Source.value)) {
        ToProto(GetFieldValue(Source.value), *Out.mutable_value(), Context);
    }
}

bool FExampleProtoConv::FromProto(const example::Person::LabelsEntry& Source, FExamplePersonLabelsEntry& Out, FConversionContext* Context) {
    Out = {};
    bool bOk = true;
    if (Source.has_key()) {
        Out.key.Value = FromProtoString(Source.key());
        Out.key.bIsSet = true;
    }
    if (Source.has_value()) {
        auto& Dest = Out.value.Value;
        Dest = {};
        Out.value.bIsSet = true;
        bOk = FromProto(Source.{field_name}(), Dest, Context) && bOk;
    }
    return bOk && (!Context || !Context->HasErrors());
}

namespace {
FString FormatConversionErrors(const FExampleProtoConv::FConversionContext& Context) {
    FString Combined;
    const auto& Errors = Context.GetErrors();
    for (const auto& ConversionError : Errors) {
        if (!Combined.IsEmpty()) {
            Combined += TEXT("; ");
        }
        if (!ConversionError.FieldPath.IsEmpty()) {
            Combined += ConversionError.FieldPath;
            Combined += TEXT(": ");
        }
        Combined += ConversionError.Message;
    }
    if (Combined.IsEmpty()) {
        return FString(TEXT("Unknown conversion error."));
    }
    return Combined;
}
}  // namespace

bool UProto2UEBlueprintLibrary::ExampleMetaToProtoBytes(const FExampleMeta& Source, TArray<uint8>& OutBytes, FString& Error) {
    FExampleProtoConv::FConversionContext Context;
    example::Meta ProtoMessage;
    FExampleProtoConv::ToProto(Source, ProtoMessage, &Context);
    if (Context.HasErrors()) {
        Error = FormatConversionErrors(Context);
        return false;
    }
    std::string Serialized;
    if (!ProtoMessage.SerializeToString(&Serialized)) {
        Error = TEXT("Failed to serialize protobuf message.");
        return false;
    }
    OutBytes = FExampleProtoConv::FromProtoBytes(Serialized);
    Error = FString();
    return true;
}

bool UProto2UEBlueprintLibrary::ExampleMetaFromProtoBytes(const TArray<uint8>& InBytes, FExampleMeta& OutData, FString& Error) {
    const std::string Serialized = FExampleProtoConv::ToProtoBytes(InBytes);
    example::Meta ProtoMessage;
    if (!ProtoMessage.ParseFromString(Serialized)) {
        Error = TEXT("Failed to parse protobuf bytes.");
        return false;
    }
    FExampleProtoConv::FConversionContext Context;
    if (!FExampleProtoConv::FromProto(ProtoMessage, OutData, &Context)) {
        Error = FormatConversionErrors(Context);
        return false;
    }
    Error = FString();
    return true;
}

bool UProto2UEBlueprintLibrary::ExamplePersonToProtoBytes(const FExamplePerson& Source, TArray<uint8>& OutBytes, FString& Error) {
    FExampleProtoConv::FConversionContext Context;
    example::Person ProtoMessage;
    FExampleProtoConv::ToProto(Source, ProtoMessage, &Context);
    if (Context.HasErrors()) {
        Error = FormatConversionErrors(Context);
        return false;
    }
    std::string Serialized;
    if (!ProtoMessage.SerializeToString(&Serialized)) {
        Error = TEXT("Failed to serialize protobuf message.");
        return false;
    }
    OutBytes = FExampleProtoConv::FromProtoBytes(Serialized);
    Error = FString();
    return true;
}

bool UProto2UEBlueprintLibrary::ExamplePersonFromProtoBytes(const TArray<uint8>& InBytes, FExamplePerson& OutData, FString& Error) {
    const std::string Serialized = FExampleProtoConv::ToProtoBytes(InBytes);
    example::Person ProtoMessage;
    if (!ProtoMessage.ParseFromString(Serialized)) {
        Error = TEXT("Failed to parse protobuf bytes.");
        return false;
    }
    FExampleProtoConv::FConversionContext Context;
    if (!FExampleProtoConv::FromProto(ProtoMessage, OutData, &Context)) {
        Error = FormatConversionErrors(Context);
        return false;
    }
    Error = FString();
    return true;
}

