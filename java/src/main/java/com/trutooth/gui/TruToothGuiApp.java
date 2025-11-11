package com.trutooth.gui;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

import javax.swing.BorderFactory;
import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSpinner;
import javax.swing.JSplitPane;
import javax.swing.JTable;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.ListSelectionModel;
import javax.swing.SpinnerNumberModel;
import javax.swing.SwingUtilities;
import javax.swing.SwingWorker;
import javax.swing.UIManager;
import javax.swing.WindowConstants;
import javax.swing.border.EmptyBorder;
import javax.swing.table.DefaultTableModel;

import com.fasterxml.jackson.databind.JsonNode;
import com.trutooth.gui.api.EventStream;
import com.trutooth.gui.api.MonitorConfig;
import com.trutooth.gui.api.TruToothApiClient;
import com.trutooth.gui.model.ScanResult;

/**
 * Minimal Swing front-end for the TruTooth backend. Provides scanning, monitor
 * control,
 * and live event streaming in a single window.
 */
public final class TruToothGuiApp extends JFrame {
    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter.ofPattern("HH:mm:ss");

    private final JTextField baseUrlField = new JTextField("http://127.0.0.1:8000", 28);
    private final JSpinner scanTimeoutSpinner = new JSpinner(new SpinnerNumberModel(6.0, 1.0, 120.0, 1.0));
    private final JButton scanButton = new JButton("Scan");
    private final DefaultTableModel devicesModel = new DefaultTableModel(new Object[] { "Address", "Name", "RSSI" },
            0) {
        @Override
        public boolean isCellEditable(int row, int column) {
            return false;
        }
    };
    private final JTable devicesTable = new JTable(devicesModel);

    private final JTextField deviceField = new JTextField();
    private final JTextField logField = new JTextField("metrics.csv");
    private final JTextField adapterField = new JTextField();
    private final JTextField mtuField = new JTextField();
    private final JTextField connectTimeoutField = new JTextField("10");
    private final JTextField pollIntervalField = new JTextField("5");
    private final JTextField baseBackoffField = new JTextField("2");
    private final JTextField maxBackoffField = new JTextField("60");
    private final JTextField runtimeField = new JTextField();
    private final JTextArea metadataArea = new JTextArea(3, 24);
    private final JLabel monitorStatusLabel = new JLabel("Idle");
    private final JButton startButton = new JButton("Start Monitor");
    private final JButton stopButton = new JButton("Stop Monitor");

    private final JTextArea eventsArea = new JTextArea();
    private final JButton clearEventsButton = new JButton("Clear");
    private final JLabel statusBar = new JLabel("Ready.");

