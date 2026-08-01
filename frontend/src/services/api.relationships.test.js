import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRelationship,
  deleteRelationship,
  listRelationshipCandidates,
  listRelationships,
} from "./api";
import {
  clearAuthentication,
  configureAuthentication,
} from "./httpClient";


function jsonResponse(body) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}


describe("relationship API helpers", () => {
  beforeEach(() => {
    configureAuthentication({ token: "test-token", onUnauthorized: vi.fn() });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({})));
  });

  afterEach(() => {
    clearAuthentication();
    vi.unstubAllGlobals();
  });

  it("encodes bounded relationship list filters", async () => {
    const controller = new AbortController();
    await listRelationships(7, "rfi", 12, {
      direction: "incoming",
      relationshipType: "references",
      relatedType: "drawing_revision",
      limit: 25,
      offset: 50,
      signal: controller.signal,
    });
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/projects/7/relationships?entity_type=rfi&entity_id=12&direction=incoming&relationship_type=references&related_type=drawing_revision&limit=25&offset=50",
      expect.objectContaining({
        signal: controller.signal,
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
        }),
      })
    );
  });

  it("posts only the relationship payload", async () => {
    const payload = {
      source_type: "rfi",
      source_id: 12,
      target_type: "drawing_revision",
      target_id: 30,
      relationship_type: "references",
    };
    await createRelationship(7, payload);
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/projects/7/relationships",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      })
    );
  });

  it("encodes candidate search and paired exclusion", async () => {
    await listRelationshipCandidates(7, "document", {
      search: "issued plans",
      limit: 20,
      excludeType: "document",
      excludeId: 14,
    });
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/projects/7/relationship-candidates?entity_type=document&search=issued+plans&limit=20&exclude_type=document&exclude_id=14",
      expect.any(Object)
    );
  });

  it("deletes one project-scoped relationship", async () => {
    await deleteRelationship(7, 99);
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/projects/7/relationships/99",
      expect.objectContaining({ method: "DELETE" })
    );
  });
});
