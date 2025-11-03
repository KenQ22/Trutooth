package trutoothSim;

// tiny holder for name + address
public class DeviceId {
    public final String name;
    public final String address;

    public DeviceId(String name, String address) {
        this.name = name;
        this.address = address;
    }

    public String shortStr() { return name + " (" + address + ")"; }
}
