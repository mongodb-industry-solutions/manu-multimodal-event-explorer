import { NextResponse } from 'next/server';

/**
 * POST /api/chat/stream - Proxy streaming chat requests to FastAPI backend
 * 
 * This Next.js API route acts as a proxy between the browser and the FastAPI backend,
 * converting SSE (Server-Sent Events) to NDJSON streaming which works better with proxies.
 * 
 * Flow:
 * 1. Browser sends messages via fetch() to /api/chat/stream
 * 2. This route forwards to FastAPI backend at http://localhost:8000/api/chat/stream
 * 3. FastAPI returns SSE events
 * 4. We parse SSE and convert to NDJSON
 * 5. Browser consumes NDJSON stream with response.body.getReader()
 */
export async function POST(request) {
  try {
    const body = await request.json();
    const { messages } = body;

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: 'Invalid request: messages array required' },
        { status: 400 }
      );
    }

    // Forward to FastAPI backend (using 127.0.0.1 to avoid IPv6 issues)
    const backendUrl = 'http://127.0.0.1:8000/api/chat/stream';
    
    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages }),
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      return NextResponse.json(
        { error: `Backend error: ${errorText}` },
        { status: backendResponse.status }
      );
    }

    // Create a ReadableStream that converts SSE to NDJSON
    const stream = new ReadableStream({
      async start(controller) {
        const reader = backendResponse.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
              // SSE format: "data: {json}\n"
              if (line.startsWith('data: ')) {
                const data = line.slice(6).trim();
                if (data === '[DONE]') {
                  // End of stream marker
                  controller.enqueue(
                    new TextEncoder().encode(
                      JSON.stringify({ type: 'done' }) + '\n'
                    )
                  );
                  break;
                }
                // Forward the JSON event as NDJSON
                controller.enqueue(new TextEncoder().encode(data + '\n'));
              }
            }
          }
        } catch (error) {
          console.error('[API Route] Stream error:', error);
          controller.enqueue(
            new TextEncoder().encode(
              JSON.stringify({ type: 'error', message: error.message }) + '\n'
            )
          );
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'application/x-ndjson',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('[API Route] Error:', error);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}
