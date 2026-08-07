import { useCallback, useEffect, useRef, useState } from "react";

import {
  addPreconstructionReviewSource,
  archivePreconstructionComparisonPlan,
  archivePreconstructionReviewSet,
  closePreconstructionFollowUp,
  createPreconstructionComparisonPlan,
  createPreconstructionFollowUp,
  createPreconstructionManualFinding,
  linkPreconstructionFollowUp,
  listPreconstructionFindingFollowUps,
  updatePreconstructionFollowUp,
  getPreconstructionComparisonReadiness,
  listPreconstructionComparisonPlans,
  listPreconstructionFindingSets,
  listPreconstructionFindings,
  reviewPreconstructionFinding,
  runPreconstructionComparison,
  updatePreconstructionComparisonPlan,
  cancelPreconstructionPreparationRun,
  cancelPreconstructionRun,
  createPreconstructionManualAssertion,
  createPreconstructionReviewSet,
  createPreconstructionRun,
  getPreconstructionScopeTaxonomy,
  getPreconstructionSourceContent,
  getPreconstructionReadiness,
  getPreconstructionReviewSet,
  listPreconstructionAssertionSets,
  listPreconstructionAssertions,
  listPreconstructionReviewSets,
  listPreconstructionReviewSources,
  listPreconstructionRuns,
  listPreconstructionSourceCandidates,
  preparePreconstructionSource,
  removePreconstructionReviewSource,
  reviewPreconstructionAssertion,
  retryPreconstructionRun,
  retryPreconstructionPreparationRun,
  updatePreconstructionReviewSet,
  updatePreconstructionReviewSource,
} from "../services/api";


function isAbortError(error) {
  return error?.name === "AbortError";
}


const EMPTY_DETAIL = {
  reviewSet: null,
  sources: [],
  roles: [],
  readiness: null,
  runs: [],
};


const EMPTY_ASSERTIONS = {
  items: [],
  total: 0,
  limit: 25,
  offset: 0,
  summary: null,
  latestAssertionSetId: null,
  taxonomyVersion: null,
  sets: [],
};


const EMPTY_COMPARISON = {
  plans: [],
  comparisonTypes: [],
  selectedPlanId: null,
  readiness: null,
  findings: {
    items: [],
    total: 0,
    limit: 25,
    offset: 0,
    summary: null,
    latestFindingSetId: null,
    taxonomyVersion: null,
    sets: [],
  },
};


const EMPTY_FOLLOW_UPS = {
  findingId: null,
  items: [],
  actions: [],
  availableActions: [],
  drafts: [],
  eligible: false,
  findingStatus: null,
};


const DEFAULT_FINDING_QUERY = {
  findingSetId: undefined,
  findingType: undefined,
  severity: undefined,
  reviewStatus: undefined,
  origin: undefined,
  search: "",
  limit: 25,
  offset: 0,
};


const DEFAULT_ASSERTION_QUERY = {
  reviewStatus: undefined,
  category: undefined,
  assertionType: undefined,
  sourceId: undefined,
  origin: undefined,
  inclusionState: undefined,
  search: "",
  assertionSetId: undefined,
  limit: 25,
  offset: 0,
};


