import { lazy } from "react";

import FirstRunPage from "./pages/FirstRunPage";
import HomePage from "./pages/HomePage";
import { formatDisplayDate as formatDate } from "./utils/date";

const ChangeOrdersPage = lazy(() => import("./pages/ChangeOrdersPage"));
const DailyLogsPage = lazy(() => import("./pages/DailyLogsPage"));
const InspectionsPage = lazy(() => import("./pages/InspectionsPage"));
const NotesDelaysPage = lazy(() => import("./pages/NotesDelaysPage"));
const ProjectDashboardPage = lazy(
  () => import("./pages/ProjectDashboardPage")
);
const ProjectDocumentsPage = lazy(
  () => import("./pages/ProjectDocumentsPage")
);
const ProjectDocumentSearchPage = lazy(
  () => import("./pages/ProjectDocumentSearchPage")
);
const ProjectDrawingsPage = lazy(
  () => import("./pages/ProjectDrawingsPage")
);
const ProjectDrawingViewerPage = lazy(
  () => import("./pages/ProjectDrawingViewerPage")
);
const ProjectSettingsPage = lazy(
  () => import("./pages/ProjectSettingsPage")
);
const PunchItemsPage = lazy(() => import("./pages/PunchItemsPage"));
const RFIsPage = lazy(() => import("./pages/RFIsPage"));
const SchedulerPage = lazy(() => import("./pages/SchedulerPage"));
const SubmittalsPage = lazy(() => import("./pages/SubmittalsPage"));

/**
 * Selects and wires the page for the current route. Pure presentation
 * plumbing: all state arrives composed from App's hooks; nothing here owns
 * state or side effects.
 */
