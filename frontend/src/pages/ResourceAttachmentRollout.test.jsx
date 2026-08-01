import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({
  listAttachments: vi.fn(),
  uploadAttachment: vi.fn(),
  downloadAttachment: vi.fn(),
  deleteAttachment: vi.fn(),
  listRelationships: vi.fn(),
  createRelationship: vi.fn(),
  deleteRelationship: vi.fn(),
  listRelationshipCandidates: vi.fn(),
}));

import ChangeOrdersPage from "./ChangeOrdersPage";
import PunchItemsPage from "./PunchItemsPage";
import RFIsPage from "./RFIsPage";
import SubmittalsPage from "./SubmittalsPage";
import { listAttachments, listRelationships } from "../services/api";


const noop = () => {};


function commonProps(projectId, records, resourceKey) {
  return {
    projectId,
    projectName: "North Ridge",
    [resourceKey]: records,
    projectCompanies: [],
    formatDate: (value) => value || "-",
    onNavigate: noop,
    onLogout: noop,
    onRefresh: noop,
    onSave: noop,
    onEdit: vi.fn(),
    onCancelEdit: noop,
    onDelete: vi.fn(),
    onAttachmentError: vi.fn(),
  };
}


function rfiProps(projectId, records, overrides = {}) {
  return {
    ...commonProps(projectId, records, "rfis"),
    editingRFIId: null,
    editingRFINumber: "",
    rfiSubject: "",
    rfiQuestion: "",
    rfiResponsibleCompany: "",
    rfiSubmittedDate: "2026-07-26",
    rfiDueDate: "",
    rfiResponse: "",
    rfiStatus: "Open",
    onSubjectChange: noop,
    onQuestionChange: noop,
    onResponsibleCompanyChange: noop,
    onSubmittedDateChange: noop,
    onDueDateChange: noop,
    onResponseChange: noop,
    onStatusChange: noop,
    ...overrides,
  };
}


function submittalProps(projectId, records, overrides = {}) {
  return {
    ...commonProps(projectId, records, "submittals"),
    editingSubmittalId: null,
    editingSubmittalNumber: "",
    specificationSection: "",
    title: "",
    responsibleCompany: "",
    submittedDate: "",
    requiredByDate: "",
    reviewedDate: "",
    status: "Draft",
    reviewer: "",
    remarks: "",
    onSpecificationSectionChange: noop,
    onTitleChange: noop,
    onResponsibleCompanyChange: noop,
    onSubmittedDateChange: noop,
    onRequiredByDateChange: noop,
    onReviewedDateChange: noop,
    onStatusChange: noop,
    onReviewerChange: noop,
    onRemarksChange: noop,
    ...overrides,
  };
}


function punchItemProps(projectId, records, overrides = {}) {
  return {
    ...commonProps(projectId, records, "punchItems"),
    editingPunchItemId: null,
    editingPunchItemNumber: "",
    location: "",
    trade: "",
    description: "",
    responsibleCompany: "",
    assignedTo: "",
    priority: "Medium",
    status: "Open",
    dueDate: "",
    completedDate: "",
    onLocationChange: noop,
    onTradeChange: noop,
    onDescriptionChange: noop,
    onResponsibleCompanyChange: noop,
    onAssignedToChange: noop,
    onPriorityChange: noop,
    onStatusChange: noop,
    onDueDateChange: noop,
    onCompletedDateChange: noop,
    ...overrides,
  };
}


function changeOrderProps(projectId, records, overrides = {}) {
  return {
    ...commonProps(projectId, records, "changeOrders"),
    editingChangeOrderId: null,
    editingChangeOrderNumber: "",
    changeOrderDate: "2026-07-26",
    changeOrderTitle: "",
    changeOrderCompany: "",
    changeOrderStatus: "Draft",
    changeOrderDescription: "",
    changeOrderReason: "",
    changeOrderProposedAmount: "",
    changeOrderApprovedAmount: "",
    changeOrderScheduleImpactDays: "",
    changeOrderRequestedDate: "",
    changeOrderSubmittedDate: "",
    changeOrderApprovedDate: "",
    changeOrderExecutedDate: "",
    changeOrderResponsibleParty: "",
    onDateChange: noop,
    onTitleChange: noop,
    onCompanyChange: noop,
    onStatusChange: noop,
    onDescriptionChange: noop,
    onReasonChange: noop,
    onProposedAmountChange: noop,
    onApprovedAmountChange: noop,
    onScheduleImpactDaysChange: noop,
    onRequestedDateChange: noop,
    onSubmittedDateChange: noop,
    onApprovedDateChange: noop,
    onExecutedDateChange: noop,
    onResponsiblePartyChange: noop,
    ...overrides,
  };
}


