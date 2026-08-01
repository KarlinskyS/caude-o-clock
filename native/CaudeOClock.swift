import AppKit
import Foundation
import SwiftUI

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
            throw UsageError.message("Claude usage API returned \((response as? HTTPURLResponse)?.statusCode ?? 0).")
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

@MainActor
final class UsageModel: ObservableObject {
    @Published private(set) var usage: UsageSnapshot?
    @Published private(set) var errorMessage: String?
    @Published private(set) var isLoading = false

    init() {
        refresh()
    }

    var statusTitle: String {
        if let usage { return "\(Int(usage.fiveHour.rounded()))%" }
        return errorMessage == nil ? "…" : "!"
    }

    func refresh() {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil
        Task {
            do {
                usage = try await UsageLoader.fetch()
            } catch {
                errorMessage = error.localizedDescription
            }
            isLoading = false
        }
    }
}

struct UsagePopover: View {
    @ObservedObject var model: UsageModel

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("Caude o'clock")
                    .font(.headline)
                Spacer()
                Text(model.usage?.plan ?? "Claude Code")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Divider()

            if let usage = model.usage {
                UsageSection(
                    title: "5-Hour Window",
                    value: usage.fiveHour,
                    reset: resetText(usage.fiveHourReset)
                )
                Divider()
                UsageSection(
                    title: "Weekly",
                    value: usage.weekly,
                    reset: resetText(usage.weeklyReset)
                )
            } else if model.isLoading {
                HStack(spacing: 8) {
                    ProgressView()
                    Text("Loading Claude usage…")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, minHeight: 100)
            } else if let error = model.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, minHeight: 100, alignment: .leading)
            }

            Divider()

            HStack {
                Button {
                    model.refresh()
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .buttonStyle(.plain)
                .disabled(model.isLoading)

                Spacer()

                Link("Open claude.ai ↗", destination: URL(string: "https://claude.ai/settings/usage")!)
                    .buttonStyle(.plain)

                Button("Quit") {
                    NSApplication.shared.terminate(nil)
                }
                .buttonStyle(.plain)
            }
            .font(.caption)
        }
        .frame(width: 320)
        .padding(16)
    }

    private func resetText(_ date: Date?) -> String {
        guard let date else { return "Resets —" }
        let remaining = max(0, Int(date.timeIntervalSinceNow / 60))
        let hours = remaining / 60
        let minutes = remaining % 60
        return hours > 0 ? "Resets in \(hours)h \(minutes)m" : "Resets in \(minutes)m"
    }
}

private struct UsageSection: View {
    let title: String
    let value: Double
    let reset: String

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .firstTextBaseline) {
                Text(title)
                    .font(.subheadline.weight(.medium))
                Spacer()
                Text("\(Int(value.rounded()))%")
                    .font(.title3.weight(.bold))
            }
            ProgressView(value: min(max(value, 0), 100), total: 100)
                .tint(value >= 80 ? .orange : .blue)
            Text(reset)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

@main
struct CaudeOClockApp: App {
    @StateObject private var model = UsageModel()

    var body: some Scene {
        MenuBarExtra {
            UsagePopover(model: model)
        } label: {
            Label(model.statusTitle, systemImage: "clock")
        }
        .menuBarExtraStyle(.window)
    }
}
