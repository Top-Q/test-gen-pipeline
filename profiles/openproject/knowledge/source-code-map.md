# OpenProject Source Code Navigation

OpenProject is a Ruby on Rails application. When building locators and understanding the DOM:

## Local Source Code Location

The OpenProject Rails application source code is at:
`C:\Users\itaiag\git\ruby\openproject`

Use this to read Angular components, views, and routes directly to understand the DOM structure.

Key paths to read when building work package page objects:
- Angular work packages: `C:\Users\itaiag\git\ruby\openproject\frontend\src\app\features\work-packages\`
- Work package views: `C:\Users\itaiag\git\ruby\openproject\app\views\work_packages\`
- Work package routes: `C:\Users\itaiag\git\ruby\openproject\config\routes\work_packages.rb`

## Key Source Paths (in the Rails app)
- Routes: `config/routes.rb` and `config/routes/*.rb`
- Views: `app/views/` (ERB templates)
- Angular frontend: `frontend/src/app/`
- I18n keys: `config/locales/en.yml`
- Stimulus controllers: `app/javascript/controllers/`

## URL Patterns
- Base URL: `http://localhost:8090`
- API URL: `http://localhost:8080`
- Projects: `/projects/<identifier>/`
- Work packages: `/projects/<id>/work_packages`
- Boards: `/projects/<id>/boards`
- Members: `/projects/<id>/members`
- Meetings: `/projects/<id>/meetings`

## Authentication
- Default admin: username `admin`, password `admin`
- Session-based auth via cookie after login

## Common UI Patterns
- OpenProject uses Turbo (Hotwire) for page transitions
- Angular components for complex UI (work packages, boards)
- Primer design system for newer components
- `op-` prefix on custom Angular components
