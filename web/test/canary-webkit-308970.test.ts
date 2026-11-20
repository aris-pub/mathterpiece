import { describe, expect, it } from "vitest";

// On iOS 26 (Safari 26), getScreenCTM() leaves out CSS transforms on the elements around an SVG
// (WebKit bug 308970, fixed in Safari 27), so the runtime measures where three points are drawn
// instead (mtp-fuy1). This test fails on the date below, about a year after iOS 27 ships, so that
// someone checks whether readers still use iOS 26 and removes the measuring if few do. Bead mtp-wtgr.
const REVIEW = new Date("2027-09-01T00:00:00Z");

describe("WebKit 308970 workaround", () => {
  it("is reviewed before its date", () => {
    expect(
      Date.now() < REVIEW.getTime(),
      "WebKit 308970 workaround: check how many readers still use iOS 26, and remove the measuring of drawn points in web/src/elements.ts and web/src/svg.ts if few do (mtp-fuy1).",
    ).toBe(true);
  });
});
