import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addPreconstructionReviewSource,
  archivePreconstructionReviewSet,
  cancelPreconstructionPreparationRun,
  cancelPreconstructionRun,
  createPreconstructionManualAssertion,
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
});
