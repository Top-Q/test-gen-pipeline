# OpenProject Source Code Navigation

The OpenProject Rails application source code is at:
`C:\Users\itaiag\git\ruby\openproject`

**MANDATORY:** Before writing locators for any module, read the relevant source files listed below to find element IDs, CSS classes, data attributes, ARIA attributes, and column definitions. Derive locators from actual source code — do not guess.

## How to Use Source Code for Locator Discovery

| Source File Type | What to Extract |
|-----------------|-----------------|
| **ERB form partials** (`_form.html.erb`, `_member_form.html.erb`) | Form `id`, input `id`, submit button `id`, `data-*` attributes |
| **Ruby row_component.rb** | Column CSS classes (via `column_css_class`), row `id` pattern (via `row_css_id`), cell content structure |
| **Ruby table_component.rb** | Column names (maps to CSS classes), table container class, sort columns |
| **Ruby dialog components** | Dialog `id`, button labels, Primer component types |
| **Ruby sub_header / header components** | Button IDs, filter button structure, action menu setup |
| **Stimulus controllers** (`.controller.ts`) | `static targets` (maps to `data-*-target` attributes), action methods, DOM query selectors used internally |

### Reading Priority

1. Read the **form partial** first — it has the form ID, all input IDs, and submit button IDs
2. Read **row_component.rb** and **table_component.rb** — they define column CSS classes and row ID patterns
3. Read **header/sub_header components** — they define page-level buttons and their IDs
4. Read **dialog components** — they define confirmation dialog structure
5. Read **Stimulus controllers** — they reveal dynamic behavior targets and CSS selectors

### Primer Components

OpenProject uses GitHub's Primer design system. When source code uses Primer components, know that:
- `Primer::Alpha::ActionMenu` → renders `button[aria-haspopup="true"]` as trigger
- `Primer::Alpha::Dialog` → renders `[role="dialog"]` container
- `Primer::Beta::IconButton` → renders `button` with `aria-label`
- `Primer::Alpha::ActionList` → renders `[role="menuitem"]` items inside menus

## Common Patterns

- **Base URL:** `http://localhost:8090`
- **API URL:** `http://localhost:8080`
- **Authentication:** session-based, admin/admin
- **Page transitions:** Turbo (Hotwire) for server-rendered pages, Angular for complex UI (work packages, boards)
- **I18n keys:** `config/locales/en.yml` — useful for finding button labels and heading text

---

## Members Module

**URL:** `/projects/<id>/members`

### Views & Components
| File | Contains |
|------|----------|
| `app/views/members/_member_form.html.erb` | Add member form: `#members_add_form`, `#member_role_ids`, `#add-member--submit-button`, Angular autocompleter |
| `app/views/members/index.html.erb` | Main index page layout |
| `app/components/members/row_component.rb` | Row ID pattern (`member-{id}`), column CSS classes (`email`, `roles`, `status`, `name`), action menu (Primer ActionMenu), cell content rendering |
| `app/components/members/table_component.rb` | Column definitions: `name, mail, roles, groups, shared, status` — the `mail` column renders with CSS class `email` |
| `app/components/members/delete_member_dialog_component.rb` | Delete confirmation dialog (Primer Dialog) |
| `app/components/members/role_form_component.rb` | Inline role editing form within table rows |
| `app/components/members/index_page_header_component.rb` | Page header |
| `app/components/members/index_sub_header_component.rb` | Filter button (`#filter-member-button`), Add member button (`#add-member-button`) |
| `app/components/members/user_filter_component.rb` | Filter panel form |

### Stimulus Controllers
| File | Contains |
|------|----------|
| `frontend/src/stimulus/controllers/dynamic/members-form.controller.ts` | Targets: `filterContainer`, `addMemberForm`, `search`, `addMemberButton`. Reveals `.ng-input input` selector for autocompleter focus |

### Angular Components
| File | Contains |
|------|----------|
| `frontend/src/app/shared/components/autocompleter/members-autocompleter/` | Members search autocompleter — renders combobox with `.ng-dropdown-panel .ng-option` for options |

---

## Boards Module

**URL:** `/projects/<id>/boards`

### Views & Components
| File | Contains |
|------|----------|
| `modules/boards/app/views/boards/boards/index.html.erb` | Board listing page |
| `modules/boards/app/views/boards/boards/new.html.erb` | New board form (combined: title + type radio + create button) |
| `modules/boards/app/views/boards/boards/show.html.erb` | Individual board view |
| `modules/boards/app/views/boards/boards/_form.html.erb` | Board form partial |
| `modules/boards/app/components/boards/table_component.rb` | Board table structure |
| `modules/boards/app/components/boards/row_component.rb` | Board row: links, delete action |
| `modules/boards/app/components/boards/add_button_component.rb` | Add board button — exists in TWO variants (text + icon-only mobile) |

