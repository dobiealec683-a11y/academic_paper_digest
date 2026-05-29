from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from collections.abc import Iterable

from config import NOTEBOOKLM_MODE, EXPORTS_DIR
from utils import log_context, topic_slug

logger = logging.getLogger(__name__)

class NotebookLMBridge:
    def __init__(self, mode: str = NOTEBOOKLM_MODE) -> None:
        self.mode = mode.lower()
        self.exports_dir = EXPORTS_DIR
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def create_notebook(self, topic_name: str) -> str:
        """Creates a new notebook for the given topic."""
        if not topic_name.strip():
            raise ValueError("Notebook topic cannot be empty.")

        logger.info("Creating NotebookLM notebook", extra=log_context(mode=self.mode, topic=topic_name))
        if self.mode == "enterprise":
            raise NotImplementedError(
                "NotebookLM enterprise mode is not wired to a concrete API client yet. "
                "Use NOTEBOOKLM_MODE=mock or NOTEBOOKLM_MODE=notebooklm_py."
            )
        elif self.mode == "notebooklm_py":
            try:
                cmd = ["notebooklm", "create", "--title", topic_name]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                output = result.stdout.strip()
                logger.info("Created notebook through notebooklm CLI", extra=log_context(output=output))
                return topic_slug(topic_name)
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise RuntimeError(
                    "Failed to create NotebookLM notebook with notebooklm-py. "
                    "Confirm the `notebooklm` CLI is installed and authenticated with `notebooklm login`."
                ) from exc
        else:
            return f"mock_notebook_{topic_slug(topic_name)}"

    def upload_file_source(self, notebook_id: str, file_path: str | Path) -> bool:
        """Uploads a PDF or markdown file source."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"NotebookLM source file does not exist: {file_path}")

        logger.info(
            "Uploading file source to NotebookLM",
            extra=log_context(mode=self.mode, notebook_id=notebook_id, file=str(file_path)),
        )
        if self.mode == "enterprise":
            raise NotImplementedError("NotebookLM enterprise upload is not implemented.")
        elif self.mode == "notebooklm_py":
            try:
                cmd = ["notebooklm", "upload", "--notebook", notebook_id, "--file", str(file_path)]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise RuntimeError(f"Failed to upload {file_path} through notebooklm-py.") from exc
        else:
            return True

    def add_web_source(self, notebook_id: str, url: str) -> bool:
        """Adds a web URL source."""
        logger.info("Adding web source to NotebookLM", extra=log_context(mode=self.mode, url=url))
        if self.mode == "enterprise":
            raise NotImplementedError("NotebookLM enterprise web-source upload is not implemented.")
        elif self.mode == "notebooklm_py":
            try:
                cmd = ["notebooklm", "upload", "--notebook", notebook_id, "--url", url]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise RuntimeError(f"Failed to add URL source {url} through notebooklm-py.") from exc
        else:
            return True

    def add_text_source(self, notebook_id: str, source_name: str, content: str) -> bool:
        """Adds a raw text source."""
        logger.info("Adding text source to NotebookLM", extra=log_context(mode=self.mode, source=source_name))
        if self.mode == "enterprise":
            raise NotImplementedError("NotebookLM enterprise text-source upload is not implemented.")
        elif self.mode == "notebooklm_py":
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as file:
                file.write(content)
                temp_path = Path(file.name)
            try:
                cmd = ["notebooklm", "upload", "--notebook", notebook_id, "--file", str(temp_path)]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise RuntimeError(f"Failed to add text source {source_name} through notebooklm-py.") from exc
            finally:
                if temp_path.exists():
                    temp_path.unlink()
        else:
            return True

    def batch_add_sources(self, notebook_id: str, sources: Iterable[str | Path]) -> int:
        """Uploads multiple sources in batch."""
        success_count = 0
        for src in sources:
            if isinstance(src, (str, Path)):
                p = Path(src)
                if p.exists():
                    if self.upload_file_source(notebook_id, p):
                        success_count += 1
                else:
                    # Treat as web URL if it looks like one
                    if str(src).startswith("http") and self.add_web_source(notebook_id, str(src)):
                        success_count += 1
                    else:
                        logger.warning("Skipping missing NotebookLM source", extra=log_context(source=str(src)))
        return success_count

    def ask_notebook(self, notebook_id: str, prompt: str, output_filename: str | None = None) -> str:
        """Queries the notebook and returns the response string."""
        if not prompt.strip():
            raise ValueError("NotebookLM prompt cannot be empty.")
        logger.info("Querying NotebookLM", extra=log_context(mode=self.mode, notebook_id=notebook_id))
        
        response_text = ""
        if self.mode == "enterprise":
            raise NotImplementedError("NotebookLM enterprise query is not implemented.")
        elif self.mode == "notebooklm_py":
            try:
                cmd = ["notebooklm", "ask", "--notebook", notebook_id, "--prompt", prompt]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                response_text = result.stdout
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise RuntimeError(
                    "NotebookLM query failed through notebooklm-py. "
                    "Confirm the CLI is installed, authenticated, and the notebook id is valid."
                ) from exc
        else:
            response_text = self._generate_mock_response(notebook_id, prompt)

        if output_filename:
            out_path = self.exports_dir / output_filename
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response_text)
            logger.info("Saved NotebookLM response", extra=log_context(path=str(out_path)))

        return response_text

    def _generate_mock_response(self, notebook_id: str, prompt: str) -> str:
        """Generates realistic mock responses for dry-run/testing purposes."""
        cleaned_prompt = prompt.lower()
        topic = notebook_id.replace("mock_notebook_", "").replace("_", " ").title()
        
        if "per-paper extraction" in cleaned_prompt or "every paper" in cleaned_prompt:
            return f"""# Paper Extraction Table: {topic}