function AppRouter({
  currentPage,
  routeParams,
  selectedProjectId,
  navigateTo,
  onLogout,
  data,
  schedule,
  scheduleBaselines,
  lookAheadPlans,
  projectResources,
  resourceLoading,
  forms,
  onboarding,
  onDeleteTask,
  onDeleteChangeOrder,
  onDeleteRFI,
  onDeleteSubmittal,
  onDeletePunchItem,
  onAttachmentError,
  onDashboardError,
}) {
  const {
    projects,
    hasLoadedProjects,
    templates,
    tasks,
    scheduleSettings,
    taskLoadError,
    dailyLogs,
    inspections,
    notesDelays,
    changeOrders,
    rfis,
    submittals,
    punchItems,
    projectCompanies,
    isOperationActive,
    isResourceLoading,
  } = data;

  // Shared prop builders: one place for the loading-flag pattern, the
  // navigation/logout pair, and the selected project's display name.
  const loading = (key) => !hasLoadedProjects || isResourceLoading(key);
  const navProps = { onNavigate: navigateTo, onLogout };
  const projectName =
    projects.find((project) => project.id === selectedProjectId)?.name ||
    "Project";

  if (currentPage === "home") {
    const showOnboarding =
      hasLoadedProjects && projects.length === 0 && !onboarding.dismissed;

    if (showOnboarding) {
      return (
        <FirstRunPage
          onLoadSample={onboarding.onLoadSample}
          onStartEmpty={onboarding.onStartEmpty}
          isSeeding={isOperationActive("seedDemo")}
          seedProgress={onboarding.seedProgress}
          onLogout={onLogout}
        />
      );
    }

    return (
      <HomePage
        projects={projects}
        templates={templates}
        selectedProjectId={selectedProjectId}
        newProjectName={forms.newProjectName}
        onProjectSelect={(projectId) => {
          navigateTo("projectDashboard", projectId);
        }}
        onNewProjectNameChange={forms.setNewProjectName}
        onCreateProject={forms.handleCreateProject}
        isCreating={isOperationActive("createProject")}
        isLoadingProjects={loading("projects")}
        isLoadingTemplates={isResourceLoading("templates")}
        onLogout={onLogout}
      />
    );
  }

  if (currentPage === "projectDashboard") {
    return (
      <ProjectDashboardPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        onRequestError={onDashboardError}
        {...navProps}
      />
    );
  }

  if (currentPage === "dailyLogs") {
    return (
      <DailyLogsPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        dailyLogs={dailyLogs}
        projectCompanies={projectCompanies}
        logDate={forms.logDate}
        logCompany={forms.logCompany}
        logManpower={forms.logManpower}
        logNotes={forms.logNotes}
        formatDate={formatDate}
        {...navProps}
        onRefresh={forms.handleRefreshDailyLogs}
        onCreate={forms.handleCreateDailyLog}
        isCreating={isOperationActive("createDailyLog")}
        isRefreshing={isOperationActive("refreshDailyLogs")}
        isLoading={loading("dailyLogs")}
        isLoadingCompanies={loading("companies")}
        onDateChange={forms.setLogDate}
        onCompanyChange={forms.setLogCompany}
        onManpowerChange={forms.setLogManpower}
        onNotesChange={forms.setLogNotes}
        onAttachmentError={onAttachmentError}
      />
    );
  }

  if (currentPage === "inspections") {
    return (
      <InspectionsPage
        projectName={projectName}
        inspections={inspections}
        inspectionDate={forms.inspectionDate}
        inspectionType={forms.inspectionType}
        inspectionStatus={forms.inspectionStatus}
        formatDate={formatDate}
        {...navProps}
        onRefresh={forms.handleRefreshInspections}
        onCreate={forms.handleCreateInspection}
        isCreating={isOperationActive("createInspection")}
        isRefreshing={isOperationActive("refreshInspections")}
        isLoading={loading("inspections")}
        onDateChange={forms.setInspectionDate}
        onTypeChange={forms.setInspectionType}
        onStatusChange={forms.setInspectionStatus}
      />
    );
  }

  if (currentPage === "notesDelays") {
    return (
      <NotesDelaysPage
        projectName={projectName}
        notesDelays={notesDelays}
        projectCompanies={projectCompanies}
        noteDelayDate={forms.noteDelayDate}
        noteDelayType={forms.noteDelayType}
        noteDelayCompany={forms.noteDelayCompany}
        noteDelayDescription={forms.noteDelayDescription}
        noteDelayImpact={forms.noteDelayImpact}
        formatDate={formatDate}
        {...navProps}
        onRefresh={forms.handleRefreshNotesDelays}
        onCreate={forms.handleCreateNoteDelay}
        isCreating={isOperationActive("createNoteDelay")}
        isRefreshing={isOperationActive("refreshNotesDelays")}
        isLoading={loading("notesDelays")}
        isLoadingCompanies={loading("companies")}
        onDateChange={forms.setNoteDelayDate}
        onTypeChange={forms.setNoteDelayType}
        onCompanyChange={forms.setNoteDelayCompany}
        onDescriptionChange={forms.setNoteDelayDescription}
        onImpactChange={forms.setNoteDelayImpact}
      />
    );
  }

  if (currentPage === "changeOrders") {
    return (
      <ChangeOrdersPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        changeOrders={changeOrders}
        projectCompanies={projectCompanies}
        editingChangeOrderId={forms.editingChangeOrderId}
        editingChangeOrderNumber={forms.editingChangeOrderNumber}
        changeOrderDate={forms.changeOrderDate}
        changeOrderTitle={forms.changeOrderTitle}
        changeOrderCompany={forms.changeOrderCompany}
        changeOrderStatus={forms.changeOrderStatus}
        changeOrderDescription={forms.changeOrderDescription}
        changeOrderReason={forms.changeOrderReason}
        changeOrderProposedAmount={forms.changeOrderProposedAmount}
        changeOrderApprovedAmount={forms.changeOrderApprovedAmount}
        changeOrderScheduleImpactDays={
          forms.changeOrderScheduleImpactDays
        }
        changeOrderRequestedDate={forms.changeOrderRequestedDate}
        changeOrderSubmittedDate={forms.changeOrderSubmittedDate}
        changeOrderApprovedDate={forms.changeOrderApprovedDate}
        changeOrderExecutedDate={forms.changeOrderExecutedDate}
        changeOrderResponsibleParty={forms.changeOrderResponsibleParty}
        formatDate={formatDate}
        {...navProps}
        onRefresh={forms.handleRefreshChangeOrders}
        onSave={forms.handleSaveChangeOrder}
        onEdit={forms.handleEditChangeOrder}
        onCancelEdit={forms.resetChangeOrderForm}
        isSaving={isOperationActive("saveChangeOrder")}
        isRefreshing={isOperationActive("refreshChangeOrders")}
        isLoading={loading("changeOrders")}
        isLoadingCompanies={loading("companies")}
        onDelete={onDeleteChangeOrder}
        onDateChange={forms.setChangeOrderDate}
        onTitleChange={forms.setChangeOrderTitle}
        onCompanyChange={forms.setChangeOrderCompany}
        onStatusChange={forms.setChangeOrderStatus}
        onDescriptionChange={forms.setChangeOrderDescription}
        onReasonChange={forms.setChangeOrderReason}
        onProposedAmountChange={forms.setChangeOrderProposedAmount}
        onApprovedAmountChange={forms.setChangeOrderApprovedAmount}
        onScheduleImpactDaysChange={
          forms.setChangeOrderScheduleImpactDays
        }
        onRequestedDateChange={forms.setChangeOrderRequestedDate}
        onSubmittedDateChange={forms.setChangeOrderSubmittedDate}
        onApprovedDateChange={forms.setChangeOrderApprovedDate}
        onExecutedDateChange={forms.setChangeOrderExecutedDate}
        onResponsiblePartyChange={forms.setChangeOrderResponsibleParty}
        onAttachmentError={onAttachmentError}
      />
    );
  }

  if (currentPage === "rfis") {
    return (
      <RFIsPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        rfis={rfis}
        projectCompanies={projectCompanies}
        editingRFIId={forms.editingRFIId}
        editingRFINumber={forms.editingRFINumber}
        rfiSubject={forms.rfiSubject}
        rfiQuestion={forms.rfiQuestion}
        rfiResponsibleCompany={forms.rfiResponsibleCompany}
        rfiSubmittedDate={forms.rfiSubmittedDate}
        rfiDueDate={forms.rfiDueDate}
        rfiResponse={forms.rfiResponse}
        rfiStatus={forms.rfiStatus}
        formatDate={formatDate}
        {...navProps}
        onRefresh={forms.handleRefreshRFIs}
        onSave={forms.handleSaveRFI}
        onEdit={forms.handleEditRFI}
        onCancelEdit={forms.resetRFIForm}
        onDelete={onDeleteRFI}
        onSubjectChange={forms.setRFISubject}
        onQuestionChange={forms.setRFIQuestion}
        onResponsibleCompanyChange={forms.setRFIResponsibleCompany}
        onSubmittedDateChange={forms.setRFISubmittedDate}
        onDueDateChange={forms.setRFIDueDate}
        onResponseChange={forms.setRFIResponse}
        onStatusChange={forms.setRFIStatus}
        isSaving={isOperationActive("saveRFI")}
        isRefreshing={isOperationActive("refreshRFIs")}
        isLoading={loading("rfis")}
        onAttachmentError={onAttachmentError}
      />
    );
  }

  if (currentPage === "submittals") {
    return (
      <SubmittalsPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        submittals={submittals}
        projectCompanies={projectCompanies}
        editingSubmittalId={forms.editingSubmittalId}
        editingSubmittalNumber={forms.editingSubmittalNumber}
        specificationSection={forms.submittalSpecificationSection}
        title={forms.submittalTitle}
        responsibleCompany={forms.submittalResponsibleCompany}
        submittedDate={forms.submittalSubmittedDate}
        requiredByDate={forms.submittalRequiredByDate}
        reviewedDate={forms.submittalReviewedDate}
        status={forms.submittalStatus}
        reviewer={forms.submittalReviewer}
        remarks={forms.submittalRemarks}
        formatDate={formatDate}
        {...navProps}
        onRefresh={forms.handleRefreshSubmittals}
        onSave={forms.handleSaveSubmittal}
        onEdit={forms.handleEditSubmittal}
        onCancelEdit={forms.resetSubmittalForm}
        onDelete={onDeleteSubmittal}
        onSpecificationSectionChange={
          forms.setSubmittalSpecificationSection
        }
        onTitleChange={forms.setSubmittalTitle}
        onResponsibleCompanyChange={
          forms.setSubmittalResponsibleCompany
        }
        onSubmittedDateChange={forms.setSubmittalSubmittedDate}
        onRequiredByDateChange={forms.setSubmittalRequiredByDate}
        onReviewedDateChange={forms.setSubmittalReviewedDate}
        onStatusChange={forms.setSubmittalStatus}
        onReviewerChange={forms.setSubmittalReviewer}
        onRemarksChange={forms.setSubmittalRemarks}
        isSaving={isOperationActive("saveSubmittal")}
        isRefreshing={isOperationActive("refreshSubmittals")}
        isLoading={loading("submittals")}
        onAttachmentError={onAttachmentError}
      />
    );
  }

  if (currentPage === "punchItems") {
    return (
      <PunchItemsPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        punchItems={punchItems}
        projectCompanies={projectCompanies}
        editingPunchItemId={forms.editingPunchItemId}
        editingPunchItemNumber={forms.editingPunchItemNumber}
        location={forms.punchItemLocation}
        trade={forms.punchItemTrade}
        description={forms.punchItemDescription}
        responsibleCompany={forms.punchItemResponsibleCompany}
        assignedTo={forms.punchItemAssignedTo}
        priority={forms.punchItemPriority}
        status={forms.punchItemStatus}
        dueDate={forms.punchItemDueDate}
        completedDate={forms.punchItemCompletedDate}
        formatDate={formatDate}
        {...navProps}
        onRefresh={forms.handleRefreshPunchItems}
        onSave={forms.handleSavePunchItem}
        onEdit={forms.handleEditPunchItem}
        onCancelEdit={forms.resetPunchItemForm}
        onDelete={onDeletePunchItem}
        onLocationChange={forms.setPunchItemLocation}
        onTradeChange={forms.setPunchItemTrade}
        onDescriptionChange={forms.setPunchItemDescription}
        onResponsibleCompanyChange={
          forms.setPunchItemResponsibleCompany
        }
        onAssignedToChange={forms.setPunchItemAssignedTo}
        onPriorityChange={forms.setPunchItemPriority}
        onStatusChange={forms.setPunchItemStatus}
        onDueDateChange={forms.setPunchItemDueDate}
        onCompletedDateChange={forms.setPunchItemCompletedDate}
        isSaving={isOperationActive("savePunchItem")}
        isRefreshing={isOperationActive("refreshPunchItems")}
        isLoading={loading("punchItems")}
        onAttachmentError={onAttachmentError}
      />
    );
  }

  if (currentPage === "projectSettings") {
    return (
      <ProjectSettingsPage
        projectId={selectedProjectId}
        projectName={projectName}
        projectCompanies={projectCompanies}
        companyName={forms.companyName}
        companyTrade={forms.companyTrade}
        {...navProps}
        onCreate={forms.handleCreateProjectCompany}
        isCreating={isOperationActive("createCompany")}
        isLoading={loading("companies")}
        onNameChange={forms.setCompanyName}
        onTradeChange={forms.setCompanyTrade}
        onAttachmentError={onAttachmentError}
      />
    );
  }

  if (currentPage === "projectDocuments") {
    return (
      <ProjectDocumentsPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        {...navProps}
        onRequestError={onAttachmentError}
      />
    );
  }

  if (currentPage === "projectDocumentSearch") {
    return (
      <ProjectDocumentSearchPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        {...navProps}
        onRequestError={onAttachmentError}
      />
    );
  }

  if (currentPage === "projectDrawings") {
    return (
      <ProjectDrawingsPage
        key={selectedProjectId}
        projectId={selectedProjectId}
        projectName={projectName}
        {...navProps}
        onRequestError={onAttachmentError}
      />
    );
  }

  if (currentPage === "drawingViewer") {
    return (
      <ProjectDrawingViewerPage
        projectId={selectedProjectId}
        projectName={projectName}
        sheetId={routeParams?.sheetId}
        revisionId={routeParams?.revisionId}
        {...navProps}
        onRequestError={onAttachmentError}
      />
    );
  }

  const hasCurrentTaskCollection = data.taskProjectId === selectedProjectId;
  const currentScheduleSettings =
    scheduleSettings?.project_id === selectedProjectId
      ? scheduleSettings
      : null;

  return (
    <SchedulerPage
      key={selectedProjectId}
      projectName={projectName}
      tasks={hasCurrentTaskCollection ? tasks : []}
      scheduleSummary={
        hasCurrentTaskCollection ? data.scheduleSummary : null
      }
      templates={templates}
      scheduleSettings={currentScheduleSettings}
      selectedProjectId={selectedProjectId}
      selectedTaskId={schedule.selectedTaskId}
      editingCell={schedule.editingCell}
      editValue={schedule.editValue}
      templateName={schedule.templateName}
      selectedTemplateId={schedule.selectedTemplateId}
      scheduleView={schedule.scheduleView}
      baselines={scheduleBaselines}
      lookAhead={lookAheadPlans}
      projectResources={projectResources}
      resourceLoading={resourceLoading}
      projectCompanies={projectCompanies}
      setSelectedTaskId={schedule.setSelectedTaskId}
      setEditValue={schedule.setEditValue}
      setTemplateName={schedule.setTemplateName}
      setSelectedTemplateId={schedule.setSelectedTemplateId}
      setScheduleView={schedule.setScheduleView}
      onNavigate={navigateTo}
      onSaveTemplate={schedule.handleSaveTemplate}
      onApplyTemplate={schedule.handleApplyTemplate}
      onExport={schedule.handleExportProjectPdf}
      isSavingTemplate={isOperationActive("saveTemplate")}
      isApplyingTemplate={schedule.isScheduleMutationActive("applyTemplate")}
      isExporting={isOperationActive("exportPdf")}
      isLoadingTasks={loading("tasks") || !hasCurrentTaskCollection}
      isLoadingScheduleSettings={loading("scheduleSettings")}
      isUpdatingScheduleSettings={schedule.isScheduleMutationActive(
        "updateScheduleSettings"
      )}
      isLoadingTemplates={isResourceLoading("templates")}
      taskLoadError={taskLoadError}
      onLogout={onLogout}
      onDragEnd={schedule.handleDragEnd}
      onCellClick={schedule.handleCellClick}
      onCellSave={schedule.handleCellSave}
      onCellCancel={schedule.handleCellCancel}
      onDelete={onDeleteTask}
      onIndent={schedule.handleIndentTask}
      onOutdent={schedule.handleOutdentTask}
      onToggleCollapse={schedule.handleToggleCollapse}
      onRetryTasks={data.loadTasks}
      onUpdateScheduleStart={schedule.handleUpdateScheduleStart}
      onUpdateDataDate={schedule.handleUpdateDataDate}
      onOpenTaskProgress={schedule.openTaskProgress}
      onCloseTaskProgress={schedule.closeTaskProgress}
      onUpdateTaskProgress={async (...args) => {
        const result = await schedule.handleUpdateTaskProgress(...args);
        if (result) await lookAheadPlans.retryDetail();
        return result;
      }}
      progressTaskId={schedule.progressTaskId}
      isUpdatingTaskProgress={schedule.isScheduleMutationActive(
        `updateProgress:${schedule.progressTaskId}`
      )}
      onOpenTaskPlanning={schedule.openTaskPlanning}
      onCloseTaskPlanning={schedule.closeTaskPlanning}
      onUpdateTaskPlanning={async (...args) => {
        const result = await schedule.handleUpdateTaskPlanning(...args);
        if (result) await lookAheadPlans.retryDetail();
        return result;
      }}
      planningTaskId={schedule.planningTaskId}
      isUpdatingTaskPlanning={schedule.isScheduleMutationActive(
        `updatePlanning:${schedule.planningTaskId}`
      )}
      getEmptyRow={schedule.getEmptyRow}
      formatDate={formatDate}
      taskHasChildren={schedule.taskHasChildren}
      isTaskHiddenByCollapsedParent={schedule.isTaskHiddenByCollapsedParent}
      getTaskDepth={schedule.getTaskDepth}
    />
  );
}

export default AppRouter;
