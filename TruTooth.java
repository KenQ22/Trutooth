package TruTooth;

import javax.bluetooth.*;
import javax.microedition.io.*;
import java.io.*;

public class TruTooth {
	    private static final String TARGET_DEVICE_NAME = "MyBluetoothDevice"; 
	    private static final int RECONNECT_DELAY_MS = 5000; //The 5000ms = 5 secs

	public static void main(String[] args) {
		// TODO Auto-generated method stub
		private static final String TARGET_DEVICE_NAME = "MyBluetoothDevice";
		private static final String int RECONNECT_DELAY_MS = 5000; // 5000ms = 5secs
		
		public static void main(String[] args) {
			while (true) {
				try {
					RemoteDevice device = findDeviceByName(TARGET_DEVICE_NAME);
					if (device != null) {
						System.out.println("Device foumd: " + device.getBluetoothAddress());
					}else {
						System.out.println("Device not found. Retrying in 5 seconds.");
						Thread.sleep(RECONNECT_DELAY_MS);
					}
					} catch (Exception e) {
						System.err.println("Error: " + e.getMessage());
						try {
							Thread.sleep(RECONNECT_DELAY_MS);
						}
				} catch (Exception e) {
					System.err.println("Error: " + e.getmessage());
					Thread.sleep(RECONNECT_DELAY_MS);
					}
					} catch (InterruptedException ignored) {}
			}
		
		}
	}

