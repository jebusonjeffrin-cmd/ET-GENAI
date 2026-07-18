import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import Copilot from "./Copilot";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Copilot", () => {
  it("shows the backend's answer with citations after sending a question", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            answer: "Pump P-101 was serviced by R. Iyer. [1]",
            citations: [{ index: 1, document_id: "doc-1", chunk_id: "doc-1:0", text: "Work order WO-4521..." }],
          }),
      }),
    );

    render(<Copilot />);
    const input = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(input, "Who serviced P-101?");
    await userEvent.click(screen.getByText("Send"));

    await waitFor(() => {
      expect(screen.getByText(/Pump P-101 was serviced by R. Iyer/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/document doc-1/i)).toBeInTheDocument();
  });

  it("does not send an empty message", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Copilot />);
    await userEvent.click(screen.getByText("Send"));
    expect(screen.queryByText(/Thinking/i)).not.toBeInTheDocument();
  });

  it("shows an error message when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    render(<Copilot />);
    const input = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(input, "Who serviced P-101?");
    await userEvent.click(screen.getByText("Send"));

    await waitFor(() => {
      expect(screen.getByText(/Couldn't reach the Copilot backend/i)).toBeInTheDocument();
    });
  });

  it("shows a fallback message when the backend returns no answer", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ answer: "", citations: [] }),
      }),
    );

    render(<Copilot />);
    const input = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(input, "Something not in the corpus");
    await userEvent.click(screen.getByText("Send"));

    await waitFor(() => {
      expect(screen.getByText(/No answer produced/i)).toBeInTheDocument();
    });
  });
});
