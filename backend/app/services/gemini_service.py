import os
import json
import re
import requests
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = "gemini-3-flash-preview"
OPENROUTER_MODEL = "anthropic/claude-opus-4.7:fast"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _get_gemini_client():
    return genai.Client(api_key=os.getenv('GEMINI_API_KEY'))


def _call_openrouter(prompt: str, stream: bool = False) -> str:
    """Fallback: Call OpenRouter API with Claude Opus 4.7 Fast."""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key or api_key == 'your_openrouter_api_key_here':
        raise Exception("OpenRouter API key not configured. Set OPENROUTER_API_KEY in .env")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "ThinkPadLLM"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream
    }

    if stream:
        return _stream_openrouter(headers, payload)

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']


def _stream_openrouter(headers, payload):
    """Generator that yields text chunks from OpenRouter streaming response."""
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, stream=True, timeout=120)
    response.raise_for_status()
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                if data_str.strip() == '[DONE]':
                    break
                try:
                    chunk_data = json.loads(data_str)
                    delta = chunk_data.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


def _generate_with_fallback(prompt: str) -> str:
    """Try Gemini first, fall back to OpenRouter if Gemini fails."""
    # Try Gemini
    try:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt
        )
        if response.text:
            return response.text
    except Exception as gemini_err:
        print(f"[AI] Gemini failed: {gemini_err}")

    # Fallback to OpenRouter
    print("[AI] Falling back to OpenRouter (Claude Opus 4.7 Fast)...")
    return _call_openrouter(prompt)


def generate_structured_notes(extracted_text: str) -> str:
    """Generate clean, structured notes from raw OCR text."""
    prompt = f"""You are an expert note-taker and academic assistant.

Given the following raw text extracted from handwritten notes, a whiteboard, or a document:

---
{extracted_text}
---

Generate beautifully structured notes in Markdown format:
- Create clear headings (##, ###)
- Use bullet points and numbered lists where appropriate
- Bold key terms and concepts
- Add a "Key Takeaways" section at the end
- Fix any OCR errors and make the text coherent
- Maintain the original meaning and information

Return ONLY the Markdown content, no preamble."""

    return _generate_with_fallback(prompt)


def generate_summary(extracted_text: str, title: str = "") -> str:
    """Generate a concise summary with key points."""
    prompt = f"""You are an expert academic summarizer.

Content to summarize{' titled "' + title + '"' if title else ''}:
---
{extracted_text}
---

Create a comprehensive summary that includes:
1. **Executive Summary** (2-3 sentences)
2. **Main Topics Covered** (bullet list)
3. **Key Concepts** (with brief definitions)
4. **Important Takeaways** (3-5 points)
5. **Questions for Further Study** (2-3 questions)

Format in clean Markdown. Be concise but complete."""

    return _generate_with_fallback(prompt)


def generate_explanation(extracted_text: str, topic: str = "") -> str:
    """Generate a beginner-friendly explanation."""
    prompt = f"""You are a brilliant teacher who can explain complex topics simply.

Topic/Content to explain:
---
{extracted_text}
---

Create a clear, beginner-friendly explanation:
1. Start with a simple analogy or real-world example
2. Break down complex terms into simple language
3. Use the "Explain Like I'm 5" approach for key concepts
4. Add examples for each major concept
5. End with a "Quick Recap" section

Format in clean Markdown with headers and bullet points."""

    return _generate_with_fallback(prompt)


