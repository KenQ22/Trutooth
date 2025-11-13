import React from "react";
import { Device } from "../types";
import { CompassIcon } from "../icons";

interface DevicesTableProps {
  devices: Device[];
  selectedAddress: string;
  onSelect(address: string): void;
}

export function DevicesTable({ devices, selectedAddress, onSelect }: DevicesTableProps) {
  return (
    <div className="panel">
      <h2>
        <CompassIcon width={20} height={20} /> Nearby Devices
      </h2>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: "36%" }}>Address</th>
              <th style={{ width: "36%" }}>Name</th>
              <th style={{ width: "14%" }}>RSSI</th>
              <th style={{ width: "14%" }}>Connectable</th>
            </tr>
          </thead>
          <tbody>
            {devices.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", padding: "24px" }}>
                  Run a scan to populate device results.
                </td>
              </tr>
            ) : (
              devices.map((device) => {
                const address = device.address ?? "";
                const isSelected = selectedAddress === address;
                return (
                  <tr
                    key={address || device.id || Math.random()}
                    className={isSelected ? "selected" : undefined}
                    onClick={() => onSelect(address)}
                  >
                    <td>{address || "—"}</td>
                    <td>{device.name || "Unknown"}</td>
                    <td>{typeof device.rssi === "number" ? device.rssi : "—"}</td>
                    <td>{device.connectable === false ? "No" : "Yes"}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
