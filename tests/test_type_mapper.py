from __future__ import annotations

from proto2ue import model
from proto2ue.type_mapper import (
    TypeMapper,
    UEField,
    UEMessage,
    UEOneofWrapper,
    UEProtoFile,
)


def _build_sample_model() -> model.ProtoFile:
    package = "example"

    color_enum = model.Enum(
        name="Color",
        full_name=f"{package}.Color",
        values=[
            model.EnumValue(name="COLOR_RED", number=1),
            model.EnumValue(name="COLOR_GREEN", number=2),
        ],
    )

    meta_message = model.Message(name="Meta", full_name=f"{package}.Meta")

    attributes_message = model.Message(
        name="Attributes",
        full_name=f"{package}.Person.Attributes",
        fields=[
            model.Field(
                name="nickname",
                number=1,
                cardinality=model.FieldCardinality.OPTIONAL,
                kind=model.FieldKind.SCALAR,
                scalar="string",
            )
        ],
    )

    mood_enum = model.Enum(
        name="Mood",
        full_name=f"{package}.Person.Mood",
        values=[
            model.EnumValue(name="MOOD_HAPPY", number=0),
            model.EnumValue(name="MOOD_SAD", number=1),
        ],
    )

    id_field = model.Field(
        name="id",
        number=1,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="int32",
    )

    scores_field = model.Field(
        name="scores",
        number=2,
        cardinality=model.FieldCardinality.REPEATED,
        kind=model.FieldKind.SCALAR,
        scalar="float",
    )

    labels_entry = model.MapEntry(
        key_kind=model.FieldKind.SCALAR,
        key_scalar="string",
        value_kind=model.FieldKind.MESSAGE,
        value_scalar=None,
        value_type_name=f"{package}.Meta",
        value_resolved_type=meta_message,
    )

    labels_field = model.Field(
        name="labels",
        number=3,
        cardinality=model.FieldCardinality.REPEATED,
        kind=model.FieldKind.MAP,
        map_entry=labels_entry,
    )

    color_field = model.Field(
        name="primary_color",
        number=4,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.ENUM,
        type_name=f"{package}.Color",
        resolved_type=color_enum,
    )

    attributes_field = model.Field(
        name="attributes",
        number=5,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.MESSAGE,
        type_name=f"{package}.Person.Attributes",
        resolved_type=attributes_message,
    )

    email_field = model.Field(
        name="email",
        number=6,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="string",
        oneof="contact",
        oneof_index=0,
    )

    phone_field = model.Field(
        name="phone",
        number=7,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="string",
        oneof="contact",
        oneof_index=0,
    )

    mood_field = model.Field(
        name="mood",
        number=8,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.ENUM,
        type_name=f"{package}.Person.Mood",
        resolved_type=mood_enum,
    )

    contact_oneof = model.Oneof(
        name="contact",
        full_name=f"{package}.Person.contact",
        fields=[email_field, phone_field],
    )

    person_message = model.Message(
        name="Person",
        full_name=f"{package}.Person",
        fields=[
            id_field,
            scores_field,
            labels_field,
            color_field,
            attributes_field,
            email_field,
            phone_field,
            mood_field,
        ],
        nested_messages=[attributes_message],
        nested_enums=[mood_enum],
        oneofs=[contact_oneof],
    )

    proto_file = model.ProtoFile(
        name="sample.proto",
        package=package,
        messages=[person_message, meta_message],
        enums=[color_enum],
    )

    return proto_file


