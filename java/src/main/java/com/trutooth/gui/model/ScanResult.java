package com.trutooth.gui.model;

/** Represents a single device returned by the TruTooth scan endpoint. */
public record ScanResult(String address, String name, Integer rssi) {
    public String displayName() {
        if (name != null && !name.isBlank()) {
            return name;
        }
        return address != null ? address : "<unknown>";
    }
}
