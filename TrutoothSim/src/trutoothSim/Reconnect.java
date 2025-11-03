package trutoothSim;

public class Reconnect {
    // 1s, 3s, 5s, then stick at 10s
    private int fails = 0;

    public long nextDelayMs() {
        int[] steps = {1000, 3000, 5000};
        if (fails < steps.length) return steps[fails];
        return 10_000L;
    }

    public void onFailure() { fails++; }
    public void onSuccess() { fails = 0; }
}
