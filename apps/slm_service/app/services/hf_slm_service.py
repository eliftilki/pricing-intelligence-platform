import logging
import torch

from transformers import AutoTokenizer, AutoModelForCausalLM

from app.core.config import settings


logger = logging.getLogger(__name__)


class HFSLMService:
    def __init__(self) -> None:
        self.model_name = settings.hf_model_name
        self.tokenizer = None
        self.model = None

    def load_model(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        logger.info("Loading SLM model: %s", self.model_name)

        token_kwargs = {}
        if settings.hf_token:
            token_kwargs["token"] = settings.hf_token

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            **token_kwargs,
        )

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            device_map="auto",
            **token_kwargs,
        )

        self.model.eval()

        logger.info("SLM model loaded successfully.")

    def generate(self, messages: list[dict[str, str]]) -> str:
        if self.model is None or self.tokenizer is None:
            self.load_model()

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=settings.max_new_tokens,
                temperature=settings.temperature,
                top_p=settings.top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]

        response = self.tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True,
        )

        return response.strip()


slm_service = HFSLMService()