const resources = [
  {
    name: "RFI",
    Component: RFIsPage,
    parentType: "rfi",
    title: "RFI Attachments",
    relationshipTitle: "RFI Relationships",
    records: [
      {
        id: 11,
        number: "RFI-011",
        subject: "Storefront dimensions",
        question: "Confirm dimensions.",
        submitted_date: "2026-07-20",
        status: "Open",
      },
      {
        id: 12,
        number: "RFI-012",
        subject: "Finish color",
        question: "Confirm finish.",
        submitted_date: "2026-07-21",
        status: "Pending",
      },
    ],
    identifier: (record) => `RFI ${record.number}`,
    props: rfiProps,
    editOverrides: {
      editingRFIId: 12,
      editingRFINumber: "RFI-012",
    },
    editLabel: "Edit RFI-012",
    deleteLabel: "Delete RFI-011",
  },
  {
    name: "Submittal",
    Component: SubmittalsPage,
    parentType: "submittal",
    title: "Submittal Attachments",
    relationshipTitle: "Submittal Relationships",
    records: [
      {
        id: 21,
        number: "SUB-021",
        specification_section: "03 30 00",
        title: "Concrete mix",
        status: "Draft",
      },
      {
        id: 22,
        number: "SUB-022",
        specification_section: "08 41 00",
        title: "Storefront",
        status: "Submitted",
      },
    ],
    identifier: (record) => `Submittal ${record.number}`,
    props: submittalProps,
    editOverrides: {
      editingSubmittalId: 22,
      editingSubmittalNumber: "SUB-022",
    },
    editLabel: "Edit SUB-022",
    deleteLabel: "Delete SUB-021",
  },
  {
    name: "Punch Item",
    Component: PunchItemsPage,
    parentType: "punch_item",
    title: "Punch Item Attachments",
    relationshipTitle: "Punch Item Relationships",
    records: [
      {
        id: 31,
        number: "PUNCH-031",
        location: "Level 1",
        description: "Repair wall.",
        priority: "Medium",
        status: "Open",
      },
      {
        id: 32,
        number: "PUNCH-032",
        location: "Level 2",
        description: "Repair ceiling.",
        priority: "High",
        status: "In Progress",
      },
    ],
    identifier: (record) => `Punch Item ${record.number}`,
    props: punchItemProps,
    editOverrides: {
      editingPunchItemId: 32,
      editingPunchItemNumber: "PUNCH-032",
    },
    editLabel: "Edit PUNCH-032",
    deleteLabel: "Delete PUNCH-031",
  },
  {
    name: "Change Order",
    Component: ChangeOrdersPage,
    parentType: "change_order",
    title: "Change Order Attachments",
    relationshipTitle: "Change Order Relationships",
    records: [
      {
        id: 41,
        co_number: "CO-041",
        date: "2026-07-20",
        title: "Entrance revision",
        status: "Draft",
      },
      {
        id: 42,
        co_number: "CO-042",
        date: "2026-07-21",
        title: "Drainage revision",
        status: "Pending",
      },
    ],
    identifier: (record) => `change order ${record.co_number}`,
    props: changeOrderProps,
    editOverrides: {
      editingChangeOrderId: 42,
      editingChangeOrderNumber: "CO-042",
    },
    editLabel: "Edit change order CO-042",
    deleteLabel: "Delete change order CO-041",
  },
];


function attachment(id, filename) {
  return {
    id,
    original_filename: filename,
    mime_type: "image/jpeg",
    size_bytes: 4096,
    created_at: "2026-07-26T12:00:00Z",
  };
}


