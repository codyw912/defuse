{ pkgs, lib, config, inputs, ... }:

{
  # Enable devcontainer support with security settings
  devcontainer = {
    enable = true;
    settings = {
      name = "Python UV Development";
      image = "ghcr.io/astral-sh/uv:python3.13-bookworm-slim";
      
      # Security settings
      remoteUser = "devuser";
      runArgs = [
        "--cap-drop=ALL"
        "--cap-add=CHOWN"
        "--cap-add=DAC_OVERRIDE" 
        "--cap-add=FOWNER"
        "--cap-add=SETGID"
        "--cap-add=SETUID"
        "--security-opt=no-new-privileges:true"
      ];
      
      # Container initialization
      onCreateCommand = ''
        # Install additional system dependencies
        apt-get update && apt-get install -y git build-essential && rm -rf /var/lib/apt/lists/*
        
        # Create non-root user
        groupadd --gid 1000 devuser
        useradd --uid 1000 --gid devuser --shell /bin/bash --create-home devuser
        
        # Setup UV cache
        mkdir -p /tmp/uv-cache && chown devuser:devuser /tmp/uv-cache
      '';
      
      postCreateCommand = "uv sync";
      
      # Port forwarding
      forwardPorts = [ 8000 8080 ];
      
      # Volume mounts for caching
      mounts = [
        "source=uv-cache,target=/tmp/uv-cache,type=volume"
      ];
      
      # Environment variables
      containerEnv = {
        UV_CACHE_DIR = "/tmp/uv-cache";
        UV_COMPILE_BYTECODE = "1";
        UV_LINK_MODE = "copy";
        PYTHONPATH = "./src";
      };
    };
  };

  # https://devenv.sh/basics/
  env = {
    PYTHONPATH = "./src";
    # UV container optimization
    UV_CACHE_DIR = "/tmp/uv-cache";
    UV_COMPILE_BYTECODE = "1";
    UV_LINK_MODE = "copy";
  };
  
  # https://devenv.sh/packages/
  packages = with pkgs; [
    git
    just  # command runner
  ];

  # Python environment with uv
  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = false;
    };
  };

  # https://devenv.sh/tasks/
  tasks = {
    "uv:setup" = {
      exec = ''
        if [ ! -f pyproject.toml ]; then
          echo "Initializing Python project with uv..."
          uv init --no-readme
          uv add --dev pytest ruff ty
        fi
        uv sync
      '';
      before = [ "devenv:enterShell" ];
    };
  };

  # https://devenv.sh/scripts/
  scripts.test.exec = "uv run pytest";
  scripts.lint.exec = "uv run ruff check .";
  scripts.format.exec = "uv run ruff format .";
  scripts.check.exec = "uv run ty check .";  # Type check

  # https://devenv.sh/reference/options/#git-hooks
  git-hooks.hooks = {
    ruff.enable = true;
    ruff-format.enable = true;
    # ty doesn't have pre-commit hook, run manually
  };

  # Enter shell message
  enterShell = ''
    echo "🐍 Python development environment activated"
    echo "Available commands:"
    echo "  - uv run <command>   # Run with project dependencies"
    echo "  - test               # Run tests"
    echo "  - lint               # Check code"
    echo "  - format             # Format code"
    echo "  - check              # Type checking"
  '';
}
