import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addPreconstructionReviewSource,
  archivePreconstructionReviewSet,
  closePreconstructionFollowUp,
  createPreconstructionFollowUp,
  linkPreconstructionFollowUp,
  listPreconstructionFindingFollowUps,
  listPreconstructionPlanFollowUps,
  updatePreconstructionFollowUp,
  cancelPreconstructionPreparationRun,
  archivePreconstructionComparisonPlan,
  cancelPreconstructionRun,
  createPreconstructionComparisonPlan,
  createPreconstructionManualAssertion,
  createPreconstructionManualFinding,
  getPreconstructionComparisonReadiness,
  getPreconstructionFinding,
  listPreconstructionComparisonPlans,
  listPreconstructionFindingSets,
  listPreconstructionFindings,
  reviewPreconstructionFinding,
  runPreconstructionComparison,
  createPreconstructionReviewSet,
  createPreconstructionRun,
  getPreconstructionAssertion,
  getPreconstructionReadiness,
  getPreconstructionScopeTaxonomy,
  getPreconstructionPreparationRun,
  getPreconstructionReviewSet,
  getPreconstructionRun,
  getPreconstructionSourceContent,
  listPreconstructionAssertionSets,
  listPreconstructionAssertions,
  listPreconstructionReviewSets,
  listPreconstructionReviewSources,
  listPreconstructionRuns,
  listPreconstructionSourceCandidates,
  removePreconstructionReviewSource,
  preparePreconstructionSource,
  reviewPreconstructionAssertion,
  retryPreconstructionPreparationRun,
  retryPreconstructionRun,
  updatePreconstructionReviewSet,
  updatePreconstructionReviewSource,
} from "./api";
import { configureAuthentication } from "./httpClient";


function jsonResponse(body = {}, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}


