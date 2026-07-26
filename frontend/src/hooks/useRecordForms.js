import { useState } from "react";

import {
  createChangeOrder,
  createDailyLog,
  createInspection,
  createNoteDelay,
  createProject,
  createProjectCompany,
  createRFI,
  deleteChangeOrder,
  deleteRFI,
  updateRFI,
} from "../services/api";
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
  loadProjectCompanies,
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
  const [changeOrderDate, setChangeOrderDate] = useState(toLocalDateInputValue);
  const [changeOrderNumber, setChangeOrderNumber] = useState("");
  const [changeOrderCompany, setChangeOrderCompany] = useState("");
  const [changeOrderStatus, setChangeOrderStatus] = useState("Pending");
  const [changeOrderDescription, setChangeOrderDescription] = useState("");
  const [changeOrderAmount, setChangeOrderAmount] = useState("");
  const [changeOrderResponsibleParty, setChangeOrderResponsibleParty] =
    useState("");
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
  const [companyName, setCompanyName] = useState("");
  const [companyTrade, setCompanyTrade] = useState("");

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

  const handleCreateChangeOrder = async () => {
    if (!changeOrderDate || !changeOrderNumber.trim()) {
      reportValidationError(
        "Complete the date and change order number before saving."
      );
      return;
    }

    return runOperation("createChangeOrder", async () => {
      try {
        await createChangeOrder(selectedProjectId, {
          date: changeOrderDate,
          co_number: changeOrderNumber,
          company: changeOrderCompany,
          status: changeOrderStatus,
          description: changeOrderDescription,
          amount: changeOrderAmount,
          responsible_party: changeOrderResponsibleParty,
        });

        setChangeOrderDate(toLocalDateInputValue());
        setChangeOrderNumber("");
        setChangeOrderCompany("");
        setChangeOrderStatus("Pending");
        setChangeOrderDescription("");
        setChangeOrderAmount("");
        setChangeOrderResponsibleParty("");
        await loadChangeOrders();
        showNotice("success", "Change order saved.");
      } catch (error) {
        reportRequestError("Unable to create change order", error);
      }
    });
  };

  /** Executes a confirmed change-order deletion (dialog lives in App). */
  const performChangeOrderDelete = async (id) => {
    try {
      await deleteChangeOrder(selectedProjectId, id);
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
    changeOrderDate,
    setChangeOrderDate,
    changeOrderNumber,
    setChangeOrderNumber,
    changeOrderCompany,
    setChangeOrderCompany,
    changeOrderStatus,
    setChangeOrderStatus,
    changeOrderDescription,
    setChangeOrderDescription,
    changeOrderAmount,
    setChangeOrderAmount,
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
    companyName,
    setCompanyName,
    companyTrade,
    setCompanyTrade,
    handleCreateProject,
    handleCreateDailyLog,
    handleCreateInspection,
    handleCreateNoteDelay,
    handleCreateChangeOrder,
    performChangeOrderDelete,
    handleEditRFI,
    resetRFIForm,
    handleSaveRFI,
    performRFIDelete,
    handleCreateProjectCompany,
    handleRefreshDailyLogs,
    handleRefreshInspections,
    handleRefreshNotesDelays,
    handleRefreshChangeOrders,
    handleRefreshRFIs,
  };
}

export default useRecordForms;
