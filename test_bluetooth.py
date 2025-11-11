"""Quick diagnostic script to test Bluetooth scanning capability."""
import asyncio
import sys

async def test_scan():
    try:
        from bleak import BleakScanner
        print("✓ Bleak imported successfully")
        
        print("\nScanning for 10 seconds...")
        devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
        
        if not devices:
            print("\n⚠ No devices found!")
            print("\nPossible reasons:")
            print("1. Bluetooth is disabled on this computer")
            print("2. No Bluetooth devices are nearby or discoverable")
            print("3. Windows Bluetooth permissions not granted")
            print("4. Bluetooth adapter not working properly")
            print("\nTo fix:")
            print("- Enable Bluetooth in Windows Settings")
            print("- Make sure your Bluetooth devices are in pairing/discoverable mode")
            print("- Check Device Manager for Bluetooth adapter status")
            return
        
        print(f"\n✓ Found {len(devices)} device(s):")
        for device, adv_data in devices.values():
            print(f"  • {device.name or 'Unknown'} ({device.address}) - RSSI: {adv_data.rssi}")
            
    except ImportError as e:
        print(f"✗ Failed to import bleak: {e}")
        print("Run: pip install bleak")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Scan failed: {e}")
        print(f"\nError type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_scan())
