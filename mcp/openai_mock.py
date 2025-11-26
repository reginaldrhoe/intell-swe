from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import hashlib
import typing

app = FastAPI()


def _deterministic_vector(text: str, dim: int = 1536) -> typing.List[float]:
    h = hashlib.sha256(text.encode('utf-8')).digest()
    vals: typing.List[float] = []
    i = 0
    while len(vals) < dim:
        b = h[i % len(h)]
        vals.append((b / 255.0) * 2.0 - 1.0)
        i += 1
    # normalize
    norm = sum(x * x for x in vals) ** 0.5
    if norm > 0:
        vals = [x / norm for x in vals]
    return vals


@app.post('/v1/chat/completions')
async def chat_completions(req: Request):
    body = await req.json()
    # Very small deterministic reply: look into messages for keywords
    messages = body.get('messages') or []
    user_text = ''
    for m in messages:
        if m.get('role') == 'user':
            user_text = m.get('content', '')
            break

    reply = 'I am a mock OpenAI. '
    if 'sky' in user_text.lower():
        reply += 'The color of the sky is blue.'
    elif user_text:
        reply += f"You asked: {user_text[:200]}"
    else:
        reply += 'Hello from the mock.'

    response = {
        'id': 'mock-chat-1',
        'object': 'chat.completion',
        'created': 0,
        'model': body.get('model', 'gpt-mock'),
        'choices': [
            {
                'index': 0,
                'message': {'role': 'assistant', 'content': reply},
                'finish_reason': 'stop'
            }
        ],
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    }
    return JSONResponse(response)


@app.post('/v1/completions')
async def completions(req: Request):
    body = await req.json()
    prompt = ''
    if isinstance(body.get('prompt'), list):
        prompt = '\n'.join(body.get('prompt'))
    else:
        prompt = body.get('prompt') or ''

    reply = 'Mock completion.'
    if 'sky' in prompt.lower():
        reply = 'The color of the sky is blue.'
    elif prompt:
        reply = f"Prompt: {prompt[:200]}"

    response = {
        'id': 'mock-completion-1',
        'object': 'text_completion',
        'created': 0,
        'model': body.get('model', 'text-mock'),
        'choices': [{'text': reply, 'index': 0, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    }
    return JSONResponse(response)


@app.post('/v1/embeddings')
async def embeddings(req: Request):
    body = await req.json()
    input_data = body.get('input', '')
    
    # Handle both string and list inputs
    if isinstance(input_data, str):
        texts = [input_data]
    elif isinstance(input_data, list):
        # Flatten nested lists and ensure all elements are strings
        texts = []
        for item in input_data:
            if isinstance(item, list):
                texts.extend([str(x) for x in item])
            else:
                texts.append(str(item))
    else:
        texts = [str(input_data)]
    
    # Generate deterministic embeddings for each text
    data = []
    for idx, text in enumerate(texts):
        vec = _deterministic_vector(text or 'empty')
        data.append({
            'object': 'embedding',
            'embedding': vec,
            'index': idx
        })
    
    response = {
        'object': 'list',
        'data': data,
        'model': body.get('model', 'text-embedding-mock'),
        'usage': {'prompt_tokens': len(texts), 'total_tokens': len(texts)}
    }
    return JSONResponse(response)
