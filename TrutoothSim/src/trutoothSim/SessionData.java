package trutoothSim;

public class SessionData {
    public final DeviceId device;
    public long startMs = -1;
    public long endMs   = -1;

    public int drops = 0;
    public int reconnectAttempts = 0;
    public int successfulReconnects = 0;

    public SessionData(DeviceId d) { this.device = d; }

    public void start() { startMs = System.currentTimeMillis(); }
    public void end()   { endMs = System.currentTimeMillis(); }

    private long elapsedMs() {
        long stop = (endMs >= 0 ? endMs : System.currentTimeMillis());
        return (startMs >= 0 ? stop - startMs : 0);
    }

    public String summary() {
        long sec = elapsedMs() / 1000;
        return "=== Session Summary ===\n"
             + "Device: " + device.shortStr() + "\n"
             + "Time: " + sec + " s\n"
             + "Drops: " + drops + "\n"
             + "Reconnect attempts: " + reconnectAttempts + "\n"
             + "Successful reconnects: " + successfulReconnects + "\n";
    }
}
