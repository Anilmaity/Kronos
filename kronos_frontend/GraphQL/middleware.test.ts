import { describe, expect, it } from "vitest";
import { isAuthFailure } from "./middleware";

describe("isAuthFailure", () => {
  it("detects an expired-signature message", () => {
    expect(isAuthFailure(new Error("Signature has expired"))).toBe(true);
  });

  it("detects the signed-in-required message", () => {
    expect(
      isAuthFailure(
        new Error("Authentication Failure : You must be signed in")
      )
    ).toBe(true);
  });

  it("detects auth messages joined N times by Apollo", () => {
    expect(
      isAuthFailure(
        new Error("Signature has expired\nSignature has expired")
      )
    ).toBe(true);
  });

  it("detects auth messages inside graphQLErrors", () => {
    const err = {
      message: "combined message",
      graphQLErrors: [
        { message: "Something else" },
        { message: "Authentication Failure : You must be signed in" },
      ],
    };
    expect(isAuthFailure(err)).toBe(true);
  });

  it("rejects unrelated errors", () => {
    expect(isAuthFailure(new Error("Network request failed"))).toBe(false);
    expect(isAuthFailure({ message: "Some GraphQL validation error" })).toBe(
      false
    );
  });

  it("handles malformed error shapes without throwing", () => {
    expect(isAuthFailure({})).toBe(false);
    expect(isAuthFailure(null)).toBe(false);
    expect(isAuthFailure(undefined)).toBe(false);
    expect(isAuthFailure({ graphQLErrors: [{}] })).toBe(false);
  });
});
