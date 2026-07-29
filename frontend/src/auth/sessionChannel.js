const CHANNEL_NAME = "fieldflow-auth";
const STORAGE_KEY = "fieldflow.auth-event";


export function createSessionChannel(onEvent) {
  let channel = null;

  const handleStorage = (event) => {
    if (event.key !== STORAGE_KEY || !event.newValue) return;
    try {
      onEvent(JSON.parse(event.newValue));
    } catch {
      // Ignore malformed events from unrelated scripts.
    }
  };

  if (typeof BroadcastChannel !== "undefined") {
    channel = new BroadcastChannel(CHANNEL_NAME);
    channel.addEventListener("message", (event) => onEvent(event.data));
  } else {
    window.addEventListener("storage", handleStorage);
  }

  return {
    broadcast(type) {
      const event = {
        type,
        nonce: globalThis.crypto?.randomUUID?.() || String(Date.now()),
        timestamp: Date.now(),
      };
      if (channel) {
        channel.postMessage(event);
      } else {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(event));
        localStorage.removeItem(STORAGE_KEY);
      }
    },
    close() {
      channel?.close();
      window.removeEventListener("storage", handleStorage);
    },
  };
}
