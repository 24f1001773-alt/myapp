import os
from typing import List

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS: lets the grader's web page call your API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 1: hardcoded defaults
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# Alias: NUM_WORKERS means the same thing as workers
ALIASES = {"num_workers": "workers"}


def norm_key(key: str) -> str:
    key = key.strip().lower()
    return ALIASES.get(key, key)


def to_bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def coerce(key: str, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return to_bool(value)
    return str(value)


def load_yaml() -> dict:
    env = os.getenv("APP_ENV", "development")
    try:
        with open(f"config.{env}.yaml") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    return {norm_key(k): v for k, v in data.items()}


def load_dotenv(path=".env") -> dict:
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                result[norm_key(k)] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return result


def load_os_env() -> dict:
    result = {}
    for k, v in os.environ.items():
        if k.startswith("APP_") and k != "APP_ENV":
            result[norm_key(k[4:])] = v
    return result


@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    config = dict(DEFAULTS)            # weakest
    config.update(load_yaml())         # + yaml
    config.update(load_dotenv())       # + .env
    config.update(load_os_env())       # + OS env

    # Highest precedence: ?set=key=value
    for item in set:
        if "=" in item:
            k, v = item.split("=", 1)
            config[norm_key(k)] = v

    # Convert types
    result = {k: coerce(k, v) for k, v in config.items()}

    # Hide the secret
    result["api_key"] = "****"
    return result