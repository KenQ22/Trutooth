package trutoothSim;

import java.util.Random;

public class ScannerSim {
    private final Notice notice;
    private final Random rng = new Random();

    public ScannerSim(Notice notice) {
        this.notice = notice;
    }

    // returns a device sometimes; otherwise null
    public DeviceId find(String wantedName, String wantedAddr, int scanMs) throws InterruptedException {
        notice.info("Scanning for devices (" + scanMs + " ms)...");
        Thread.sleep(Math.min(scanMs, 1000)); // pretend work

        // 50% chance the speaker is "seen" on this scan
        boolean seen = rng.nextDouble() < 0.50;
        if (!seen) return null;

        String name = wantedName != null ? wantedName : "Speaker-" + hex2();
        String addr = wantedAddr != null ? wantedAddr : randomAddr();
        return new DeviceId(name, addr);
    }

    private String randomAddr() {
        return hex2()+":"+hex2()+":"+hex2()+":"+hex2()+":"+hex2()+":"+hex2();
    }
    private String hex2() { return String.format("%02X", rng.nextInt(256)); }
}
