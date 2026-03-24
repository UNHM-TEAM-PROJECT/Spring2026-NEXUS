## AI-Based Syllabus Information Detection (GROQ Integration)
Created By: Swathi Danturi, Team NEXUS Spring 2026

### What is GROQ used for
- GROQ is used to add AI-based detection in the system
- It uses a Large Language Model (LLaMA 3) to read syllabus text and extract the preferred contact method
- Instead of matching patterns, it understands the meaning of the text

### Why GROQ
- It uses models like LLaMA 3, which are open-source. This means they are more flexible and not restricted to be paid.

- Another important reason is that GROQ provides a free tier, so we can test and run our system without extra cost. It also supports decent size inputs, up to 8192 tokens, which is enough for handling syllabus text.

### How GROQ works in this system
- The extracted syllabus text is sent to GROQ API
- A prompt asks the model to find the preferred contact method
- GROQ returns: A value (Email, Canvas, etc.) or `Not found` if missing

### GROQ set up and usage
- Step 1: Install GROQ library: `pip install groq`
- Step 2: Get GROQ API Key
    - go to https://console.groq.com
    - sign up or login 
    - generate an API key
- Step 3: Set API key
    - in your terminal, `setx GROQ_API_KEY "your_api_key_here"`
    - restart your terminal after this
Use this key in your code for detector in the backend

### Token Usage
- GROQ processes text in tokens, small parts of text
- Typical usage for this PoC: Input text: ~1000–3000 tokens, Output: ~1–5 tokens
- Limit per request is 8192 tokens, and it is 30 requests/min × 3000 tokens ≈ 90,000 tokens/min
- This is within safe limits, so the system runs efficiently without hitting limits