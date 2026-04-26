# Project-Local Claude Configuration

This folder contains all Claude Code settings and configuration specific to the ExstreamVectorLessRag / Compass project.

## Files

- **settings.json** — Project-specific settings including Python version, LLM configuration, environment variables, and file paths

## Environment Setup

Before running Claude Code tasks on this project, ensure the following environment variable is set:

```bash
set OPENROUTER_API_KEY=your_openrouter_api_key_here
```

Or on Windows PowerShell:
```powershell
$env:OPENROUTER_API_KEY="your_openrouter_api_key_here"
```

## Project Configuration

- **Python Version:** 3.11.9
- **LLM Provider:** OpenRouter
- **LLM Model:** Deepseek v4 (deepseek/deepseek-chat)
- **Project Root:** E:\AIWorkSpace\ExstreamVectorLessRag

All paths and settings are project-local and not shared with global Claude configuration.
