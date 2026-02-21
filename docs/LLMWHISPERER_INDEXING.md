# LLMWhisperer V2 indexing checklist

Use this checklist so document indexing works when the profile uses **LLMWhisperer V2** as the text extractor.

---

## 1. Config (URL + API key)

### Environment variables

Set these **before** creating default adapters (or when running the backend that stores adapter config):

| Variable | Description | Example |
|----------|-------------|---------|
| `LLMWHISPERER_URL` | Base URL of the LLMWhisperer V2 service (no trailing slash). Must be reachable from **prompt-service**. | `http://llmwhisperer:8080` or `https://llmwhisperer.example.com` |
| `LLMWHISPERER_KEY` | API key for the `unstract-key` header. | Your LLMWhisperer API key |

### Create or update the adapter

- **If using default adapters:**  
  Set `LLMWHISPERER_URL` and `LLMWHISPERER_KEY`, then run:
  ```bash
  python manage.py create_default_adapters
  ```
  The LLMWhisperer V2 adapter will be created with `url` and `unstract_key` from these env vars.

- **If creating/editing the adapter in the UI:**  
  In the adapter configuration set:
  - **url** – same as `LLMWHISPERER_URL` above.
  - **unstract_key** – same as `LLMWHISPERER_KEY` above.

### Attach to the profile used for indexing

- In Prompt Studio, the profile used for indexing (usually the **default LLM profile**) must have its **text extractor / x2text** set to the **LLMWhisperer V2** adapter instance.
- If you only have one profile, set its text extractor to LLMWhisperer V2 and set it as default.

---

## 2. Network (prompt-service → LLMWhisperer)

- The **prompt-service** process (not the backend) calls the LLMWhisperer URL. So the URL must be a hostname and port that **prompt-service** can resolve and connect to.

- **Do not use `localhost`** unless LLMWhisperer runs in the **same** container as prompt-service. Prefer:
  - Docker service name, e.g. `http://llmwhisperer:8080`, if both run in the same Docker Compose stack.
  - Hostname or IP that resolves from the prompt-service host/container.

- **Test connectivity** from the same environment where prompt-service runs. Use the script `docker/scripts/test_llmwhisperer_from_prompt_service.sh` (run it from inside the prompt-service container so it uses the same network; mount the repo or copy the script in if needed):
  ```bash
  # Example: repo mounted at /app in container
  docker compose exec prompt-service sh -c 'apk add --no-cache curl 2>/dev/null; sh /app/docker/scripts/test_llmwhisperer_from_prompt_service.sh'
  # Or pass URL and key as arguments:
  docker compose exec -e LLMWHISPERER_URL=http://llmwhisperer:8080 -e LLMWHISPERER_KEY=yourkey prompt-service sh /app/docker/scripts/test_llmwhisperer_from_prompt_service.sh
  ```
  A **2xx** result means the URL is reachable and the key is accepted.

- **Firewall / security groups:** Allow outbound traffic from the prompt-service host to the LLMWhisperer host and port.

---

## 3. Service (LLMWhisperer V2 up and response format)

- **Keep the service running** (e.g. restart policy, health checks). If it is down, extraction will fail after retries.

- **Response format:** The adapter expects the extraction response to include **`result_text`**. If your LLMWhisperer API returns the text under a different key, the integration must be updated to map it to `result_text`.

---

## Quick reference

| Your responsibility | What to do |
|---------------------|------------|
| **Config** | Set `LLMWHISPERER_URL` and `LLMWHISPERER_KEY`; run `create_default_adapters` or set `url` and `unstract_key` in the adapter; attach LLMWhisperer V2 to the profile used for indexing. |
| **Network** | Use a URL that prompt-service can resolve and reach; test with `curl` from the prompt-service host; open firewall if needed. |
| **Service** | Keep LLMWhisperer V2 running and returning responses that include `result_text`. |

Once config and network are correct, retries and error messages in the code will help indexing succeed or give clear errors to fix.
