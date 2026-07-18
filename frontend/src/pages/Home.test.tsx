import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RoleProvider } from "../layout/RoleContext";
import Home from "./Home";

describe("Home", () => {
  it("renders the welcome heading with the current role", () => {
    render(
      <RoleProvider>
        <Home />
      </RoleProvider>,
    );
    expect(screen.getByText(/Welcome back — viewing as Maintenance Engineer/i)).toBeInTheDocument();
  });

  it("renders the ask-anything prompt", () => {
    render(
      <RoleProvider>
        <Home />
      </RoleProvider>,
    );
    expect(screen.getByText(/Ask anything/i)).toBeInTheDocument();
  });
});
