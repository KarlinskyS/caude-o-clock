import AppKit
import Foundation

struct UsageSnapshot {
    let fiveHour: Double
    let weekly: Double
    let fiveHourReset: Date?
    let weeklyReset: Date?
    let plan: String
}

enum UsageError: LocalizedError {
    case message(String)

    var errorDescription: String? {
        switch self {
        case .message(let text): return text
        }
    }
}

enum UsageLoader {
    static func fetch() async throws -> UsageSnapshot {
        let credentials = try readCredentials()
        guard let token = credentials["accessToken"] as? String else {
            throw UsageError.message("Claude Code credentials do not contain an access token.")
        }

        var request = URLRequest(url: URL(string: "https://api.anthropic.com/api/oauth/usage")!)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("oauth-2025-04-20", forHTTPHeaderField: "anthropic-beta")
        request.timeoutInterval = 10

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw UsageError.message("Claude usage API returned \((response as? HTTPURLResponse)?.statusCode ?? 0): \(body)")
        }
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw UsageError.message("Claude usage API returned an unexpected response.")
        }

        let five = root["five_hour"] as? [String: Any] ?? [:]
        let week = root["seven_day"] as? [String: Any] ?? [:]
        let plan = (credentials["subscriptionType"] as? String ?? "Claude Code").capitalized
        return UsageSnapshot(
            fiveHour: five["utilization"] as? Double ?? 0,
            weekly: week["utilization"] as? Double ?? 0,
            fiveHourReset: parseDate(five["resets_at"] as? String),
            weeklyReset: parseDate(week["resets_at"] as? String),
            plan: plan
        )
    }

    private static func readCredentials() throws -> [String: Any] {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/security")
        process.arguments = ["find-generic-password", "-s", "Claude Code-credentials", "-w"]
        let output = Pipe()
        process.standardOutput = output
        process.standardError = Pipe()
        try process.run()
        process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            throw UsageError.message("Not signed in. Run `claude login` in Terminal first.")
        }
        let data = output.fileHandleForReading.readDataToEndOfFile()
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let credentials = root["claudeAiOauth"] as? [String: Any] else {
            throw UsageError.message("Claude Code credentials have an unexpected format.")
        }
        return credentials
    }

    private static func parseDate(_ value: String?) -> Date? {
        guard let value else { return nil }
        return ISO8601DateFormatter().date(from: value)
    }
}

final class UsageViewController: NSViewController {
    private let titleLabel = label("Caude o'clock", size: 15, weight: .semibold)
    private let planLabel = label("", size: 11, color: .secondaryLabelColor)
    private let fiveLabel = label("5-Hour Window", size: 13, weight: .medium)
    private let fiveValue = label("—", size: 18, weight: .bold)
    private let fiveReset = label("Loading…", size: 11, color: .secondaryLabelColor)
    private let fiveBar = progressBar()
    private let weeklyLabel = label("Weekly", size: 13, weight: .medium)
    private let weeklyValue = label("—", size: 18, weight: .bold)
    private let weeklyReset = label("", size: 11, color: .secondaryLabelColor)
    private let weeklyBar = progressBar()
    private let errorLabel = label("", size: 11, color: .systemRed)
    var onRefresh: (() -> Void)?
    var onOpenClaude: (() -> Void)?
    var onQuit: (() -> Void)?

    override func loadView() {
        let root = NSView(frame: NSRect(x: 0, y: 0, width: 320, height: 1))
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 7
        stack.translatesAutoresizingMaskIntoConstraints = false
        root.addSubview(stack)

        let header = NSStackView(views: [titleLabel, spacer(), planLabel])
        header.orientation = .horizontal
        header.alignment = .centerY
        header.spacing = 8
        stack.addArrangedSubview(header)
        stack.addArrangedSubview(divider())
        stack.addArrangedSubview(section(label: fiveLabel, value: fiveValue, bar: fiveBar, reset: fiveReset))
        stack.addArrangedSubview(divider())
        stack.addArrangedSubview(section(label: weeklyLabel, value: weeklyValue, bar: weeklyBar, reset: weeklyReset))
        stack.addArrangedSubview(divider())
        errorLabel.maximumNumberOfLines = 3
        errorLabel.isHidden = true
        stack.addArrangedSubview(errorLabel)

        let refresh = textButton("⟳ Refresh", action: #selector(refreshPressed))
        let open = textButton("Open claude.ai ↗", action: #selector(openPressed))
        let quit = textButton("Quit", action: #selector(quitPressed))
        let footer = NSStackView(views: [refresh, spacer(), open, quit])
        footer.orientation = .horizontal
        footer.alignment = .centerY
        footer.spacing = 12
        stack.addArrangedSubview(footer)

        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: root.leadingAnchor, constant: 18),
            stack.trailingAnchor.constraint(equalTo: root.trailingAnchor, constant: -18),
            stack.topAnchor.constraint(equalTo: root.topAnchor, constant: 16),
            stack.bottomAnchor.constraint(equalTo: root.bottomAnchor, constant: -16),
            fiveBar.widthAnchor.constraint(equalToConstant: 284),
            weeklyBar.widthAnchor.constraint(equalToConstant: 284),
        ])
        self.view = root
    }

