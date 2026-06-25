---
name: Export Data from App
created_at: '2026-06-12T14:49:21Z'
updated_at: '2026-06-12T14:49:21Z'
version: 1
---

# Skill Name: Export Data from App
## Core Problem
User needs to export data from an application through the settings menu.
## S_route
| Intent | Action | Resource |
| Open app | launch | app |
| Access settings | click | Settings |
| Initiate export | choose | Export |
## S_body
1. Open the app.
2. Click Settings.
3. Choose Export.
## S_trigger
- keywords: export, settings, app, data export
## S_params
- app: the application to open and export data from