describe.each(resources)("$name attachment rollout", (resource) => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachments.mockResolvedValue({
      attachments: [attachment(91, "field-photo.jpg")],
    });
  });

  it("loads only the expanded persisted record with accessible controls", async () => {
    const user = userEvent.setup();
    const props = resource.props(1, resource.records);
    const { Component } = resource;

    render(<Component {...props} />);
    await new Promise((resolve) => window.setTimeout(resolve, 0));
    expect(listAttachments).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("heading", { name: resource.title })
    ).not.toBeInTheDocument();

    const identifier = resource.identifier(resource.records[0]);
    const open = screen.getByRole("button", {
      name: `Attachments for ${identifier}`,
    });
    expect(open).toHaveAttribute("aria-expanded", "false");
    open.focus();
    await user.keyboard("{Enter}");

    expect(props.onEdit).not.toHaveBeenCalled();
    expect(open).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("heading", { name: resource.title })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/choose files/i)).toBeEnabled();
    expect(
      await screen.findByRole("button", {
        name: "Delete field-photo.jpg",
      })
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: "Preview field-photo.jpg" })
    ).toBeInTheDocument();
    expect(listAttachments).toHaveBeenCalledTimes(1);
    expect(listAttachments).toHaveBeenCalledWith(
      1,
      resource.parentType,
      resource.records[0].id,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );

    await user.click(
      screen.getByRole("button", {
        name: `Close attachments for ${identifier}`,
      })
    );
    expect(
      screen.queryByRole("heading", { name: resource.title })
    ).not.toBeInTheDocument();
  });

  it("replaces stale data and keeps the same identity open during edit", async () => {
    const user = userEvent.setup();
    let resolveFirst;
    listAttachments.mockImplementation((_projectId, _type, parentId) => {
      if (parentId === resource.records[0].id) {
        return new Promise((resolve) => {
          resolveFirst = resolve;
        });
      }
      return Promise.resolve({
        attachments: [attachment(92, "second-record.jpg")],
      });
    });
    const props = resource.props(1, resource.records);
    const { Component } = resource;
    const { rerender } = render(<Component {...props} />);

    await user.click(
      screen.getByRole("button", {
        name: `Attachments for ${resource.identifier(resource.records[0])}`,
      })
    );
    await waitFor(() => expect(listAttachments).toHaveBeenCalledTimes(1));
    await user.click(
      screen.getByRole("button", {
        name: `Attachments for ${resource.identifier(resource.records[1])}`,
      })
    );
    expect(await screen.findByText("second-record.jpg")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: resource.editLabel })
    );
    expect(props.onEdit).toHaveBeenCalledWith(resource.records[1]);
    rerender(
      <Component
        {...resource.props(
          1,
          resource.records.map((record) => ({ ...record })),
          resource.editOverrides
        )}
      />
    );
    expect(
      screen.getByRole("heading", { name: resource.title })
    ).toBeInTheDocument();
    expect(listAttachments).toHaveBeenCalledTimes(2);

    await act(async () => {
      resolveFirst({
        attachments: [attachment(91, "stale-record.jpg")],
      });
    });
    expect(screen.queryByText("stale-record.jpg")).not.toBeInTheDocument();
  });

  it("keeps the panel for failed parent deletion and closes after success", async () => {
    const user = userEvent.setup();
    const props = resource.props(1, resource.records);
    const { Component } = resource;
    const { rerender } = render(<Component {...props} />);

    await user.click(
      screen.getByRole("button", {
        name: `Attachments for ${resource.identifier(resource.records[0])}`,
      })
    );
    await screen.findByText("field-photo.jpg");
    await user.click(
      screen.getByRole("button", { name: resource.deleteLabel })
    );
    expect(props.onDelete).toHaveBeenCalledWith(
      resource.records[0].id,
      resource.records[0].number || resource.records[0].co_number
    );
    expect(
      screen.getByRole("heading", { name: resource.title })
    ).toBeInTheDocument();

    rerender(
      <Component
        {...resource.props(1, resource.records.slice(1))}
      />
    );
    expect(
      screen.queryByRole("heading", { name: resource.title })
    ).not.toBeInTheDocument();
    expect(listAttachments).toHaveBeenCalledTimes(1);
  });

  it("clears selection on project change and reports failures globally", async () => {
    const user = userEvent.setup();
    const requestError = new Error("Storage is unavailable");
    listAttachments.mockRejectedValue(requestError);
    const props = resource.props(1, resource.records);
    const { Component } = resource;
    const { rerender } = render(
      <Component key={1} {...props} />
    );

    await user.click(
      screen.getByRole("button", {
        name: `Attachments for ${resource.identifier(resource.records[0])}`,
      })
    );
    expect(await screen.findByText(requestError.message)).toBeInTheDocument();
    expect(props.onAttachmentError).toHaveBeenCalledWith(
      "Unable to load attachments",
      requestError
    );

    rerender(
      <Component
        key={2}
        {...resource.props(2, resource.records)}
      />
    );
    expect(
      screen.queryByRole("heading", { name: resource.title })
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", {
      name: resource.name === "Change Order"
        ? "Create Change Order"
        : `Create ${resource.name}`,
    })).toBeEnabled();
  });
});


