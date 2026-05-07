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

### Views & Components
| File | Contains |
|------|----------|
| `app/views/work_packages/index.html.erb` | Work packages list (Angular-rendered) |
| `app/views/work_packages/show.html.erb` | Single work package view |
| `app/views/work_packages/split_view.html.erb` | Split view layout |
| `app/components/work_packages/split_view_component.rb` | Split view component |
| `app/components/work_packages/status_button_component.rb` | Status badge/button |
| `app/components/work_packages/dialogs/create_dialog_component.rb` | Create WP dialog |
| `app/components/work_packages/dialogs/create_form_component.rb` | Create WP form |
| `app/components/work_packages/date_picker/form_component.rb` | Date picker form |
| `app/components/work_packages/progress/base_modal_component.rb` | Progress modal |
| `app/components/work_packages/activities_tab/index_component.rb` | Activities tab |

### Stimulus Controllers
| File | Contains |
|------|----------|
| `frontend/src/stimulus/controllers/dynamic/work-packages/create-dialog.controller.ts` | Create dialog behavior |
| `frontend/src/stimulus/controllers/dynamic/work-packages/date-picker/` | Date picker controllers |
| `frontend/src/stimulus/controllers/dynamic/work-packages/activities-tab/` | Activities tab controllers |
| `frontend/src/stimulus/controllers/dynamic/work-packages/progress/` | Progress modal controllers |

### Angular Components
| File | Contains |
|------|----------|
| `frontend/src/app/features/work-packages/` | Full Angular WP module: table, detail view, inline editing |

**Note:** Work packages use Angular extensively — the table and detail views are Angular components, not server-rendered ERB. Read the Angular component templates for DOM structure.

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
