import json
import tempfile
import unittest
from pathlib import Path

from crud_generator.parsing import DefinitionError
from crud_generator.stream_schema import load_stream_definition


VALID_DEFINITION = {
    "project": "sales-streams",
    "package": "com.example.sales",
    "input": {
        "topic": "orders-topic1",
        "event": "Order",
        "fields": [
            {"name": "order_id", "type": "string"},
            {"name": "customer_id", "type": "string"},
            {"name": "amount", "type": "double"},
        ],
    },
    "output": {"topic": "total-sales-topic1", "event": "OrderWithTotal"},
    "processing": {
        "group_by_field": "customer_id",
        "aggregate_field": "amount",
        "aggregate_as": "total_amount",
        "filter_field": "amount",
        "filter_operator": ">",
        "filter_value": 10,
    },
}


def _write_definition(overrides=None, remove=None):
    definition = json.loads(json.dumps(VALID_DEFINITION))
    if remove:
        for key_path in remove:
            target = definition
            for key in key_path[:-1]:
                target = target[key]
            del target[key_path[-1]]
    if overrides:
        for key_path, value in overrides.items():
            target = definition
            for key in key_path[:-1]:
                target = target[key]
            target[key_path[-1]] = value
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(definition, tmp)
    tmp.close()
    return tmp.name


class LoadStreamDefinitionTest(unittest.TestCase):
    def test_loads_a_valid_definition(self):
        path = _write_definition()
        definition = load_stream_definition(path)

        self.assertEqual("sales-streams", definition["project"])
        self.assertEqual("com.example.sales", definition["package"])
        self.assertEqual("orders-topic1", definition["input_topic"])
        self.assertEqual("Order", definition["input_event"])
        self.assertEqual(3, len(definition["input_fields"]))
        self.assertEqual("total-sales-topic1", definition["output_topic"])
        self.assertEqual("OrderWithTotal", definition["output_event"])
        self.assertEqual("customer_id", definition["group_by_field"])
        self.assertEqual("amount", definition["aggregate_field"])
        self.assertEqual("total_amount", definition["aggregate_as"])
        self.assertEqual("amount", definition["filter_field"])
        self.assertEqual(">", definition["filter_operator"])
        self.assertEqual(10, definition["filter_value"])

    def test_filters_are_optional(self):
        path = _write_definition(
            remove=[
                ["processing", "filter_field"],
                ["processing", "filter_operator"],
                ["processing", "filter_value"],
            ]
        )
        definition = load_stream_definition(path)

        self.assertIsNone(definition["filter_field"])
        self.assertIsNone(definition["filter_operator"])
        self.assertIsNone(definition["filter_value"])

    def test_rejects_partial_filter_keys(self):
        path = _write_definition(remove=[["processing", "filter_operator"]])

        with self.assertRaises(DefinitionError) as ctx:
            load_stream_definition(path)

        self.assertIn("filter_field", str(ctx.exception))

    def test_rejects_unknown_top_level_keys(self):
        path = _write_definition(overrides={("extra",): True})

        with self.assertRaises(DefinitionError) as ctx:
            load_stream_definition(path)

        self.assertIn("Claves desconocidas", str(ctx.exception))

    def test_rejects_invalid_project_name(self):
        path = _write_definition(overrides={("project",): "Sales_Streams"})

        with self.assertRaises(DefinitionError):
            load_stream_definition(path)

    def test_rejects_group_by_field_not_in_input_fields(self):
        path = _write_definition(overrides={("processing", "group_by_field"): "missing"})

        with self.assertRaises(DefinitionError) as ctx:
            load_stream_definition(path)

        self.assertIn("group_by_field", str(ctx.exception))

    def test_rejects_non_string_group_by_field(self):
        path = _write_definition(overrides={("processing", "group_by_field"): "amount"})

        with self.assertRaises(DefinitionError) as ctx:
            load_stream_definition(path)

        self.assertIn("tipo 'string'", str(ctx.exception))

    def test_rejects_non_double_aggregate_field(self):
        path = _write_definition(overrides={("processing", "aggregate_field"): "order_id"})

        with self.assertRaises(DefinitionError) as ctx:
            load_stream_definition(path)

        self.assertIn("tipo 'double'", str(ctx.exception))

    def test_rejects_aggregate_as_colliding_with_input_field(self):
        path = _write_definition(overrides={("processing", "aggregate_as"): "amount"})

        with self.assertRaises(DefinitionError):
            load_stream_definition(path)

    def test_rejects_output_event_equal_to_input_event(self):
        path = _write_definition(overrides={("output", "event"): "Order"})

        with self.assertRaises(DefinitionError):
            load_stream_definition(path)

    def test_rejects_invalid_topic_name(self):
        path = _write_definition(overrides={("input", "topic"): "not a topic!"})

        with self.assertRaises(DefinitionError):
            load_stream_definition(path)

    def test_rejects_non_numeric_filter_field(self):
        path = _write_definition(overrides={("processing", "filter_field"): "order_id"})

        with self.assertRaises(DefinitionError):
            load_stream_definition(path)

    def test_rejects_unknown_field_type(self):
        path = _write_definition(
            overrides={("input", "fields"): [{"name": "order_id", "type": "uuid"}]}
        )

        with self.assertRaises(DefinitionError):
            load_stream_definition(path)

    def test_rejects_missing_file(self):
        with self.assertRaises(DefinitionError):
            load_stream_definition(str(Path(tempfile.gettempdir()) / "does-not-exist.json"))

    def test_passthrough_mode_when_processing_is_absent(self):
        path = _write_definition(remove=[["processing"]])
        definition = load_stream_definition(path)

        self.assertIsNone(definition["group_by_field"])
        self.assertIsNone(definition["aggregate_field"])
        self.assertIsNone(definition["aggregate_as"])

    def test_passthrough_mode_when_processing_has_no_aggregation_keys(self):
        path = _write_definition(
            remove=[
                ["processing", "group_by_field"],
                ["processing", "aggregate_field"],
                ["processing", "aggregate_as"],
            ]
        )
        definition = load_stream_definition(path)

        self.assertIsNone(definition["group_by_field"])
        # El filtro sigue siendo independiente de la agregacion.
        self.assertEqual("amount", definition["filter_field"])

    def test_rejects_partial_aggregation_keys(self):
        path = _write_definition(remove=[["processing", "aggregate_as"]])

        with self.assertRaises(DefinitionError) as ctx:
            load_stream_definition(path)

        self.assertIn("group_by_field", str(ctx.exception))

    def test_rejects_invalid_json(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp.write("{not valid json")
        tmp.close()

        with self.assertRaises(DefinitionError):
            load_stream_definition(tmp.name)


if __name__ == "__main__":
    unittest.main()