describe.each(resources)("$name relationship rollout", (resource) => {
  beforeEach(() => {
    vi.clearAllMocks();
    listRelationships.mockResolvedValue({
      relationships: [],
      pagination: {
        limit: 50,
        offset: 0,
        total: 0,
        has_more: false,
      },
    });
  });

  it("loads exactly one selected persisted record without row fan-out", async () => {
    const user = userEvent.setup();
    const props = resource.props(1, resource.records);
    const { Component } = resource;
    render(<Component {...props} />);

    await new Promise((resolve) => window.setTimeout(resolve, 0));
    expect(listRelationships).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("heading", { name: resource.relationshipTitle })
    ).not.toBeInTheDocument();

    const firstIdentifier = resource.identifier(resource.records[0]);
    await user.click(
      screen.getByRole("button", {
        name: `Relationships for ${firstIdentifier}`,
      })
    );
    expect(
      screen.getByRole("heading", { name: resource.relationshipTitle })
    ).toBeInTheDocument();
    await waitFor(() => expect(listRelationships).toHaveBeenCalledTimes(1));
    expect(listRelationships).toHaveBeenLastCalledWith(
      1,
      resource.parentType,
      resource.records[0].id,
      expect.objectContaining({
        limit: 50,
        offset: 0,
        signal: expect.any(AbortSignal),
      })
    );

    await user.click(
      screen.getByRole("button", {
        name: `Relationships for ${resource.identifier(resource.records[1])}`,
      })
    );
    await waitFor(() => expect(listRelationships).toHaveBeenCalledTimes(2));
    expect(listRelationships).toHaveBeenLastCalledWith(
      1,
      resource.parentType,
      resource.records[1].id,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(
      screen.getAllByRole("heading", { name: resource.relationshipTitle })
    ).toHaveLength(1);
  });

  it("keeps create and edit forms independent from relationship state", async () => {
    const user = userEvent.setup();
    const props = resource.props(1, resource.records);
    const { Component } = resource;
    render(<Component {...props} />);

    expect(screen.queryByText("No relationships yet.")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: `Relationships for ${resource.identifier(resource.records[0])}`,
      })
    );
    await screen.findByText("No relationships yet.");
    await user.click(screen.getByRole("button", { name: resource.editLabel }));
    expect(props.onEdit).toHaveBeenCalledWith(resource.records[1]);
    expect(
      screen.getByRole("heading", { name: resource.relationshipTitle })
    ).toBeInTheDocument();
    expect(listRelationships).toHaveBeenCalledTimes(1);
  });

  it("clears on project change and reports request failures globally", async () => {
    const user = userEvent.setup();
    const requestError = new Error("Relationships unavailable");
    listRelationships.mockRejectedValueOnce(requestError);
    const props = resource.props(1, resource.records);
    const { Component } = resource;
    const view = render(<Component key={1} {...props} />);

    await user.click(
      screen.getByRole("button", {
        name: `Relationships for ${resource.identifier(resource.records[0])}`,
      })
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      requestError.message
    );
    expect(props.onAttachmentError).toHaveBeenCalledWith(
      "Unable to load relationships",
      requestError
    );

    view.rerender(
      <Component key={2} {...resource.props(2, resource.records)} />
    );
    expect(
      screen.queryByRole("heading", { name: resource.relationshipTitle })
    ).not.toBeInTheDocument();
  });
});
