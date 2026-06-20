import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import HomePage from "./HomePage";


describe("HomePage", () => {
  it("selects a project by numeric ID", async () => {
    const user = userEvent.setup();
    const onProjectSelect = vi.fn();

    render(
      <HomePage
        projects={[
          { id: 10, name: "North Ridge" },
          { id: 20, name: "Desert View" },
        ]}
        templates={[]}
        selectedProjectId={null}
        newProjectName=""
        onProjectSelect={onProjectSelect}
        onNewProjectNameChange={vi.fn()}
        onCreateProject={vi.fn()}
        onLogout={vi.fn()}
      />
    );

    await user.selectOptions(screen.getByLabelText("Project"), "20");

    expect(onProjectSelect).toHaveBeenCalledWith(20);
  });

  it("creates a project and supports logout", async () => {
    const user = userEvent.setup();
    const onNameChange = vi.fn();
    const onCreateProject = vi.fn();
    const onLogout = vi.fn();

    const { rerender } = render(
      <HomePage
        projects={[]}
        templates={[{ id: 1, name: "Standard" }]}
        selectedProjectId={null}
        newProjectName=""
        onProjectSelect={vi.fn()}
        onNewProjectNameChange={onNameChange}
        onCreateProject={onCreateProject}
        onLogout={onLogout}
      />
    );

    await user.type(
      screen.getByLabelText("Project name *"),
      "Canyon Estates"
    );

    rerender(
      <HomePage
        projects={[]}
        templates={[{ id: 1, name: "Standard" }]}
        selectedProjectId={null}
        newProjectName="Canyon Estates"
        onProjectSelect={vi.fn()}
        onNewProjectNameChange={onNameChange}
        onCreateProject={onCreateProject}
        onLogout={onLogout}
      />
    );

    await user.type(screen.getByLabelText("Project name *"), "{enter}");
    await user.click(screen.getByRole("button", { name: "Logout" }));

    expect(onNameChange).toHaveBeenCalled();
    expect(onCreateProject).toHaveBeenCalledOnce();
    expect(onLogout).toHaveBeenCalledOnce();
    expect(screen.getByText("1 saved template(s)")).toBeInTheDocument();
  });
});
