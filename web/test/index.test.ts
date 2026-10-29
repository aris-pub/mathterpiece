import { describe, expect, it } from "vitest";
import "../src/index.ts";

describe("loading the runtime", () => {
  it("registers the elements", () => {
    expect(customElements.get("mtp-model")).toBeDefined();
    expect(customElements.get("mtp-canvas")).toBeDefined();
  });
});
