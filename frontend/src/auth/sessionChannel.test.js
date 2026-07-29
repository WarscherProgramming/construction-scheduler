import { afterEach, describe, expect, it, vi } from "vitest";

import { createSessionChannel } from "./sessionChannel";


class FakeBroadcastChannel {
  static instances = [];

  constructor(name) {
    this.name = name;
    this.listener = null;
    this.messages = [];
    this.closed = false;
    FakeBroadcastChannel.instances.push(this);
  }

  addEventListener(_type, listener) {
    this.listener = listener;
  }

  postMessage(message) {
    this.messages.push(message);
  }

  emit(data) {
    this.listener?.({ data });
  }

  close() {
    this.closed = true;
  }
}


describe("sessionChannel", () => {
  afterEach(() => {
    FakeBroadcastChannel.instances = [];
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("broadcasts only a non-sensitive session marker", () => {
    vi.stubGlobal("BroadcastChannel", FakeBroadcastChannel);
    const channel = createSessionChannel(vi.fn());

    channel.broadcast("logout");

    const message = FakeBroadcastChannel.instances[0].messages[0];
    expect(message.type).toBe("logout");
    expect(message.nonce).toBeTruthy();
    expect(message.timestamp).toEqual(expect.any(Number));
    expect(JSON.stringify(message)).not.toMatch(/token|password|authorization/i);
  });

  it("delivers remote events and closes the channel listener", () => {
    vi.stubGlobal("BroadcastChannel", FakeBroadcastChannel);
    const onEvent = vi.fn();
    const channel = createSessionChannel(onEvent);
    const transport = FakeBroadcastChannel.instances[0];

    transport.emit({ type: "session_expired" });
    channel.close();

    expect(onEvent).toHaveBeenCalledWith({ type: "session_expired" });
    expect(transport.closed).toBe(true);
  });

  it("uses storage events when BroadcastChannel is unavailable", () => {
    vi.stubGlobal("BroadcastChannel", undefined);
    const onEvent = vi.fn();
    const channel = createSessionChannel(onEvent);

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "fieldflow.auth-event",
        newValue: JSON.stringify({ type: "logout" }),
      })
    );
    channel.close();

    expect(onEvent).toHaveBeenCalledWith({ type: "logout" });
  });
});
