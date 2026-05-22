from typing import Literal, Sequence, Any, Callable, Generic, cast

import streamlit as st
st_version = st.version.STREAMLIT_VERSION_STRING.split(".")
major_version, minor_version, patch_version = int(st_version[0]), int(st_version[1]), int(st_version[2])

from streamlit.elements.lib.options_selector_utils import convert_to_sequence_and_check_comparable, get_default_indices
Width = None
BindOption = None
from streamlit.runtime.state.common import RegisterWidgetResult

if major_version == 1:
    if minor_version < 38:
        raise ImportError(
            "The button_group plugin requires Streamlit version 1.38 or higher. "
            "Please upgrade your Streamlit installation."
        )
    if minor_version < 45:
        from streamlit.elements.widgets.button_group import SingleOrMultiSelectSerde, V
        ButtonGroupSerde = SingleOrMultiSelectSerde
    elif minor_version < 55:
        from streamlit.elements.widgets.button_group import ButtonGroupSerde, V
    elif minor_version >= 55:
        from streamlit.elements.widgets.button_group import _SingleSelectButtonGroupSerde, _MultiSelectButtonGroupSerde, T, V
        from streamlit.elements.lib.layout_utils import Width
        from streamlit.runtime.state.common import BindOption
        from streamlit.elements.lib.options_selector_utils import maybe_coerce_enum_sequence, maybe_coerce_enum
        from streamlit.string_util import validate_material_icon, is_emoji

        class ButtonGroupSerde(Generic[T]):
            def __init__(
                    self,
                    selection_mode: Literal["single", "multi"],
                    options: Sequence[T],
                    formatted_options: list[str],
                    formatted_option_to_option_index: dict[str, int],
                    default_option_indices: list[int] | None = None,
                    format_func: Callable[[Any], str] = str
            ):
                if selection_mode == "multi":
                    self.serde = _MultiSelectButtonGroupSerde[T](
                        options,
                        formatted_options=formatted_options,
                        formatted_option_to_option_index=formatted_option_to_option_index,
                        default_option_indices=default_option_indices,
                        format_func=format_func,
                    )
                else:
                    self.serde = _SingleSelectButtonGroupSerde[T](
                        options,
                        formatted_options=formatted_options,
                        formatted_option_to_option_index=formatted_option_to_option_index,
                        default_option_index=default_option_indices[0] if default_option_indices else None,
                        format_func=format_func,
                    )

            def serialize(self, value: T | list[T] | None) -> list[str]:
                return self.serde.serialize(cast(Any, value))

            def deserialize(self, ui_value: list[str] | None) -> list[T] | T | None:
                return self.serde.deserialize(ui_value)

else:
    raise NotImplemented("Only implemented for streamlit version 1")

from streamlit.errors import StreamlitAPIException
from streamlit.proto.ButtonGroup_pb2 import ButtonGroup as ButtonGroupProto
from streamlit.runtime.state import WidgetCallback
from streamlit.string_util import validate_material_icon


