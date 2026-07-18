import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import Copilot from "./Copilot";

describe("Copilot", () => {
  it("shows the fixture answer with citations after sending a question", async () => {
    render(<Copilot />);
    const input = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(input, "Why did P-101 fail?");
    await userEvent.click(screen.getByText("Send"));

    expect(screen.getByText("Why did P-101 fail?")).toBeInTheDocument();
    expect(screen.getByText(/Phase 0 mock response/i)).toBeInTheDocument();
    expect(screen.getByText("mock-source-1.pdf")).toBeInTheDocument();
  });

  it("does not send an empty message", async () => {
    render(<Copilot />);
    await userEvent.click(screen.getByText("Send"));
    expect(screen.queryByText(/Phase 0 mock response/i)).not.toBeInTheDocument();
  });
});