Here is the structured extraction for the papers in this notebook.

| Full Title | Authors | Year | Research Question | Key Findings | Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Attention Is All You Need | Vaswani et al. | 2017 | Can we train sequence models without recurrence? | The Transformer model achieves state-of-the-art results using self-attention mechanisms. | Computational cost of global attention on very long sequences. |
| Deep Residual Learning for Image Recognition | He et al. | 2016 | How to train extremely deep neural networks? | Residual connections solve the vanishing gradient problem in deep networks. | Diminishing returns after a certain depth. |
| Generative Adversarial Nets | Goodfellow et al. | 2014 | How to train generative models through adversarial games? | Discriminator and Generator networks trained simultaneously converge to realistic data samples. | Unstable training dynamics and mode collapse. |

*Sources: Vaswani et al. (2017) [1], He et al. (2016) [2], Goodfellow et al. (2014) [3].*
"""
        elif "cross-paper synthesis" in cleaned_prompt or "synthesize the literature" in cleaned_prompt:
            return f"""# Literature Synthesis: {topic}

Based on the uploaded sources, here is the synthesis of the body of research.

## 1. Agreement
The literature broadly agrees that deep architectures are fundamental to state-of-the-art AI representation, but the mechanism of routing information (residual paths, self-attention, adversarial feedback) dictates training stability and overall performance.

## 2. Disagreements and Conflicts
There are ongoing debates about resource efficiency. While self-attention allows massive parallelization (Vaswani et al., 2017), residual convolution networks are still highly preferred for pixel-level feature density without quadratic compute complexity (He et al., 2016).

## 3. Strongest Findings
- Skip/residual connections reliably stabilize gradients across hundreds of layers.
- Self-attention mechanisms capture long-range dependencies far better than recurrent models.

## 4. Weakest Findings / Gaps
- Theoretical convergence guarantees for GAN models are limited in practical high-dimensional settings.
- The scalability of transformers on infinite sequence lengths remains an open challenge.

## 5. Practitioner Action Items
- Use **Transformer backbones** for sequential, textual, or multi-modal contextual tasks.
- Integrate **Residual connections** as a mandatory baseline when building deep neural architectures.
"""
        elif "executive brief" in cleaned_prompt or "executive digest" in cleaned_prompt:
            return f"""# Executive Research Brief: {topic}

An executive summary of key insights extracted from the research literature.

### Insight 1: Attention is Highly Scale-Efficient
- **Why it matters:** Eliminates recurrent bottlenecks.
- **Evidence:** 100x training speedups over RNNs (Vaswani et al., 2017).
- **Implication:** Developers can train larger models on larger datasets.
- **Confidence:** High.

### Insight 2: Residual Connections Unlock Depth
- **Why it matters:** Avoids performance degradation during training.
- **Evidence:** Enabled 152-layer deep models (He et al., 2016).
- **Implication:** Always use residual skip links in complex networks.
- **Confidence:** High.

### Insight 3: Adversarial Games Yield Ultra-Realistic Generations
- **Why it matters:** Enables clean generative modeling of complex distributions.
- **Evidence:** Generator loss successfully guides image synthesis (Goodfellow et al., 2014).
- **Implication:** Prompts generative modeling frameworks.
- **Confidence:** Medium.
"""
        else:
            return f"""# Research Map: {topic}

## Theme A: Foundation Models & Self-Attention
- **Paper:** *Attention Is All You Need* (Vaswani et al., 2017)
  - **Key Finding:** Eliminating recurrence in favor of self-attention yields parallelizable sequence training.
- **Paper:** *Generative Adversarial Nets* (Goodfellow et al., 2014)
  - **Key Finding:** Adversarial loss guides neural networks to fit complex data distributions.

## Theme B: Architectural Depth and Optimization
- **Paper:** *Deep Residual Learning for Image Recognition* (He et al., 2016)
  - **Key Finding:** Identity shortcut connections map clean gradients directly back through deep networks.
"""
