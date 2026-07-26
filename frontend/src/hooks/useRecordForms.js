import { useState } from "react";

import {
  createChangeOrder,
  createDailyLog,
  createInspection,
  createNoteDelay,
  createPunchItem,
  createProject,
  createProjectCompany,
  createRFI,
  createSubmittal,
  deleteChangeOrder,
  deletePunchItem,
  deleteRFI,
  deleteSubmittal,
  updateRFI,
  updateChangeOrder,
  updatePunchItem,
  updateSubmittal,
} from "../services/api";
import {
  normalizeMoneyInput,
  normalizeOptionalValue,
  normalizeScheduleImpact,
  validateChangeOrderForm,
} from "../utils/changeOrder";
import { toLocalDateInputValue } from "../utils/date";

/**
 * Owns the field state and submission handlers for every record form:
 * projects, daily logs, inspections, notes & delays, change orders, and
 * project companies — plus the record refresh actions. Validation messages
 * and success notices are identical to the pre-refactor behavior.
 */
function useRecordForms({
  selectedProjectId,
  runOperation,
  showNotice,
  reportRequestError,
  reportValidationError,
  setProjects,
  navigateTo,
  loadDailyLogs,
  loadInspections,
  loadNotesDelays,
  loadChangeOrders,
  loadRFIs,
  loadSubmittals,
  loadPunchItems,
  loadProjectCompanies,
  clearNotice,
}) {
  const [newProjectName, setNewProjectName] = useState("");
  const [logDate, setLogDate] = useState(toLocalDateInputValue);
  const [logCompany, setLogCompany] = useState("");
  const [logManpower, setLogManpower] = useState("");
  const [logNotes, setLogNotes] = useState("");
  const [inspectionDate, setInspectionDate] = useState(toLocalDateInputValue);
  const [inspectionType, setInspectionType] = useState("");
  const [inspectionStatus, setInspectionStatus] = useState("Pending");
  const [noteDelayDate, setNoteDelayDate] = useState(toLocalDateInputValue);
  const [noteDelayType, setNoteDelayType] = useState("Note");
  const [noteDelayCompany, setNoteDelayCompany] = useState("");
  const [noteDelayDescription, setNoteDelayDescription] = useState("");
  const [noteDelayImpact, setNoteDelayImpact] = useState("");
  const [editingChangeOrderId, setEditingChangeOrderId] = useState(null);
  const [editingChangeOrderNumber, setEditingChangeOrderNumber] = useState("");
  const [changeOrderDate, setChangeOrderDate] = useState(toLocalDateInputValue);
  const [changeOrderTitle, setChangeOrderTitle] = useState("");
  const [changeOrderCompany, setChangeOrderCompany] = useState("");
  const [changeOrderStatus, setChangeOrderStatus] = useState("Pending");
  const [changeOrderDescription, setChangeOrderDescription] = useState("");
  const [changeOrderReason, setChangeOrderReason] = useState("");
  const [changeOrderProposedAmount, setChangeOrderProposedAmount] =
    useState("");
  const [changeOrderApprovedAmount, setChangeOrderApprovedAmount] =
    useState("");
  const [changeOrderScheduleImpactDays, setChangeOrderScheduleImpactDays] =
    useState("");
  const [changeOrderRequestedDate, setChangeOrderRequestedDate] =
    useState("");
  const [changeOrderSubmittedDate, setChangeOrderSubmittedDate] =
    useState("");
  const [changeOrderApprovedDate, setChangeOrderApprovedDate] = useState("");
  const [changeOrderExecutedDate, setChangeOrderExecutedDate] = useState("");
  const [changeOrderResponsibleParty, setChangeOrderResponsibleParty] =
    useState("");
  const [changeOrderProjectId, setChangeOrderProjectId] =
    useState(selectedProjectId);
  const [editingRFIId, setEditingRFIId] = useState(null);
  const [editingRFINumber, setEditingRFINumber] = useState("");
  const [rfiSubject, setRFISubject] = useState("");
  const [rfiQuestion, setRFIQuestion] = useState("");
  const [rfiResponsibleCompany, setRFIResponsibleCompany] = useState("");
  const [rfiSubmittedDate, setRFISubmittedDate] =
    useState(toLocalDateInputValue);
  const [rfiDueDate, setRFIDueDate] = useState("");
  const [rfiResponse, setRFIResponse] = useState("");
  const [rfiStatus, setRFIStatus] = useState("Open");
  const [rfiProjectId, setRFIProjectId] = useState(selectedProjectId);
  const [editingSubmittalId, setEditingSubmittalId] = useState(null);
  const [editingSubmittalNumber, setEditingSubmittalNumber] = useState("");
  const [submittalSpecificationSection, setSubmittalSpecificationSection] =
    useState("");
  const [submittalTitle, setSubmittalTitle] = useState("");
  const [submittalResponsibleCompany, setSubmittalResponsibleCompany] =
    useState("");
  const [submittalSubmittedDate, setSubmittalSubmittedDate] = useState("");
  const [submittalRequiredByDate, setSubmittalRequiredByDate] = useState("");
  const [submittalReviewedDate, setSubmittalReviewedDate] = useState("");
  const [submittalStatus, setSubmittalStatus] = useState("Draft");
  const [submittalReviewer, setSubmittalReviewer] = useState("");
  const [submittalRemarks, setSubmittalRemarks] = useState("");
  const [submittalProjectId, setSubmittalProjectId] =
    useState(selectedProjectId);
  const [editingPunchItemId, setEditingPunchItemId] = useState(null);
  const [editingPunchItemNumber, setEditingPunchItemNumber] = useState("");
  const [punchItemLocation, setPunchItemLocation] = useState("");
  const [punchItemTrade, setPunchItemTrade] = useState("");
  const [punchItemDescription, setPunchItemDescription] = useState("");
  const [punchItemResponsibleCompany, setPunchItemResponsibleCompany] =
    useState("");
  const [punchItemAssignedTo, setPunchItemAssignedTo] = useState("");
  const [punchItemPriority, setPunchItemPriority] = useState("Medium");
  const [punchItemStatus, setPunchItemStatus] = useState("Open");
  const [punchItemDueDate, setPunchItemDueDate] = useState("");
  const [punchItemCompletedDate, setPunchItemCompletedDate] = useState("");
  const [punchItemProjectId, setPunchItemProjectId] =
    useState(selectedProjectId);
  const [companyName, setCompanyName] = useState("");
  const [companyTrade, setCompanyTrade] = useState("");

  if (changeOrderProjectId !== selectedProjectId) {
    setChangeOrderProjectId(selectedProjectId);
    setEditingChangeOrderId(null);
    setEditingChangeOrderNumber("");
    setChangeOrderDate(toLocalDateInputValue());
    setChangeOrderTitle("");
    setChangeOrderCompany("");
    setChangeOrderStatus("Pending");
    setChangeOrderDescription("");
    setChangeOrderReason("");
    setChangeOrderProposedAmount("");
    setChangeOrderApprovedAmount("");
    setChangeOrderScheduleImpactDays("");
    setChangeOrderRequestedDate("");
    setChangeOrderSubmittedDate("");
    setChangeOrderApprovedDate("");
    setChangeOrderExecutedDate("");
    setChangeOrderResponsibleParty("");
    clearNotice();
  }

  if (rfiProjectId !== selectedProjectId) {
    setRFIProjectId(selectedProjectId);
    setEditingRFIId(null);
    setEditingRFINumber("");
    setRFISubject("");
    setRFIQuestion("");
    setRFIResponsibleCompany("");
    setRFISubmittedDate(toLocalDateInputValue());
    setRFIDueDate("");
    setRFIResponse("");
    setRFIStatus("Open");
  }

  if (submittalProjectId !== selectedProjectId) {
    setSubmittalProjectId(selectedProjectId);
    setEditingSubmittalId(null);
    setEditingSubmittalNumber("");
    setSubmittalSpecificationSection("");
    setSubmittalTitle("");
    setSubmittalResponsibleCompany("");
    setSubmittalSubmittedDate("");
    setSubmittalRequiredByDate("");
    setSubmittalReviewedDate("");
    setSubmittalStatus("Draft");
    setSubmittalReviewer("");
    setSubmittalRemarks("");
  }

  if (punchItemProjectId !== selectedProjectId) {
    setPunchItemProjectId(selectedProjectId);
    setEditingPunchItemId(null);
    setEditingPunchItemNumber("");
    setPunchItemLocation("");
    setPunchItemTrade("");
    setPunchItemDescription("");
    setPunchItemResponsibleCompany("");
    setPunchItemAssignedTo("");
    setPunchItemPriority("Medium");
    setPunchItemStatus("Open");
    setPunchItemDueDate("");
    setPunchItemCompletedDate("");
  }

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      reportValidationError("Enter a project name before adding it.");
      return;
    }

    return runOperation("createProject", async () => {
      try {
        const project = await createProject({
          name: newProjectName,
        });

        setProjects((currentProjects) => [...currentProjects, project]);
        setNewProjectName("");
        navigateTo("projectDashboard", project.id);
        showNotice("success", `${project.name} was added.`);
      } catch (error) {
        reportRequestError("Unable to create project", error);
      }
    });
  };

  const handleCreateDailyLog = async () => {
    if (!logDate || !logCompany || !logManpower) {
      reportValidationError(
        "Complete the date, company, and manpower fields before saving."
      );
      return;
    }

    return runOperation("createDailyLog", async () => {
      try {
        await createDailyLog(selectedProjectId, {
          date: logDate,
          company: logCompany,
          manpower: Number(logManpower),
          notes: logNotes,
        });

        setLogDate(toLocalDateInputValue());
        setLogCompany("");
        setLogManpower("");
        setLogNotes("");
        await loadDailyLogs();
        showNotice("success", "Daily log saved.");
      } catch (error) {
        reportRequestError("Unable to create daily log", error);
      }
    });
  };

  const handleCreateInspection = async () => {
    if (!inspectionDate || !inspectionType) {
      reportValidationError(
        "Complete the date and inspection fields before saving."
      );
      return;
    }

    return runOperation("createInspection", async () => {
      try {
        await createInspection(selectedProjectId, {
          date: inspectionDate,
          inspection_type: inspectionType,
          status: inspectionStatus,
        });

        setInspectionDate(toLocalDateInputValue());
        setInspectionType("");
        setInspectionStatus("Pending");
        await loadInspections();
        showNotice("success", "Inspection saved.");
      } catch (error) {
        reportRequestError("Unable to create inspection", error);
      }
    });
  };

  const handleCreateNoteDelay = async () => {
    if (!noteDelayDate || !noteDelayDescription.trim()) {
      reportValidationError(
        "Complete the date and description fields before saving."
      );
      return;
    }

    return runOperation("createNoteDelay", async () => {
      try {
        await createNoteDelay(selectedProjectId, {
          date: noteDelayDate,
          entry_type: noteDelayType,
          company: noteDelayCompany,
          description: noteDelayDescription,
          impact: noteDelayImpact,
        });

        setNoteDelayDate(toLocalDateInputValue());
        setNoteDelayType("Note");
        setNoteDelayCompany("");
        setNoteDelayDescription("");
        setNoteDelayImpact("");
        await loadNotesDelays();
        showNotice(
          "success",
          noteDelayType === "Delay" ? "Delay recorded." : "Note saved."
        );
      } catch (error) {
        reportRequestError("Unable to create note or delay", error);
      }
    });
  };

  const resetChangeOrderForm = () => {
    setEditingChangeOrderId(null);
    setEditingChangeOrderNumber("");
    setChangeOrderDate(toLocalDateInputValue());
    setChangeOrderTitle("");
    setChangeOrderCompany("");
    setChangeOrderStatus("Pending");
    setChangeOrderDescription("");
    setChangeOrderReason("");
    setChangeOrderProposedAmount("");
    setChangeOrderApprovedAmount("");
    setChangeOrderScheduleImpactDays("");
    setChangeOrderRequestedDate("");
    setChangeOrderSubmittedDate("");
    setChangeOrderApprovedDate("");
    setChangeOrderExecutedDate("");
    setChangeOrderResponsibleParty("");
  };

  const handleEditChangeOrder = (changeOrder) => {
    setEditingChangeOrderId(changeOrder.id);
    setEditingChangeOrderNumber(changeOrder.co_number);
    setChangeOrderDate(changeOrder.date || toLocalDateInputValue());
    setChangeOrderTitle(changeOrder.title || "");
    setChangeOrderCompany(changeOrder.company || "");
    setChangeOrderStatus(changeOrder.status);
    setChangeOrderDescription(changeOrder.description || "");
    setChangeOrderReason(changeOrder.reason || "");
    setChangeOrderProposedAmount(changeOrder.proposed_amount ?? "");
    setChangeOrderApprovedAmount(changeOrder.approved_amount ?? "");
    setChangeOrderScheduleImpactDays(
      changeOrder.schedule_impact_days ?? ""
    );
    setChangeOrderRequestedDate(changeOrder.requested_date || "");
    setChangeOrderSubmittedDate(changeOrder.submitted_date || "");
    setChangeOrderApprovedDate(changeOrder.approved_date || "");
    setChangeOrderExecutedDate(changeOrder.executed_date || "");
    setChangeOrderResponsibleParty(changeOrder.responsible_party || "");
  };

  const handleSaveChangeOrder = async () => {
    const validationMessage = validateChangeOrderForm({
      date: changeOrderDate,
      title: changeOrderTitle,
      description: changeOrderDescription,
      proposedAmount: changeOrderProposedAmount,
      approvedAmount: changeOrderApprovedAmount,
      scheduleImpactDays: changeOrderScheduleImpactDays,
      requestedDate: changeOrderRequestedDate,
      submittedDate: changeOrderSubmittedDate,
      approvedDate: changeOrderApprovedDate,
      executedDate: changeOrderExecutedDate,
    });

    if (validationMessage) {
      reportValidationError(validationMessage);
      return;
    }

    return runOperation("saveChangeOrder", async () => {
      const payload = {
        date: changeOrderDate,
        title: normalizeOptionalValue(changeOrderTitle),
        company: normalizeOptionalValue(changeOrderCompany),
        status: changeOrderStatus.trim(),
        description: normalizeOptionalValue(changeOrderDescription),
        reason: normalizeOptionalValue(changeOrderReason),
        proposed_amount: normalizeMoneyInput(changeOrderProposedAmount),
        approved_amount: normalizeMoneyInput(changeOrderApprovedAmount),
        schedule_impact_days: normalizeScheduleImpact(
          changeOrderScheduleImpactDays
        ),
        requested_date: normalizeOptionalValue(changeOrderRequestedDate),
        submitted_date: normalizeOptionalValue(changeOrderSubmittedDate),
        approved_date: normalizeOptionalValue(changeOrderApprovedDate),
        executed_date: normalizeOptionalValue(changeOrderExecutedDate),
        responsible_party: normalizeOptionalValue(
          changeOrderResponsibleParty
        ),
      };
      const isEditing = editingChangeOrderId !== null;

      try {
        if (isEditing) {
          await updateChangeOrder(
            selectedProjectId,
            editingChangeOrderId,
            payload
          );
        } else {
          await createChangeOrder(selectedProjectId, payload);
        }

        resetChangeOrderForm();
        await loadChangeOrders();
        showNotice(
          "success",
          isEditing ? "Change order updated." : "Change order created."
        );
      } catch (error) {
        reportRequestError(
          isEditing
            ? "Unable to update change order"
            : "Unable to create change order",
          error
        );
      }
    });
  };

  /** Executes a confirmed change-order deletion (dialog lives in App). */
  const performChangeOrderDelete = async (id) => {
    try {
      await deleteChangeOrder(selectedProjectId, id);
      if (editingChangeOrderId === id) {
        resetChangeOrderForm();
      }
      await loadChangeOrders();
      showNotice("success", "Change order deleted.");
    } catch (error) {
      reportRequestError("Unable to delete change order", error);
    }
  };

  const resetRFIForm = () => {
    setEditingRFIId(null);
    setEditingRFINumber("");
    setRFISubject("");
    setRFIQuestion("");
    setRFIResponsibleCompany("");
    setRFISubmittedDate(toLocalDateInputValue());
    setRFIDueDate("");
    setRFIResponse("");
    setRFIStatus("Open");
  };

  const handleEditRFI = (rfi) => {
    setEditingRFIId(rfi.id);
    setEditingRFINumber(rfi.number);
    setRFISubject(rfi.subject);
    setRFIQuestion(rfi.question);
    setRFIResponsibleCompany(rfi.responsible_company || "");
    setRFISubmittedDate(rfi.submitted_date);
    setRFIDueDate(rfi.due_date || "");
    setRFIResponse(rfi.response || "");
    setRFIStatus(rfi.status);
  };

  const handleSaveRFI = async () => {
    const subject = rfiSubject.trim();
    const question = rfiQuestion.trim();

    if (!subject || !question || !rfiSubmittedDate) {
      reportValidationError(
        "Complete the subject, question, and submitted date before saving."
      );
      return;
    }

    if (rfiDueDate && rfiDueDate < rfiSubmittedDate) {
      reportValidationError(
        "Due date cannot be earlier than submitted date."
      );
      return;
    }

    return runOperation("saveRFI", async () => {
      const payload = {
        subject,
        question,
        responsible_company: rfiResponsibleCompany.trim() || null,
        submitted_date: rfiSubmittedDate,
        due_date: rfiDueDate || null,
        response: rfiResponse.trim() || null,
        status: rfiStatus,
      };
      const isEditing = editingRFIId !== null;

      try {
        if (isEditing) {
          await updateRFI(selectedProjectId, editingRFIId, payload);
        } else {
          await createRFI(selectedProjectId, payload);
        }

        resetRFIForm();
        await loadRFIs();
        showNotice("success", isEditing ? "RFI updated." : "RFI created.");
      } catch (error) {
        reportRequestError(
          isEditing ? "Unable to update RFI" : "Unable to create RFI",
          error
        );
      }
    });
  };

  const performRFIDelete = async (id) => {
    try {
      await deleteRFI(selectedProjectId, id);
      await loadRFIs();
      showNotice("success", "RFI deleted.");
    } catch (error) {
      reportRequestError("Unable to delete RFI", error);
    }
  };

  const resetSubmittalForm = () => {
    setEditingSubmittalId(null);
    setEditingSubmittalNumber("");
    setSubmittalSpecificationSection("");
    setSubmittalTitle("");
    setSubmittalResponsibleCompany("");
    setSubmittalSubmittedDate("");
    setSubmittalRequiredByDate("");
    setSubmittalReviewedDate("");
    setSubmittalStatus("Draft");
    setSubmittalReviewer("");
    setSubmittalRemarks("");
  };

  const handleEditSubmittal = (submittal) => {
    setEditingSubmittalId(submittal.id);
    setEditingSubmittalNumber(submittal.number);
    setSubmittalSpecificationSection(submittal.specification_section);
    setSubmittalTitle(submittal.title);
    setSubmittalResponsibleCompany(
      submittal.responsible_company || ""
    );
    setSubmittalSubmittedDate(submittal.submitted_date || "");
    setSubmittalRequiredByDate(submittal.required_by_date || "");
    setSubmittalReviewedDate(submittal.reviewed_date || "");
    setSubmittalStatus(submittal.status);
    setSubmittalReviewer(submittal.reviewer || "");
    setSubmittalRemarks(submittal.remarks || "");
  };

  const handleSaveSubmittal = async () => {
    const specificationSection = submittalSpecificationSection.trim();
    const title = submittalTitle.trim();

    if (!specificationSection || !title) {
      reportValidationError(
        "Complete the specification section and title before saving."
      );
      return;
    }

    if (
      submittalSubmittedDate &&
      submittalRequiredByDate &&
      submittalRequiredByDate < submittalSubmittedDate
    ) {
      reportValidationError(
        "Required-by date cannot be earlier than submitted date."
      );
      return;
    }

    if (
      submittalSubmittedDate &&
      submittalReviewedDate &&
      submittalReviewedDate < submittalSubmittedDate
    ) {
      reportValidationError(
        "Reviewed date cannot be earlier than submitted date."
      );
      return;
    }

    return runOperation("saveSubmittal", async () => {
      const payload = {
        specification_section: specificationSection,
        title,
        responsible_company:
          submittalResponsibleCompany.trim() || null,
        submitted_date: submittalSubmittedDate || null,
        required_by_date: submittalRequiredByDate || null,
        reviewed_date: submittalReviewedDate || null,
        status: submittalStatus,
        reviewer: submittalReviewer.trim() || null,
        remarks: submittalRemarks.trim() || null,
      };
      const isEditing = editingSubmittalId !== null;

      try {
        if (isEditing) {
          await updateSubmittal(
            selectedProjectId,
            editingSubmittalId,
            payload
          );
        } else {
          await createSubmittal(selectedProjectId, payload);
        }

        resetSubmittalForm();
        await loadSubmittals();
        showNotice(
          "success",
          isEditing ? "Submittal updated." : "Submittal created."
        );
      } catch (error) {
        reportRequestError(
          isEditing
            ? "Unable to update Submittal"
            : "Unable to create Submittal",
          error
        );
      }
    });
  };

  const performSubmittalDelete = async (id) => {
    try {
      await deleteSubmittal(selectedProjectId, id);
      await loadSubmittals();
      showNotice("success", "Submittal deleted.");
    } catch (error) {
      reportRequestError("Unable to delete Submittal", error);
    }
  };

  const resetPunchItemForm = () => {
    setEditingPunchItemId(null);
    setEditingPunchItemNumber("");
    setPunchItemLocation("");
    setPunchItemTrade("");
    setPunchItemDescription("");
    setPunchItemResponsibleCompany("");
    setPunchItemAssignedTo("");
    setPunchItemPriority("Medium");
    setPunchItemStatus("Open");
    setPunchItemDueDate("");
    setPunchItemCompletedDate("");
  };

  const handleEditPunchItem = (punchItem) => {
    setEditingPunchItemId(punchItem.id);
    setEditingPunchItemNumber(punchItem.number);
    setPunchItemLocation(punchItem.location);
    setPunchItemTrade(punchItem.trade || "");
    setPunchItemDescription(punchItem.description);
    setPunchItemResponsibleCompany(
      punchItem.responsible_company || ""
    );
    setPunchItemAssignedTo(punchItem.assigned_to || "");
    setPunchItemPriority(punchItem.priority);
    setPunchItemStatus(punchItem.status);
    setPunchItemDueDate(punchItem.due_date || "");
    setPunchItemCompletedDate(punchItem.completed_date || "");
  };

  const handleSavePunchItem = async () => {
    const location = punchItemLocation.trim();
    const description = punchItemDescription.trim();

    if (!location || !description) {
      reportValidationError(
        "Complete the location and description before saving."
      );
      return;
    }

    if (
      punchItemDueDate &&
      punchItemCompletedDate &&
      punchItemCompletedDate < punchItemDueDate
    ) {
      reportValidationError(
        "Completed date cannot be earlier than due date."
      );
      return;
    }

    return runOperation("savePunchItem", async () => {
      const payload = {
        location,
        trade: punchItemTrade.trim() || null,
        description,
        responsible_company:
          punchItemResponsibleCompany.trim() || null,
        assigned_to: punchItemAssignedTo.trim() || null,
        priority: punchItemPriority,
        status: punchItemStatus,
        due_date: punchItemDueDate || null,
        completed_date: punchItemCompletedDate || null,
      };
      const isEditing = editingPunchItemId !== null;

      try {
        if (isEditing) {
          await updatePunchItem(
            selectedProjectId,
            editingPunchItemId,
            payload
          );
        } else {
          await createPunchItem(selectedProjectId, payload);
        }

        resetPunchItemForm();
        await loadPunchItems();
        showNotice(
          "success",
          isEditing ? "Punch Item updated." : "Punch Item created."
        );
      } catch (error) {
        reportRequestError(
          isEditing
            ? "Unable to update Punch Item"
            : "Unable to create Punch Item",
          error
        );
      }
    });
  };

  const performPunchItemDelete = async (id) => {
    try {
      await deletePunchItem(selectedProjectId, id);
      await loadPunchItems();
      showNotice("success", "Punch Item deleted.");
    } catch (error) {
      reportRequestError("Unable to delete Punch Item", error);
    }
  };

  const handleCreateProjectCompany = async () => {
    if (!companyName.trim()) {
      reportValidationError("Enter a company name before adding it.");
      return;
    }

    return runOperation("createCompany", async () => {
      try {
        await createProjectCompany(selectedProjectId, {
          name: companyName,
          trade: companyTrade,
        });

        setCompanyName("");
        setCompanyTrade("");
        await loadProjectCompanies();
        showNotice("success", "Company added to the project.");
      } catch (error) {
        reportRequestError("Unable to add project company", error);
      }
    });
  };

  const handleRefreshDailyLogs = () =>
    runOperation("refreshDailyLogs", loadDailyLogs);
  const handleRefreshInspections = () =>
    runOperation("refreshInspections", loadInspections);
  const handleRefreshNotesDelays = () =>
    runOperation("refreshNotesDelays", loadNotesDelays);
  const handleRefreshChangeOrders = () =>
    runOperation("refreshChangeOrders", loadChangeOrders);
  const handleRefreshRFIs = () => runOperation("refreshRFIs", loadRFIs);
  const handleRefreshSubmittals = () =>
    runOperation("refreshSubmittals", loadSubmittals);
  const handleRefreshPunchItems = () =>
    runOperation("refreshPunchItems", loadPunchItems);

  return {
    newProjectName,
    setNewProjectName,
    logDate,
    setLogDate,
    logCompany,
    setLogCompany,
    logManpower,
    setLogManpower,
    logNotes,
    setLogNotes,
    inspectionDate,
    setInspectionDate,
    inspectionType,
    setInspectionType,
    inspectionStatus,
    setInspectionStatus,
    noteDelayDate,
    setNoteDelayDate,
    noteDelayType,
    setNoteDelayType,
    noteDelayCompany,
    setNoteDelayCompany,
    noteDelayDescription,
    setNoteDelayDescription,
    noteDelayImpact,
    setNoteDelayImpact,
    editingChangeOrderId,
    editingChangeOrderNumber,
    changeOrderDate,
    setChangeOrderDate,
    changeOrderTitle,
    setChangeOrderTitle,
    changeOrderCompany,
    setChangeOrderCompany,
    changeOrderStatus,
    setChangeOrderStatus,
    changeOrderDescription,
    setChangeOrderDescription,
    changeOrderReason,
    setChangeOrderReason,
    changeOrderProposedAmount,
    setChangeOrderProposedAmount,
    changeOrderApprovedAmount,
    setChangeOrderApprovedAmount,
    changeOrderScheduleImpactDays,
    setChangeOrderScheduleImpactDays,
    changeOrderRequestedDate,
    setChangeOrderRequestedDate,
    changeOrderSubmittedDate,
    setChangeOrderSubmittedDate,
    changeOrderApprovedDate,
    setChangeOrderApprovedDate,
    changeOrderExecutedDate,
    setChangeOrderExecutedDate,
    changeOrderResponsibleParty,
    setChangeOrderResponsibleParty,
    editingRFIId,
    editingRFINumber,
    rfiSubject,
    setRFISubject,
    rfiQuestion,
    setRFIQuestion,
    rfiResponsibleCompany,
    setRFIResponsibleCompany,
    rfiSubmittedDate,
    setRFISubmittedDate,
    rfiDueDate,
    setRFIDueDate,
    rfiResponse,
    setRFIResponse,
    rfiStatus,
    setRFIStatus,
    editingSubmittalId,
    editingSubmittalNumber,
    submittalSpecificationSection,
    setSubmittalSpecificationSection,
    submittalTitle,
    setSubmittalTitle,
    submittalResponsibleCompany,
    setSubmittalResponsibleCompany,
    submittalSubmittedDate,
    setSubmittalSubmittedDate,
    submittalRequiredByDate,
    setSubmittalRequiredByDate,
    submittalReviewedDate,
    setSubmittalReviewedDate,
    submittalStatus,
    setSubmittalStatus,
    submittalReviewer,
    setSubmittalReviewer,
    submittalRemarks,
    setSubmittalRemarks,
    editingPunchItemId,
    editingPunchItemNumber,
    punchItemLocation,
    setPunchItemLocation,
    punchItemTrade,
    setPunchItemTrade,
    punchItemDescription,
    setPunchItemDescription,
    punchItemResponsibleCompany,
    setPunchItemResponsibleCompany,
    punchItemAssignedTo,
    setPunchItemAssignedTo,
    punchItemPriority,
    setPunchItemPriority,
    punchItemStatus,
    setPunchItemStatus,
    punchItemDueDate,
    setPunchItemDueDate,
    punchItemCompletedDate,
    setPunchItemCompletedDate,
    companyName,
    setCompanyName,
    companyTrade,
    setCompanyTrade,
    handleCreateProject,
    handleCreateDailyLog,
    handleCreateInspection,
    handleCreateNoteDelay,
    handleEditChangeOrder,
    resetChangeOrderForm,
    handleSaveChangeOrder,
    performChangeOrderDelete,
    handleEditRFI,
    resetRFIForm,
    handleSaveRFI,
    performRFIDelete,
    handleEditSubmittal,
    resetSubmittalForm,
    handleSaveSubmittal,
    performSubmittalDelete,
    handleEditPunchItem,
    resetPunchItemForm,
    handleSavePunchItem,
    performPunchItemDelete,
    handleCreateProjectCompany,
    handleRefreshDailyLogs,
    handleRefreshInspections,
    handleRefreshNotesDelays,
    handleRefreshChangeOrders,
    handleRefreshRFIs,
    handleRefreshSubmittals,
    handleRefreshPunchItems,
  };
}

export default useRecordForms;
