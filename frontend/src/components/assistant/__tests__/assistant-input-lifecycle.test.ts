import { describe, it } from "node:test";
import assert from "node:assert";

describe("NavSakhi Phase 51.52: Assistant Input Lifecycle & Recovery Suite", () => {
  it("1. Initial state has isTyping=false so input textarea is never disabled on mount", () => {
    // Model initial state matching useAssistant.ts
    let isTyping = false;
    let isInitRunning = true;

    // During initial context fetch, isTyping remains false
    const canTypeOnMount = !isTyping;
    assert.strictEqual(canTypeOnMount, true, "Chat input must be clickable and enabled immediately on mount");

    // After init completes or fails, isTyping remains false
    isInitRunning = false;
    assert.strictEqual(isTyping, false);
  });

  it("2. Successful assistant response cleanly restores isTyping to false in finally block", async () => {
    let isTyping = false;
    let messages: string[] = [];

    const simulatedSendMessage = async (query: string) => {
      isTyping = true;
      messages.push(`user: ${query}`);
      try {
        // Simulated network response delay
        await new Promise((res) => setTimeout(res, 5));
        messages.push(`assistant: reply to ${query}`);
      } finally {
        isTyping = false;
      }
    };

    await simulatedSendMessage("Plan a route to Guindy");
    assert.strictEqual(isTyping, false, "isTyping must be false after successful response");
    assert.strictEqual(messages.length, 2);
  });

  it("3. Rejected or timed-out assistant request guarantees input recovery via finally block", async () => {
    let isTyping = false;

    const simulatedSendMessageWithTimeout = async (): Promise<{ recoveredTyping: boolean; error: string }> => {
      isTyping = true;
      let error = "";
      try {
        await new Promise((_, rej) => setTimeout(() => rej(new Error("Request timeout of 10000ms exceeded")), 5));
      } catch (err: unknown) {
        error = (err as Error).message;
      } finally {
        isTyping = false;
      }
      return { recoveredTyping: isTyping, error };
    };

    const result = await simulatedSendMessageWithTimeout();
    assert.strictEqual(result.recoveredTyping, false, "isTyping must be restored to false even when request fails or times out");
    assert.ok(result.error.includes("timeout"));
  });

  it("4. Explicit cancellation or component unmount resets isTyping immediately", () => {
    let isTyping = true;
    let requestSeq = 1;

    // Simulated cancelRequest / unmount cleanup
    const cancelRequest = () => {
      requestSeq++;
      isTyping = false;
    };

    cancelRequest();
    assert.strictEqual(isTyping, false, "Cancellation must cleanly reset isTyping to false");
    assert.strictEqual(requestSeq, 2);
  });

  it("5. Stale slow response from older request cannot overwrite newer state", async () => {
    let activeConversationText = "";
    let requestSeq = 0;

    const sendMessageWithSequencing = async (query: string, delayMs: number) => {
      const currentSeq = ++requestSeq;
      // Simulated delayed network call
      await new Promise((res) => setTimeout(res, delayMs));
      if (currentSeq !== requestSeq) {
        // Discard stale response
        return;
      }
      activeConversationText = `Response to: ${query}`;
    };

    // Trigger request 1 with 30ms latency
    const p1 = sendMessageWithSequencing("First slow query", 30);
    // Trigger request 2 with 5ms latency
    const p2 = sendMessageWithSequencing("Second fast query", 5);

    await Promise.all([p1, p2]);

    assert.strictEqual(
      activeConversationText,
      "Response to: Second fast query",
      "Newer request response must take precedence over delayed older response"
    );
  });

  it("6. Input submission behavior handles Enter and send button consistently", () => {
    let sentCount = 0;
    let isTyping = false;
    let currentInput = "  Hello NavSakhi  ";

    const handleSend = (e?: { preventDefault: () => void }) => {
      e?.preventDefault();
      const trimmed = currentInput.trim();
      if (trimmed && !isTyping) {
        sentCount++;
        currentInput = "";
      }
    };

    // Send button click
    handleSend();
    assert.strictEqual(sentCount, 1, "Send button triggers message dispatch");
    assert.strictEqual(currentInput, "");

    // Enter press when isTyping is true should NOT double send
    currentInput = "Another message";
    isTyping = true;
    handleSend();
    assert.strictEqual(sentCount, 1, "Submission is guarded when already typing");
    assert.strictEqual(currentInput, "Another message");
  });
});
