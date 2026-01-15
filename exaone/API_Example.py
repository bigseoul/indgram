from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "LGAI-EXAONE/K-EXAONE-236B-A23B"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype="bfloat16",
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

messages = [
    {"role": "system", "content": "You are K-EXAONE, a large language model developed by LG AI Research in South Korea, built to serve as a helpful and reliable assistant."},
    {"role": "user", "content": "Which one is bigger, 3.9 vs 3.12?"}
]
input_ids = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors="pt",
    enable_thinking=True,   # skippable (default: True)
)

generated_ids = model.generate(
    **input_ids.to(model.device),
    max_new_tokens=16384,
    temperature=1.0,
    top_p=0.95,
    do_sample=True,
)
output_ids = generated_ids[0][input_ids['input_ids'].shape[-1]:]
print(tokenizer.decode(output_ids, skip_special_tokens=True))
