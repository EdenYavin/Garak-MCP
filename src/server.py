from mcp.server.fastmcp import FastMCP
import requests
from src.utils import get_terminal_commands_output
from src.config import ModelConfig
import json
import tempfile
import os
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import asyncio
import subprocess
from typing import AsyncGenerator

os.makedirs("../output", exist_ok=True) # Will be used to store the output of the attack

REPORT_PREFIX = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output")), "output")

class GarakServer:

    def __init__(self):
        self.model_types = {
            "ollama": "rest",
            "huggingface": "huggingface",
            "openai": "openai",
            "ggml": "ggml"
        }
        self.ollama_api_url = "http://localhost:11434/api/generate"
        self.config = ModelConfig()


    def _get_generator_options_file(self, model_name: str) -> str:
        """
        Create a temporary config file with the model name set.
        
        Args:
            model_name (str): The name of the model to use
            
        Returns:
            str: Path to the temporary config file
        """
        # Load the base config
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ollama.json')
      
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Set the model name
        config['rest']['RestGenerator']['req_template_json_object']['model'] = model_name
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(config, temp_file)
        temp_file.close()
        
        return temp_file.name

    def run_attack(self, model_type: str, model_name: str, probe_name: str):
        """
        Run an attack with the given model and probe.

        Args:
            model_type (str): The type of model to use.
            model_name (str): The name of the model to use.
            probe_name (str): The name of the probe to use. 

        Returns:
            list: A list of vulnerabilities.
        """
        if model_type == "ollama":
            config_file = self._get_generator_options_file(model_name)
            try:
                return get_terminal_commands_output([
                    'garak',
                    '--model_type', 'rest',
                    '--generator_option_file', config_file,
                    '--probes', probe_name,
                    '--report_prefix', REPORT_PREFIX,
                    "--generations", "1",
                    "--config", "fast"

                ])
            finally:
                # Clean up the temporary file
                if os.path.exists(config_file):
                    os.unlink(config_file)
        else:
            return get_terminal_commands_output([
                'garak',
                '--model_type', model_type,
                '--model_name', model_name,
                '--probes', probe_name,
                '--report_prefix', REPORT_PREFIX,
                "--generations", "1",
                "--config", "fast"
            ])

# MCP Server
mcp = FastMCP("Garak MCP Server")


@mcp.tool()
def list_model_types():
    """
    List all available model types.

    Returns:
        list[str]: A list of available model types.
    """
    return list(GarakServer().model_types.keys())


@mcp.tool()
def list_models(model_type: str) -> list[str]:
    """
    List all available models for a given model type.
    Those models can be used for the attack and target models.

    Args:
        model_type (str): The type of model to list (ollama, openai, huggingface, ggml)

    Returns:
        list[str]: A list of available models.
    """
    return GarakServer().config.list_models(model_type)

@mcp.tool()
def list_garak_probes():
    """
    List all available Garak probes.

    Returns:
        list: A list of available probes / attacks.
    """
    return get_terminal_commands_output(['garak', '--list_probes'])

@mcp.tool()
def get_report():
    """
    Get the report of the last run.

    Returns:
        str: The path to the report file.
    """
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'output.report.jsonl')

@mcp.tool()
def run_attack(model_type: str, model_name: str, probe_name: str):
    """
    Run an attack with the given model and probe.

    Args:
        model_type (str): The type of model to use.
        model_name (str): The name of the model to use.
        probe_name (str): The name of the probe to use.

    Returns:
        list: A list of vulnerabilities.
    """
    return GarakServer().run_attack(model_type, model_name, probe_name)


