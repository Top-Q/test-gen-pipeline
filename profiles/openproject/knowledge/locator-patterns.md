# Locator Patterns & Best Practices

## Preferred Locator Strategy (in order)

1. `getByRole()` — most resilient, matches accessible roles
2. `getByLabel()` / `getByPlaceholder()` — for form fields
3. `getByText()` — for static text content
4. `getByTestId()` — when semantic locators aren't sufficient
5. `locator()` with CSS — last resort

## Scoping Locators to Avoid Ambiguity

When the same text/role appears in multiple page areas (e.g., sidebar and main content), scope the locator to a container:

```typescript
// BAD — may match sidebar + main content (strict mode violation)
getBoardLink(name: string): Locator {
    return this.page.getByRole('link', { name, exact: true });
}

// GOOD — scoped to the table in main content
getBoardLink(name: string): Locator {
    return this.page.getByRole('table').getByRole('link', { name, exact: true });
}
```

## Inline-Edit Pattern

When an input is located by its current text (e.g., an editable heading), `fill()` changes the accessible name, which breaks the original locator. Use `page.keyboard.press()` for subsequent actions:

```typescript
// BAD — locator breaks after fill() because heading name changes
async renameItem(currentName: string, newName: string): Promise<void> {
    const input = this.page.getByRole('heading', { name: currentName })
        .getByPlaceholder('Name of this view');
    await input.click();
    await input.fill(newName);
    await input.press('Enter'); // FAILS — heading no longer has currentName
}

// GOOD — use page.keyboard after fill changes the accessible name
async renameItem(currentName: string, newName: string): Promise<void> {
    const input = this.page.getByRole('heading', { name: currentName })
        .getByPlaceholder('Name of this view');
    await input.click();
    await input.fill(newName);
    await this.page.keyboard.press('Enter'); // Works — doesn't re-query the locator
}
```

## Menu Interaction Pattern

For dropdown menus triggered by a button, use `getByRole('menuitem')`:

```typescript
async addNewCard(taskName: string): Promise<void> {
    await this.addCardButton.click();
    await this.page.getByRole('menuitem', { name: 'Add new card' }).click();
}
```

## Dynamic Locator Getters

When locators depend on runtime data, expose them as getter methods with parameters:

```typescript
getListHeading(listName: string): Locator {
    return this.page.getByRole('heading', { name: listName, level: 3 });
}

getCardInList(taskName: string): Locator {
    return this.page.getByText(taskName);
}
```
