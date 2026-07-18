import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RoleProvider } from "../layout/RoleContext";
import Sidebar from "./Sidebar";

function renderSidebar() {
  return render(
    <RoleProvider>
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    </RoleProvider>,
  );
}

describe("Sidebar", () => {
  it("renders every module link", () => {
    renderSidebar();
    const nav = screen.getByRole("navigation");
    for (const label of ["Home", "Document Library", "Knowledge Graph", "Copilot", "Maintenance & RCA", "Admin"]) {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    }
  });

  it("switches the active role via the select", async () => {
    renderSidebar();
    const select = screen.getByLabelText(/Viewing as/i) as HTMLSelectElement;
    expect(select.value).toBe("Maintenance Engineer");
    await userEvent.selectOptions(select, "Field Technician");
    expect(select.value).toBe("Field Technician");
  });
});
