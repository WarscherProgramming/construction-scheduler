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
    try {
      channel = new BroadcastChannel(CHANNEL_NAME);
      channel.addEventListener("message", (event) => onEvent(event.data));
    } catch {
      channel = null;
    }
  }
  if (!channel) {
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
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(event));
          localStorage.removeItem(STORAGE_KEY);
        } catch {
          // Local state changes still complete when browser storage is blocked.
        }
      }
    },
    close() {
      channel?.close();
      window.removeEventListener("storage", handleStorage);
    },
  };
}
