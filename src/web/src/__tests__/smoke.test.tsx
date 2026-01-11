import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../App";

describe("App smoke test", () => {
  it("renders menu page call-to-action", () => {
    render(<App />);
    expect(screen.getByText(/选择一个世界包/i)).toBeInTheDocument();
  });
});
