import okhttp3.*;
import java.util.concurrent.TimeUnit;
import okhttp3.ws.WebSocketCall; // placeholder if needed

public class TruTooth {
    static final OkHttpClient http = new OkHttpClient.Builder()
            .callTimeout(10, TimeUnit.SECONDS)
            .build();

    public static void main(String[] args) throws Exception {
        Request scanReq = new Request.Builder().url("http://127.0.0.1:8000/scan?timeout=6").build();
        try (Response res = http.newCall(scanReq).execute()) {
            System.out.println("SCAN -> " + res.code());
            System.out.println(res.body().string());
        }

        // Start monitor (placeholder MAC)
        HttpUrl startUrl = HttpUrl.parse("http://127.0.0.1:8000/monitor/start").newBuilder()
                .addQueryParameter("device", "AA:BB:CC:DD:EE:FF")
                .addQueryParameter("log", "metrics.csv").build();
        try (Response res = http.newCall(new Request.Builder().url(startUrl)
                .post(RequestBody.create(new byte[0])).build()).execute()) {
            System.out.println("START -> " + res.code());
            System.out.println(res.body().string());
        }

        Request wsReq = new Request.Builder().url("ws://127.0.0.1:8000/events").build();
        http.newWebSocket(wsReq, new WebSocketListener() {
            @Override public void onOpen(WebSocket ws, Response resp) { System.out.println("WS OPEN"); }
            @Override public void onMessage(WebSocket ws, String text) { System.out.println("EVT: " + text); }
            @Override public void onFailure(WebSocket ws, Throwable t, Response r) { t.printStackTrace(); }
        });

        Thread.sleep(10000);

        HttpUrl stopUrl = HttpUrl.parse("http://127.0.0.1:8000/monitor/stop").newBuilder().build();
        try (Response res = http.newCall(new Request.Builder().url(stopUrl)
                .post(RequestBody.create(new byte[0])).build()).execute()) {
            System.out.println("STOP -> " + res.code());
            System.out.println(res.body().string());
        }
    }
}
