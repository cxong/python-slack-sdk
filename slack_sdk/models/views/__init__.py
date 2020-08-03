import copy
import logging
from typing import List, Optional, Union, Dict

from slack_sdk.models.basic_objects import JsonObject, JsonValidator
from slack_sdk.models.block_kit import Block, TextObject, PlainTextObject, Option


class View(JsonObject):
    """View object for modals and Home tabs.

    https://api.slack.com/reference/surfaces/views
    """

    types = ["modal", "home"]

    attributes = {
        "type",
        "id",
        "callback_id",
        "external_id",
        "team_id",
        "bot_id",
        "app_id",
        "root_view_id",
        "previous_view_id",
        "title",
        "submit",
        "close",
        "blocks",
        "private_metadata",
        "state",
        "hash",
        "clear_on_close",
        "notify_on_close",
    }

    def __init__(
        self,
        type: str,  # "modal", "home"
        id: Optional[str] = None,
        callback_id: Optional[str] = None,
        external_id: Optional[str] = None,
        team_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        app_id: Optional[str] = None,
        root_view_id: Optional[str] = None,
        previous_view_id: Optional[str] = None,
        title: Union[str, dict, PlainTextObject] = None,
        submit: Optional[Union[str, dict, PlainTextObject]] = None,
        close: Optional[Union[str, dict, PlainTextObject]] = None,
        blocks: List[Union[dict, Block]] = [],
        private_metadata: Optional[str] = None,
        state: Optional[Union[dict, "ViewState"]] = None,
        hash: Optional[str] = None,
        clear_on_close: Optional[bool] = None,
        notify_on_close: Optional[bool] = None,
        **kwargs,
    ):
        self.type = type
        self.id = id
        self.callback_id = callback_id
        self.external_id = external_id
        self.team_id = team_id
        self.bot_id = bot_id
        self.app_id = app_id
        self.root_view_id = root_view_id
        self.previous_view_id = previous_view_id
        self.title = TextObject.parse(title, default_type=PlainTextObject.type)
        self.submit = TextObject.parse(submit, default_type=PlainTextObject.type)
        self.close = TextObject.parse(close, default_type=PlainTextObject.type)
        self.blocks = Block.parse_all(blocks)
        self.private_metadata = private_metadata
        self.state = state
        self.hash = hash
        self.clear_on_close = clear_on_close
        self.notify_on_close = notify_on_close
        self.additional_attributes = kwargs

    title_max_length = 24
    blocks_max_length = 100
    close_max_length = 24
    submit_max_length = 24
    private_metadata_max_length = 3000
    callback_id_max_length: int = 255

    @JsonValidator('type must be either "modal" or "home"')
    def _validate_type(self):
        return self.type is not None and self.type in self.types

    @JsonValidator(f"title must be between 1 and {title_max_length} characters")
    def _validate_title_length(self):
        return self.title is None or 1 <= len(self.title.text) <= self.title_max_length

    @JsonValidator(f"views must contain between 1 and {blocks_max_length} blocks")
    def _validate_blocks_length(self):
        return self.blocks is None or 0 < len(self.blocks) <= self.blocks_max_length

    @JsonValidator("home view cannot have input blocks")
    def _validate_input_blocks(self):
        return self.type == "modal" or (
            self.type == "home"
            and len([b for b in self.blocks if b.type == "input"]) == 0
        )

    @JsonValidator("home view cannot have submit and close")
    def _validate_home_tab_structure(self):
        return self.type != "home" or (
            self.type == "home" and self.close is None and self.submit is None
        )

    @JsonValidator(f"close cannot exceed {close_max_length} characters")
    def _validate_close_length(self):
        return self.close is None or len(self.close.text) <= self.close_max_length

    @JsonValidator(f"submit cannot exceed {submit_max_length} characters")
    def _validate_submit_length(self):
        return self.submit is None or len(self.submit.text) <= int(
            self.submit_max_length
        )

    @JsonValidator(
        f"private_metadata cannot exceed {private_metadata_max_length} characters"
    )
    def _validate_private_metadata_max_length(self):
        return (
            self.private_metadata is None
            or len(self.private_metadata) <= self.private_metadata_max_length
        )

    @JsonValidator(f"callback_id cannot exceed {callback_id_max_length} characters")
    def _validate_callback_id_max_length(self):
        return (
            self.callback_id is None
            or len(self.callback_id) <= self.callback_id_max_length
        )

    def __str__(self):
        return str(self.get_non_null_attributes())

    def __repr__(self):
        return self.__str__()


class ViewState(JsonObject):
    attributes = {"values"}
    logger = logging.getLogger(__name__)

    @classmethod
    def _show_warning_about_unknown(self, value):
        c = value.__class__
        name = ".".join([c.__module__, c.__name__])
        self.logger.warning(
            f"Unknown type for view.state.values detected ({name}) and ViewState skipped to add it"
        )

    def __init__(
        self, *, values: Dict[str, Dict[str, Union[dict, "ViewStateValue"]]],
    ):
        value_objects: Dict[str, Dict[str, ViewStateValue]] = {}
        new_state_values = copy.copy(values)
        for block_id, actions in new_state_values.items():
            if actions is None:
                continue
            elif isinstance(actions, dict):
                new_actions = copy.copy(actions)
                for action_id, v in actions.items():
                    if isinstance(v, dict):
                        d = copy.copy(v)
                        value_object = ViewStateValue(**d)
                    elif isinstance(v, ViewStateValue):
                        value_object = v
                    else:
                        self._show_warning_about_unknown(v)
                        continue
                    new_actions[action_id] = value_object
                value_objects[block_id] = new_actions
            else:
                self._show_warning_about_unknown(v)
        self.values = value_objects

    def to_dict(self, *args) -> Dict[str, Dict[str, Dict[str, dict]]]:
        self.validate_json()
        if self.values:
            dict_values = {}
            for block_id, actions in self.values.items():
                if actions:
                    dict_value: Dict[str, dict] = {
                        action_id: value.to_dict()
                        for action_id, value in actions.items()
                    }
                    dict_values[block_id] = dict_value
            return {"values": dict_values}
        else:
            return {}


class ViewStateValue(JsonObject):
    attributes = {
        "type",
        "value",
        "selected_date",
        "selected_conversation",
        "selected_channel",
        "selected_user",
        "selected_option",
        "selected_conversations",
        "selected_channels",
        "selected_users",
        "selected_options",
    }

    def __init__(
        self,
        *,
        type: Optional[str] = None,
        value: Optional[str] = None,
        selected_date: Optional[str] = None,
        selected_conversation: Optional[str] = None,
        selected_channel: Optional[str] = None,
        selected_user: Optional[str] = None,
        selected_option: Optional[str] = None,
        selected_conversations: Optional[List[str]] = None,
        selected_channels: Optional[List[str]] = None,
        selected_users: Optional[List[str]] = None,
        selected_options: Optional[List[Union[dict, Option]]] = None,
    ):
        self.type = type
        self.value = value
        self.selected_date = selected_date
        self.selected_conversation = selected_conversation
        self.selected_channel = selected_channel
        self.selected_user = selected_user
        self.selected_option = selected_option
        self.selected_conversations = selected_conversations
        self.selected_channels = selected_channels
        self.selected_users = selected_users
        if selected_options:
            if isinstance(selected_options, dict):
                self.selected_options = [Option(**d) for d in selected_options]
            else:
                self.selected_options = selected_options
