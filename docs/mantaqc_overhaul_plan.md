## MantaQC Overhaul Plan

### 1. Goals & Scope
- Rebrand entire product to **MantaQC** across UI, docs, APIs, and logs.
- Replace legacy multi-format reporting with a single Excel-first pipeline that mirrors the provided analytical sample (structure, styling, charts).
- Extend analytics (brigade score, deltas, period summaries, advanced KPIs) and expose them in both admin and user dashboards.
- Deliver end-to-end Excel export (reports & summaries), Bitrix ticket automation, checklist CRUD, web-based log viewing/editing, and robust automated testing.

### 2. Architecture Overview
**Layers**
- `app/services/analytics_service.py` (new): aggregates data from `check_instances`, `brigade_daily_scores`, `daily_checklist_metrics`, etc., producing DTOs for reports, dashboards, and period summaries.
- `app/services/report_builder.py` (new): constructs Excel workbooks via OpenPyXL, injects charts (line/bar/pie), summary sheets, and detail sheets that adhere to the reference layout. Consumes analytics DTOs only.
- `app/services/report_dispatcher.py` (new orchestrator): coordinates analytics -> Excel -> storage upload -> Bitrix ticket triggers. Replaces `report_service.py`.
- `app/services/bitrix_alert_service.py` (new helper): encapsulates logic for mapping report anomalies/warnings to Bitrix payloads (title, description, tags, responsible). Uses existing `bitrix_integration`.
- `app/services/checklist_crud_service.py` (new): wraps CRUD for templates + versions + checklist items, includes validation, and is used by REST + web UI.
- `app/services/reset_service.py` (new): encapsulates safe project reset (purge DB except admin user + base fixtures).

**Supporting modules**
- `app/api/v1/reports.py` extended for:
  - Excel-only downloads.
  - Sorting/filter filters (date, author, status).
  - Period summary endpoints (`/reports/summaries`).
  - Log viewing endpoints returning HTML-safe payloads for web UI.
- `app/api/v1/checklists.py` expanded to full CRUD (list/create/update/delete, version management, inline editing of checklist items, server-side validation).
- `app/api/v1/dashboards.py` (new): aggregates analytics per role (admin vs user), feeds the dashboards.
- `app/api/v1/bitrix.py` (new) optional hooks/testing.

### 3. Data Model & Migrations
Create new Alembic migration:
- Update `reports.format` enum → replace (`pdf/html/json`) with `xlsx` and rename enum class to `ReportFormatXLSX`. Enforce not-null `metadata JSONB` column storing analytics snapshot + Bitrix ticket ids.
- Add `reports.author_id` (FK `users.id`) to track generator.
- Add tables for:
  - `report_period_summaries` storing precomputed day/week/month aggregates with delta vs previous period, filters (department, brigade, author).
  - `report_generation_events` (history/log for automated scheduling).
- Extend `brigade_daily_scores` to ensure `overall_score` precision and add `formula_version`.
- Add `checklist_templates.name_slug` unique for friendly URLs (used in CRUD UI).

### 4. Excel Report Layout
Workbook structure:
1. **Cover sheet** (“MantaQC — Сводный отчёт”) with metadata (project, template, inspector, dates) + KPI cards (avg score, brigade score, defects, remark count, period deltas).
2. **Analytics sheet** replicating provided format: matrix of brigades vs days, month totals, MoM deltas, sparkline-like chart, conditional formatting.
3. **Issues sheet**: tabular list of warnings/errors with severity, check link, attachments, and Bitrix status (auto-populated).
4. **Checks sheet**: detailed checklist data (section/question/answer/comment/photos).

Charts:
- Use OpenPyXL chart objects (LineChart, BarChart, PieChart) anchored to Analytics & Issues sheets.
- For quick previews in dashboards, continue generating PNG chart URIs via Matplotlib (already in place) but re-use analytics DTOs.

### 5. Bitrix Automation
- During report generation, inspect analytics DTO for any `alerts` (failed checks, warnings, low brigade score, data quality issues). For each unique issue:
  - Build payload with human-readable description, severity, links, attachments.
  - Deduplicate by issue hash; store mapping in `reports.metadata["bitrix"]`.
  - Expose API endpoints to re-sync/resend tasks if needed.
- Provide system settings via `.env` (already there) + UI switches in admin panel (per issue type).

### 6. Web Experience
- **Admin dashboard (`static/admin.html`)**: rebuild from `user.html` base, add:
  - Landing dashboard with cards + charts (status pie, period summaries, brigade leaderboard, outstanding Bitrix tasks).
  - Tables for reports/checks with sorting & filtering controls (date range, author, template).
  - Inline viewers (obход logs, checklist editor) using modals/panels instead of downloads.
  - Buttons “Сброс проекта” + “Демо-версия” moved to footer, styled as subdued links with confirmation modals and role-based visibility.
- **User dashboard**: filter all data by current user; show personal KPIs, latest assigned checks, quick Excel download buttons, and accessible “Назад” on login page (already partially there, extend to worker login).
- **Report/Log viewers**: new `static/logs.html` or embedded component that calls `/api/v1/checks/{id}/logs` returning JSON -> rendered as collapsible timeline.

### 7. Checklist CRUD Workflow
- Backend: extend endpoints for list/search, create (with schema validation), update (including version bump), delete (soft delete + cascade), clone from templates.
- Frontend: new UI component for tree-based editing (sections/questions). All via web forms.
- Add server-side form validation errors surfaced in UI.

### 8. Testing Strategy
- **Unit tests**: analytics service (edge cases, deltas), report builder (structure assertions using OpenPyXL), Bitrix alert mapper, checklist CRUD validations, reset service.
- **Integration tests**: API endpoints for dashboards, Excel download (check headers), project reset flow, Bitrix stub tasks triggered by report anomalies.
- **E2E/API tests**: use `httpx.AsyncClient` + temporary DB to simulate full report generation + Bitrix ticket creation; include period summary export cases.
- Ensure coverage also touches legacy paths (auth, brigades, schedules) per requirement.

### 9. Rollout Plan
1. Create migrations → rename enums, add metadata columns, new tables.
2. Introduce analytics/report builder services with feature flags; keep old endpoints but switch implementation gradually.
3. Rebuild admin/user static pages, add new dashboard endpoints feeding them.
4. Implement checklist CRUD API + UI.
5. Wire Bitrix automation + project reset fix + summary exports.
6. Write/expand automated tests + CI instructions.
7. Update README and `.env.example` to reflect MantaQC naming + new settings.

### 10. Open Questions / Assumptions
- Provided Excel sample is referenced but not present in repo; we assume structure described by stakeholder and will encode as best effort with configurable template JSON for adjustments.
- Bitrix responsible/creator IDs: fall back to admin user or `.env` defaults.
- Large Excel exports may need background Celery tasks; initial implementation keeps synchronous path with streaming download, but hooks Celery for long-running (configurable).

This plan should be kept up to date while implementing to reflect any scope adjustments.