describe("preconstruction API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    configureAuthentication({ token: null, onUnauthorized: null });
  });

  it("builds bounded review, source, readiness, and run reads with AbortSignal", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse()));
    const controller = new AbortController();
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await listPreconstructionReviewSets(4, { state: "archived", limit: 20, offset: 10, signal: controller.signal });
    await getPreconstructionReviewSet(4, 8, { signal: controller.signal });
    await listPreconstructionReviewSources(4, 8, { signal: controller.signal });
    await getPreconstructionReadiness(4, 8, {
      analysisType: "content_contract_validation",
      signal: controller.signal,
    });
    await listPreconstructionRuns(4, 8, { limit: 15, offset: 5, signal: controller.signal });
    await getPreconstructionRun(4, 12, { signal: controller.signal });

    expect(fetchMock.mock.calls[0][0]).toContain("/projects/4/preconstruction/review-sets?state=archived&limit=20&offset=10");
    expect(fetchMock.mock.calls[1][0]).toContain("/review-sets/8");
    expect(fetchMock.mock.calls[2][0]).toContain("/review-sets/8/sources");
    expect(fetchMock.mock.calls[3][0]).toContain("/review-sets/8/readiness?analysis_type=content_contract_validation");
    expect(fetchMock.mock.calls[4][0]).toContain("/review-sets/8/runs?limit=15&offset=5");
    expect(fetchMock.mock.calls[5][0]).toContain("/runs/12");
    expect(fetchMock.mock.calls.every((call) => call[1].signal === controller.signal)).toBe(true);
  });

  it("builds bounded preparation and content inspection requests", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({})));
    const controller = new AbortController();
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await preparePreconstructionSource(4, 8, 3, { signal: controller.signal });
    await getPreconstructionPreparationRun(4, 12, { signal: controller.signal });
    await cancelPreconstructionPreparationRun(4, 12, { signal: controller.signal });
    await retryPreconstructionPreparationRun(4, 12, { signal: controller.signal });
    await getPreconstructionSourceContent(4, 8, 3, {
      snapshotId: 9,
      page: 2,
      segmentOffset: 25,
      segmentLimit: 25,
      search: "shelf lighting & controls",
      signal: controller.signal,
    });

    expect(fetchMock.mock.calls[0][0]).toContain("/review-sets/8/sources/3/prepare");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[1][0]).toContain("/preparation-runs/12");
    expect(fetchMock.mock.calls[2][0]).toContain("/preparation-runs/12/cancel");
    expect(fetchMock.mock.calls[3][0]).toContain("/preparation-runs/12/retry");
    expect(fetchMock.mock.calls[4][0]).toContain(
      "snapshot_id=9&page=2&segment_offset=25&segment_limit=25&search=shelf+lighting+%26+controls"
    );
    expect(fetchMock.mock.calls.every((call) => call[1].signal === controller.signal)).toBe(true);
    expect(fetchMock.mock.calls.every((call) => !call[0].includes("download"))).toBe(true);
  });

  it("encodes candidate search and never requests binary routes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [] }));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await listPreconstructionSourceCandidates(9, {
      sourceType: "drawing_revision",
      search: "A6.02 & lighting",
      limit: 20,
    });

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("source_type=drawing_revision&search=A6.02+%26+lighting&limit=20");
    expect(url).not.toContain("download");
    expect(url).not.toContain("content");
  });

  it("uses strict JSON mutations for every lifecycle action", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ id: 1 }, 201)));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await createPreconstructionReviewSet(4, { name: "Bid", purpose: "bid_scope_review" });
    await updatePreconstructionReviewSet(4, 8, { description: "Updated" });
    await archivePreconstructionReviewSet(4, 8);
    await addPreconstructionReviewSource(4, 8, { source_type: "document", document_id: 2, document_role: "drawing" });
    await updatePreconstructionReviewSource(4, 8, 3, { document_role: "specification" });
    await removePreconstructionReviewSource(4, 8, 3);
    await createPreconstructionRun(4, 8, { analysis_type: "provider_contract_validation" });
    await cancelPreconstructionRun(4, 12);
    await retryPreconstructionRun(4, 12);

    expect(fetchMock.mock.calls.map((call) => call[1].method)).toEqual([
      "POST", "PUT", "POST", "POST", "PUT", "DELETE", "POST", "POST", "POST",
    ]);
    expect(fetchMock.mock.calls[0][1].body).toBe(JSON.stringify({ name: "Bid", purpose: "bid_scope_review" }));
  });

  it("builds bounded, allowlisted scope assertion and taxonomy requests", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ items: [] })));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await getPreconstructionScopeTaxonomy(4, {
      category: "electrical",
      scopeKind: "physical_element",
      search: "luminaire",
    });
    const taxonomyUrl = fetchMock.mock.calls[0][0];
    expect(taxonomyUrl).toContain("/projects/4/preconstruction/scope-taxonomy");
    expect(taxonomyUrl).toContain("category=electrical");
    expect(taxonomyUrl).toContain("scope_kind=physical_element");
    expect(taxonomyUrl).toContain("search=luminaire");

    await listPreconstructionAssertions(4, 8, {
      reviewStatus: "proposed",
      category: "electrical",
      assertionType: "physical_item",
      origin: "provider",
      confidenceMin: 0.5,
      search: "lighting",
      limit: 25,
      offset: 50,
    });
    const listUrl = fetchMock.mock.calls[1][0];
    expect(listUrl).toContain("/review-sets/8/assertions");
    expect(listUrl).toContain("review_status=proposed");
    expect(listUrl).toContain("assertion_type=physical_item");
    expect(listUrl).toContain("origin=provider");
    expect(listUrl).toContain("confidence_min=0.5");
    expect(listUrl).toContain("offset=50");

    await listPreconstructionAssertionSets(4, 8, { limit: 50 });
    expect(fetchMock.mock.calls[2][0]).toContain("/review-sets/8/assertion-sets");

    await getPreconstructionAssertion(4, 51);
    expect(fetchMock.mock.calls[3][0]).toContain("/assertions/51");

    // Reads never request binary content or a download.
    for (const call of fetchMock.mock.calls) {
      expect(call[0]).not.toContain("download");
      expect(call[0]).not.toContain("/attachments");
    }
  });

  it("sends scope mutations as strict JSON without client-controlled state", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ id: 1 }, 201)));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await createPreconstructionManualAssertion(4, 8, {
      source_id: 3,
      concept_code: "electrical.lighting_fixture",
      assertion_type: "physical_item",
      subject: "Fixtures",
      inclusion_state: "included",
      evidence_segment_ids: [77],
    });
    await reviewPreconstructionAssertion(4, 51, {
      decision: "accepted",
      reason_code: null,
      reviewer_note: null,
    });

    expect(fetchMock.mock.calls.map((call) => call[1].method)).toEqual(["POST", "POST"]);
    expect(fetchMock.mock.calls[0][0]).toContain("/review-sets/8/assertions/manual");
    expect(fetchMock.mock.calls[1][0]).toContain("/assertions/51/reviews");

    const manualBody = JSON.parse(fetchMock.mock.calls[0][1].body);
    for (const forbidden of [
      "origin", "confidence", "status", "project_id", "assertion_set_id",
      "provider_assertion_key", "taxonomy_version", "reviewed_by",
    ]) {
      expect(manualBody).not.toHaveProperty(forbidden);
    }
  });

  it("builds bounded, allowlisted comparison and finding requests", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ items: [] })));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await listPreconstructionComparisonPlans(4, 8, { limit: 50 });
    expect(fetchMock.mock.calls[0][0]).toContain("/review-sets/8/comparison-plans");

    await getPreconstructionComparisonReadiness(4, 5);
    expect(fetchMock.mock.calls[1][0]).toContain("/comparison-plans/5/readiness");

    await listPreconstructionFindings(4, 5, {
      findingType: "missing_coverage",
      severity: "high",
      reviewStatus: "proposed",
      origin: "deterministic",
      findingSetId: 3,
      search: "lighting",
      limit: 25,
      offset: 50,
    });
    const listUrl = fetchMock.mock.calls[2][0];
    expect(listUrl).toContain("/comparison-plans/5/findings");
    expect(listUrl).toContain("finding_type=missing_coverage");
    expect(listUrl).toContain("severity=high");
    expect(listUrl).toContain("review_status=proposed");
    expect(listUrl).toContain("origin=deterministic");
    expect(listUrl).toContain("finding_set_id=3");
    expect(listUrl).toContain("offset=50");

    await listPreconstructionFindingSets(4, 5, { limit: 50 });
    expect(fetchMock.mock.calls[3][0]).toContain("/comparison-plans/5/finding-sets");

    await getPreconstructionFinding(4, 91);
    expect(fetchMock.mock.calls[4][0]).toContain("/findings/91");

    // Comparison reads never request binary content or a dashboard aggregate.
    for (const call of fetchMock.mock.calls) {
      expect(call[0]).not.toContain("download");
      expect(call[0]).not.toContain("/attachments");
      expect(call[0]).not.toContain("/dashboard");
    }
  });

  it("sends comparison mutations as strict JSON without client-controlled state", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ id: 1 }, 201)));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await createPreconstructionComparisonPlan(4, 8, {
      name: "Bid coverage",
      comparison_type: "general_scope_coverage",
      minimum_review_state: "accepted",
    });
    await runPreconstructionComparison(4, 5, {});
    await reviewPreconstructionFinding(4, 91, {
      decision: "accepted",
      reason_code: "confirmed_gap",
      reviewer_note: null,
    });
    await createPreconstructionManualFinding(4, 5, {
      finding_type: "missing_coverage",
      title: "Uncovered scope",
      assertions: [{ assertion_id: 51, side: "requirement" }],
      evidence_ids: [70],
    });
    await archivePreconstructionComparisonPlan(4, 5);

    expect(fetchMock.mock.calls.map((call) => call[1].method)).toEqual([
      "POST", "POST", "POST", "POST", "POST",
    ]);
    expect(fetchMock.mock.calls[1][0]).toContain("/comparison-plans/5/runs");
    expect(fetchMock.mock.calls[2][0]).toContain("/findings/91/reviews");
    expect(fetchMock.mock.calls[3][0]).toContain("/comparison-plans/5/findings/manual");

    const planBody = JSON.parse(fetchMock.mock.calls[0][1].body);
    const manualBody = JSON.parse(fetchMock.mock.calls[3][1].body);
    for (const forbidden of ["status", "project_id", "configuration_hash", "locked_at"]) {
      expect(planBody).not.toHaveProperty(forbidden);
    }
    for (const forbidden of [
      "origin", "provider_confidence", "status", "finding_set_id",
      "deterministic_match_score", "excerpt",
    ]) {
      expect(manualBody).not.toHaveProperty(forbidden);
    }
  });

  it("builds bounded follow-up reads with allowlisted filters", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse()));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await listPreconstructionFindingFollowUps(4, 91);
    expect(fetchMock.mock.calls[0][0]).toContain("/findings/91/follow-ups");

    await listPreconstructionPlanFollowUps(4, 5, {
      actionType: "rfi",
      followUpStatus: "planned",
      targetType: "rfi",
      findingId: 91,
      limit: 25,
      offset: 25,
    });
    const listUrl = fetchMock.mock.calls[1][0];
    expect(listUrl).toContain("/comparison-plans/5/follow-ups");
    expect(listUrl).toContain("action_type=rfi");
    expect(listUrl).toContain("follow_up_status=planned");
    expect(listUrl).toContain("target_type=rfi");
    expect(listUrl).toContain("finding_id=91");
    expect(listUrl).toContain("offset=25");

    // Follow-up reads never request a workflow record collection or a binary.
    for (const call of fetchMock.mock.calls) {
      expect(call[0]).toContain("/preconstruction/");
      expect(call[0]).not.toContain("download");
      expect(call[0]).not.toContain("/relationships");
    }
  });

  it("sends follow-up mutations to preconstruction routes only", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ id: 1 }, 201)));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "precon-token" });

    await createPreconstructionFollowUp(4, 91, {
      action_type: "rfi",
      draft_title: "Missing coverage",
      draft_body: "Please clarify.",
    });
    await updatePreconstructionFollowUp(4, 12, { draft_title: "Edited" });
    await linkPreconstructionFollowUp(4, 12, { target_type: "rfi", target_id: 7 });
    await closePreconstructionFollowUp(4, 12, {
      status: "completed",
      closure_note: null,
    });

    expect(fetchMock.mock.calls.map((call) => call[1].method)).toEqual([
      "POST", "PUT", "POST", "POST",
    ]);
    expect(fetchMock.mock.calls[0][0]).toContain("/findings/91/follow-ups");
    expect(fetchMock.mock.calls[1][0]).toContain("/follow-ups/12");
    expect(fetchMock.mock.calls[2][0]).toContain("/follow-ups/12/link");
    expect(fetchMock.mock.calls[3][0]).toContain("/follow-ups/12/close");

    // No follow-up mutation ever posts to an authoritative workflow endpoint.
    for (const call of fetchMock.mock.calls) {
      expect(call[0]).toContain("/preconstruction/");
      for (const authoritative of ["/rfis", "/change-orders", "/submittals", "/relationships"]) {
        expect(call[0]).not.toContain(authoritative);
      }
    }

    const createBody = JSON.parse(fetchMock.mock.calls[0][1].body);
    for (const forbidden of [
      "status", "project_id", "finding_review_id", "target_type", "target_id",
      "created_by", "draft_template_version",
    ]) {
      expect(createBody).not.toHaveProperty(forbidden);
    }
  });
});