def generate_mermaid_diagram(extracted_text: str) -> str:
    """Generate a Mermaid.js flowchart from content."""
    prompt = f"""You are an expert at creating Mermaid.js diagrams.

Based on this content:
---
{extracted_text}
---

Generate a Mermaid.js diagram that visually represents the main concepts, processes, or relationships.

Rules:
- Use `graph TD` (top-down) or `graph LR` (left-right) based on what fits best
- Keep node labels short (under 30 chars)
- Use subgraphs for grouped concepts
- Add styling with `style` commands for important nodes
- Maximum 15-20 nodes for clarity

Return ONLY the raw Mermaid syntax, starting with `graph TD` or `graph LR`.
Do NOT include any markdown code blocks, backticks, or explanations.
ONLY return the raw mermaid diagram code."""

    text = _generate_with_fallback(prompt)
    text = text.strip()
    text = re.sub(r'^```mermaid\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def generate_quiz(extracted_text: str, num_questions: int = 5) -> list:
    """Generate quiz questions from content."""
    prompt = f"""You are an expert quiz creator.

Based on this content:
---
{extracted_text}
---

Create {num_questions} multiple-choice quiz questions. Return ONLY a valid JSON array with this exact structure:
[
  {{
    "question": "Question text here?",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "correct": "A",
    "explanation": "Brief explanation of why this is correct"
  }}
]

Make questions test understanding, not just memorization.
Return ONLY the JSON array, no other text."""

    text = _generate_with_fallback(prompt)
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []


def generate_flashcards(extracted_text: str, num_cards: int = 8) -> list:
    """Generate flashcards from content."""
    prompt = f"""You are an expert educational content creator.

Based on this content:
---
{extracted_text}
---

Create {num_cards} flashcards for studying. Return ONLY a valid JSON array:
[
  {{
    "front": "Term or Question",
    "back": "Definition or Answer",
    "category": "Category name"
  }}
]

Focus on key terms, concepts, and important relationships.
Return ONLY the JSON array, no other text."""

    text = _generate_with_fallback(prompt)
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []


def chat_with_context(messages: list, context: str, user_message: str) -> str:
    """Contextual AI chat using workspace content as RAG context."""
    system_prompt = f"""You are Insight AI, an intelligent learning assistant for ThinkPadLLM.

You have access to the user's notes and workspace content:
---
CONTEXT (User's Notes/Content):
{context[:8000]}  
---

Instructions:
- Answer questions based on the provided context
- If the answer isn't in the context, say so but still try to help
- Be conversational, clear, and educational
- When explaining complex topics, use simple analogies
- If asked to generate a flowchart/diagram, respond with: [DIAGRAM]: followed by valid Mermaid.js syntax
- If asked to generate a quiz, format as numbered questions with options
- Keep responses focused and structured with Markdown formatting"""

    full_prompt = f"{system_prompt}\n\nPrevious conversation:\n"
    for msg in messages[-10:]:
        role = "User" if msg['role'] == 'user' else "Assistant"
        full_prompt += f"\n{role}: {msg['content']}"

    full_prompt += f"\n\nUser: {user_message}\nAssistant:"

    return _generate_with_fallback(full_prompt)


def stream_chat_with_context(messages: list, context: str, user_message: str):
    """Streaming version of chat_with_context. Tries Gemini, falls back to OpenRouter."""
    system_prompt = f"""You are Insight AI, an intelligent learning assistant for ThinkPadLLM.

You have access to the user's notes and workspace content:
---
CONTEXT:
{context[:8000]}
---

Be helpful, educational, and use Markdown formatting in your responses."""

    full_prompt = f"{system_prompt}\n\n"
    for msg in messages[-8:]:
        role = "User" if msg['role'] == 'user' else "Assistant"
        full_prompt += f"{role}: {msg['content']}\n"
    full_prompt += f"\nUser: {user_message}\nAssistant:"

    # Try Gemini streaming first
    try:
        client = _get_gemini_client()
        response = client.models.generate_content_stream(
            model=GEMINI_MODEL, contents=full_prompt
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
        return  # Success — don't fall back
    except Exception as gemini_err:
        print(f"[AI] Gemini streaming failed: {gemini_err}")

    # Fallback to OpenRouter streaming
    print("[AI] Falling back to OpenRouter streaming (Claude Opus 4.7 Fast)...")
    for chunk in _call_openrouter(full_prompt, stream=True):
        yield chunk


def extract_key_topics(extracted_text: str) -> list:
    """Extract main topics from content."""
    prompt = f"""Extract the 5-8 main topics or key concepts from this content:
---
{extracted_text[:3000]}
---

Return ONLY a JSON array of strings:
["Topic 1", "Topic 2", "Topic 3"]

No other text."""

    text = _generate_with_fallback(prompt)
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except:
        return []


def generate_title_from_content(extracted_text: str) -> str:
    """Generate a descriptive title from content."""
    prompt = f"""Generate a short, descriptive title (5-8 words max) for this content:
---
{extracted_text[:500]}
---

Return ONLY the title text, no quotes, no punctuation at end."""

    text = _generate_with_fallback(prompt)
    return text.strip().replace('"', '').replace("'", "")
