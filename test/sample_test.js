import { describe, it } from "https://deno.land/std/testing/bdd.ts";
import { expect } from "https://deno.land/std/expect/mod.ts";
import { sumar } from "./calculadora.js";

describe("calculadora", () => {
  it("debería sumar dos números", () => {
    const resultado = sumar(2, 3);
    expect(resultado).toBe(5);
  });
});