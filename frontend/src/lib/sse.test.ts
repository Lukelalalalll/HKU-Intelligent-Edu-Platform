import { describe, expect, it } from "vitest";
import { consumeSse } from "./apiClient";

function streamFrom(chunks: string[]) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
}

describe("consumeSse", () => {
  it("joins split frames and supports multi-line data", async () => {
    const events: unknown[] = [];
    const response = new Response(streamFrom(["data: {\"type\":\n", "data: \"chunk\", \"value\": \"value\"}\n\n", "data: {\"type\":\"complete\"}\n\n"]), { status: 200 });
    await consumeSse(response, (event) => events.push(event));
    expect(events).toEqual([{ type: "chunk", "value": "value" }, { type: "complete" }]);
  });

  it("ignores malformed frames and still consumes later events", async () => {
    const events: unknown[] = [];
    const response = new Response(streamFrom(["data: broken\n\n", "data: {\"ok\":true}\n\n"]), { status: 200 });
    await consumeSse(response, (event) => events.push(event));
    expect(events).toEqual([{ ok: true }]);
  });
});