### Routes
| File | Contains |
|------|----------|
| `modules/boards/config/routes.rb` | Board routing configuration |

### Angular Components
| File | Contains |
|------|----------|
| `frontend/src/app/features/boards/` | Full Angular board feature: board list, card components, drag-and-drop |

---

## Meetings Module

**URL:** `/projects/<id>/meetings`

### Views & Components
| File | Contains |
|------|----------|
| `modules/meeting/app/views/meetings/index.html.erb` | Meetings index page |
| `modules/meeting/app/views/meetings/history.html.erb` | Meeting history page |
| `modules/meeting/app/views/meetings/details_dialog.turbo_stream.erb` | Details dialog (Turbo Stream) |
| `modules/meeting/app/components/meetings/table_component.rb` | Meetings table structure |
| `modules/meeting/app/components/meetings/row_component.rb` | Meeting row |
| `modules/meeting/app/components/meetings/show_component.rb` | Single meeting view |
| `modules/meeting/app/components/meetings/side_panel_component.rb` | Side panel with meeting details |
| `modules/meeting/app/components/meetings/header_component.rb` | Meeting page header |
| `modules/meeting/app/components/meetings/delete_dialog_component.rb` | Delete confirmation dialog |
| `modules/meeting/app/components/meetings/index/form_component.rb` | New meeting form |
| `modules/meeting/app/components/meetings/index/dialog_component.rb` | Meeting creation dialog |
| `modules/meeting/app/components/meetings/participants/list_component.rb` | Participant list |
| `modules/meeting/app/components/meetings/participants/manage_participants_dialog.rb` | Manage participants dialog |
| `modules/meeting/app/components/meetings/side_panel/details_dialog_component.rb` | Side panel details dialog |
| `modules/meeting/app/components/meetings/side_panel/details_form_component.rb` | Side panel details form |
| `modules/meeting/app/components/meetings/index_page_header_component.rb` | Index page header |

### Stimulus Controllers
| File | Contains |
|------|----------|
| `frontend/src/stimulus/controllers/dynamic/meeting-agenda-item-form.controller.ts` | Agenda item form behavior |
| `frontend/src/stimulus/controllers/dynamic/meetings/form.controller.ts` | Meeting form controller |
| `frontend/src/stimulus/controllers/dynamic/meetings/section-form.controller.ts` | Section form controller |
| `frontend/src/stimulus/controllers/dynamic/meetings/submit.controller.ts` | Submit behavior |
| `frontend/src/stimulus/controllers/dynamic/meetings/drag-and-drop.controller.ts` | Drag-and-drop for agenda items |

### Routes
| File | Contains |
|------|----------|
| `modules/meeting/config/routes.rb` | Meeting routing configuration |

---

## Work Packages Module

**URL:** `/projects/<id>/work_packages`

**Critical note:** The WP list and table are **fully Angular-rendered** — there is no server-side ERB table. The Angular `<wp-table>` component writes rows directly to the DOM via JavaScript builders. Do NOT look for ERB table structure; read the Angular builder files and HTML templates listed below instead.

### Create Button (WP list toolbar) — Angular Route Navigation

| File | Contains |
|------|----------|
| `frontend/src/app/features/work-packages/components/wp-buttons/wp-create-button/wp-create-button.html` | `<button class="button -primary add-work-package">` with directive `opTypesCreateDropdown`. Clicking opens a type-selection dropdown (`role="menuitem"` items) |
| `frontend/src/app/features/work-packages/components/op-types-context-menu/op-types-context-menu.directive.ts` | Handles type item click: calls `$state.go('work-packages.partitioned.list.new', { type: type.id })` — **router navigation, NOT a dialog** |

**CRITICAL — the toolbar create button does NOT open a dialog.** Selecting a type from the dropdown triggers Angular router navigation to state `work-packages.partitioned.list.new`. This renders `WorkPackageNewSplitViewComponent` in the right panel of the split view. There is no `create-work-package-dialog` involved.

The correct create flow from the toolbar:
1. Click `.add-work-package` → type dropdown appears (Primer ActionList, items have `role="menuitem"`)
2. Click a type → the type item's `href` navigates to `/projects/<id>/work_packages/new?type=<type-id>`. The ARIA label pattern is `aria-labelledby="quick-add-menu-item--item-<type-name-lowercase>"`. Use `getByRole('menuitem', { name: 'Task', exact: true })`.
3. The right panel renders a new-WP form (Angular split-view). URL changes to `.../work_packages/new?type=<id>`.
4. Fill the subject using `#wp-new-inline-edit--field-subject` (input type=text, auto-focused)
5. Save with `#work-packages--edit-actions-save` or cancel with `#work-packages--edit-actions-cancel`

**Verified live DOM selectors for the split-view create form:**

