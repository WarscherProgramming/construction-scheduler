import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ScopeComparisonWorkspace from "./ScopeComparisonWorkspace";


function metric(overrides = {}) {
  return {
    id: 1,
    execution_kind: "scope_comparison",
    execution_kind_label: "Deterministic scope comparison",
    execution_id: 3,
    metrics_version: "preconstruction-execution-1",
    duration_ms: 42,
    phase_durations: { resolve: 5, match: 20, persist: 15, total: 42 },
    query_count: null,
    response_bytes: null,
    input_units: null,
    output_units: null,
    estimated_cost_micros: null,
    estimated_cost_display: null,
    cost_rate_configured: false,
    manifest_reused: false,
    budget_stop_reason: null,
    budget_stop_label: null,
    recorded_at: "2026-08-07T12:00:00Z",
    ...overrides,
  };
}


function workspaceProps(overrides = {}) {
  const { readiness, execution, ...rest } = overrides;
  return {
    comparison: {
      plans: [
        {
          id: 5,
          name: "Bid coverage",
          comparison_type_label: "General Scope Coverage",
          status: "locked",
        },
      ],
      comparisonTypes: [],
      selectedPlanId: 5,
      readiness: readiness === undefined
        ? {
            ready: true,
            blockers: [],
            warnings: [],
            comparison_type: "general_scope_coverage",
            requirement_assertion_count: 40,
            coverage_assertion_count: 25,
            accepted_assertion_count: 65,
            stale_assertion_count: 0,
            unsupported_taxonomy_count: 0,
            deterministic_comparison_available: true,
            provider_validation_available: false,
            provider_profile: "disabled",
            taxonomy_version: "construction-scope-1",
            diagnostics: {
              pair_budget: {
                left_count: 40,
                right_count: 25,
                estimated_pairs: 1000,
                maximum_pairs: 1000000,
                within_budget: true,
              },
              persist_chunk_size: 500,
              finding_evidence_limit: 10,
              metrics_enabled: true,
            },
          }
        : readiness,
      findings: {
        items: [],
        total: 0,
        limit: 25,
        offset: 0,
        summary: null,
        latestFindingSetId: 3,
        taxonomyVersion: "construction-scope-1",
        evidenceLimit: 10,
        sets: [],
      },
      execution: execution === undefined
        ? {
            items: [metric()],
            total: 1,
            limit: 50,
            offset: 0,
            summary: {
              total_executions: 1,
              total_duration_ms: 42,
              estimated_cost_micros: null,
              estimated_cost_display: null,
              cost_rate_configured: false,
              by_kind: [],
            },
            metrics_enabled: true,
            metrics_version: "preconstruction-execution-1",
          }
        : execution,
    },
    query: { search: "", limit: 25, offset: 0 },
    isLoading: false,
    error: null,
    isSaving: false,
    onChangeQuery: vi.fn(),
    onRetry: vi.fn(),
    onSelectPlan: vi.fn(),
    onCreatePlan: vi.fn(),
    onArchivePlan: vi.fn(),
    onRunComparison: vi.fn(),
    onReview: vi.fn(),
    onCreateManual: vi.fn(),
    onInspect: vi.fn(),
    ...rest,
  };
}


describe("Execution diagnostics panel", () => {
  it("reports the exact pair count and budget as text", () => {
    render(<ScopeComparisonWorkspace {...workspaceProps()} />);
    const metrics = screen.getByRole("group", {
      name: "Execution diagnostics metrics",
    });
    expect(
      within(metrics).getByText("Comparisons to perform").closest("div")
    ).toHaveTextContent("1000");
    expect(
      within(metrics).getByText("Pair budget").closest("div")
    ).toHaveTextContent("Within budget");
  });

  it("says the budget was exceeded rather than only colouring it", () => {
    const props = workspaceProps();
    props.comparison.readiness.diagnostics.pair_budget = {
      left_count: 2000,
      right_count: 2000,
      estimated_pairs: 4000000,
      maximum_pairs: 1000000,
      within_budget: false,
    };
    render(<ScopeComparisonWorkspace {...props} />);
    const metrics = screen.getByRole("group", {
      name: "Execution diagnostics metrics",
    });
    expect(
      within(metrics).getByText("Pair budget").closest("div")
    ).toHaveTextContent("Exceeded");
  });

  it("shows the last run duration and whether a manifest was reused", () => {
    render(<ScopeComparisonWorkspace {...workspaceProps()} />);
    const metrics = screen.getByRole("group", {
      name: "Execution diagnostics metrics",
    });
    expect(
      within(metrics).getByText("Last run duration").closest("div")
    ).toHaveTextContent("42 ms");
    expect(
      within(metrics).getByText("Last run reused").closest("div")
    ).toHaveTextContent("No");
  });

  it("reports an unconfigured cost rate instead of showing zero", () => {
    render(<ScopeComparisonWorkspace {...workspaceProps()} />);
    const metrics = screen.getByRole("group", {
      name: "Execution diagnostics metrics",
    });
    expect(
      within(metrics).getByText("Estimated cost").closest("div")
    ).toHaveTextContent("No rate configured");
  });

  it("shows a configured cost when a rate exists", () => {
    const props = workspaceProps();
    props.comparison.execution.summary = {
      ...props.comparison.execution.summary,
      estimated_cost_micros: 6000,
      estimated_cost_display: "0.006000",
      cost_rate_configured: true,
    };
    render(<ScopeComparisonWorkspace {...props} />);
    const metrics = screen.getByRole("group", {
      name: "Execution diagnostics metrics",
    });
    expect(
      within(metrics).getByText("Estimated cost").closest("div")
    ).toHaveTextContent("0.006000");
  });

  it("surfaces an early budget stop in words", () => {
    const props = workspaceProps();
    props.comparison.execution.items = [
      metric({
        budget_stop_reason: "candidate_limit_reached",
        budget_stop_label: "Candidate limit reached",
      }),
    ];
    render(<ScopeComparisonWorkspace {...props} />);
    expect(
      screen.getByText(/Last run stopped early: Candidate limit reached/)
    ).toBeInTheDocument();
  });

  it("renders nothing when diagnostics and metrics are both absent", () => {
    const props = workspaceProps({ execution: null });
    props.comparison.readiness = { ...props.comparison.readiness, diagnostics: null };
    render(<ScopeComparisonWorkspace {...props} />);
    expect(
      screen.queryByRole("group", { name: "Execution diagnostics metrics" })
    ).not.toBeInTheDocument();
  });

  it("carries no assertion, evidence, or reviewer text", () => {
    const { container } = render(<ScopeComparisonWorkspace {...workspaceProps()} />);
    const panel = container.querySelector(".comparison-execution");
    expect(panel).not.toBeNull();
    for (const forbidden of ["excerpt", "reviewer", "prompt", "rationale"]) {
      expect(panel.textContent.toLowerCase()).not.toContain(forbidden);
    }
  });
});
