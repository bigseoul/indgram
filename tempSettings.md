{
    "editor.tabSize": 4,
    "editor.insertSpaces": true,
    "editor.formatOnSave": true,
    "editor.links": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "terminal.integrated.cwd": "${workspaceFolder}",
    "files.associations": {
        "**/*.html": "html",
        "**/*.js": "javascript",
        "**/*.css": "css",
        "**/requirements{/**,*}.{txt,in}": "pip-requirements"
    },
    "emmet.triggerExpansionOnTab": true,
    "[python]": {
        "editor.tabSize": 4,
        "editor.codeActionsOnSave": {
            "source.fixAll": "explicit",
            "source.organizeImports": "explicit"
        },
        "editor.defaultFormatter": "charliermarsh.ruff"
    },
    "[jsonc]": {
        "editor.defaultFormatter": "vscode.json-language-features"
    },
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true
}


===

antigravity
{
    "mcpServers": {
        "context7": {
            "serverUrl": "https://mcp.context7.com/mcp",
            "headers": {
                "CONTEXT7_API_KEY": "ctx7sk-21ed3816-db2f-4f31-a5ad-482ef583d371"
            }
        },
        "serena": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/oraios/serena",
                "serena",
                "start-mcp-server",
                "--transport",
                "stdio"
            ]
        }
    }
}
