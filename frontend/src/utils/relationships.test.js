import { describe, expect, it, vi } from "vitest";

import {
  buildRelationshipPayload,
  getRelationshipChoices,
  getRelationshipOptions,
  isExistingRelationship,
  navigateToRelationship,
  RELATIONSHIP_ENTITY_LABELS,
} from "./relationships";


describe("relationship utilities", () => {
  it("exposes every supported entity label", () => {
    expect(Object.keys(RELATIONSHIP_ENTITY_LABELS)).toEqual([
      "document",
      "drawing_set",
      "drawing_sheet",
      "drawing_revision",
      "drawing_issue",
      "rfi",
      "submittal",
      "punch_item",
      "change_order",
      "daily_log",
    ]);
  });

  it("derives forward, reverse, and symmetric options", () => {
    expect(getRelationshipOptions("rfi")).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          relationshipType: "references",
          relationshipLabel: "References",
          relatedType: "drawing_revision",
          direction: "outgoing",
        }),
        expect.objectContaining({
          relationshipType: "responds_to",
          relationshipLabel: "Has response",
          relatedType: "submittal",
          direction: "incoming",
        }),
        expect.objectContaining({
          relationshipType: "associated_with",
          relationshipLabel: "Associated with",
          relatedType: "document",
          direction: "symmetric",
        }),
      ])
    );
  });

  it("groups one relationship choice across allowed related types", () => {
    const references = getRelationshipChoices("submittal").find(
      (choice) =>
        choice.relationshipType === "references" &&
        choice.direction === "outgoing"
    );
    expect(references.options.map((option) => option.relatedType)).toEqual([
      "drawing_revision",
      "drawing_sheet",
    ]);
  });

  it("builds directional payloads in the backend canonical direction", () => {
    const incoming = getRelationshipOptions("drawing_revision").find(
      (option) =>
        option.relationshipType === "references" &&
        option.relatedType === "rfi"
    );
    expect(
      buildRelationshipPayload("drawing_revision", 55, incoming, {
        id: 20,
      })
    ).toEqual({
      source_type: "rfi",
      source_id: 20,
      target_type: "drawing_revision",
      target_id: 55,
      relationship_type: "references",
    });
  });

  it("builds symmetric payloads from the current perspective", () => {
    const symmetric = getRelationshipOptions("rfi").find(
      (option) => option.relationshipType === "associated_with"
    );
    expect(buildRelationshipPayload("rfi", 20, symmetric, { id: 7 })).toEqual({
      source_type: "rfi",
      source_id: 20,
      target_type: "document",
      target_id: 7,
      relationship_type: "associated_with",
    });
  });

  it("detects only exact active relationship duplicates", () => {
    const relationships = [
      {
        relationship_type: "references",
        related: { type: "drawing_sheet", id: 9 },
      },
    ];
    expect(
      isExistingRelationship(relationships, "references", {
        type: "drawing_sheet",
        id: 9,
      })
    ).toBe(true);
    expect(
      isExistingRelationship(relationships, "impacts", {
        type: "drawing_sheet",
        id: 9,
      })
    ).toBe(false);
  });

  it("navigates page-level and exact drawing-viewer routes safely", () => {
    const onNavigate = vi.fn();
    expect(
      navigateToRelationship(
        {
          available: true,
          route: {
            page: "drawingViewer",
            sheet_id: 4,
            revision_id: 8,
          },
        },
        onNavigate,
        2
      )
    ).toBe(true);
    expect(onNavigate).toHaveBeenCalledWith("drawingViewer", 2, {
      sheetId: 4,
      revisionId: 8,
    });

    expect(
      navigateToRelationship(
        { available: false, route: null },
        onNavigate,
        2
      )
    ).toBe(false);
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });
});