def st_button_group(
    label: str | None,
    options: Sequence[Any],
    *,
    key: str = "button_group",
    default: Sequence[V] | V | None = None,
    selection_mode: Literal["single", "multi"] = "single",
    disabled: bool = False,
    format_func: Callable[[Any], str] | None = None,
    style: Literal["borderless", "pills", "segmented_control"] = "pills",
    on_change: WidgetCallback | None = None,
    args=None,
    kwargs=None,
    label_visibility: Literal["visible", "hidden", "collapsed"] = "visible",
    # Opciones nuevas para controlar la visibilidad de la selección en modo single
    # selection_visualization: Literal["only_selected", "all_up_to_selected"] = "only_selected",
    keep_selection: Literal["always_visible", "never_visible"] = None,
    help: str | None = None,
    width: Width = "content",
    bind: BindOption = None,
):
    # i_key = 0
    # if f"{key}_{i_key}__check" in st.session_state:
    #     # Exist a button with this value
    #     if st.session_state[f"{key}_{i_key}__check"]:
    #         i_key += 1
    #         st.session_state[f"{key}_{i_key}__check"] = False


    unique_key = key

    # Use str as default format_func
    actual_format_func: Callable[[Any], str] = format_func or str

    def _transformed_format_func(option: V) -> ButtonGroupProto.Option:
        """If option starts with a material icon or an emoji, we extract it to send
        it parsed to the frontend.
        """
        transformed = actual_format_func(option)
        transformed_parts = transformed.split(" ")
        icon: str | None = None
        if len(transformed_parts) > 0:
            maybe_icon = transformed_parts[0].strip()
            try:
                if maybe_icon.startswith(":material"):
                    icon = validate_material_icon(maybe_icon)
                elif is_emoji(maybe_icon):
                    icon = maybe_icon

                if icon:
                    # reassamble the option string without the icon - also
                    # works if len(transformed_parts) == 1
                    transformed = " ".join(transformed_parts[1:])
            except StreamlitAPIException:
                # we don't have a valid icon or emoji, so we just pass
                pass
        return ButtonGroupProto.Option(
            content=transformed,
            content_icon=icon,
        )

    indexable_options = convert_to_sequence_and_check_comparable(options)
    default_values = get_default_indices(indexable_options, default)

    # Create string-based mappings for the serde
    formatted_options: list[str] = []
    formatted_option_to_option_index: dict[str, int] = {}
    for index, _option in enumerate(indexable_options):
        formatted = actual_format_func(_option)
        formatted_options.append(formatted)
        # If formatted labels are duplicated, the last one wins. We keep this
        # behavior to mirror radio/selectbox/multiselect.
        formatted_option_to_option_index[formatted] = index

    serde: ButtonGroupSerde[V] = ButtonGroupSerde[V](
        selection_mode,
        indexable_options,
        formatted_options=formatted_options,
        formatted_option_to_option_index=formatted_option_to_option_index,
        default_option_indices=default_values,
        format_func=actual_format_func

    )
    # if selection_visualization == "only_selected":
    #     selection_visualization = ButtonGroupProto.SelectionVisualization.ONLY_SELECTED
    # elif selection_visualization == "all_up_to_selected":
    #     selection_visualization = ButtonGroupProto.SelectionVisualization.ALL_UP_TO_SELECTED


    params = dict(
        indexable_options=indexable_options,
        default=default_values,
        selection_mode=selection_mode,
        disabled=disabled,
        format_func=_transformed_format_func,
        key=unique_key,
        help=help,
        width=width,
        style=style,
        serializer=serde.serialize,
        deserializer=serde.deserialize,
        on_change=on_change, args=args, kwargs=kwargs,
        label=label,
        label_visibility=label_visibility,
        options_format_func=actual_format_func,
        bind=bind,
        string_formatted_options=formatted_options,
        # selection_visualization=selection_visualization,
    )

    if selection_mode == "single" and keep_selection == "always_visible":
        view = st.empty()
        if st.session_state.get(unique_key) is None:
            st.session_state[unique_key] = st.session_state.get(f"{unique_key}__prev_value", default)
            # params["default"] = get_default_indices(indexable_options, st.session_state.get(f"{unique_key}__prev_value", default))
        with view:
            params["default"] = None
            res: RegisterWidgetResult[Any] = st._main._button_group(**params)
            # st.session_state[f"{unique_key}__check"] = True

    elif selection_mode == "single" and keep_selection == "never_visible":
        # Valor forzado por el usuario externamente
        click_value = st.session_state.get(unique_key)
        st.session_state[unique_key] = None
        st.session_state[f"{unique_key}_nv_value"] = None
        params["default"] = None

        view = st.empty()
        if click_value is None:
            click_value = st.session_state.get(f"{unique_key}__prev_value", default)
        with view:
            res: RegisterWidgetResult[Any] = st._main._button_group(**params)
            # st.session_state[f"{unique_key}__check"] = True
            res = RegisterWidgetResult(value=click_value, value_changed=False)

    else:
        res: RegisterWidgetResult[Any] = st._main._button_group(**params)
        # st.session_state[f"{unique_key}__check"] = True

    if selection_mode == "multi":
        if RegisterWidgetResult is not Any:
            multi_res: RegisterWidgetResult[Any] = cast("RegisterWidgetResult[list[V] | list[V | str]]", res)
            multi_res = maybe_coerce_enum_sequence(
                multi_res, options, indexable_options
            )
            res = multi_res

        # st.session_state[f"{unique_key}__prev_value"] = res.value
        return cast("list[V]", res.value)

    single_res = cast("RegisterWidgetResult[V | str | None]", res)
    single_res = maybe_coerce_enum(single_res, options, indexable_options)
    res = single_res

    st.session_state[f"{unique_key}__prev_value"] = res.value
    return cast("V | None", res.value)