    func render(_ usage: UsageSnapshot) {
        errorLabel.isHidden = true
        planLabel.stringValue = usage.plan
        fiveValue.stringValue = "\(Int(usage.fiveHour.rounded()))%"
        weeklyValue.stringValue = "\(Int(usage.weekly.rounded()))%"
        fiveBar.doubleValue = usage.fiveHour
        weeklyBar.doubleValue = usage.weekly
        fiveReset.stringValue = resetText(usage.fiveHourReset, prefix: "Resets")
        weeklyReset.stringValue = resetText(usage.weeklyReset, prefix: "Resets")
    }

    func showError(_ error: Error) {
        errorLabel.stringValue = error.localizedDescription
        errorLabel.isHidden = false
    }

    @objc private func refreshPressed() { onRefresh?() }
    @objc private func openPressed() { onOpenClaude?() }
    @objc private func quitPressed() { onQuit?() }

    private func section(label: NSTextField, value: NSTextField, bar: NSProgressIndicator, reset: NSTextField) -> NSStackView {
        let top = NSStackView(views: [label, spacer(), value])
        top.orientation = .horizontal
        top.alignment = .centerY
        let section = NSStackView(views: [top, bar, reset])
        section.orientation = .vertical
        section.alignment = .leading
        section.spacing = 5
        return section
    }

    private func resetText(_ date: Date?, prefix: String) -> String {
        guard let date else { return "\(prefix) —" }
        let remaining = max(0, Int(date.timeIntervalSinceNow / 60))
        let hours = remaining / 60
        let minutes = remaining % 60
        return hours > 0 ? "\(prefix) in \(hours)h \(minutes)m" : "\(prefix) in \(minutes)m"
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let popover = NSPopover()
    private let controller = UsageViewController()
    private var statusItem: NSStatusItem!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        // Visibility can be restored from a prior menu-bar layout.  Give this
        // item a stable identity and explicitly restore it on every launch so
        // an older removed/hidden entry cannot keep the app invisible.
        statusItem.autosaveName = "com.karlinskys.caude-oc.status-item"
        statusItem.isVisible = true
        guard let button = statusItem.button else { return }
        // A template image stays legible in both macOS light and dark menu
        // bars.  It is intentionally supplied in addition to the percentage:
        // macOS may compact textual menu extras when space is constrained.
        let image = NSImage(systemSymbolName: "clock", accessibilityDescription: "Caude o'clock")
        image?.isTemplate = true
        button.image = image
        button.imagePosition = .imageLeft
        button.title = " …"
        button.target = self
        button.action = #selector(togglePopover(_:))
        button.font = .monospacedDigitSystemFont(ofSize: 13, weight: .semibold)

        popover.behavior = .transient
        popover.contentViewController = controller
        controller.onRefresh = { [weak self] in self?.refresh() }
        controller.onOpenClaude = { NSWorkspace.shared.open(URL(string: "https://claude.ai/settings/usage")!) }
        controller.onQuit = { NSApp.terminate(nil) }
        refresh()
    }

    @objc private func togglePopover(_ sender: Any?) {
        guard let button = statusItem.button else { return }
        if popover.isShown { popover.performClose(sender) }
        else { popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY) }
    }

    private func refresh() {
        statusItem.button?.title = " …"
        Task {
            do {
                let usage = try await UsageLoader.fetch()
                await MainActor.run { [weak self] in
                    self?.controller.render(usage)
                    self?.statusItem.button?.title = " \(Int(usage.fiveHour.rounded()))%"
                }
            } catch {
                await MainActor.run { [weak self] in
                    self?.controller.showError(error)
                    self?.statusItem.button?.title = " !"
                }
            }
        }
    }
}

private func label(_ text: String, size: CGFloat, weight: NSFont.Weight = .regular, color: NSColor? = nil) -> NSTextField {
    let field = NSTextField(labelWithString: text)
    field.font = NSFont.systemFont(ofSize: size, weight: weight)
    field.textColor = color ?? .labelColor
    return field
}

private func progressBar() -> NSProgressIndicator {
    let bar = NSProgressIndicator()
    bar.isIndeterminate = false
    bar.minValue = 0
    bar.maxValue = 100
    bar.controlSize = .small
    bar.style = .bar
    return bar
}

private func divider() -> NSBox {
    let line = NSBox()
    line.boxType = .separator
    return line
}

private func spacer() -> NSView {
    let view = NSView()
    view.setContentHuggingPriority(.defaultLow, for: .horizontal)
    view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
    return view
}

private func textButton(_ title: String, action: Selector) -> NSButton {
    let button = NSButton(title: title, target: nil, action: action)
    button.isBordered = false
    button.font = .systemFont(ofSize: 11)
    return button
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.finishLaunching()
app.run()
