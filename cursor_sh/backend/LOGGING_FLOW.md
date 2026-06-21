# Logging Flow

This service writes two complementary log layers:

- Request audit logs: every API call has `X-Trace-ID`, method, path, actor, IP, status, duration, and sanitized payload.
- Business event logs: state-changing business milestones use stable `event=...` names and now inherit the same `trace_id`, actor, path, and IP from the request context.
- Handled error logs: HTTP 5xx errors use `event=http_exception_5xx` and include the original exception cause when the endpoint raised the safe HTTP error with `from e`.

## Where Logs Land

- File logs: `${LOG_DIR}/<module>/<module>_YYYY-MM-DD.log`
- Error logs: `${LOG_DIR}/error/error_YYYY-MM-DD.log`
- Crash logs: `${LOG_DIR}/crash/crash_YYYY-MM-DD.log`
- Audit DB: write requests are stored when `LOG_DB_ENABLED=True` and the HTTP method is listed in `LOG_DB_METHODS`.

## Core Customer Flow

1. Login/register
   - Request audit: `/api/auth/*`
   - Business events: auth service events where present

2. AI chat and handoff
   - Chat persistence: `event=chat_session_synced`, `event=chat_message_saved` if enabled in the AI chat history paths
   - Human handoff: `event=human_handoff_recorded`
   - Extraction failure: `event=human_handoff_extract_failed`

3. Order draft/create/submit
   - Draft or order create: `event=order_created`
   - Draft edit: `event=order_updated`
   - Draft submit or status change: `event=order_status_updated`
   - Confirmation PDF archive: `event=order_confirmation_pdf_archived`
   - Confirmation email: `event=order_confirmation_email_sent`

4. Internal assignment and production
   - Staff assignment: `event=order_assigned`
   - Preview upload: `event=preview_uploaded`
   - Preview review: `event=preview_reviewed`
   - User feedback: `event=feedback_submitted`
   - Contract advance: `event=order_contract_advanced`
   - Admin cancel: `event=order_cancelled_by_admin`

5. Contractor workflow
   - Admin assignment: `event=contractor_assignment_created`
   - Contractor accept: `event=contractor_assignment_accepted`
   - Contractor reject: `event=contractor_assignment_rejected`
   - Deliverable draft create: `event=contractor_deliverable_draft_created`
   - Deliverable draft update: `event=contractor_deliverable_draft_updated`
   - Deliverable submit: `event=contractor_deliverable_submitted`
   - Admin deliverable review: `event=contractor_deliverable_reviewed`
   - Publish to user: `event=contractor_deliverable_published`
   - Advance workflow stage: `event=contractor_assignment_advanced`
   - Admin comment: `event=contractor_deliverable_commented`

6. Notifications
   - Create one: `event=notification_created`
   - Create batch: `event=notifications_created`
   - Mark read: `event=notification_marked_read`
   - Mark all read: `event=notifications_marked_all_read`
   - Delete: `event=notification_deleted`

## Recommended Production Queries

Find everything for one request:

```bash
rg "trace_id_here" logs
```

Find one order across modules:

```bash
rg "order_number=\"UV.*\"" logs
rg "order_id=\"order_.*\"" logs
```

Find failed notification or external dependency events:

```bash
rg "failed|level=warning|ERROR" logs
rg "notification_failed|email_failed|sms_.*failed|oss_.*failed" logs
```

Find handled endpoint failures:

```bash
rg "event=http_exception_5xx|event=unhandled_exception|event=request_validation_failed" logs
```

Find external service retry/final-failure events:

```bash
rg "retrying|_provider_call_failed|oss_.*_failed|sms_.*_failed|email_.*_failed|ai_.*_failed" logs
```

## Logging Rules

- Do not log passwords, SMS codes, tokens, secrets, full phone numbers, or full email usernames.
- Prefer ids and counts over large payloads.
- Every state transition should include `status_from` and `status_to`.
- Every cross-role handoff should include the relevant ids: `order_id`, `assignment_id`, `deliverable_id`, `user_id`, `contractor_id`, or `admin_id`.
- Outbound provider calls should emit `*_retrying` on transient retries and `*_failed` after final failure.
