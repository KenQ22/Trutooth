package com.trutooth.gui.api;

/** Immutable configuration for starting the monitor via the backend API. */
public record MonitorConfig(
        String device,
        String log,
        String adapter,
        Integer mtu,
        Double connectTimeout,
        Double pollInterval,
        Double baseBackoff,
        Double maxBackoff,
        Double runtime,
        String metadata) {
}