| Element | Selector |
|---------|----------|
| Subject input (auto-focused) | `#wp-new-inline-edit--field-subject` |
| Save button | `#work-packages--edit-actions-save` |
| Cancel button | `#work-packages--edit-actions-cancel` |
| Type dropdown item (e.g. Task) | `getByRole('menuitem', { name: 'Task', exact: true })` |

**Note:** The type dropdown items are NOT in the ARIA snapshot (they're in an Angular overlay). Use `getByRole('menuitem')` — Playwright can find them even when outside the ARIA tree.

### Create Dialog (non-toolbar context)

The `create-work-package-dialog` ViewComponent exists but is NOT triggered from the toolbar button. It may be used from board cards or other entry points.

| File | Contains |
|------|----------|
| `app/components/work_packages/dialogs/create_dialog_component.html.erb` | Primer `Dialog` container: `id="create-work-package-dialog"`. Footer: Cancel button has `data-close-dialog-id="create-work-package-dialog"`; Create/Save submit button has `form="create-work-package-form"` and `type="submit"` |
| `app/components/work_packages/dialogs/create_form_component.html.erb` | Form: `id="create-work-package-form"`, `data-controller="work-packages--create-dialog"` |

### Table & Rows (Angular, read these for DOM structure)

| File | Contains |
|------|----------|
| `frontend/src/app/features/work-packages/routing/wp-list-view/wp-list-view.component.html` | Renders `<wp-table class="work-packages-split-view--tabletimeline-content">` |
| `frontend/src/app/features/work-packages/components/wp-fast-table/builders/rows/single-row-builder.ts` | Each WP row is a `<tr>` with: CSS class `wp-table--row`, `wp--row`, `wp-row-{id}`, `issue`; attribute `data-work-package-id="{id}"` |
| `frontend/src/app/features/work-packages/components/wp-table/table-actions/table-action.ts` | CSS class constants: context-menu TD = `wp-table--context-menu-td`; context-menu span = `wp-table--context-menu-span`; context-menu link = `wp-table-context-menu-link`; icon = `wp-table-context-menu-icon` |
| `frontend/src/app/features/work-packages/components/wp-table/table-actions/actions/context-menu-table-action.ts` | Renders `<a class="wp-table-context-menu-link wp-table-context-menu-icon">` (the "⋯" button per row); title is `label_open_context_menu` i18n key |

### Locator quick-reference

| Element | Locator |
|---------|---------|
| WP list table body rows | `tr.wp-table--row` |
| Specific WP row by ID | `tr[data-work-package-id="123"]` |
| Subject cell in a row | `td.wp-table--cell-td.subject` inside the row |
| Context menu button per row | `a.wp-table-context-menu-link` inside the row |
| Create button (toolbar) | `.add-work-package` |
| Type dropdown items | `getByRole('menuitem', { name: 'Task', exact: true })` |
| Subject input (split-view create form) | `#wp-new-inline-edit--field-subject` ✓ verified |
| Save button (split-view create form) | `#work-packages--edit-actions-save` ✓ verified |
| Cancel button (split-view create form) | `#work-packages--edit-actions-cancel` ✓ verified |
| Quick text filter | `#filter-by-text-input` |

### Filter

| File | Contains |
|------|----------|
| `frontend/src/app/features/work-packages/components/filters/quick-filter-by-text-input/quick-filter-by-text-input.html` | `<input id="filter-by-text-input" type="text">` — the quick text search box visible in the WP list toolbar |

---

## Time and Costs Module

**URL:** `/projects/<id>/cost_reports` (cost reports), time entries via work package detail

### Time Entries
| File | Contains |
|------|----------|
| `modules/costs/app/views/time_entries/dialog.turbo_stream.erb` | Log time dialog (Turbo Stream) |
| `modules/costs/app/components/time_entries/time_entry_form_component.rb` | Time entry form |
| `modules/costs/app/components/time_entries/entry_dialog_component.rb` | Entry dialog wrapper |
| `modules/costs/app/components/time_entries/activity_form.rb` | Activity selector |
| `modules/costs/app/components/time_entries/comments_form.rb` | Comments field |
| `modules/costs/app/components/time_entries/days_and_hours_form.rb` | Hours input |

### Cost Reports
| File | Contains |
|------|----------|
| `modules/reporting/app/views/cost_reports/index.html.erb` | Cost reports page |
| `modules/reporting/app/components/cost_reports/index_page_header_component.rb` | Page header |

### Stimulus Controllers
| File | Contains |
|------|----------|
| `frontend/src/stimulus/controllers/dynamic/time-entry.controller.ts` | Time entry form behavior |

### Routes
| File | Contains |
|------|----------|
| `modules/costs/config/routes.rb` | Time entry routes |
| `modules/reporting/config/routes.rb` | Cost report routes |
