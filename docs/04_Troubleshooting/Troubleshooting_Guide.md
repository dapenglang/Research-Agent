# Troubleshooting Guide — Research Agent v3

**Date:** 2026-08-15

---

## 1. Python 3.12 Dependency Error

**Symptom:** `ModuleNotFoundError` or `ImportError` when running the pipeline.
**Cause:** A dependency in `requirements.txt` is not compatible with Python 3.12.
**Check:**
```powershell
conda activate research_agent_v3
python --version  # Should show 3.12.x
pip list | findstr <package_name>
```
**Fix:**
1. Check `requirements.txt` for the minimum version requirement.
2. Upgrade the package: `pip install --upgrade <package_name>`
3. If the package has no Python 3.12 wheel, record it as `PY312_COMPATIBILITY_BLOCKER`.
**Verify:** `python -c "import <package_name>; print('OK')"`

---

## 2. CUDA Unavailable (`torch.cuda.is_available() = False`)

**Symptom:** PyTorch reports CUDA is not available; GPU experiments cannot run.
**Cause:** NVIDIA driver missing, incompatible, or PyTorch installed without CUDA support.
**Check:**
```powershell
python -c "import torch; print(torch.cuda.is_available())"
python -c "import torch; print(torch.version.cuda)"
nvidia-smi
```
**Fix:**
1. Install/update NVIDIA display driver (compatible with CUDA 12.1).
2. Reinstall PyTorch with CUDA: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`
3. If no NVIDIA GPU: real experiments will not run. Use synthetic experiments only.
**Verify:** `python -c "import torch; print(torch.cuda.is_available())"` should show `True`.

---

## 3. GPU Out of Memory (OOM)

**Symptom:** `RuntimeError: CUDA out of memory` during model loading or experiment execution.
**Cause:** Model exceeds available VRAM (4GB on RTX A500).
**Check:**
```powershell
python -c "import torch; print(f'VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')"
```
**Fix:**
1. Use 4-bit quantization: `model = AutoModelForCausalLM.from_pretrained(name, load_in_4bit=True)`
2. Use CPU offloading: `device_map="auto"`
3. Use gradient checkpointing.
4. Reduce batch size in experiment config.
5. If still OOM: system returns `BLOCKED_BY_VRAM`. Do NOT swap to a smaller model silently.
**Verify:** Re-run the experiment and confirm no OOM error.

---

## 4. Hugging Face Download Timeout

**Symptom:** `requests.exceptions.ReadTimeout` or `ConnectionError` when downloading models.
**Cause:** Network timeout, firewall, or Hugging Face rate limiting.
**Check:**
```powershell
python -c "import requests; r = requests.get('https://huggingface.co', timeout=10); print(r.status_code)"
```
**Fix:**
1. Check internet connection.
2. Set proxy in `configs/machine.yaml` if behind a firewall.
3. Set `HF_TOKEN` environment variable for authenticated access.
4. Download manually using `huggingface-cli download`.
5. Use offline copy (see Model Hub Guide).
**Verify:** Model directory exists and contains `config.json`.

---

## 5. Proxy Error

**Symptom:** `ProxyError` or `ConnectionRefusedError` when accessing external APIs.
**Cause:** Corporate proxy not configured.
**Fix:**
1. Set proxy in `configs/machine.yaml`:
   ```yaml
   machine:
     network:
       proxy: "http://proxy.company.com:8080"
   ```
2. Set environment variables:
   ```powershell
   $env:HTTP_PROXY = "http://proxy.company.com:8080"
   $env:HTTPS_PROXY = "http://proxy.company.com:8080"
   ```
**Verify:** `python -c "import requests; print(requests.get('https://api.openai.com').status_code)"`

---

## 6. Model Missing

**Symptom:** `FileNotFoundError` or `OSError: Model path does not exist`.
**Cause:** Model not downloaded or path incorrect in `model_registry.yaml`.
**Check:**
```powershell
# Check if the path exists
python -c "
import yaml, os
reg = yaml.safe_load(open('configs/model_registry.yaml'))
storage = yaml.safe_load(open('configs/storage.yaml'))
root = storage['storage']['root']
for name, spec in reg['models'].items():
    path = spec['local_path'].replace('${DATA_ROOT}', root)
    print(f'{name}: {path} -> exists={os.path.exists(path)}')
