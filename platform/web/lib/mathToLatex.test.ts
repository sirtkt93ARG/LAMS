import test from "node:test";
import assert from "node:assert/strict";
import { mathToLatex } from "./mathToLatex.ts";

test("multiplicación, potencias y fracciones", () => {
  assert.equal(mathToLatex("1500+200*n"), "1500+200 \\cdot n");
  assert.equal(mathToLatex("2^3"), "2^{3}");
  assert.equal(mathToLatex("3/4"), "\\frac{3}{4}");
  assert.equal(mathToLatex("1,5n"), "1{,}5n");
});

test("limita el largo y quita signos de pesos", () => {
  assert.ok(mathToLatex("x".repeat(500)).length <= 80);
  assert.equal(mathToLatex("$100"), "100");
});
