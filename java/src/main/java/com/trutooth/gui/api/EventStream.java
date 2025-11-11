package com.trutooth.gui.api;

import java.util.concurrent.atomic.AtomicBoolean;

import okhttp3.WebSocket;

/**
 * Lightweight wrapper around the backend event websocket so callers can close
 * it cleanly.
 */
public final class EventStream implements AutoCloseable {
    private final WebSocket socket;
    private final AtomicBoolean closed = new AtomicBoolean(false);

    EventStream(WebSocket socket) {
        this.socket = socket;
    }

    public boolean isClosed() {
        return closed.get();
    }

    @Override
    public void close() {
        if (closed.compareAndSet(false, true)) {
            socket.close(1000, "client closing");
        }
    }
}
