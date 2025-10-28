from __future__ import annotations

from proto2ue import model
from proto2ue.type_mapper import (
    TypeMapper,
    UEField,
    UEMessage,
    UEOneofWrapper,
    UEOptionalWrapper,
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
        options={
            "unreal": {
                "specifiers": ["Flags"],
                "meta": {"DisplayName": "Color"},
            }
        },
    )

    meta_created_by_field = model.Field(
        name="created_by",
        number=1,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="string",
    )

    meta_message = model.Message(
        name="Meta",
        full_name=f"{package}.Meta",
        fields=[meta_created_by_field],
        options={"unreal": {"blueprint_type": False}},
    )

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
                options={
                    "unreal": {
                        "category": "Profile",
                        "meta": {"DisplayName": "Nickname"},
                    }
                },
            )
        ],
        options={
            "unreal": {
                "struct_specifiers": ["Atomic"],
                "meta": {"DisplayName": "Attributes"},
            }
        },
    )

    mood_enum = model.Enum(
        name="Mood",
        full_name=f"{package}.Person.Mood",
        values=[
            model.EnumValue(name="MOOD_HAPPY", number=0),
            model.EnumValue(name="MOOD_SAD", number=1),
        ],
        options={"unreal": {"blueprint_type": False}},
    )

    id_field = model.Field(
        name="id",
        number=1,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="int32",
        options={
            "unreal": {
                "specifiers": ["EditAnywhere"],
                "category": "Identity",
                "meta": {"ClampMin": 0},
                "blueprint_read_only": True,
            }
        },
    )

    scores_field = model.Field(
        name="scores",
        number=2,
        cardinality=model.FieldCardinality.REPEATED,
        kind=model.FieldKind.SCALAR,
        scalar="float",
        options={"unreal": {"blueprint_exposed": False}},
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
        options={"unreal": {"specifiers": ["VisibleAnywhere"]}},
    )

    color_field = model.Field(
        name="primary_color",
        number=4,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.ENUM,
        type_name=f"{package}.Color",
        resolved_type=color_enum,
        options={"unreal": {"category": "Appearance"}},
    )

    attributes_field = model.Field(
        name="attributes",
        number=5,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.MESSAGE,
        type_name=f"{package}.Person.Attributes",
        resolved_type=attributes_message,
        options={
            "unreal": {
                "meta": {"DisplayName": "Attributes"},
            }
        },
    )

    email_field = model.Field(
        name="email",
        number=6,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="string",
        oneof="contact",
        oneof_index=0,
        options={"unreal": {"specifiers": ["EditAnywhere"]}},
    )

    phone_field = model.Field(
        name="phone",
        number=7,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="string",
        oneof="contact",
        oneof_index=0,
        options={
            "unreal": {
                "specifiers": ["BlueprintGetter=GetPhone"],
                "meta": {"DisplayName": "Phone"},
            }
        },
    )

    mood_field = model.Field(
        name="mood",
        number=8,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.ENUM,
        type_name=f"{package}.Person.Mood",
        resolved_type=mood_enum,
        options={"unreal": {"blueprint_exposed": False}},
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
        options={
            "unreal": {
                "struct_specifiers": ["Atomic"],
                "meta": {"DisplayName": "Person"},
                "category": "Characters",
            }
        },
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
    assert person.blueprint_type is True
    assert person.struct_specifiers == ["Atomic"]
    assert person.struct_metadata == {"DisplayName": "Person"}
    assert person.category == "Characters"
    assert len(person.fields) == 8

    id_field = person.fields[0]
    assert isinstance(id_field, UEField)
    assert id_field.name == "id"
    assert id_field.base_type == "int32"
    assert id_field.ue_type == "FProtoOptionalSampleInt32"
    assert id_field.is_optional is True
    assert id_field.container == "FProtoOptionalSampleInt32"
    assert isinstance(id_field.optional_wrapper, UEOptionalWrapper)
    assert id_field.optional_wrapper.base_type == "int32"
    assert id_field.optional_wrapper.ue_name == "FProtoOptionalSampleInt32"
    assert id_field.blueprint_exposed is True
    assert id_field.blueprint_read_only is True
    assert id_field.uproperty_specifiers == ["EditAnywhere"]
    assert id_field.category == "Identity"
    assert id_field.uproperty_metadata == {"ClampMin": "0"}

    scores_field = person.fields[1]
    assert scores_field.ue_type == "TArray<float>"
    assert scores_field.base_type == "float"
    assert scores_field.is_repeated is True
    assert scores_field.container == "TArray"
    assert scores_field.blueprint_exposed is False

    labels_field = person.fields[2]
    assert labels_field.is_map is True
    assert labels_field.ue_type == "TMap<FString, FMeta>"
    assert labels_field.map_key_type == "FString"
    assert labels_field.map_value_type == "FMeta"
    assert labels_field.uproperty_specifiers == ["VisibleAnywhere"]

    color_field = person.fields[3]
    assert color_field.base_type == "EColor"
    assert color_field.ue_type == "FProtoOptionalSampleEColor"
    assert color_field.category == "Appearance"

    attributes_field = person.fields[4]
    assert attributes_field.base_type == "FPersonAttributes"
    assert attributes_field.ue_type == "FProtoOptionalSampleFPersonAttributes"
    assert attributes_field.uproperty_metadata == {"DisplayName": "Attributes"}

    email_field = person.fields[5]
    phone_field = person.fields[6]
    assert email_field.oneof_group == "contact"
    assert phone_field.oneof_group == "contact"
    assert email_field.is_optional is True
    assert phone_field.is_optional is True
    assert email_field.ue_type == "FProtoOptionalSampleFString"
    assert email_field.container == "FProtoOptionalSampleFString"
    assert phone_field.ue_type == "FProtoOptionalSampleFString"
    assert phone_field.container == "FProtoOptionalSampleFString"
    assert email_field.uproperty_specifiers == ["EditAnywhere"]
    assert phone_field.uproperty_specifiers == ["BlueprintGetter=GetPhone"]
    assert phone_field.uproperty_metadata == {"DisplayName": "Phone"}

    mood_field = person.fields[7]
    assert mood_field.base_type == "EPersonMood"
    assert mood_field.ue_type == "FProtoOptionalSampleEPersonMood"
    assert mood_field.blueprint_exposed is False
    assert isinstance(mood_field.optional_wrapper, UEOptionalWrapper)
    assert mood_field.optional_wrapper.value_blueprint_exposed is False

    assert len(person.oneofs) == 1

    contact_wrapper = person.oneofs[0]
    assert isinstance(contact_wrapper, UEOneofWrapper)
    assert contact_wrapper.ue_name == "FPersonContactOneof"
    assert [case.field.name for case in contact_wrapper.cases] == ["email", "phone"]
    assert contact_wrapper.cases[0].ue_case_name == "FPersonContactOneofEmailCase"

    assert len(person.nested_messages) == 1
    assert person.nested_messages[0].ue_name == "FPersonAttributes"
    assert person.nested_messages[0].blueprint_type is True
    assert person.nested_messages[0].struct_specifiers == ["Atomic"]
    assert person.nested_messages[0].struct_metadata == {"DisplayName": "Attributes"}
    nickname_field = person.nested_messages[0].fields[0]
    assert nickname_field.category == "Profile"
    assert nickname_field.ue_type == "FProtoOptionalSampleFString"

    assert len(person.nested_enums) == 1
    assert person.nested_enums[0].ue_name == "EPersonMood"
    assert person.nested_enums[0].blueprint_type is False

    meta = ue_file.messages[1]
    assert meta.ue_name == "FMeta"
    assert meta.blueprint_type is False
    created_by_field = meta.fields[0]
    assert created_by_field.ue_type == "FProtoOptionalSampleFString"
    assert isinstance(created_by_field.optional_wrapper, UEOptionalWrapper)

    optional_wrappers = {wrapper.base_type: wrapper for wrapper in ue_file.optional_wrappers}
    assert set(optional_wrappers) == {
        "int32",
        "EColor",
        "FPersonAttributes",
        "EPersonMood",
        "FString",
    }
    assert optional_wrappers["int32"].ue_name == "FProtoOptionalSampleInt32"
    assert optional_wrappers["FString"].ue_name == "FProtoOptionalSampleFString"
    assert optional_wrappers["int32"].blueprint_type is True
    assert optional_wrappers["int32"].value_blueprint_exposed is True
    assert optional_wrappers["EPersonMood"].blueprint_type is False
    assert optional_wrappers["EPersonMood"].value_blueprint_exposed is False

    color_enum = ue_file.enums[0]
    assert color_enum.ue_name == "EColor"
    assert [value.name for value in color_enum.values] == ["COLOR_RED", "COLOR_GREEN"]
    assert color_enum.blueprint_type is True
    assert color_enum.specifiers == ["Flags"]
    assert color_enum.metadata == {"DisplayName": "Color"}


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
    assert ue_consumer.fields[0].ue_type == "FProtoOptionalConsumerFSharedMessage"
    assert isinstance(ue_consumer.fields[0].optional_wrapper, UEOptionalWrapper)
    assert ue_consumer.fields[0].optional_wrapper.base_type == "FSharedMessage"
    assert ue_consumer.fields[1].base_type == "ESharedState"
    assert ue_consumer.fields[1].ue_type == "FProtoOptionalConsumerESharedState"
    wrappers = {wrapper.base_type: wrapper for wrapper in ue_file.optional_wrappers}
    assert set(wrappers) == {"FSharedMessage", "ESharedState"}


def test_optional_wrapper_names_include_proto_path_segments() -> None:
    mapper = TypeMapper()

    first_field = model.Field(
        name="name",
        number=1,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="string",
    )
    first_message = model.Message(
        name="Thing",
        full_name="example.Thing",
        fields=[first_field],
    )
    first_proto = model.ProtoFile(
        name="foo/common.proto",
        package="example",
        messages=[first_message],
        enums=[],
    )

    second_field = model.Field(
        name="name",
        number=1,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.SCALAR,
        scalar="string",
    )
    second_message = model.Message(
        name="Thing",
        full_name="example.Thing",
        fields=[second_field],
    )
    second_proto = model.ProtoFile(
        name="bar/common.proto",
        package="example",
        messages=[second_message],
        enums=[],
    )

    first_result = mapper.map_file(first_proto)
    second_result = mapper.map_file(second_proto)

    first_wrapper = {wrapper.base_type: wrapper for wrapper in first_result.optional_wrappers}["FString"]
    second_wrapper = {wrapper.base_type: wrapper for wrapper in second_result.optional_wrappers}["FString"]

    assert first_wrapper.ue_name == "FProtoOptionalFooCommonFString"
    assert second_wrapper.ue_name == "FProtoOptionalBarCommonFString"
    assert first_wrapper.ue_name != second_wrapper.ue_name


def test_type_mapper_avoids_unreal_reserved_names() -> None:
    vector3d_message = model.Message(name="Vector3d", full_name="math.Vector3d")
    vector2d_message = model.Message(name="Vector2D", full_name="math.Vector2D")
    vector_state_enum = model.Enum(
        name="VectorState",
        full_name="math.VectorState",
        values=[
            model.EnumValue(name="VECTOR_STATE_UNKNOWN", number=0),
            model.EnumValue(name="VECTOR_STATE_READY", number=1),
        ],
    )

    vector_field = model.Field(
        name="vector",
        number=1,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.MESSAGE,
        type_name="math.Vector3d",
        resolved_type=vector3d_message,
    )

    state_field = model.Field(
        name="state",
        number=2,
        cardinality=model.FieldCardinality.OPTIONAL,
        kind=model.FieldKind.ENUM,
        type_name="math.VectorState",
        resolved_type=vector_state_enum,
    )

    container_message = model.Message(
        name="Container",
        full_name="math.Container",
        fields=[vector_field, state_field],
    )

    proto_file = model.ProtoFile(
        name="math.proto",
        package="math",
        messages=[vector3d_message, vector2d_message, container_message],
        enums=[vector_state_enum],
    )

    mapper = TypeMapper()
    ue_file = mapper.map_file(proto_file)

    message_names = {message.name: message.ue_name for message in ue_file.messages}

    assert message_names["Vector3d"] == "FProtoVector3d"
    assert message_names["Vector2D"] == "FProtoVector2D"

    container = next(message for message in ue_file.messages if message.name == "Container")
    assert container.fields[0].base_type == "FProtoVector3d"
    assert container.fields[0].ue_type == "FProtoOptionalMathFProtoVector3d"
    assert container.fields[1].base_type == "EProtoVectorState"
    assert container.fields[1].ue_type == "FProtoOptionalMathEProtoVectorState"

    assert ue_file.enums[0].ue_name == "EProtoVectorState"