"
```
**Fix:**
1. Download the model (see Model Hub Guide).
2. Verify the path in `model_registry.yaml` matches the actual location.
3. Ensure `storage.root` is set correctly in `storage.yaml`.
**Verify:** Re-run the check command and confirm `exists=True`.

---

## 7. Model Loading Falls Back to Mock

**Symptom:** System silently uses Mock provider instead of a real LLM.
**Cause:** Provider not configured, API key missing, or `llm.type` set to `"mock"` in task config.
**Fix:**
1. Check `research_task.yaml`: ensure `llm.type` is `"openai"` or `"local"`, NOT `"mock"`.
2. Check `OPENAI_API_KEY` environment variable is set.
3. Check `providers.yaml` has correct configuration.
4. The `validate_usage()` function should prevent this for production tasks. If it happens, check logs.
**Verify:** `python -c "from Research_Agent_v3.infrastructure.llm.llm_provider import validate_usage; print(validate_usage('mock', 'literature_analysis'))"` should return `False`.

---

## 8. LLM Provider Missing

**Symptom:** `BLOCKED` or `NOT_CONFIGURED` error when starting a production task.
**Cause:** No real LLM provider configured (OpenAI API key missing, local endpoint unreachable).
**Fix:**
1. Set `OPENAI_API_KEY` environment variable, OR
2. Start a local LLM server and update `providers.yaml`.
3. Set `llm.type` in `research_task.yaml` to `"openai"` or `"local"`.
**Verify:** `python -c "from Research_Agent_v3.infrastructure.llm.llm_provider import LLMProviderFactory; f=LLMProviderFactory(); p=f.create('openai'); print(p.is_available())"`

---

## 9. Config Path Error

**Symptom:** `FileNotFoundError` when loading config files.
**Cause:** Config file not found at expected path, or `storage.root` not set.
**Check:**
```powershell
python -c "
import yaml
for f in ['machine', 'storage', 'providers', 'model_registry']:
    try:
        yaml.safe_load(open(f'configs/{f}.yaml'))
        print(f'{f}.yaml: OK')
    except FileNotFoundError:
        print(f'{f}.yaml: MISSING')
"
```
**Fix:**
1. Ensure all config files exist in `configs/`.
2. Set `storage.root` in `storage.yaml`.
3. Use forward slashes `/` in YAML paths.
**Verify:** Re-run the check command.

---

## 10. Windows Path Issues

**Symptom:** Path-related errors on Windows (backslash vs forward slash).
**Cause:** Windows uses backslashes but YAML and Python prefer forward slashes.
**Fix:**
1. In YAML config files: use forward slashes `/` (e.g. `D:/ResearchData/models`)
2. In PowerShell: both `\` and `/` work.
3. In Python: `pathlib.Path` handles both.
4. Avoid spaces in directory names.
**Verify:** Pipeline starts without path errors.

---

## 11. PowerShell vs Bash

**Symptom:** Script fails because it was written for the wrong shell.
**Cause:** Using the bash script on Windows or vice versa.
**Fix:**
- On Windows: use `scripts/setup_environment_windows.ps1`
- On Linux/macOS: use `scripts/setup_environment.sh`
- Do NOT mix them.
**Verify:** Script runs successfully.

---

## 12. Checkpoint / Resume Failure

**Symptom:** `resume` command fails or resumes from wrong state.
**Cause:** State files corrupted, or state directory not found.
**Check:**
```powershell
# Check state directory
python -m Research_Agent_v3.cli.cli status --task my_task.yaml
```
**Fix:**
1. Check `--state-root` directory exists.
2. If state is corrupted: start fresh with `start` command.
3. Check the state machine status (`EXPERIMENT_RUNNING`, `EXPERIMENT_INTERRUPTED`, `EXPERIMENT_RESUMING`).
**Verify:** `status` command shows correct state.

---

## 13. Module Validation Failure

**Symptom:** Module raises `ValidationError` during `validate_input()` or `validate_output()`.
**Cause:** Input/output files don't match the module's schema.
**Fix:**
1. Check the module's `schema.py` for required fields.
2. Ensure upstream module produced all required output files.
3. Use `rerun --from <module_id>` to re-run from the failing module.
4. Check `data_origin` tags (synthetic vs real) are correct.
**Verify:** Re-run the module and confirm validation passes.

---

## 14. Import Error — Module Not Found

**Symptom:** `ModuleNotFoundError: No module named 'Research_Agent_v3'`
**Cause:** Python path not set, or running from wrong directory.
**Fix:**
```powershell
# Run from the PARENT directory of Research_Agent_v3
cd C:\  # or wherever the parent is
python -m Research_Agent_v3.cli.cli --help
```
**Verify:** CLI help message appears.
