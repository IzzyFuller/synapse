"""Tests for error models (ErrorInfo, ErrorDetails)."""

from synapse.models.error import ErrorInfo, ErrorDetails


class TestErrorDetails:
    """Test ErrorDetails model."""

    def test_create_error_details_with_all_fields(self):
        """Can create ErrorDetails with all optional fields populated."""
        details = ErrorDetails(
            file_path="/path/to/file.pdf",
            error_code="FILE_404",
            stack_trace="Traceback: ...\n  File main.py, line 42",
        )

        assert details.file_path == "/path/to/file.pdf"
        assert details.error_code == "FILE_404"
        assert details.stack_trace == "Traceback: ...\n  File main.py, line 42"

    def test_create_error_details_with_no_fields(self):
        """Can create ErrorDetails with all fields as None (all are optional)."""
        details = ErrorDetails()

        assert details.file_path is None
        assert details.error_code is None
        assert details.stack_trace is None

    def test_create_error_details_with_partial_fields(self):
        """Can create ErrorDetails with only some fields populated."""
        details = ErrorDetails(error_code="TIMEOUT", file_path="/path/to/doc.pdf")

        assert details.error_code == "TIMEOUT"
        assert details.file_path == "/path/to/doc.pdf"
        assert details.stack_trace is None

    def test_error_details_serializes_to_camel_case(self):
        """ErrorDetails should serialize field names to camelCase."""
        details = ErrorDetails(file_path="/test.pdf", error_code="ERR_001", stack_trace="trace")

        data = details.model_dump(by_alias=True)

        assert data == {"filePath": "/test.pdf", "errorCode": "ERR_001", "stackTrace": "trace"}

    def test_error_details_parses_from_camel_case_json(self):
        """ErrorDetails should parse from camelCase JSON."""
        json_data = '{"filePath": "/doc.pdf", "errorCode": "E123"}'
        details = ErrorDetails.model_validate_json(json_data)

        assert details.file_path == "/doc.pdf"
        assert details.error_code == "E123"
        assert details.stack_trace is None

    def test_error_details_exclude_none_on_serialization(self):
        """When serializing with exclude_none, only populated fields appear."""
        details = ErrorDetails(error_code="PARSE_ERROR")

        data = details.model_dump(by_alias=True, exclude_none=True)

        assert data == {"errorCode": "PARSE_ERROR"}
        assert "filePath" not in data
        assert "stackTrace" not in data


class TestErrorInfo:
    """Test ErrorInfo model."""

    def test_create_error_info_minimal(self):
        """Can create ErrorInfo with just type and message (details optional)."""
        error = ErrorInfo(type="validation_error", message="Invalid input")

        assert error.type == "validation_error"
        assert error.message == "Invalid input"
        assert error.details is None

    def test_create_error_info_with_details(self):
        """Can create ErrorInfo with nested ErrorDetails."""
        details = ErrorDetails(file_path="/file.pdf", error_code="NOT_FOUND")
        error = ErrorInfo(type="file_not_found", message="File does not exist", details=details)

        assert error.type == "file_not_found"
        assert error.message == "File does not exist"
        assert error.details is not None
        assert error.details.file_path == "/file.pdf"
        assert error.details.error_code == "NOT_FOUND"

    def test_error_info_serializes_to_camel_case(self):
        """ErrorInfo should serialize to camelCase (details is already camelCase)."""
        error = ErrorInfo(type="timeout", message="Request timed out")

        data = error.model_dump(by_alias=True)

        # type and message don't have underscores, so they stay the same
        # details is also already camelCase
        assert data == {"type": "timeout", "message": "Request timed out", "details": None}

    def test_error_info_with_nested_details_serializes_correctly(self):
        """ErrorInfo with nested ErrorDetails should serialize nested object to camelCase."""
        error = ErrorInfo(
            type="processing_error",
            message="Failed to process",
            details=ErrorDetails(
                file_path="/test.pdf", error_code="PROC_ERR", stack_trace="Stack: ..."
            ),
        )

        data = error.model_dump(by_alias=True)

        assert data == {
            "type": "processing_error",
            "message": "Failed to process",
            "details": {
                "filePath": "/test.pdf",
                "errorCode": "PROC_ERR",
                "stackTrace": "Stack: ...",
            },
        }

    def test_error_info_parses_from_camel_case_json(self):
        """ErrorInfo should parse from camelCase JSON with nested details."""
        json_data = """
        {
            "type": "file_error",
            "message": "Could not read file",
            "details": {
                "filePath": "/missing.pdf",
                "errorCode": "404"
            }
        }
        """
        error = ErrorInfo.model_validate_json(json_data)

        assert error.type == "file_error"
        assert error.message == "Could not read file"
        assert error.details is not None
        assert error.details.file_path == "/missing.pdf"
        assert error.details.error_code == "404"

    def test_error_info_round_trip_serialization(self):
        """ErrorInfo should round-trip through JSON serialization correctly."""
        original = ErrorInfo(
            type="validation",
            message="Schema mismatch",
            details=ErrorDetails(error_code="SCHEMA_001"),
        )

        # Serialize to JSON
        json_str = original.model_dump_json(by_alias=True)

        # Deserialize back
        restored = ErrorInfo.model_validate_json(json_str)

        assert restored.type == original.type
        assert restored.message == original.message
        assert restored.details is not None
        assert restored.details.error_code == original.details.error_code

    def test_error_info_exclude_none_excludes_empty_details(self):
        """Serializing with exclude_none should omit the details field when None."""
        error = ErrorInfo(type="warn", message="Warning occurred")

        data = error.model_dump(by_alias=True, exclude_none=True)

        assert data == {"type": "warn", "message": "Warning occurred"}
        assert "details" not in data

    def test_error_info_with_complex_stack_trace(self):
        """ErrorInfo should handle multi-line stack traces correctly."""
        stack = """Traceback (most recent call last):
  File "main.py", line 10, in process
    raise ValueError("Bad value")
ValueError: Bad value"""

        error = ErrorInfo(
            type="runtime_error",
            message="Unexpected error",
            details=ErrorDetails(stack_trace=stack),
        )

        # Verify stack trace preserved correctly
        assert error.details is not None
        assert error.details.stack_trace == stack

        # Verify JSON serialization preserves newlines
        json_str = error.model_dump_json(by_alias=True)
        restored = ErrorInfo.model_validate_json(json_str)

        assert restored.details is not None
        assert restored.details.stack_trace == stack
