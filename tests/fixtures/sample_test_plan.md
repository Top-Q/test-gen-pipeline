---
id: TEST-001
suite: Example
feature: Example CRUD
component: example
priority: P1
tags: [ui, example, regression]
variables:
  itemName: "test-item-<uuid4>"
---

Background:
  Given the user is authenticated as "default"
  And the user is on the Example page

Scenario: Create a new example item
  When the user creates a new item with name "<itemName>"
  Then the item appears in the list with name "<itemName>"

---
id: TEST-002
suite: Example
feature: Example CRUD
component: example
priority: P2
tags: [ui, example]
variables:
  itemName: "delete-me-<uuid4>"
setup:
  - create_item: { name: "{{ itemName }}" }
---

Background:
  Given the user is authenticated as "default"
  And the user is on the Example page

Scenario: Delete an existing example item
  When the user deletes the item with name "<itemName>"
  Then the item no longer appears in the list
