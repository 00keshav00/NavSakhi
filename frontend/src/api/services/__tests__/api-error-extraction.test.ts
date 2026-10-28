import test, { describe, it } from "node:test";
import assert from "node:assert/strict";
import { extractApiErrorMessage } from "../../client.ts";

describe("NavSakhi Phase 51.34: Frontend API Error Message Extraction Suite", () => {
  it("1. FastAPI HTTP 422 response with a string 'detail' returns that descriptive message", () => {
    const error = {
      name: "AxiosError",
      message: "Request failed with status code 422",
      response: {
        status: 422,
        data: {
          detail: "Could not find source location 'InvalidPlaceX1Y2Z3NonExistent'. Please verify the place name or select a verified place from suggestions."
        }
      }
    };

    const result = extractApiErrorMessage(error, "Fallback message");
    assert.equal(
      result,
      "Could not find source location 'InvalidPlaceX1Y2Z3NonExistent'. Please verify the place name or select a verified place from suggestions."
    );
  });

  it("2. Nested error envelope (error.response.data.error.message) remains supported", () => {
    const error = {
      name: "AxiosError",
      message: "Request failed with status code 400",
      response: {
        status: 400,
        data: {
          success: false,
          error: {
            code: "VALIDATION_ERROR",
            message: "Source and destination are required.",
            details: {}
          }
        }
      }
    };

    const result = extractApiErrorMessage(error, "Fallback message");
    assert.equal(result, "Source and destination are required.");
  });

  it("3. Top-level response message (error.response.data.message) remains supported", () => {
    const error = {
      name: "AxiosError",
      message: "Request failed with status code 500",
      response: {
        status: 500,
        data: {
          message: "Internal server error occurred while computing routes."
        }
      }
    };

    const result = extractApiErrorMessage(error, "Fallback message");
    assert.equal(result, "Internal server error occurred while computing routes.");
  });

  it("4. Normal JavaScript/Axios error message is used as fallback when response data has no custom messages", () => {
    const error = new Error("Network timeout while contacting backend service");

    const result = extractApiErrorMessage(error, "Fallback message");
    assert.equal(result, "Network timeout while contacting backend service");
  });

  it("5. Missing or malformed error data produces the user-friendly fallback", () => {
    assert.equal(extractApiErrorMessage(null, "Safe fallback"), "Safe fallback");
    assert.equal(extractApiErrorMessage(undefined, "Safe fallback"), "Safe fallback");
    assert.equal(extractApiErrorMessage({}, "Safe fallback"), "Safe fallback");
    assert.equal(
      extractApiErrorMessage({ response: { data: { detail: {} } } }, "Safe fallback"),
      "Safe fallback"
    );
    assert.equal(
      extractApiErrorMessage({ response: { data: { detail: "   " } } }, "Safe fallback"),
      "Safe fallback"
    );
    assert.equal(
      extractApiErrorMessage({ message: "[object Object]" }, "Safe fallback"),
      "Safe fallback"
    );
  });

  it("6. Journey-planning error path extracts descriptive detail instead of generic 422 Axios text", () => {
    const axios422Error = {
      name: "AxiosError",
      message: "Request failed with status code 422",
      response: {
        status: 422,
        data: {
          detail: "Cannot determine source location from 'detecting...'. Please provide coordinates (latitude, longitude) or select a verified place."
        }
      }
    };

    // Before this fix: (axios422Error as Error).message would yield "Request failed with status code 422"
    assert.equal((axios422Error as Error).message, "Request failed with status code 422");

    // After this fix: extractApiErrorMessage extracts the actionable server guidance
    const extracted = extractApiErrorMessage(
      axios422Error,
      "An unexpected error occurred while planning your journey."
    );
    assert.equal(
      extracted,
      "Cannot determine source location from 'detecting...'. Please provide coordinates (latitude, longitude) or select a verified place."
    );
    assert.notEqual(extracted, "Request failed with status code 422");
  });

  it("7. FastAPI Pydantic validation error array is formatted into readable message", () => {
    const pydanticError = {
      name: "AxiosError",
      message: "Request failed with status code 422",
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ["body", "source"], msg: "Field required", type: "value_error.missing" },
            { loc: ["body", "destination"], msg: "Field required", type: "value_error.missing" }
          ]
        }
      }
    };

    const extracted = extractApiErrorMessage(pydanticError, "Fallback");
    assert.equal(extracted, "source: Field required; destination: Field required");
  });
});