def test_type_mapper_builds_symbol_table_and_converts_types() -> None:
    proto_file = _build_sample_model()

    mapper = TypeMapper()
    ue_file = mapper.map_file(proto_file)

    assert isinstance(ue_file, UEProtoFile)
    assert ue_file.name == "sample.proto"
    assert len(ue_file.messages) == 2
    assert len(ue_file.enums) == 1

    person = ue_file.messages[0]
    assert isinstance(person, UEMessage)
    assert person.ue_name == "FPerson"
    assert len(person.fields) == 8

    id_field = person.fields[0]
    assert isinstance(id_field, UEField)
    assert id_field.name == "id"
    assert id_field.base_type == "int32"
    assert id_field.ue_type == "TOptional<int32>"
    assert id_field.is_optional is True
    assert id_field.container == "TOptional"

    scores_field = person.fields[1]
    assert scores_field.ue_type == "TArray<float>"
    assert scores_field.base_type == "float"
    assert scores_field.is_repeated is True
    assert scores_field.container == "TArray"

    labels_field = person.fields[2]
    assert labels_field.is_map is True
    assert labels_field.ue_type == "TMap<FString, FMeta>"
    assert labels_field.map_key_type == "FString"
    assert labels_field.map_value_type == "FMeta"

    color_field = person.fields[3]
    assert color_field.base_type == "EColor"
    assert color_field.ue_type == "TOptional<EColor>"

    attributes_field = person.fields[4]
    assert attributes_field.base_type == "FPersonAttributes"
    assert attributes_field.ue_type == "TOptional<FPersonAttributes>"

    email_field = person.fields[5]
    phone_field = person.fields[6]
    assert email_field.oneof_group == "contact"
    assert phone_field.oneof_group == "contact"
    assert email_field.is_optional is False
    assert phone_field.is_optional is False
    assert email_field.ue_type == "FString"

    mood_field = person.fields[7]
    assert mood_field.base_type == "EPersonMood"
    assert mood_field.ue_type == "TOptional<EPersonMood>"

    assert len(person.oneofs) == 1

    contact_wrapper = person.oneofs[0]
    assert isinstance(contact_wrapper, UEOneofWrapper)
    assert contact_wrapper.ue_name == "FPersonContactOneof"
    assert [case.field.name for case in contact_wrapper.cases] == ["email", "phone"]
    assert contact_wrapper.cases[0].ue_case_name == "FPersonContactOneofEmailCase"

    assert len(person.nested_messages) == 1
    assert person.nested_messages[0].ue_name == "FPersonAttributes"

    assert len(person.nested_enums) == 1
    assert person.nested_enums[0].ue_name == "EPersonMood"

    meta = ue_file.messages[1]
    assert meta.ue_name == "FMeta"

    color_enum = ue_file.enums[0]
    assert color_enum.ue_name == "EColor"
    assert [value.name for value in color_enum.values] == ["COLOR_RED", "COLOR_GREEN"]


def test_type_mapper_registers_imported_symbols_across_files() -> None:
    shared_enum = model.Enum(
        name="SharedState",
        full_name="common.SharedState",
        values=[
            model.EnumValue(name="SHARED_STATE_ENABLED", number=0),
            model.EnumValue(name="SHARED_STATE_DISABLED", number=1),
        ],
    )

    shared_message = model.Message(name="SharedMessage", full_name="common.SharedMessage")

    shared_file = model.ProtoFile(
        name="shared.proto",
        package="common",
        messages=[shared_message],
        enums=[shared_enum],
    )

    imported_message_field = model.Field(
        name="shared_message",
        number=1,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.MESSAGE,
        type_name="common.SharedMessage",
        resolved_type=shared_message,
    )

    imported_enum_field = model.Field(
        name="shared_state",
        number=2,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.ENUM,
        type_name="common.SharedState",
        resolved_type=shared_enum,
    )

    consumer_message = model.Message(
        name="Consumer",
        full_name="consumer.Consumer",
        fields=[imported_message_field, imported_enum_field],
    )

    consumer_file = model.ProtoFile(
        name="consumer.proto",
        package="consumer",
        dependencies=["shared.proto"],
        messages=[consumer_message],
    )

    mapper = TypeMapper()
    mapper.register_files([shared_file, consumer_file])

    ue_file = mapper.map_file(consumer_file)

    assert len(ue_file.messages) == 1
    ue_consumer = ue_file.messages[0]
    assert ue_consumer.fields[0].base_type == "FSharedMessage"
    assert ue_consumer.fields[0].ue_type == "TOptional<FSharedMessage>"
    assert ue_consumer.fields[1].base_type == "ESharedState"
    assert ue_consumer.fields[1].ue_type == "TOptional<ESharedState>"

