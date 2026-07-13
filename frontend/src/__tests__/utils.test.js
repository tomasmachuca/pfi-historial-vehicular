import { describe, it, expect } from "vitest";
import { calcularScore } from "../utils.js";

describe("calcularScore", () => {
  it("devuelve 100 para un vehiculo 0km", () => {
    expect(calcularScore(0, 0)).toBe(100);
  });

  it("devuelve 100 cuando cumple los servicios esperados", () => {
    expect(calcularScore(5, 5)).toBe(100);
  });

  it("penaliza proporcionalmente cuando faltan servicios", () => {
    expect(calcularScore(1, 4)).toBe(25);
  });
});
