/**
 * Async generator to parse NDJSON events from a ReadableStream
 * @param {ReadableStream} stream
 * @returns {AsyncGenerator<object>}
 */
export async function* streamChatEvents(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      let lines = buffer.split('\n');
      buffer = lines.pop() || ''; // last line may be incomplete

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event.type === 'done') {
            return; // End of stream
          }
          yield event;
        } catch (e) {
          console.warn('[streamChatEvents] Failed to parse line:', line, e);
        }
      }
    }

    // Process any remaining buffer
    if (buffer.trim()) {
      try {
        yield JSON.parse(buffer);
      } catch (e) {
        console.warn('[streamChatEvents] Failed to parse final buffer:', buffer, e);
      }
    }
  } finally {
    reader.releaseLock();
  }
}