function usePreconstruction({ projectId, onError }) {
  const [filter, setFilter] = useState("active");
  const [reviewSets, setReviewSets] = useState([]);
  const [selectedReviewSetId, setSelectedReviewSetId] = useState(null);
  const [detail, setDetail] = useState(EMPTY_DETAIL);
  const [isListLoading, setIsListLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [listError, setListError] = useState(null);
  const [detailError, setDetailError] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [isCandidateLoading, setIsCandidateLoading] = useState(false);
  const [content, setContent] = useState(null);
  const [contentSourceId, setContentSourceId] = useState(null);
  const [contentQuery, setContentQuery] = useState({
    page: null,
    segmentOffset: 0,
    segmentLimit: 25,
    search: "",
  });
  const [isContentLoading, setIsContentLoading] = useState(false);
  const [contentError, setContentError] = useState(null);
  const [assertions, setAssertions] = useState(EMPTY_ASSERTIONS);
  const [assertionQuery, setAssertionQuery] = useState(DEFAULT_ASSERTION_QUERY);
  const [isAssertionLoading, setIsAssertionLoading] = useState(false);
  const [assertionError, setAssertionError] = useState(null);
  const [taxonomy, setTaxonomy] = useState(null);
  const [isTaxonomyLoading, setIsTaxonomyLoading] = useState(false);
  const [comparison, setComparison] = useState(EMPTY_COMPARISON);
  const [findingQuery, setFindingQuery] = useState(DEFAULT_FINDING_QUERY);
  const [isComparisonLoading, setIsComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState(null);
  const [followUps, setFollowUps] = useState(EMPTY_FOLLOW_UPS);
  const [isFollowUpLoading, setIsFollowUpLoading] = useState(false);
  const assertionRequestRef = useRef(null);
  const assertionQueryRef = useRef(DEFAULT_ASSERTION_QUERY);
  const comparisonRequestRef = useRef(null);
  const findingQueryRef = useRef(DEFAULT_FINDING_QUERY);
  const selectedPlanRef = useRef(null);
  const followUpRequestRef = useRef(null);
  const followUpFindingRef = useRef(null);
  // Set below once loadFollowUps exists, so the finding-review callback can
  // refresh an open panel without depending on declaration order.
  const loadFollowUpsRef = useRef(null);
  const taxonomyRequestRef = useRef(null);
  const projectRef = useRef(projectId);
  const selectedReviewSetRef = useRef(null);
  const onErrorRef = useRef(onError);
  const listRequestRef = useRef(null);
  const detailRequestRef = useRef(null);
  const candidateRequestRef = useRef(null);
  const contentRequestRef = useRef(null);
  const contentSourceRef = useRef(null);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    projectRef.current = projectId;
    listRequestRef.current?.abort();
    detailRequestRef.current?.abort();
    candidateRequestRef.current?.abort();
    contentRequestRef.current?.abort();
    assertionRequestRef.current?.abort();
    comparisonRequestRef.current?.abort();
    followUpRequestRef.current?.abort();
    taxonomyRequestRef.current?.abort();
    contentSourceRef.current = null;
    selectedReviewSetRef.current = null;
    selectedPlanRef.current = null;
    followUpFindingRef.current = null;
    assertionQueryRef.current = DEFAULT_ASSERTION_QUERY;
    findingQueryRef.current = DEFAULT_FINDING_QUERY;
    const resetTimer = window.setTimeout(() => {
      setReviewSets([]);
      setSelectedReviewSetId(null);
      setDetail(EMPTY_DETAIL);
      setCandidates([]);
      setListError(null);
      setDetailError(null);
      setContent(null);
      setContentSourceId(null);
      setContentError(null);
      setAssertions(EMPTY_ASSERTIONS);
      setAssertionQuery(DEFAULT_ASSERTION_QUERY);
      setAssertionError(null);
      setTaxonomy(null);
      setComparison(EMPTY_COMPARISON);
      setFindingQuery(DEFAULT_FINDING_QUERY);
      setComparisonError(null);
      setFollowUps(EMPTY_FOLLOW_UPS);
    }, 0);
    return () => window.clearTimeout(resetTimer);
  }, [projectId]);

  useEffect(() => () => {
    projectRef.current = null;
    listRequestRef.current?.abort();
    detailRequestRef.current?.abort();
    candidateRequestRef.current?.abort();
    contentRequestRef.current?.abort();
    assertionRequestRef.current?.abort();
    comparisonRequestRef.current?.abort();
    followUpRequestRef.current?.abort();
    taxonomyRequestRef.current?.abort();
  }, []);

  const loadReviewSets = useCallback(() => {
    if (!projectId) return Promise.resolve(null);
    listRequestRef.current?.abort();
    const controller = new AbortController();
    listRequestRef.current = controller;
    setIsListLoading(true);
    setListError(null);
    return listPreconstructionReviewSets(projectId, {
      state: filter,
      limit: 100,
      signal: controller.signal,
    })
      .then((response) => {
        if (projectRef.current !== projectId || controller.signal.aborted) return null;
        setReviewSets(response.items);
        setSelectedReviewSetId((current) => {
          const next = response.items.some((item) => item.id === current)
            ? current
            : null;
          selectedReviewSetRef.current = next;
          return next;
        });
        return response;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== projectId) return null;
        setListError(error);
        onErrorRef.current?.("Unable to load preconstruction review sets", error);
        return null;
      })
      .finally(() => {
        if (listRequestRef.current === controller) {
          listRequestRef.current = null;
          setIsListLoading(false);
        }
      });
  }, [filter, projectId]);

  useEffect(() => {
    const startTimer = window.setTimeout(() => void loadReviewSets(), 0);
    return () => window.clearTimeout(startTimer);
  }, [loadReviewSets]);

  const loadDetail = useCallback((reviewSetId = selectedReviewSetId) => {
    if (!projectId || !reviewSetId) {
      setDetail(EMPTY_DETAIL);
      return Promise.resolve(null);
    }
    detailRequestRef.current?.abort();
    const controller = new AbortController();
    const identity = { controller, projectId, reviewSetId };
    detailRequestRef.current = controller;
    setDetail(EMPTY_DETAIL);
    setIsDetailLoading(true);
    setDetailError(null);
    return Promise.all([
      getPreconstructionReviewSet(projectId, reviewSetId, { signal: controller.signal }),
      listPreconstructionReviewSources(projectId, reviewSetId, { signal: controller.signal }),
      getPreconstructionReadiness(projectId, reviewSetId, {
        analysisType: "content_contract_validation",
        signal: controller.signal,
      }),
      listPreconstructionRuns(projectId, reviewSetId, { limit: 100, signal: controller.signal }),
    ])
      .then(([reviewSet, sources, readiness, runs]) => {
        if (
          projectRef.current !== identity.projectId ||
          selectedReviewSetRef.current !== identity.reviewSetId ||
          controller.signal.aborted
        ) return null;
        const next = {
          reviewSet,
          sources: sources.items,
          roles: sources.roles,
          readiness,
          runs: runs.items,
        };
        setDetail(next);
        return next;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== projectId) return null;
        setDetailError(error);
        onErrorRef.current?.("Unable to load preconstruction review details", error);
        return null;
      })
      .finally(() => {
        if (detailRequestRef.current === controller) {
          detailRequestRef.current = null;
          setIsDetailLoading(false);
        }
      });
  }, [projectId, selectedReviewSetId]);

  useEffect(() => {
    const startTimer = window.setTimeout(
      () => void loadDetail(selectedReviewSetId),
      0
    );
    return () => window.clearTimeout(startTimer);
  }, [loadDetail, selectedReviewSetId]);

  const runMutation = useCallback(async (message, operation, refresh = "detail") => {
    setIsSaving(true);
    try {
      const value = await operation();
      if (projectRef.current !== projectId) return null;
      if (refresh === "list") await loadReviewSets();
      if (refresh === "detail") await loadDetail();
      return value;
    } catch (error) {
      if (!isAbortError(error) && projectRef.current === projectId) {
        onErrorRef.current?.(message, error);
      }
      throw error;
    } finally {
      if (projectRef.current === projectId) setIsSaving(false);
    }
  }, [loadDetail, loadReviewSets, projectId]);

  const createReviewSet = useCallback((values) =>
    runMutation(
      "Unable to create preconstruction review set",
      () => createPreconstructionReviewSet(projectId, values),
      "none"
    ).then(async (created) => {
      if (created) {
        await loadReviewSets();
        selectedReviewSetRef.current = created.id;
        setSelectedReviewSetId(created.id);
      }
      return created;
    }), [loadReviewSets, projectId, runMutation]);

  const updateReviewSet = useCallback((values) => runMutation(
    "Unable to update preconstruction review set",
    () => updatePreconstructionReviewSet(projectId, selectedReviewSetId, values),
    "detail"
  ).then(async (updated) => {
    if (updated) await loadReviewSets();
    return updated;
  }), [loadReviewSets, projectId, runMutation, selectedReviewSetId]);

  const archiveReviewSet = useCallback(() => runMutation(
    "Unable to archive preconstruction review set",
    () => archivePreconstructionReviewSet(projectId, selectedReviewSetId),
    "none"
  ).then(async (archived) => {
    if (archived) {
      selectedReviewSetRef.current = null;
      setSelectedReviewSetId(null);
      await loadReviewSets();
    }
    return archived;
  }), [loadReviewSets, projectId, runMutation, selectedReviewSetId]);

  const addSource = useCallback((source) => runMutation(
    "Unable to add preconstruction review source",
    () => addPreconstructionReviewSource(projectId, selectedReviewSetId, source)
  ), [projectId, runMutation, selectedReviewSetId]);

  const updateSource = useCallback((sourceId, source) => runMutation(
    "Unable to update preconstruction review source",
    () => updatePreconstructionReviewSource(projectId, selectedReviewSetId, sourceId, source)
  ), [projectId, runMutation, selectedReviewSetId]);

  const removeSource = useCallback((sourceId) => runMutation(
    "Unable to remove preconstruction review source",
    () => removePreconstructionReviewSource(projectId, selectedReviewSetId, sourceId)
  ), [projectId, runMutation, selectedReviewSetId]);

  const requestRun = useCallback(() => runMutation(
    "Unable to request preconstruction analysis run",
    () => createPreconstructionRun(projectId, selectedReviewSetId, {
      analysis_type: "content_contract_validation",
    })
  ).then(async (run) => {
    if (run) await loadReviewSets();
    return run;
  }), [loadReviewSets, projectId, runMutation, selectedReviewSetId]);

  const cancelRun = useCallback((runId) => runMutation(
    "Unable to cancel preconstruction analysis run",
    () => cancelPreconstructionRun(projectId, runId)
  ), [projectId, runMutation]);

  const retryRun = useCallback((runId) => runMutation(
    "Unable to retry preconstruction analysis run",
    () => retryPreconstructionRun(projectId, runId)
  ), [projectId, runMutation]);

  const prepareSource = useCallback((sourceId) => runMutation(
    "Unable to prepare preconstruction source content",
    () => preparePreconstructionSource(projectId, selectedReviewSetId, sourceId)
  ), [projectId, runMutation, selectedReviewSetId]);

  const cancelPreparation = useCallback((runId) => runMutation(
    "Unable to cancel source preparation",
    () => cancelPreconstructionPreparationRun(projectId, runId)
  ), [projectId, runMutation]);

  const retryPreparation = useCallback((runId) => runMutation(
    "Unable to retry source preparation",
    () => retryPreconstructionPreparationRun(projectId, runId)
  ), [projectId, runMutation]);

  const loadContent = useCallback((sourceId = contentSourceId, options = contentQuery) => {
    if (!projectId || !selectedReviewSetId || !sourceId) return Promise.resolve(null);
    contentRequestRef.current?.abort();
    const controller = new AbortController();
    const identity = { projectId, reviewSetId: selectedReviewSetId, sourceId };
    const query = {
      page: options.page ?? null,
      segmentOffset: options.segmentOffset ?? 0,
      segmentLimit: options.segmentLimit ?? 25,
      search: options.search ?? "",
    };
    contentRequestRef.current = controller;
    contentSourceRef.current = sourceId;
    setContentSourceId(sourceId);
    setContentQuery(query);
    setContent(null);
    setContentError(null);
    setIsContentLoading(true);
    return getPreconstructionSourceContent(projectId, selectedReviewSetId, sourceId, {
      ...query,
      signal: controller.signal,
    }).then((response) => {
      if (
        projectRef.current !== identity.projectId ||
        selectedReviewSetRef.current !== identity.reviewSetId ||
        contentSourceRef.current !== identity.sourceId ||
        controller.signal.aborted
      ) return null;
      setContent(response);
      return response;
    }).catch((error) => {
      if (isAbortError(error) || projectRef.current !== identity.projectId) return null;
      setContentError(error);
      onErrorRef.current?.("Unable to load prepared source content", error);
      return null;
    }).finally(() => {
      if (contentRequestRef.current === controller) {
        contentRequestRef.current = null;
        setIsContentLoading(false);
      }
    });
  }, [contentQuery, contentSourceId, projectId, selectedReviewSetId]);

  const closeContent = useCallback(() => {
    contentRequestRef.current?.abort();
    contentRequestRef.current = null;
    contentSourceRef.current = null;
    setContentSourceId(null);
    setContent(null);
    setContentError(null);
    setIsContentLoading(false);
  }, []);

  const searchCandidates = useCallback((sourceType, search) => {
    candidateRequestRef.current?.abort();
    const controller = new AbortController();
    candidateRequestRef.current = controller;
    setIsCandidateLoading(true);
    setCandidates([]);
    return listPreconstructionSourceCandidates(projectId, {
      sourceType,
      search,
      limit: 20,
      signal: controller.signal,
    }).then((response) => {
      if (projectRef.current !== projectId || controller.signal.aborted) return null;
      setCandidates(response.items);
      return response.items;
    }).catch((error) => {
      if (isAbortError(error) || projectRef.current !== projectId) return null;
      onErrorRef.current?.("Unable to search preconstruction source candidates", error);
      return null;
    }).finally(() => {
      if (candidateRequestRef.current === controller) {
        candidateRequestRef.current = null;
        setIsCandidateLoading(false);
      }
    });
  }, [projectId]);

  // --- scope assertions -----------------------------------------------
  const loadAssertions = useCallback((overrides = {}) => {
    const reviewSetId = selectedReviewSetId;
    if (!projectId || !reviewSetId) {
      setAssertions(EMPTY_ASSERTIONS);
      return Promise.resolve(null);
    }
    const query = { ...assertionQueryRef.current, ...overrides };
    assertionQueryRef.current = query;
    assertionRequestRef.current?.abort();
    const controller = new AbortController();
    const identity = { projectId, reviewSetId };
    assertionRequestRef.current = controller;
    setAssertionQuery(query);
    setIsAssertionLoading(true);
    setAssertionError(null);
    return Promise.all([
      listPreconstructionAssertions(projectId, reviewSetId, {
        ...query,
        signal: controller.signal,
      }),
      listPreconstructionAssertionSets(projectId, reviewSetId, {
        limit: 50,
        signal: controller.signal,
      }),
    ])
      .then(([listing, sets]) => {
        if (
          projectRef.current !== identity.projectId ||
          selectedReviewSetRef.current !== identity.reviewSetId ||
          controller.signal.aborted
        ) return null;
        const next = {
          items: listing.items,
          total: listing.total,
          limit: listing.limit,
          offset: listing.offset,
          summary: listing.summary,
          latestAssertionSetId: listing.latest_assertion_set_id,
          taxonomyVersion: listing.taxonomy_version,
          sets: sets.items,
        };
        setAssertions(next);
        return next;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== identity.projectId) return null;
        setAssertionError(error);
        onErrorRef.current?.("Unable to load scope assertions", error);
        return null;
      })
      .finally(() => {
        if (assertionRequestRef.current === controller) {
          assertionRequestRef.current = null;
          setIsAssertionLoading(false);
        }
      });
  }, [projectId, selectedReviewSetId]);

  useEffect(() => {
    if (!selectedReviewSetId) return undefined;
    const startTimer = window.setTimeout(() => void loadAssertions(), 0);
    return () => window.clearTimeout(startTimer);
    // Reload only when the selected review set changes; filter changes call
    // loadAssertions directly with explicit overrides.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, selectedReviewSetId]);

  const loadTaxonomy = useCallback((options = {}) => {
    if (!projectId) return Promise.resolve(null);
    taxonomyRequestRef.current?.abort();
    const controller = new AbortController();
    taxonomyRequestRef.current = controller;
    setIsTaxonomyLoading(true);
    return getPreconstructionScopeTaxonomy(projectId, {
      ...options,
      signal: controller.signal,
    })
      .then((response) => {
        if (projectRef.current !== projectId || controller.signal.aborted) return null;
        setTaxonomy(response);
        return response;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== projectId) return null;
        onErrorRef.current?.("Unable to load the scope taxonomy", error);
        return null;
      })
      .finally(() => {
        if (taxonomyRequestRef.current === controller) {
          taxonomyRequestRef.current = null;
          setIsTaxonomyLoading(false);
        }
      });
  }, [projectId]);

  const reviewAssertion = useCallback((assertionId, decision) => runMutation(
    "Unable to record the assertion review",
    () => reviewPreconstructionAssertion(projectId, assertionId, decision),
    "none"
  ).then(async (result) => {
    if (result) await loadAssertions();
    return result;
  }), [loadAssertions, projectId, runMutation]);

  const createManualAssertion = useCallback((values) => runMutation(
    "Unable to create the manual assertion",
    () => createPreconstructionManualAssertion(projectId, selectedReviewSetId, values),
    "none"
  ).then(async (result) => {
    if (result) await loadAssertions({ offset: 0 });
    return result;
  }), [loadAssertions, projectId, runMutation, selectedReviewSetId]);

  // --- scope comparison -------------------------------------------------
  const loadComparison = useCallback((overrides = {}) => {
    const reviewSetId = selectedReviewSetId;
    if (!projectId || !reviewSetId) {
      setComparison(EMPTY_COMPARISON);
      return Promise.resolve(null);
    }
    const planId = overrides.planId ?? selectedPlanRef.current;
    const query = { ...findingQueryRef.current, ...overrides };
    delete query.planId;
    findingQueryRef.current = query;
    comparisonRequestRef.current?.abort();
    const controller = new AbortController();
    const identity = { projectId, reviewSetId };
    comparisonRequestRef.current = controller;
    setFindingQuery(query);
    setIsComparisonLoading(true);
    setComparisonError(null);

    return listPreconstructionComparisonPlans(projectId, reviewSetId, {
      limit: 50,
      signal: controller.signal,
    })
      .then(async (plans) => {
        if (
          projectRef.current !== identity.projectId ||
          selectedReviewSetRef.current !== identity.reviewSetId ||
          controller.signal.aborted
        ) return null;
        const active = plans.items.find((item) => item.id === planId)
          || plans.items.find((item) => item.status !== "archived")
          || plans.items[0]
          || null;
        selectedPlanRef.current = active?.id ?? null;
        if (!active) {
          const empty = {
            ...EMPTY_COMPARISON,
            plans: plans.items,
            comparisonTypes: plans.comparison_types,
          };
          setComparison(empty);
          return empty;
        }
        const [readiness, findings, sets] = await Promise.all([
          getPreconstructionComparisonReadiness(projectId, active.id, {
            signal: controller.signal,
          }),
          listPreconstructionFindings(projectId, active.id, {
            ...query,
            signal: controller.signal,
          }),
          listPreconstructionFindingSets(projectId, active.id, {
            limit: 50,
            signal: controller.signal,
          }),
        ]);
        if (
          projectRef.current !== identity.projectId ||
          selectedReviewSetRef.current !== identity.reviewSetId ||
          controller.signal.aborted
        ) return null;
        const next = {
          plans: plans.items,
          comparisonTypes: plans.comparison_types,
          selectedPlanId: active.id,
          readiness,
          findings: {
            items: findings.items,
            total: findings.total,
            limit: findings.limit,
            offset: findings.offset,
            summary: findings.summary,
            latestFindingSetId: findings.latest_finding_set_id,
            taxonomyVersion: findings.taxonomy_version,
            sets: sets.items,
          },
        };
        setComparison(next);
        return next;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== identity.projectId) return null;
        setComparisonError(error);
        onErrorRef.current?.("Unable to load scope comparison", error);
        return null;
      })
      .finally(() => {
        if (comparisonRequestRef.current === controller) {
          comparisonRequestRef.current = null;
          setIsComparisonLoading(false);
        }
      });
  }, [projectId, selectedReviewSetId]);

  useEffect(() => {
    if (!selectedReviewSetId) return undefined;
    const startTimer = window.setTimeout(() => void loadComparison(), 0);
    return () => window.clearTimeout(startTimer);
    // Filter changes call loadComparison directly with explicit overrides.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, selectedReviewSetId]);

  const selectComparisonPlan = useCallback((planId) => {
    selectedPlanRef.current = planId;
    findingQueryRef.current = DEFAULT_FINDING_QUERY;
    return loadComparison({ ...DEFAULT_FINDING_QUERY, planId });
  }, [loadComparison]);

  const createComparisonPlan = useCallback((values) => runMutation(
    "Unable to create the comparison plan",
    () => createPreconstructionComparisonPlan(projectId, selectedReviewSetId, values),
    "none"
  ).then(async (plan) => {
    if (plan) {
      selectedPlanRef.current = plan.id;
      await loadComparison({ planId: plan.id });
    }
    return plan;
  }), [loadComparison, projectId, runMutation, selectedReviewSetId]);

  const updateComparisonPlan = useCallback((planId, values) => runMutation(
    "Unable to update the comparison plan",
    () => updatePreconstructionComparisonPlan(projectId, planId, values),
    "none"
  ).then(async (plan) => {
    if (plan) await loadComparison({ planId });
    return plan;
  }), [loadComparison, projectId, runMutation]);

  const archiveComparisonPlan = useCallback((planId) => runMutation(
    "Unable to archive the comparison plan",
    () => archivePreconstructionComparisonPlan(projectId, planId),
    "none"
  ).then(async (plan) => {
    if (plan) await loadComparison({ planId });
    return plan;
  }), [loadComparison, projectId, runMutation]);

  const runComparison = useCallback((planId) => runMutation(
    "Unable to run the scope comparison",
    () => runPreconstructionComparison(projectId, planId, {}),
    "none"
  ).then(async (findingSet) => {
    if (findingSet) await loadComparison({ planId, offset: 0 });
    return findingSet;
  }), [loadComparison, projectId, runMutation]);

  const reviewFinding = useCallback((findingId, decision) => runMutation(
    "Unable to record the finding review",
    () => reviewPreconstructionFinding(projectId, findingId, decision),
    "none"
  ).then(async (result) => {
    if (result) {
      await loadComparison();
      // A review decision changes follow-up eligibility, so an open panel is
      // refreshed rather than left showing a stale offer.
      if (followUpFindingRef.current === findingId) {
        await loadFollowUpsRef.current?.(findingId);
      }
    }
    return result;
  }), [loadComparison, projectId, runMutation]);

  const createManualFinding = useCallback((planId, values) => runMutation(
    "Unable to create the manual finding",
    () => createPreconstructionManualFinding(projectId, planId, values),
    "none"
  ).then(async (result) => {
    if (result) await loadComparison({ planId, offset: 0 });
    return result;
  }), [loadComparison, projectId, runMutation]);

  // --- follow-up actions --------------------------------------------------
  // Deliberately scoped to one finding at a time. There is no bulk raise and
  // no route here that creates an RFI, Change Order, or Submittal: the human
  // creates those in their own workflow and links the result back.
  const loadFollowUps = useCallback((findingId) => {
    if (!projectId || !findingId) {
      followUpFindingRef.current = null;
      setFollowUps(EMPTY_FOLLOW_UPS);
      return Promise.resolve(null);
    }
    followUpRequestRef.current?.abort();
    const controller = new AbortController();
    const identity = { projectId, findingId };
    followUpRequestRef.current = controller;
    followUpFindingRef.current = findingId;
    setIsFollowUpLoading(true);

    return listPreconstructionFindingFollowUps(projectId, findingId, {
      signal: controller.signal,
    })
      .then((payload) => {
        if (
          projectRef.current !== identity.projectId ||
          followUpFindingRef.current !== identity.findingId ||
          controller.signal.aborted
        ) return null;
        const next = {
          findingId,
          items: payload.items,
          actions: payload.actions,
          availableActions: payload.available_actions,
          drafts: payload.drafts,
          eligible: payload.eligible,
          findingStatus: payload.finding_status,
        };
        setFollowUps(next);
        return next;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== identity.projectId) return null;
        onErrorRef.current?.("Unable to load follow-up actions", error);
        return null;
      })
      .finally(() => {
        if (followUpRequestRef.current === controller) {
          followUpRequestRef.current = null;
          setIsFollowUpLoading(false);
        }
      });
  }, [projectId]);

  useEffect(() => {
    loadFollowUpsRef.current = loadFollowUps;
  }, [loadFollowUps]);

  const closeFollowUps = useCallback(() => {
    followUpRequestRef.current?.abort();
    followUpRequestRef.current = null;
    followUpFindingRef.current = null;
    setFollowUps(EMPTY_FOLLOW_UPS);
  }, []);

  const createFollowUp = useCallback((findingId, values) => runMutation(
    "Unable to raise the follow-up",
    () => createPreconstructionFollowUp(projectId, findingId, values),
    "none"
  ).then(async (result) => {
    if (result) await loadFollowUps(findingId);
    return result;
  }), [loadFollowUps, projectId, runMutation]);

  const updateFollowUp = useCallback((findingId, followUpId, values) => runMutation(
    "Unable to update the follow-up draft",
    () => updatePreconstructionFollowUp(projectId, followUpId, values),
    "none"
  ).then(async (result) => {
    if (result) await loadFollowUps(findingId);
    return result;
  }), [loadFollowUps, projectId, runMutation]);

  const linkFollowUp = useCallback((findingId, followUpId, values) => runMutation(
    "Unable to link the follow-up record",
    () => linkPreconstructionFollowUp(projectId, followUpId, values),
    "none"
  ).then(async (result) => {
    if (result) await loadFollowUps(findingId);
    return result;
  }), [loadFollowUps, projectId, runMutation]);

  const closeFollowUp = useCallback((findingId, followUpId, values) => runMutation(
    "Unable to close the follow-up",
    () => closePreconstructionFollowUp(projectId, followUpId, values),
    "none"
  ).then(async (result) => {
    if (result) await loadFollowUps(findingId);
    return result;
  }), [loadFollowUps, projectId, runMutation]);

  const selectReviewSet = useCallback((reviewSetId) => {
    closeContent();
    closeFollowUps();
    comparisonRequestRef.current?.abort();
    selectedPlanRef.current = null;
    findingQueryRef.current = DEFAULT_FINDING_QUERY;
    setComparison(EMPTY_COMPARISON);
    setFindingQuery(DEFAULT_FINDING_QUERY);
    setComparisonError(null);
    assertionRequestRef.current?.abort();
    assertionQueryRef.current = DEFAULT_ASSERTION_QUERY;
    selectedReviewSetRef.current = reviewSetId;
    setSelectedReviewSetId(reviewSetId);
    setAssertions(EMPTY_ASSERTIONS);
    setAssertionQuery(DEFAULT_ASSERTION_QUERY);
    setAssertionError(null);
  }, [closeContent, closeFollowUps]);

  return {
    comparison,
    findingQuery,
    isComparisonLoading,
    comparisonError,
    followUps,
    isFollowUpLoading,
    loadFollowUps,
    closeFollowUps,
    createFollowUp,
    updateFollowUp,
    linkFollowUp,
    closeFollowUp,
    loadComparison,
    selectComparisonPlan,
    createComparisonPlan,
    updateComparisonPlan,
    archiveComparisonPlan,
    runComparison,
    reviewFinding,
    createManualFinding,
    assertions,
    assertionQuery,
    isAssertionLoading,
    assertionError,
    taxonomy,
    isTaxonomyLoading,
    loadAssertions,
    loadTaxonomy,
    reviewAssertion,
    createManualAssertion,
    filter,
    setFilter,
    reviewSets,
    selectedReviewSetId,
    selectReviewSet,
    detail,
    isListLoading,
    isDetailLoading,
    isSaving,
    listError,
    detailError,
    candidates,
    isCandidateLoading,
    content,
    contentSourceId,
    contentQuery,
    isContentLoading,
    contentError,
    refreshList: loadReviewSets,
    refreshDetail: loadDetail,
    createReviewSet,
    updateReviewSet,
    archiveReviewSet,
    addSource,
    updateSource,
    removeSource,
    requestRun,
    cancelRun,
    retryRun,
    prepareSource,
    cancelPreparation,
    retryPreparation,
    inspectContent: loadContent,
    refreshContent: loadContent,
    closeContent,
    searchCandidates,
  };
}

export default usePreconstruction;
