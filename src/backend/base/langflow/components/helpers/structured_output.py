from typing import cast

from pydantic import BaseModel, Field, create_model

from langflow.base.models.chat_result import get_chat_result
from langflow.custom import Component
from langflow.field_typing.constants import LanguageModel
from langflow.helpers.base_model import build_model_from_schema
from langflow.io import BoolInput, HandleInput, MessageTextInput, Output, StrInput, TableInput
from langflow.schema.data import Data


class StructuredOutputComponent(Component):
    display_name = "Structured Output"
    description = "A component for structured output."

    inputs = [
        HandleInput(
            name="llm",
            display_name="Language Model",
            info="The language model to use to generate the structured output.",
            input_types=["LanguageModel"],
        ),
        MessageTextInput(name="input_value", display_name="Input message"),
        StrInput(
            name="schema_name",
            display_name="Schema Name",
            info="Provide a name for the output data schema.",
        ),
        TableInput(
            name="output_schema",
            display_name="Output Schema",
            info="Define the structure and data types for the model's output.",
            table_schema=[
                {
                    "name": "name",
                    "display_name": "Name",
                    "type": "str",
                    "description": "Specify the name of the output field.",
                },
                {
                    "name": "description",
                    "display_name": "Description",
                    "type": "str",
                    "description": "Describe the purpose of the output field.",
                },
                {
                    "name": "type",
                    "display_name": "Type",
                    "type": "str",
                    "description": (
                        "Indicate the data type of the output field " "(e.g., str, int, float, bool, list, dict)."
                    ),
                },
                {
                    "name": "multiple",
                    "display_name": "Multiple",
                    "type": "bool",
                    "description": "Set to True if this output field should be a list of the specified type.",
                },
            ],
        ),
        BoolInput(
            name="multiple",
            display_name="Generate Multiple",
            info="Set to True if the model should generate a list of outputs instead of a single output.",
        ),
    ]

    outputs = [
        Output(name="structured_output", display_name="Structured Output", method="build_structured_output"),
    ]

    def build_structured_output(self) -> Data:
        if not hasattr(self.llm, "with_structured_output"):
            msg = "Language model does not support structured output."
            raise TypeError(msg)
        if not self.output_schema:
            msg = "Output schema cannot be empty"
            raise ValueError(msg)

        _output_model = build_model_from_schema(self.output_schema)
        if self.multiple:
            output_model = create_model(
                self.schema_name,
                objects=(list[_output_model], Field(description=f"A list of {self.schema_name}.")),  # type: ignore
            )
        else:
            output_model = _output_model
        llm_with_structured_output = cast(
            LanguageModel, self.llm.with_structured_output(schema=output_model, method="json_schema")
        )
        config_dict = {
            "run_name": self.display_name,
            "project_name": self.get_project_name(),
            "callbacks": self.get_langchain_callbacks(),
        }
        output = get_chat_result(runnable=llm_with_structured_output, input_value=self.input_value, config=config_dict)
        if isinstance(output, BaseModel):
            output_dict = output.model_dump()
        else:
            msg = "Output is not a BaseModel."
            raise ValueError(msg)
        return Data(data=output_dict)