    private TruToothApiClient apiClient;
    private String currentBaseUrl;
    private EventStream eventStream;

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception ignored) {
                // default look and feel works fine if system-specific fails.
            }
            TruToothGuiApp app = new TruToothGuiApp();
            app.setVisible(true);
        });
    }

    public TruToothGuiApp() {
        super("TruTooth Control Center");
        setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
        setMinimumSize(new Dimension(1080, 720));
        buildUi();
        attachListeners();
        pack();
        setLocationRelativeTo(null);
    }

    private void buildUi() {
        getContentPane().setLayout(new BorderLayout(0, 8));
        JPanel scanControls = buildScanControls();

        JSplitPane mainSplit = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, buildDevicesPanel(), buildMonitorPanel());
        mainSplit.setResizeWeight(0.45);

        JPanel top = new JPanel(new BorderLayout(0, 8));
        top.add(scanControls, BorderLayout.NORTH);
        top.add(mainSplit, BorderLayout.CENTER);

        JSplitPane verticalSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, top, buildEventsPanel());
        verticalSplit.setResizeWeight(0.6);

        getContentPane().add(verticalSplit, BorderLayout.CENTER);
        statusBar.setBorder(new EmptyBorder(4, 8, 4, 8));
        getContentPane().add(statusBar, BorderLayout.SOUTH);
    }

    private JPanel buildScanControls() {
        JPanel panel = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 8));
        panel.setBorder(new EmptyBorder(0, 8, 0, 8));
        panel.add(new JLabel("API Base URL"));
        baseUrlField.setPreferredSize(new Dimension(280, baseUrlField.getPreferredSize().height));
        panel.add(baseUrlField);
        panel.add(new JLabel("Scan Timeout (s)"));
        scanTimeoutSpinner.setPreferredSize(new Dimension(70, scanTimeoutSpinner.getPreferredSize().height));
        panel.add(scanTimeoutSpinner);
        panel.add(scanButton);
        return panel;
    }

    private JScrollPane buildDevicesPanel() {
        devicesTable.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        devicesTable.getTableHeader().setReorderingAllowed(false);
        devicesTable.setFillsViewportHeight(true);
        devicesTable.setRowHeight(22);
        JScrollPane scroll = new JScrollPane(devicesTable);
        scroll.setBorder(BorderFactory.createTitledBorder("Nearby Devices"));
        return scroll;
    }

    private JPanel buildMonitorPanel() {
        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(BorderFactory.createTitledBorder("Monitor Configuration"));
        metadataArea.setLineWrap(true);
        metadataArea.setWrapStyleWord(true);

        GridBagConstraints label = new GridBagConstraints();
        label.gridx = 0;
        label.anchor = GridBagConstraints.WEST;
        label.insets = new Insets(4, 8, 4, 8);

        GridBagConstraints field = new GridBagConstraints();
        field.gridx = 1;
        field.weightx = 1.0;
        field.fill = GridBagConstraints.HORIZONTAL;
        field.insets = new Insets(4, 0, 4, 8);

        int row = 0;
        row = addRow(panel, row, "Device Address *", deviceField, label, field);
        row = addRow(panel, row, "Metrics Log", logField, label, field);
        row = addRow(panel, row, "Adapter", adapterField, label, field);
        row = addRow(panel, row, "MTU", mtuField, label, field);
        row = addRow(panel, row, "Connect Timeout (s)", connectTimeoutField, label, field);
        row = addRow(panel, row, "Poll Interval (s)", pollIntervalField, label, field);
        row = addRow(panel, row, "Base Backoff (s)", baseBackoffField, label, field);
        row = addRow(panel, row, "Max Backoff (s)", maxBackoffField, label, field);
        row = addRow(panel, row, "Runtime Limit (s)", runtimeField, label, field);

        GridBagConstraints notesLabel = (GridBagConstraints) label.clone();
        notesLabel.gridy = row;
        panel.add(new JLabel("Metadata (JSON)"), notesLabel);

        GridBagConstraints notesField = (GridBagConstraints) field.clone();
        notesField.gridy = row;
        notesField.weighty = 1.0;
        notesField.fill = GridBagConstraints.BOTH;
        JScrollPane metadataScroll = new JScrollPane(metadataArea);
        metadataScroll.setPreferredSize(new Dimension(200, 90));
        panel.add(metadataScroll, notesField);
        row++;

        GridBagConstraints statusLabel = (GridBagConstraints) label.clone();
        statusLabel.gridy = row;
        panel.add(new JLabel("Monitor Status"), statusLabel);

        GridBagConstraints statusField = (GridBagConstraints) field.clone();
        statusField.gridy = row;
        monitorStatusLabel.setFont(monitorStatusLabel.getFont().deriveFont(Font.BOLD));
        panel.add(monitorStatusLabel, statusField);
        row++;

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 0));
        stopButton.setEnabled(false);
        buttons.add(startButton);
        buttons.add(stopButton);

        GridBagConstraints buttonRow = new GridBagConstraints();
        buttonRow.gridx = 0;
        buttonRow.gridy = row;
        buttonRow.gridwidth = 2;
        buttonRow.anchor = GridBagConstraints.WEST;
        buttonRow.insets = new Insets(8, 8, 12, 8);
        panel.add(buttons, buttonRow);
        return panel;
    }

    private JPanel buildEventsPanel() {
        JPanel panel = new JPanel(new BorderLayout(0, 4));
        panel.setBorder(new EmptyBorder(0, 8, 8, 8));
        JPanel header = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 0));
        header.add(new JLabel("Live Events"));
        header.add(clearEventsButton);
        panel.add(header, BorderLayout.NORTH);

        eventsArea.setEditable(false);
        eventsArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
        eventsArea.setLineWrap(false);
        JScrollPane scroll = new JScrollPane(eventsArea);
        scroll.setPreferredSize(new Dimension(200, 220));
        panel.add(scroll, BorderLayout.CENTER);
        return panel;
    }

    private void attachListeners() {
        scanButton.addActionListener(e -> triggerScan());
        startButton.addActionListener(e -> triggerStart());
        stopButton.addActionListener(e -> triggerStop());
        clearEventsButton.addActionListener(e -> eventsArea.setText(""));
        devicesTable.getSelectionModel().addListSelectionListener(event -> {
            if (!event.getValueIsAdjusting()) {
                int row = devicesTable.getSelectedRow();
                if (row >= 0) {
                    Object address = devicesModel.getValueAt(row, 0);
                    if (address != null) {
                        deviceField.setText(address.toString());
                    }
                }
            }
        });

        addWindowListener(new java.awt.event.WindowAdapter() {
            @Override
            public void windowClosing(java.awt.event.WindowEvent e) {
                closeEventStream();
            }
        });
    }

    private void triggerScan() {
        double timeout = ((Number) scanTimeoutSpinner.getValue()).doubleValue();
        TruToothApiClient client;
        try {
            client = ensureClient();
        } catch (IllegalArgumentException ex) {
            showError("Invalid Configuration", ex.getMessage());
            return;
        }

        scanButton.setEnabled(false);
        setStatus("Scanning for devices...");
        new SwingWorker<List<ScanResult>, Void>() {
            @Override
            protected List<ScanResult> doInBackground() throws Exception {
                return client.scanDevices(timeout);
            }

            @Override
            protected void done() {
                scanButton.setEnabled(true);
                try {
                    List<ScanResult> devices = get();
                    devicesModel.setRowCount(0);
                    for (ScanResult dev : devices) {
                        devicesModel.addRow(new Object[] { dev.address(), dev.name(), dev.rssi() });
                    }
                    setStatus("Scan complete: " + devices.size() + " device(s) found.");
                } catch (Exception ex) {
                    handleFailure("Scan failed", ex);
                }
            }
        }.execute();
    }

    private void triggerStart() {
        TruToothApiClient client;
        try {
            client = ensureClient();
        } catch (IllegalArgumentException ex) {
            showError("Invalid Configuration", ex.getMessage());
            return;
        }

        String deviceId = deviceField.getText().trim();
        if (deviceId.isEmpty()) {
            showError("Missing Device", "Enter a device address or select one from the scan list.");
            return;
        }

        MonitorConfig config;
        try {
            config = gatherMonitorConfig(deviceId);
        } catch (IllegalArgumentException ex) {
            showError("Invalid Monitor Settings", ex.getMessage());
            return;
        }

        startButton.setEnabled(false);
        setStatus("Starting monitor for " + deviceId + "...");
        new SwingWorker<JsonNode, Void>() {
            @Override
            protected JsonNode doInBackground() throws Exception {
                return client.startMonitor(config);
            }

            @Override
            protected void done() {
                try {
                    JsonNode node = get();
                    String status = node.path("status").asText("started");
                    monitorStatusLabel.setText(status);
                    stopButton.setEnabled(true);
                    setStatus("Monitor status: " + status + ".");
                    openEventStream(client);
                } catch (Exception ex) {
                    handleFailure("Monitor start failed", ex);
                    startButton.setEnabled(true);
                }
            }
        }.execute();
    }

    private void triggerStop() {
        TruToothApiClient client;
        try {
            client = ensureClient();
        } catch (IllegalArgumentException ex) {
            showError("Invalid Configuration", ex.getMessage());
            return;
        }

        stopButton.setEnabled(false);
        setStatus("Stopping monitor...");
        new SwingWorker<JsonNode, Void>() {
            @Override
            protected JsonNode doInBackground() throws Exception {
                return client.stopMonitor();
            }

            @Override
            protected void done() {
                try {
                    JsonNode node = get();
                    String status = node.path("status").asText("stopped");
                    monitorStatusLabel.setText(status);
                    setStatus("Monitor status: " + status + ".");
                    startButton.setEnabled(true);
                    stopButton.setEnabled(false);
                    closeEventStream();
                } catch (Exception ex) {
                    stopButton.setEnabled(true);
                    String message = safeMessage(ex);
                    setStatus("Monitor stop failed: " + message);
                    showError("Monitor stop failed", message);
                }
            }
        }.execute();
    }

    private void openEventStream(TruToothApiClient client) {
        closeEventStream();
        eventStream = client.openEventStream(
                node -> SwingUtilities.invokeLater(() -> appendEvent(node)),
                error -> SwingUtilities.invokeLater(() -> setStatus("Event stream error: " + safeMessage(error))),
                () -> SwingUtilities.invokeLater(() -> setStatus("Event stream connected.")),
                () -> SwingUtilities.invokeLater(() -> setStatus("Event stream closed.")));
    }

    private void appendEvent(JsonNode node) {
        String message;
        if (node.hasNonNull("csv")) {
            message = node.get("csv").asText();
        } else {
            message = node.toString();
        }
        String timestamp = TIME_FORMAT.format(LocalTime.now());
        eventsArea.append(timestamp + "  " + message + System.lineSeparator());
        eventsArea.setCaretPosition(eventsArea.getDocument().getLength());
    }

    private MonitorConfig gatherMonitorConfig(String deviceId) {
        return new MonitorConfig(
                deviceId,
                blankToNull(logField.getText()),
                blankToNull(adapterField.getText()),
                parseIntegerField(mtuField, "MTU"),
                parseDoubleField(connectTimeoutField, "Connect timeout"),
                parseDoubleField(pollIntervalField, "Poll interval"),
                parseDoubleField(baseBackoffField, "Base backoff"),
                parseDoubleField(maxBackoffField, "Max backoff"),
                parseDoubleField(runtimeField, "Runtime"),
                blankToNull(metadataArea.getText()));
    }

    private Integer parseIntegerField(JTextField field, String name) {
        String text = field.getText().trim();
        if (text.isEmpty()) {
            return null;
        }
        try {
            return Integer.valueOf(text);
        } catch (NumberFormatException ex) {
            throw new IllegalArgumentException(name + " must be an integer.");
        }
    }

    private Double parseDoubleField(JTextField field, String name) {
        String text = field.getText().trim();
        if (text.isEmpty()) {
            return null;
        }
        try {
            return Double.valueOf(text);
        } catch (NumberFormatException ex) {
            throw new IllegalArgumentException(name + " must be a number.");
        }
    }

    private String blankToNull(String text) {
        if (text == null) {
            return null;
        }
        String trimmed = text.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private TruToothApiClient ensureClient() {
        String base = baseUrlField.getText().trim();
        if (base.isEmpty()) {
            throw new IllegalArgumentException("API base URL is required.");
        }
        if (!base.contains("://")) {
            base = "http://" + base;
        }
        if (apiClient == null || !base.equals(currentBaseUrl)) {
            apiClient = new TruToothApiClient(base);
            currentBaseUrl = base;
            baseUrlField.setText(base);
        }
        return apiClient;
    }

    private void closeEventStream() {
        if (eventStream != null && !eventStream.isClosed()) {
            eventStream.close();
        }
        eventStream = null;
    }

    private void setStatus(String message) {
        statusBar.setText(message);
    }

    private void handleFailure(String context, Exception ex) {
        String message = safeMessage(ex);
        setStatus(context + ": " + message);
        showError(context, message);
    }

    private void showError(String title, String message) {
        JOptionPane.showMessageDialog(this, message, title, JOptionPane.ERROR_MESSAGE);
    }

    private String safeMessage(Throwable ex) {
        if (ex == null) {
            return "Unknown error";
        }
        String message = ex.getMessage();
        return (message == null || message.isBlank()) ? ex.getClass().getSimpleName() : message;
    }

    private int addRow(JPanel panel, int row, String labelText, JComponent fieldComponent,
            GridBagConstraints labelConstraints, GridBagConstraints fieldConstraints) {
        GridBagConstraints labelCopy = (GridBagConstraints) labelConstraints.clone();
        labelCopy.gridy = row;
        panel.add(new JLabel(labelText), labelCopy);

        GridBagConstraints fieldCopy = (GridBagConstraints) fieldConstraints.clone();
        fieldCopy.gridy = row;
        panel.add(fieldComponent, fieldCopy);
        return row + 1;
    }
}
