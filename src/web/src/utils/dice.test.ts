import { computeOutcome, parseDiceFormula, rollDice } from "./dice";

describe("parseDiceFormula", () => {
  describe("basic dice notation", () => {
    it("parses 2d6 correctly", () => {
      const result = parseDiceFormula("2d6");
      expect(result.count).toBe(2);
      expect(result.sides).toBe(6);
      expect(result.keep).toBeUndefined();
    });

    it("parses 3d6 correctly", () => {
      const result = parseDiceFormula("3d6");
      expect(result.count).toBe(3);
      expect(result.sides).toBe(6);
      expect(result.keep).toBeUndefined();
    });

    it("handles case insensitive notation", () => {
      const result1 = parseDiceFormula("3D6");
      const result2 = parseDiceFormula("3d6KH2");
      expect(result1.count).toBe(3);
      expect(result1.sides).toBe(6);
      expect(result2.keep?.type).toBe("highest");
    });
  });

  describe("advantage (keep highest)", () => {
    it("parses 3d6kh2 correctly", () => {
      const result = parseDiceFormula("3d6kh2");
      expect(result.count).toBe(3);
      expect(result.sides).toBe(6);
      expect(result.keep?.type).toBe("highest");
      expect(result.keep?.count).toBe(2);
    });

    it("parses 4d6kh2 correctly", () => {
      const result = parseDiceFormula("4d6kh2");
      expect(result.count).toBe(4);
      expect(result.sides).toBe(6);
      expect(result.keep?.type).toBe("highest");
      expect(result.keep?.count).toBe(2);
    });

    it("parses 3d6kh3 correctly", () => {
      const result = parseDiceFormula("3d6kh3");
      expect(result.count).toBe(3);
      expect(result.sides).toBe(6);
      expect(result.keep?.type).toBe("highest");
      expect(result.keep?.count).toBe(3);
    });
  });

  describe("disadvantage (keep lowest)", () => {
    it("parses 3d6kl2 correctly", () => {
      const result = parseDiceFormula("3d6kl2");
      expect(result.count).toBe(3);
      expect(result.sides).toBe(6);
      expect(result.keep?.type).toBe("lowest");
      expect(result.keep?.count).toBe(2);
    });

    it("parses 4d6kl2 correctly", () => {
      const result = parseDiceFormula("4d6kl2");
      expect(result.count).toBe(4);
      expect(result.sides).toBe(6);
      expect(result.keep?.type).toBe("lowest");
      expect(result.keep?.count).toBe(2);
    });

    it("parses 3d6kl3 correctly", () => {
      const result = parseDiceFormula("3d6kl3");
      expect(result.count).toBe(3);
      expect(result.sides).toBe(6);
      expect(result.keep?.type).toBe("lowest");
      expect(result.keep?.count).toBe(3);
    });
  });

  describe("edge cases and error handling", () => {
    it("returns default 2d6 for empty string", () => {
      const result = parseDiceFormula("");
      expect(result.count).toBe(2);
      expect(result.sides).toBe(6);
      expect(result.keep).toBeUndefined();
    });

    it("returns default 2d6 for undefined", () => {
      const result = parseDiceFormula();
      expect(result.count).toBe(2);
      expect(result.sides).toBe(6);
      expect(result.keep).toBeUndefined();
    });

    it("returns default 2d6 for invalid notation", () => {
      const result = parseDiceFormula("invalid");
      expect(result.count).toBe(2);
      expect(result.sides).toBe(6);
      expect(result.keep).toBeUndefined();
    });

    it("handles whitespace", () => {
      const result = parseDiceFormula("  3d6kh2  ");
      expect(result.count).toBe(3);
      expect(result.keep?.type).toBe("highest");
    });

    it("limits keep count to dice count", () => {
      const result = parseDiceFormula("2d6kh5");
      expect(result.count).toBe(2);
      expect(result.keep?.count).toBe(2); // Should not exceed dice count
    });

    it("handles zero or negative values", () => {
      const result1 = parseDiceFormula("0d6");
      expect(result1.count).toBe(2); // Falls back to default

      const result2 = parseDiceFormula("3d6kh0");
      expect(result2.keep).toBeUndefined(); // Invalid keep count ignored
    });
  });

  describe("different die types", () => {
    it("parses 2d8 correctly", () => {
      const result = parseDiceFormula("2d8");
      expect(result.count).toBe(2);
      expect(result.sides).toBe(8);
    });

    it("parses 1d20 correctly", () => {
      const result = parseDiceFormula("1d20");
      expect(result.count).toBe(1);
      expect(result.sides).toBe(20);
    });
  });
});

describe("computeOutcome", () => {
  it("returns critical for 12+", () => {
    expect(computeOutcome(12, 2, 6)).toBe("critical");
    expect(computeOutcome(15, 2, 6)).toBe("critical");
  });

  it("returns success for 10-11", () => {
    expect(computeOutcome(10, 2, 6)).toBe("success");
    expect(computeOutcome(11, 2, 6)).toBe("success");
  });

  it("returns partial for 7-9", () => {
    expect(computeOutcome(7, 2, 6)).toBe("partial");
    expect(computeOutcome(8, 2, 6)).toBe("partial");
    expect(computeOutcome(9, 2, 6)).toBe("partial");
  });

  it("returns failure for 6-", () => {
    expect(computeOutcome(2, 2, 6)).toBe("failure");
    expect(computeOutcome(6, 2, 6)).toBe("failure");
  });
});

describe("rollDice", () => {
  it("returns valid dice result for 2d6", () => {
    const result = rollDice("2d6");
    expect(result.all_rolls).toHaveLength(2);
    expect(result.kept_rolls).toHaveLength(2);
    expect(result.formula).toBe("2d6");
    expect(result.total).toBeGreaterThanOrEqual(2);
    expect(result.total).toBeLessThanOrEqual(12);
    expect(result.all_rolls.every((d) => d >= 1 && d <= 6)).toBe(true);
  });

  it("returns valid dice result for 3d6kh2 (advantage)", () => {
    const result = rollDice("3d6kh2");
    expect(result.all_rolls).toHaveLength(3);
    expect(result.kept_rolls).toHaveLength(2);
    expect(result.formula).toBe("3d6kh2");
    expect(result.dropped_rolls).toHaveLength(1);
    // Verify kept_rolls are the highest two
    const sorted = [...result.all_rolls].sort((a, b) => b - a);
    expect(result.kept_rolls).toEqual(sorted.slice(0, 2));
  });

  it("returns valid dice result for 3d6kl2 (disadvantage)", () => {
    const result = rollDice("3d6kl2");
    expect(result.all_rolls).toHaveLength(3);
    expect(result.kept_rolls).toHaveLength(2);
    expect(result.formula).toBe("3d6kl2");
    expect(result.dropped_rolls).toHaveLength(1);
    // Verify kept_rolls are the lowest two
    const sorted = [...result.all_rolls].sort((a, b) => a - b);
    expect(result.kept_rolls).toEqual(sorted.slice(0, 2));
  });

  it("falls back to 2d6 for invalid formula", () => {
    const result = rollDice("invalid");
    expect(result.all_rolls).toHaveLength(2);
    expect(result.formula).toBe("2d6");
  });

  it("accepts custom RNG for testing", () => {
    const mockRng = () => 0.5; // Always rolls 4 on d6 (0.5 * 6 + 1 = 4)
    const result = rollDice("2d6", mockRng);
    expect(result.all_rolls).toEqual([4, 4]);
    expect(result.total).toBe(8);
  });
});
