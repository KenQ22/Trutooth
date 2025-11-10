package trutoothSim;

import java.util.Random;

public class ConnectionSim {
    private final Notice notice;
    private final Random rng = new Random();
    private boolean connected = false;
    private long dropAt = -1L;

    public ConnectionSim(Notice notice) {
        this.notice = notice;
    }

    public boolean connect(DeviceId d) {
        // simple 85% success rate + small delay
        try { Thread.sleep(200 + rng.nextInt(300)); } catch (InterruptedException ignore) {}
        boolean ok = rng.nextDouble() < 0.85;
        if (ok) {
            connected = true;
            scheduleDrop(); // plan a random future drop
            System.out.println("Connected to " + d.shortStr());
        }
        return ok;
    }

    public boolean isDisconnected() {
        if (connected && dropAt > 0 && System.currentTimeMillis() >= dropAt) {
            connected = false;
            dropAt = -1L;
            notice.warn("Link drop happened.");
            return true;
        }
        return !connected;
    }

    private void scheduleDrop() {
        long now = System.currentTimeMillis();
        // will drop 5–12 seconds from now
        long delay = 5_000 + rng.nextInt(8_000);
        dropAt = now + delay;
    }
}
