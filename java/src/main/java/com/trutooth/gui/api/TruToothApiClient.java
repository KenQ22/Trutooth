package com.trutooth.gui.api;

import java.io.IOException;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.trutooth.gui.model.ScanResult;

import okhttp3.HttpUrl;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

/** Client wrapper around the TruTooth backend HTTP and websocket APIs. */
public final class TruToothApiClient {
    private static final TypeReference<List<ScanResult>> SCAN_LIST_TYPE = new TypeReference<>() {
    };

    private final OkHttpClient http;
    private final ObjectMapper mapper = new ObjectMapper();
    private final HttpUrl baseHttp;
    private final String baseWsUrl;

    public TruToothApiClient(String baseUrl) {
        Objects.requireNonNull(baseUrl, "baseUrl");
        HttpUrl parsed = HttpUrl.parse(baseUrl);
        if (parsed == null) {
            throw new IllegalArgumentException("Invalid base URL: " + baseUrl);
        }
        String path = parsed.encodedPath();
        if (!path.endsWith("/")) {
            parsed = parsed.newBuilder().encodedPath(path + "/").build();
        }
        this.baseHttp = parsed;

        // Build WebSocket URL as string since HttpUrl doesn't support ws:// scheme
        String scheme = parsed.scheme();
        String wsScheme;
        if ("http".equalsIgnoreCase(scheme)) {
            wsScheme = "ws";
        } else if ("https".equalsIgnoreCase(scheme)) {
            wsScheme = "wss";
        } else {
            throw new IllegalArgumentException("Unsupported URL scheme: " + scheme);
        }
        this.baseWsUrl = wsScheme + "://" + parsed.host() + ":" + parsed.port() + parsed.encodedPath();

    this.http = new OkHttpClient.Builder()
        // Allow long-running scans to complete; backend holds the
        // connection open for the duration of the scan.
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        // Avoid an overall call timeout so readTimeout governs the
        // long-polling behavior for scans.
        .callTimeout(0, TimeUnit.SECONDS)
        .build();
    }

    public List<ScanResult> scanDevices(double timeoutSeconds) throws IOException {
        HttpUrl url = baseHttp.newBuilder()
                .addPathSegment("scan")
                .addQueryParameter("timeout", String.valueOf(timeoutSeconds))
                .build();
        Request req = new Request.Builder().url(url).get().build();
        try (Response res = http.newCall(req).execute()) {
            if (!res.isSuccessful()) {
                throw new IOException("Scan failed: " + res.code() + " " + res.message());
            }
            String json = Objects.requireNonNull(res.body(), "empty response body").string();
            return mapper.readValue(json, SCAN_LIST_TYPE);
        }
    }

    public JsonNode startMonitor(MonitorConfig config) throws IOException {
        Objects.requireNonNull(config, "config");
        if (config.device() == null || config.device().isBlank()) {
            throw new IllegalArgumentException("Device identifier is required");
        }
        HttpUrl.Builder url = baseHttp.newBuilder()
                .addPathSegment("monitor")
                .addPathSegment("start")
                .addQueryParameter("device", config.device());
        if (config.log() != null && !config.log().isBlank()) {
            url.addQueryParameter("log", config.log());
        }
        addOptional(url, "adapter", config.adapter());
        addOptionalNumber(url, "mtu", config.mtu());
        addOptionalNumber(url, "connect_timeout", config.connectTimeout());
        addOptionalNumber(url, "poll_interval", config.pollInterval());
        addOptionalNumber(url, "base_backoff", config.baseBackoff());
        addOptionalNumber(url, "max_backoff", config.maxBackoff());
        addOptionalNumber(url, "runtime", config.runtime());
        addOptional(url, "metadata", config.metadata());

        Request req = new Request.Builder()
                .url(url.build())
                .post(RequestBody.create(new byte[0]))
                .build();
        try (Response res = http.newCall(req).execute()) {
            if (!res.isSuccessful()) {
                throw new IOException("Monitor start failed: " + res.code() + " " + res.message());
            }
            String json = Objects.requireNonNull(res.body(), "empty response body").string();
            return mapper.readTree(json);
        }
    }

    public JsonNode stopMonitor() throws IOException {
        HttpUrl url = baseHttp.newBuilder()
                .addPathSegment("monitor")
                .addPathSegment("stop")
                .build();
        Request req = new Request.Builder()
                .url(url)
                .post(RequestBody.create(new byte[0]))
                .build();
        try (Response res = http.newCall(req).execute()) {
            if (!res.isSuccessful()) {
                throw new IOException("Monitor stop failed: " + res.code() + " " + res.message());
            }
            String json = Objects.requireNonNull(res.body(), "empty response body").string();
            return mapper.readTree(json);
        }
    }

    public EventStream openEventStream(
            Consumer<JsonNode> onEvent,
            Consumer<Throwable> onError,
            Runnable onOpen,
            Runnable onClose) {
        Objects.requireNonNull(onEvent, "onEvent");
        String wsUrl = baseWsUrl + "events";
        Request req = new Request.Builder().url(wsUrl).build();
        WebSocketListener listener = new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                if (onOpen != null) {
                    onOpen.run();
                }
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                try {
                    JsonNode node = mapper.readTree(text);
                    onEvent.accept(node);
                } catch (IOException ex) {
                    if (onError != null) {
                        onError.accept(ex);
                    }
                }
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                if (onError != null) {
                    onError.accept(t);
                }
                if (onClose != null) {
                    onClose.run();
                }
            }

            @Override
            public void onClosed(WebSocket webSocket, int code, String reason) {
                if (onClose != null) {
                    onClose.run();
                }
            }

            @Override
            public void onClosing(WebSocket webSocket, int code, String reason) {
                webSocket.close(code, reason);
            }
        };
        WebSocket socket = http.newWebSocket(req, listener);
        return new EventStream(socket);
    }

    private static void addOptional(HttpUrl.Builder builder, String key, String value) {
        if (value != null && !value.isBlank()) {
            builder.addQueryParameter(key, value);
        }
    }

    private static void addOptionalNumber(HttpUrl.Builder builder, String key, Number value) {
        if (value != null) {
            builder.addQueryParameter(key, value.toString());
        }
    }
}
