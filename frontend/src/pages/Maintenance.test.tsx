import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import Maintenance from "./Maintenance";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Maintenance", () => {
  it("renders the fixture equipment health table", () => {
    render(<Maintenance />);
    expect(screen.getByText("P-101")).toBeInTheDocument();
    expect(screen.getByText("C-305")).toBeInTheDocument();
  });

  it("runs an RCA investigation and shows the root cause and evidence", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            root_cause_chain: "Bearing wear caused the overcurrent trip.",
            evidence: [
              { tool: "search_equipment_history", arguments: { tag: "C-305" }, result_summary: "..." },
            ],
          }),
      }),
    );

    render(<Maintenance />);
    await userEvent.click(screen.getByText("Investigate"));

    await waitFor(() => {
      expect(screen.getByText(/Bearing wear caused the overcurrent trip/i)).toBeInTheDocument();
    });
    expect(screen.getByText("search_equipment_history")).toBeInTheDocument();
  });

  it("shows an error message when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    render(<Maintenance />);
    await userEvent.click(screen.getByText("Investigate"));

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("does not investigate an empty description", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Maintenance />);
    const textarea = screen.getByRole("textbox");
    await userEvent.clear(textarea);
    await userEvent.click(screen.getByText("Investigate"));
    expect(screen.queryByText(/Investigating/i)).not.toBeInTheDocument();
  });
});
