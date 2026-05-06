import { Locator, Page } from '@playwright/test';
import { BasePage } from '../../../internals';

/**
 * Example page for testing POM contract extraction.
 */
export class ExamplePage extends BasePage<ExamplePage> {

    private readonly heading: Locator;
    private readonly createButton: Locator;
    private readonly nameInput: Locator;

    constructor(public readonly page: Page) {
        super(page);
        this.heading = this.page.getByRole('heading', { name: 'Example' }).describe('Example page heading');
        this.createButton = this.page.getByRole('button', { name: 'Create' }).describe('Create button');
        this.nameInput = this.page.getByRole('textbox', { name: 'Name' }).describe('Name input');
    }

    async waitForLoad(): Promise<ExamplePage> {
        await this.heading.waitFor({ state: 'visible' });
        return this;
    }

    getHeading(): Locator {
        return this.heading;
    }

    getCreateButton(): Locator {
        return this.createButton;
    }

    async fillName(name: string): Promise<void> {
        await this.nameInput.fill(name);
    }

    async clickCreate(): Promise<ExamplePage> {
        await this.createButton.click();
        return await new ExamplePage(this.page).waitForLoad();
    }
}
