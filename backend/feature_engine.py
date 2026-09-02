import ollama
import json
import os


MEMORY_FILE = "fault_memory.json"

# =========================================================
# 1. LOCAL MEMORY FILE HANDLERS
# =========================================================
def load_fault_memory():
    """Safely loads the JSON cache. Returns an empty dict if missing or unreadable."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_fault_memory(data):
    """Writes the updated memory dictionary to fault_memory.json."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Nominal running baseline anchor
NOMINAL_CURRENT = 4500


def unsupervised_anomaly_detector(current_ma, pwm):
    """
    Hybrid Classifier with hard deadbands to eliminate sensor jitter.
    """
    # 1. Deterministic Box Track (Highest Priority)
    if 4000 <= current_ma <= 4900 and pwm > 0:
        return "HEALTHY_OPERATION"
    elif current_ma >= 5100 and pwm > 0:
        return "CRITICAL_STALL_FAULT"
    elif current_ma < 200 and pwm > 100:
        return "OPEN_CIRCUIT_FAULT"
        
    # 2. Adaptive Learning Track (With strict 300mA wide quantization buckets)
    else:
        # Quantize the deviation into massive 300mA blocks to kill micro-fluctuations
        raw_deviation = current_ma - NOMINAL_CURRENT
        quantized_bucket = round(raw_deviation / 300) * 300
        
        # Determine direction for better text readability
        direction = "ABOVE" if quantized_bucket >= 0 else "BELOW"
        abs_val = abs(quantized_bucket)
        
        # Unique, stable signature key (e.g., "ANOMALY_400_ABOVE")
        signature_key = f"ANOMALY_{abs_val}_{direction}"
        
        memory = load_fault_memory()
        if signature_key in memory:
            return f"LEARNED_{signature_key}"
        else:
            return f"NEW_{signature_key}"

def generate_local_ai_explanation(fault_code, current_ma, pwm):
    """
    Feeds clean, stabilized anomaly tokens to Phi-3 for flawless report generation.
    """
    memory = load_fault_memory()
    
    # Extract the clean signature substring
    sig_core = fault_code.replace("NEW_", "").replace("LEARNED_", "")
    
    historical_experience = ""
    is_new = "NEW_" in fault_code
    
    if not is_new and sig_core in memory:
        historical_experience = f"CRITICAL BASELINE: This exact electrical signature was resolved previously. Past Diagnosis: {memory[sig_core]}"

    prompt = f"""<|system|>
You are an expert embedded software diagnostic engineer. 
Instructions:
- Analyze the telemetry values provided.
- Write exactly TWO complete engineering sentences. Sentence 1: The direct physical cause of this current variance. Sentence 2: The exact localized inspection task.
- Do not use conversational introductory filler or greetings. Stop instantly after the second period.
<|user|>
Analyze this system anomaly:
- Current Telemetry: {current_ma} mA, PWM: {pwm}/255
- Signature Vector: {sig_core} (Amperage deviation trend)
{historical_experience}
<|assistant|>
"""
    try:
        response = ollama.generate(
            model='phi3',
            prompt=prompt,
            options={
                'temperature': 0.0,
                'num_predict': 120,
                'stop': ["<|end|>", "\n\n", "<|user|>"] 
            }
        )
        
        raw_text = response['response'].strip()
        if raw_text and not raw_text.endswith('.'):
            sentences = raw_text.split('.')
            if len(sentences) > 1:
                raw_text = ".".join(sentences[:-1]) + "."
                
        if is_new:
            memory[sig_core] = raw_text
            save_fault_memory(memory)
            return f"🤖 **Local Phi-3 [NEW ANOMALY CAUGHT & MEMORIZED]:**\n\n{raw_text}"
        else:
            return f"🤖 **Local Phi-3 [RECOGNIZED SIGNATURE]:**\n\n{raw_text}"
            
    except Exception as e:
        return f"⚠️ **AI Subsystem Error:** {e}"