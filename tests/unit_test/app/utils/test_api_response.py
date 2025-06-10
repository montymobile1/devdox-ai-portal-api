from pydantic import BaseModel, Field

from app.utils.api_response import serialize_api_response_data


class TestSerializeApiResponseData:
    class PydanticTemporarySchema(BaseModel):
        id: str = Field(..., description="Pydantic Id")
        name: str = Field(..., description="Pydantic name")

    def test_single_pydantic_base_model_instance(self):
        single_model = self.PydanticTemporarySchema(id="1", name="Test")
        serialized = serialize_api_response_data(data=single_model)
        assert isinstance(serialized, dict)
        assert serialized == {"id": "1", "name": "Test"}

    def test_list_pydantic_base_model_instance(self):
        model_list = [
            self.PydanticTemporarySchema(id=str(i), name=f"Test {i}")
            for i in range(3)
        ]
        serialized = serialize_api_response_data(data=model_list)
        assert isinstance(serialized, list)
        assert all(isinstance(item, dict) for item in serialized)
        assert serialized == [
            {"id": "0", "name": "Test 0"},
            {"id": "1", "name": "Test 1"},
            {"id": "2", "name": "Test 2"},
        ]

    def test_nested_level_1_list_pydantic_base_model_instance(self):
        model_list_1 = [
            self.PydanticTemporarySchema(id=str(i), name=f"Test {i}")
            for i in range(3)
        ]

        model_list_2 = [
            self.PydanticTemporarySchema(id=str(i), name=f"Test 2 {i}")
            for i in range(3)
        ]

        serialized = serialize_api_response_data(
            data={
                "total": len(model_list_1) + len(model_list_2),
                "models_1": model_list_1,
                "models_2": model_list_2
            }
        )

        assert serialized == {
            "total": len(model_list_1) + len(model_list_2),
            "models_1": [
                {"id": "0", "name": "Test 0"},
                {"id": "1", "name": "Test 1"},
                {"id": "2", "name": "Test 2"},
            ],
            "models_2": [
                {"id": "0", "name": "Test 2 0"},
                {"id": "1", "name": "Test 2 1"},
                {"id": "2", "name": "Test 2 2"},
            ]
        }

    def test_nested_level_1_single_pydantic_base_model_instance(self):
        single_model_1 = self.PydanticTemporarySchema(id="1", name="Test")
        single_model_2 = self.PydanticTemporarySchema(id="1", name="Test 2")

        serialized = serialize_api_response_data(data={"total": 2, "models_1": single_model_1, "models_2": single_model_2})

        assert serialized == {
            "total": 2,
            "models_1": {"id": "1", "name": "Test"},
            "models_2": {"id": "1", "name": "Test 2"},
        }

    def test_nested_level_1_mixed_pydantic_base_model_instance(self):
        model_list_1 = [
            self.PydanticTemporarySchema(id=str(i), name=f"Test {i}") for i in range(3)
        ]

        model_list_2 = [
            self.PydanticTemporarySchema(id=str(i), name=f"Test 2 {i}")
            for i in range(3)
        ]

        single_model_1 = self.PydanticTemporarySchema(id="1", name="Test")
        single_model_2 = self.PydanticTemporarySchema(id="1", name="Test 2")

        serialized = serialize_api_response_data(
            data={
                "total": 2 + len(model_list_1) + len(model_list_2),
                "single_model_1": single_model_1,
                "single_model_2": single_model_2,
                "list_model_1": model_list_1,
                "list_model_2": model_list_2,
            }
        )

        assert serialized == {
            "total": 2 + len(model_list_1) + len(model_list_2),
            "single_model_1": {"id": "1", "name": "Test"},
            "single_model_2": {"id": "1", "name": "Test 2"},
            "list_model_1": [
                {"id": "0", "name": "Test 0"},
                {"id": "1", "name": "Test 1"},
                {"id": "2", "name": "Test 2"},
            ],
            "list_model_2": [
                {"id": "0", "name": "Test 2 0"},
                {"id": "1", "name": "Test 2 1"},
                {"id": "2", "name": "Test 2 2"},
            ],
        }
    
    