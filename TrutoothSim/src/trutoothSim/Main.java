package trutoothSim;

public class Main {
    public static void main(String[] args) throws Exception {
        System.out.println("trutoothSim starting...");

        // what we are "looking" for
        String targetName = "MySpeaker";
        String targetAddr = null; // or set like "AA:BB:CC:DD:EE:FF"

        Notice notice = new Notice();
        ScannerSim scanner = new ScannerSim(notice);
        ConnectionSim conn = new ConnectionSim(notice);
        Reconnect backoff = new Reconnect();
        SessionData session = null;

        // 1) Find the device (simulated)
        DeviceId found;
        while (true) {
            found = scanner.find(targetName, targetAddr, 3000);
            if (found != null) {
                System.out.println("Device found: " + found.name + " (" + found.address + ")");
                break;
            } else {
                System.out.println("Device not found. Retrying in 5 seconds...");
                Thread.sleep(5000);
            }
        }

        // 2) Start session + connect
        session = new SessionData(found);
        session.start();

        if (!conn.connect(found)) {
            System.out.println("Initial connect failed. Ending.");
            session.end();
            System.out.println(session.summary());
            return;
        }

        System.out.println("Connected. Watching for drops...");

        // 3) Simple monitor loop (~45 seconds demo)
        long stopTime = System.currentTimeMillis() + 45_000;
        while (System.currentTimeMillis() < stopTime) {
            Thread.sleep(500);

            if (conn.isDisconnected()) {
                session.drops++;
                notice.info("Disconnected from " + found.shortStr());

                backoff.onFailure();
                session.reconnectAttempts++;

                long wait = backoff.nextDelayMs();
                System.out.println("Retrying in " + wait + " ms...");
                Thread.sleep(wait);

                if (conn.connect(found)) {
                    backoff.onSuccess();
                    session.successfulReconnects++;
                    notice.info("Reconnected to " + found.shortStr());
                } else {
                    System.out.println("Reconnect failed.");
                }
            }
        }

        session.end();
        System.out.println();
        System.out.println(session.summary());
        System.out.println("SpeakerSim done.");
    }
}
