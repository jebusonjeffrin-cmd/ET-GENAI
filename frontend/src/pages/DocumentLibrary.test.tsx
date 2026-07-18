import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import DocumentLibrary from "./DocumentLibrary";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("DocumentLibrary", () => {
  it("renders the empty state when the backend returns no documents", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      }),
    );

    render(<DocumentLibrary />);

    await waitFor(() => {
      expect(screen.getByText(/No documents ingested yet/i)).toBeInTheDocument();
    });
  });

  it("renders a document row when the backend returns one", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve([{ id: "1", filename: "sop.txt", status: "done", document_type: "sop" }]),
      }),
    );

    render(<DocumentLibrary />);

    await waitFor(() => {
      expect(screen.getByText("sop.txt")).toBeInTheDocument();
    });
    expect(screen.getByText("done")).toBeInTheDocument();
  });

  it("shows an error message when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    render(<DocumentLibrary />);

    await waitFor(() => {
      expect(screen.getByText(/is the backend running/i)).toBeInTheDocument();
    });
  });
});
